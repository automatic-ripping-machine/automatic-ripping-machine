"""ARM route blueprint for database pages."""

import os
import json
import re
from datetime import datetime
from pathlib import Path

from flask_login import LoginManager, login_required  # noqa: F401
from flask import render_template, request, Blueprint, flash, redirect, session, url_for, send_file
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

import arm.ui.utils as ui_utils
from arm.ui import app, db, constants
from arm.models.job import Job
import arm.config.config as cfg
from arm.ui.metadata import get_omdb_poster
from arm.ui.forms import DBUpdate, DatabaseBackupForm, DatabaseRestoreForm

app.app_context().push()
route_database = Blueprint('route_database', __name__,
                           template_folder='templates',
                           static_folder='../static')

# This attaches the armui_cfg globally to let the users use any bootswatch skin from cdn
armui_cfg = ui_utils.arm_db_cfg()


def _empty_pagination():
    class EmptyPagination:
        page = 1
        pages = 1
        prev_num = 1
        next_num = 1

        @staticmethod
        def iter_pages(*_args, **_kwargs):
            return []

    return EmptyPagination()


@route_database.route('/database')
@login_required
def view_database():
    """
    The main database page

    Outputs every job from the database
     this can cause serious slow-downs with + 3/4000 entries
    """
    # regenerate the armui_cfg we don't want old settings
    armui_cfg = ui_utils.arm_db_cfg()

    page = request.args.get('page', 1, type=int)
    app.logger.debug(armui_cfg)

    # Check for database file
    try:
        jobs_pagination = Job.query.order_by(db.desc(Job.job_id)).paginate(
            page=page,
            max_per_page=int(armui_cfg.database_limit),
            error_out=False
        )
        job_items = jobs_pagination.items
    except SQLAlchemyError as error:
        app.logger.error('ERROR: /database unable to query database: %s', error)
        jobs_pagination = _empty_pagination()
        job_items = []

    session["page_title"] = "Database"

    return render_template(
        'databaseview.html',
        jobs=job_items,
        pages=jobs_pagination,
        date_format=cfg.arm_config['DATE_FORMAT'],
    )


@route_database.route('/dbupdate', methods=['POST'])
def update_database():
    """
    Update the ARM database when changes are made or the arm db file is missing
    """
    form = DBUpdate(request.form)
    if request.method == 'POST' and form.validate():
        if form.dbfix.data == "migrate":
            app.logger.debug("User requested - Database migration")
            ui_utils.arm_db_migrate()
            flash("ARM database migration successful!", "success")
        elif form.dbfix.data == "new":
            app.logger.debug("User requested - New database")
            ui_utils.check_db_version(cfg.arm_config['INSTALLPATH'], cfg.arm_config['DBFILE'])
            flash("ARM database setup successful!", "success")
        else:
            # No method defined
            app.logger.debug(f"No update method defined from DB Update - {form.dbfix.data}")
            flash("Error no update method specified, report this as a bug.", "error")

        # Update the arm UI config from DB post update
        ui_utils.arm_db_cfg()

        return redirect('/index')
    else:
        # Catch for GET requests of the page, redirect to index
        return redirect('/index')


@route_database.route('/database/backup', methods=['POST'])
@login_required
def download_backup():
    """Create a fresh database backup and send it to the user."""

    form = DatabaseBackupForm()
    settings_db_tools_url = url_for('route_settings.settings') + '#databaseTools'
    if not form.validate_on_submit():
        flash('Invalid backup request submitted.', 'danger')
        return redirect(settings_db_tools_url)

    backup_path = ui_utils.arm_db_backup('manual')
    if not backup_path or not os.path.exists(backup_path):
        flash('Database backup could not be created.', 'danger')
        return redirect(settings_db_tools_url)

    try:
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=os.path.basename(backup_path),
            max_age=0,
        )
    except OSError as error:
        app.logger.error('Failed to stream backup %s: %s', backup_path, error)
        flash('Database backup was created but could not be downloaded.', 'danger')
        return redirect(settings_db_tools_url)


@route_database.route('/database/restore', methods=['POST'])
@login_required
def restore_database():
    """Restore the ARM database from an uploaded backup file."""

    form = DatabaseRestoreForm()
    settings_db_tools_url = url_for('route_settings.settings') + '#databaseTools'
    if not form.validate_on_submit():
        flash('Select a backup file before submitting.', 'danger')
        return redirect(settings_db_tools_url)

    file_storage = form.backup_file.data
    filename = secure_filename(file_storage.filename or '')
    if not filename:
        flash('The provided backup file is missing a valid name.', 'danger')
        return redirect(settings_db_tools_url)

    lower_name = filename.lower()
    if not lower_name.endswith(('.json', '.db')):
        flash('Unsupported backup format. Upload a .json or .db file.', 'danger')
        return redirect(settings_db_tools_url)

    backup_root = cfg.arm_config.get('DATABASE_BACKUP_PATH')
    if not backup_root:
        backup_root = os.path.join(cfg.arm_config['INSTALLPATH'], 'db', 'uploads')
    backup_dir = Path(backup_root)
    ui_utils.make_dir(str(backup_dir))

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stored_name = f"restore_{timestamp}_{filename}"
    stored_path = backup_dir / stored_name

    try:
        file_storage.save(stored_path)
    except OSError as error:
        app.logger.error('Unable to store uploaded backup %s: %s', stored_path, error)
        flash('Failed to save the uploaded backup. Check file permissions.', 'danger')
        return redirect(settings_db_tools_url)

    safety_backup = ui_utils.arm_db_backup('pre_restore')
    try:
        ui_utils.arm_db_restore(str(stored_path))
    except (OSError, SQLAlchemyError, json.JSONDecodeError, ValueError) as error:
        app.logger.error('Database restore failed using %s: %s', stored_path, error)
        flash('Database restore failed. Review the logs for details.', 'danger')
        return redirect(settings_db_tools_url)

    ui_utils.arm_db_cfg()
    message = f"Database restored from backup '{filename}'."
    if safety_backup:
        message += f" A safety backup was saved to '{safety_backup}'."
    flash(message, 'success')
    return redirect(settings_db_tools_url)


@route_database.route('/import_movies')
@login_required
def import_movies():
    """
    Function for finding all movies not currently tracked by ARM in the COMPLETED_PATH
    This should not be run frequently
    This causes a HUGE number of requests to OMdb\n
    :return: Outputs json - contains a dict/json of movies added and a notfound list
             that doesn't match ARM identified folder format.
    .. note:: This should eventually be moved to /json page load times are too long
    """
    my_path = cfg.arm_config['COMPLETED_PATH']
    app.logger.debug(my_path)
    movies = {0: {'notfound': {}}}
    i = 1
    movie_dirs = ui_utils.generate_file_list(my_path)
    app.logger.debug(movie_dirs)
    if len(movie_dirs) < 1:
        app.logger.debug("movie_dirs found none")

    for movie in movie_dirs:
        # will match 'Movie (0000)'
        regex = r"([\w\ \'\.\-\&\,]*?) \((\d{2,4})\)"
        # get our match
        matched = re.match(regex, movie)
        # if we can match the standard arm output format "Movie (year)"
        if matched:
            poster_image, imdb_id = get_omdb_poster(matched.group(1), matched.group(2))
            app.logger.debug(os.path.join(my_path, str(movie)))
            app.logger.debug(str(os.listdir(os.path.join(my_path, str(movie)))))
            movies[i] = ui_utils.import_movie_add(poster_image,
                                                  imdb_id, matched,
                                                  os.path.join(my_path, str(movie)))
        else:
            # If we didn't get a match assume that the directory is a main directory for other folders
            # This means we can check for "series" type movie folders e.g
            # - Lord of the rings
            #     - The Lord of the Rings The Fellowship of the Ring (2001)
            #     - The Lord of the Rings The Two Towers (2002)
            #     - The Lord of the Rings The Return of the King (2003)
            #
            sub_path = os.path.join(my_path, str(movie))
            # Go through each folder and treat it as a sub-folder of movie folder
            subfiles = ui_utils.generate_file_list(sub_path)
            for sub_movie in subfiles:
                sub_matched = re.match(regex, sub_movie)
                if sub_matched:
                    # Fix poster image and imdb_id
                    poster_image, imdb_id = get_omdb_poster(sub_matched.group(1), sub_matched.group(2))
                    app.logger.debug(os.listdir(os.path.join(sub_path, str(sub_movie))))
                    # Add the movies to the main movie dict
                    movies[i] = ui_utils.import_movie_add(poster_image,
                                                          imdb_id, sub_matched,
                                                          os.path.join(sub_path, str(sub_movie)))
                else:
                    movies[0]['notfound'][str(i)] = str(sub_movie)
            app.logger.debug(subfiles)
        i += 1
    app.logger.debug(movies)
    db.session.commit()
    movies = {k: v for k, v in movies.items() if v}
    return app.response_class(response=json.dumps(movies, indent=4, sort_keys=True),
                              status=200,
                              mimetype=constants.JSON_TYPE)
