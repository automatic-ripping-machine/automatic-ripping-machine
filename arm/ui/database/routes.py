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
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import current_app as app

import config.config as cfg
from ui import db
from models.job import Job
# from models.track import Track
# from models.config import Config
from models.ui_settings import UISettings
from ui.database import route_database


# todo: what is this used for?
# app.app_context().push()

def get_session(bind_key=None):
    engine = db.get_engine(app,bind=bind_key)
    session_factory = sessionmaker(bind=engine)
    return scoped_session(session_factory)


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


@app.route('/databasemigrate')
@login_required
def database_migrate():
    """
    Migrate ARM jobs from SQLite to MYSQL Database
    User-driven option
    """
    error = False
    count = 0
    message = ""
    sqlite_data = None

    try:
        # Set the database to use sqlite
        arm_sqlite_db = Job.change_binds(bind_key='sqlite')
        sqlite_session = get_session(bind_key='sqlite')
        sqlite_data = sqlite_session.query(arm_sqlite_db).all()
        # app.logger.debug(sqlite_data)
        sqlite_session.remove()
    except exc.SQLAlchemyError as e:
        app.logger.error(f"ERROR: Unable to retrieve data from SQLite file. {e}")

    if sqlite_data:
        for sqlite_job in sqlite_data:
            mysql_job = Job(devpath = sqlite_job.devpath)

            mysql_job.arm_version = sqlite_job.arm_version
            mysql_job.crc_id = sqlite_job.crc_id
            mysql_job.logfile = sqlite_job.logfile
            mysql_job.start_time = sqlite_job.start_time
            mysql_job.stop_time = sqlite_job.stop_time
            mysql_job.job_length = sqlite_job.job_length
            mysql_job.status = sqlite_job.status
            mysql_job.stage = sqlite_job.stage
            mysql_job.no_of_titles = sqlite_job.no_of_titles
            mysql_job.title = sqlite_job.title
            mysql_job.title_auto = sqlite_job.title_auto
            mysql_job.title_manual = sqlite_job.title_manual
            mysql_job.year = sqlite_job.year
            mysql_job.year_auto = sqlite_job.year_auto
            mysql_job.year_manual = sqlite_job.year_manual
            mysql_job.video_type = sqlite_job.video_type
            mysql_job.video_type_auto = sqlite_job.video_type_auto
            mysql_job.video_type_manual = sqlite_job.video_type_manual
            mysql_job.imdb_id = sqlite_job.imdb_id
            mysql_job.imdb_id_auto = sqlite_job.imdb_id_auto
            mysql_job.imdb_id_manual = sqlite_job.imdb_id_manual
            mysql_job.poster_url = sqlite_job.poster_url
            mysql_job.poster_url_auto = sqlite_job.poster_url_auto
            mysql_job.poster_url_manual = sqlite_job.poster_url_manual
            # mysql_job.devpath = sqlite_job.devpath
            mysql_job.mountpoint = sqlite_job.mountpoint
            mysql_job.hasnicetitle = sqlite_job.hasnicetitle
            mysql_job.errors = sqlite_job.errors
            mysql_job.disctype = sqlite_job.disctype
            mysql_job.label = sqlite_job.label
            mysql_job.path = sqlite_job.path
            mysql_job.ejected = sqlite_job.ejected
            mysql_job.updated = sqlite_job.updated
            mysql_job.pid = sqlite_job.pid
            mysql_job.pid_hash = abs(sqlite_job.pid_hash)
            mysql_job.is_iso = sqlite_job.is_iso

            db.session.add(mysql_job)
            db.session.commit()

            count += 1

        message = f'Migrated {count} jobs from SQLite to MYSQL Database'
        app.logger.debug(message)
    else:
        error = True

    if error:
        flash("Error: Unable to migrate jobs.", category='info')
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
