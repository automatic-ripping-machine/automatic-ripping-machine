"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Database

Covers
    - database [GET]
    - import_movies [JSON]
"""
from flask import current_app as app
from flask import render_template, request, flash, session
from flask_login import login_required
from sqlalchemy import desc, exc

import arm.config.config as cfg
from arm.models.job import Job
from arm.models.ui_settings import UISettings
from arm.ui.database import route_database


# todo: what is this used for?
# app.app_context().push()


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
