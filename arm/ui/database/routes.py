"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Database

Covers
    - database [GET]
    - import_movies [JSON]
"""
from flask import render_template, request, flash, session, redirect
from flask_login import login_required
from sqlalchemy import desc, exc
from flask import current_app as app

from ui.database import route_database
from ui.database import utils
import config.config as cfg
from models.job import Job
from models.ui_settings import UISettings


@route_database.route('/database')
@login_required
def view_database():
    """
    Flask view:
        /database

    Outputs every job from the database
    Note: this can cause serious slow-downs with + 3/4000 entries
    """
    page = request.args.get('page', 1, type=int)
    armui_cfg = UISettings.query.first()

    try:
        jobs = Job.query.order_by(desc(Job.job_id)).paginate(page=page,
                                                             max_per_page=int(armui_cfg.database_limit),
                                                             error_out=False)
    except exc.SQLAlchemyError:
        flash("Unable to retrieve jobs.", category='error')
        app.logger.error("ERROR: Jobs database doesn't exist")
        jobs = {}

    session["page_title"] = "Database"

    return render_template('databaseview.html',
                           jobs=jobs.items,
                           pages=jobs,
                           date_format=cfg.arm_config['DATE_FORMAT'])


# Update to manage migrations of the database
# @route_database.route('/dbupdate', methods=['POST'])
# def update_database():
#     """
#     Update the ARM database when changes are made or the arm db file is missing
#     """
#     form = DBUpdate(request.form)
#     if request.method == 'POST' and form.validate():
#         if form.dbfix.data == "migrate":
#             app.logger.debug("User requested - Database migration")
#             ui_utils.arm_db_migrate()
#             flash("ARM database migration successful!", "success")
#         elif form.dbfix.data == "new":
#             app.logger.debug("User requested - New database")
#             ui_utils.check_db_version(cfg.arm_config['INSTALLPATH'], cfg.arm_config['DBFILE'])
#             flash("ARM database setup successful!", "success")
#         else:
#             # No method defined
#             app.logger.debug(f"No update method defined from DB Update - {form.dbfix.data}")
#             flash("Error no update method specified, report this as a bug.", "error")
#
#         # Update the arm UI config from DB post update
#         ui_utils.arm_db_cfg()
#
#         return redirect('/index')
#     else:
#         # Catch for GET requests of the page, redirect to index
#         return redirect('/index')


@app.route('/databasemigrate')
@login_required
def database_migrate():
    """
    Migrate ARM jobs from SQLite to MYSQL Database
    User-driven option
    """
    error: bool = False
    count: int = 0
    message: str = "Error: Unable to migrate jobs."

    # Check that the arm.db file exists before starting a migration
    file_exists = utils.check_sqlite_file(cfg.arm_config['DBFILE'])
    if not file_exists:
        error = True
        message = f"Unable to access arm.db sqlite database file. <br>Location {cfg.arm_config['DBFILE']}"

    # Migrate data from arm.db
    if not error:
        count = utils.migrate_data()
        message = f'Migrated {count} jobs from SQLite to MYSQL Database'
        app.logger.debug(message)
    else:
        error = True

    if error:
        flash(message, category='danger')
    else:
        flash(message, category='success')

    return redirect('/database')


# Todo: Is this feature still required? There is no call to the UI for Import Movies
# @route_database.route('/import_movies')
# @login_required
# def import_movies():
#     """
#     Function for finding all movies not currently tracked by ARM in the COMPLETED_PATH
#     This should not be run frequently
#     This causes a HUGE number of requests to OMdb\n
#     :return: Outputs json - contains a dict/json of movies added and a notfound list
#              that doesn't match ARM identified folder format.
#     .. note:: This should eventually be moved to /json page load times are too long
#     """
#     my_path = cfg.arm_config['COMPLETED_PATH']
#     app.logger.debug(my_path)
#     movies = {0: {'notfound': {}}}
#     i = 1
#     movie_dirs = ui_utils.generate_file_list(my_path)
#     app.logger.debug(movie_dirs)
#     if len(movie_dirs) < 1:
#         app.logger.debug("movie_dirs found none")
#
#     for movie in movie_dirs:
#         # will match 'Movie (0000)'
#         regex = r"([\w\ \'\.\-\&\,]*?) \((\d{2,4})\)"
#         # get our match
#         matched = re.match(regex, movie)
#         # if we can match the standard arm output format "Movie (year)"
#         if matched:
#             poster_image, imdb_id = get_omdb_poster(matched.group(1), matched.group(2))
#             app.logger.debug(os.path.join(my_path, str(movie)))
#             app.logger.debug(str(os.listdir(os.path.join(my_path, str(movie)))))
#             movies[i] = ui_utils.import_movie_add(poster_image,
#                                                   imdb_id, matched,
#                                                   os.path.join(my_path, str(movie)))
#         else:
#             # If we didn't get a match assume that the directory is a main directory for other folders
#             # This means we can check for "series" type movie folders e.g
#             # - Lord of the rings
#             #     - The Lord of the Rings The Fellowship of the Ring (2001)
#             #     - The Lord of the Rings The Two Towers (2002)
#             #     - The Lord of the Rings The Return of the King (2003)
#             #
#             sub_path = os.path.join(my_path, str(movie))
#             # Go through each folder and treat it as a sub-folder of movie folder
#             subfiles = ui_utils.generate_file_list(sub_path)
#             for sub_movie in subfiles:
#                 sub_matched = re.match(regex, sub_movie)
#                 if sub_matched:
#                     # Fix poster image and imdb_id
#                     poster_image, imdb_id = get_omdb_poster(sub_matched.group(1), sub_matched.group(2))
#                     app.logger.debug(os.listdir(os.path.join(sub_path, str(sub_movie))))
#                     # Add the movies to the main movie dict
#                     movies[i] = ui_utils.import_movie_add(poster_image,
#                                                           imdb_id, sub_matched,
#                                                           os.path.join(sub_path, str(sub_movie)))
#                 else:
#                     movies[0]['notfound'][str(i)] = str(sub_movie)
#             app.logger.debug(subfiles)
#         i += 1
#     app.logger.debug(movies)
#     db.session.commit()
#     movies = {k: v for k, v in movies.items() if v}
#     return app.response_class(response=json.dumps(movies, indent=4, sort_keys=True),
#                               status=200,
#                               mimetype=constants.JSON_TYPE)
