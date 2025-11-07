"""
ARM route blueprint for jobs pages
Covers
- jobdetail [GET]
- jobdetailload [POST]
- titlesearch [GET]
- custometitle [GET]
- gettitle / customtitle [GET]
- updatetitle [GET]
- activerips [GET]
- changeparams [GET]
- list_titles [GET]
- json [JSON GET]
"""

import json
from dataclasses import dataclass
from flask_login import LoginManager, login_required, current_user  # noqa: F401
from flask import render_template, request, Blueprint, flash, redirect, url_for
from werkzeug.routing import ValidationError

import arm.ui.utils as ui_utils
from arm.ui import app, db, constants, json_api
from arm.models.job import Job, JobState
from arm.models.notifications import Notifications
import arm.config.config as cfg
from arm.ui.forms import TitleSearchForm, ChangeParamsForm, TrackFormDynamic

route_jobs = Blueprint('route_jobs', __name__,
                       template_folder='templates',
                       static_folder='../static')


def _json_response(payload, status=200, *, indent=2, default=None, sort_keys=False):
    """Return a Flask JSON response using the shared ARM response class."""
    dumps_kwargs = {'indent': indent, 'sort_keys': sort_keys}
    if default is not None:
        dumps_kwargs['default'] = default
    response_body = json.dumps(payload, **dumps_kwargs)
    return app.response_class(
        response=response_body,
        status=status,
        mimetype=constants.JSON_TYPE,
    )


@route_jobs.route('/jobdetail')
@login_required
def jobdetail():
    """
    Page for showing in-depth details about a job

    Shows Job/Config/Track class details
    displays them in a clear and easy to ready format
    """
    manual_edit = False

    # Initialise form
    track_form = TrackFormDynamic()

    job_id = request.args.get('job_id')
    if (job := Job.query.get(job_id)) is None:
        raise ValueError('Job not found')

    # Check if a manual job, waiting for input and user has not provided input
    if job.manual_mode and job.status == JobState.MANUAL_WAIT_STARTED.value and not job.manual_start:
        manual_edit = True

    # Get Job and Track data
    tracks = job.tracks.all()
    track_form.track_ref.min_entries = len(tracks)
    app.logger.debug(f"Found [{len(tracks)}] tracks")
    track_form.track_ref.entries.clear()
    # Loop through each track entry and build the WTForms dynamically
    for track_row in tracks:
        track_form.track_ref.append_entry({'track_ref': track_row.track_id,
                                           'checkbox': track_row.process})
    # For Jobs that are not waiting and in manual mode, disable the process checkbox
    if not manual_edit:
        for entry in track_form.track_ref.entries:
            entry.checkbox.render_kw = {'disabled': 'disabled'}

    search_results = ui_utils.metadata_selector("get_details", job.title, job.year, job.imdb_id)

    if search_results and 'Error' not in search_results:
        job.plot = search_results['Plot'] if 'Plot' in search_results else "There was a problem getting the plot"
        job.background = search_results['background_url'] if 'background_url' in search_results else None

    return render_template('jobdetail.html',
                           jobs=job,
                           tracks=tracks,
                           s=search_results,
                           manual_edit=manual_edit,
                           form=track_form)


@route_jobs.route('/jobdetailload', methods=['POST'])
@login_required
def jobdetail_load():
    """
    Process updated track ID fields against a job and load to the ARM database if valid
    All data passed via POST
    """
    # Initialise form
    track_form = TrackFormDynamic()

    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)

    # Data passed back from webpage, process and update track fields
    if request.method == 'POST' and track_form.validate_on_submit():
        app.logger.debug(f"Job id [{job.job_id}]")
        app.logger.debug(f"Returned [{len(track_form.track_ref.entries)}] tracks")
        for track_row in track_form.track_ref.entries:
            # app.logger.debug(f"Track deets [{track_row}]")
            track_id = track_row.data['track_ref']
            checkbox_value = track_row.data['checkbox']
            app.logger.debug(f"Setting [{track_id}] to [{checkbox_value}]")

            db_track = job.tracks.filter_by(track_id=track_id).first()
            if db_track:
                db_track.process = checkbox_value
                db.session.commit()

        # Set job to ready
        job.manual_start = True
        db.session.commit()
        app.logger.debug(f"Setting [{job.job_id}] to [{job.manual_start}], lets get ripping")
        flash("Tracks was updated", "success")

    return redirect(url_for('route_jobs.jobdetail', job_id=job_id))


@route_jobs.route('/titlesearch')
@login_required
def title_search():
    """
    The initial search page
    """
    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    form = TitleSearchForm(request.args)
    if form.validate():
        flash(f'Search for {request.args.get("title")}, year={request.args.get("year")}', 'success')
        return redirect(url_for('route_jobs.list_titles', title=request.args.get("title"),
                                year=request.args.get("year"), job_id=job_id))
    return render_template('titlesearch.html', title='Update Title', form=form, job=job)


@route_jobs.route('/customTitle')
@login_required
def customtitle():
    """
    For setting custom title for series with multiple discs
    """
    job_id = request.args.get('job_id')
    ui_utils.job_id_validator(job_id)
    job = Job.query.get(job_id)
    form = TitleSearchForm(obj=job)
    if request.args.get("title"):
        args = {
            'title': request.args.get("title"),
            'title_manual': request.args.get("title"),
            'year': request.args.get("year")
        }
        notification = Notifications(f"Job: {job.job_id} was updated",
                                     f'Title: {job.title} ({job.year}) was updated to '
                                     f'{request.args.get("title")} ({request.args.get("year")})')
        db.session.add(notification)
        ui_utils.database_updater(args, job)
        flash(f'Custom title changed. Title={job.title}, Year={job.year}.', "success")
        return redirect(url_for('home'))
    return render_template('customTitle.html', title='Change Title', form=form, job=job)


@route_jobs.route('/gettitle')
@route_jobs.route('/select_title')
@login_required
def gettitle():
    """
    Used to display plot info from the search result page when the user clicks the title
    and to forward the user to save the selected details

    This was also used previously for the getdetails page but it no longer needed there
    """
    imdb_id = request.args.get('imdbID').strip() if request.args.get('imdbID') else None
    job_id = request.args.get('job_id').strip() if request.args.get('job_id') else None
    if imdb_id == "" or imdb_id is None:
        app.logger.debug("gettitle - no imdb supplied")
        flash("No imdb supplied", "danger")
        raise ValidationError("No imdb supplied")
    if job_id == "" or job_id is None:
        app.logger.debug("gettitle - no job supplied")
        flash(constants.NO_JOB, "danger")
        raise ValidationError(constants.NO_JOB)
    dvd_info = ui_utils.metadata_selector("get_details", None, None, imdb_id)
    return render_template('showtitle.html', results=dvd_info, job_id=job_id)


@route_jobs.route('/updatetitle')
@login_required
def updatetitle():
    """
    used to save the details from the search
    Example URL
    updatetitle?title=Home&amp;year=2015&amp;imdbID=tt2224026&amp;type=movie&amp;
    poster=http://image.tmdb.org/t/p/original/usFenYnk6mr8C62dB1MoAfSWMGR.jpg&amp;job_id=109

    args
    title - new movie title
    year - new movie year
    imdbID - new movie IMDB reference
    type - new movie type
    poster - new movie poster URL
    job_id - job to update
    """
    #

    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    old_title = job.title
    old_year = job.year
    app.logger.debug(f"Old Title and Year: {old_title}, {old_year}")

    app.logger.debug(f"New Title: {request.args.get('title')}")
    new_title = ui_utils.clean_for_filename(request.args.get('title'))
    app.logger.debug(f"Cleaned New Title: {new_title}")
    job.title = job.title_manual = new_title

    app.logger.debug(f"New Year: {request.args.get('year')}")
    app.logger.debug(f"New Type: {request.args.get('type')}")
    app.logger.debug(f"New IMDB: {request.args.get('imdbID')}")
    app.logger.debug(f"New Poster: {request.args.get('poster')}")

    job.year = job.year_manual = request.args.get('year')
    job.video_type = job.video_type_manual = request.args.get('type')
    job.imdb_id = job.imdb_id_manual = request.args.get('imdbID')
    job.poster_url = job.poster_url_manual = request.args.get('poster')

    job.hasnicetitle = True
    notification = Notifications(f"Job: {job.job_id} was updated",
                                 f'Title: {old_title} ({old_year}) was updated to '
                                 f'{request.args.get("title")} ({request.args.get("year")})')
    db.session.add(notification)
    db.session.commit()
    flash(f'Title: {old_title} ({old_year}) was updated to '
          f'{request.args.get("title")} ({request.args.get("year")})', "success")
    return redirect("/")


@route_jobs.route('/activerips')
@login_required
def rips():
    """
    This no longer works properly because of the 'transcoding' status
    """
    active_jobs = Job.query.filter_by(~Job.finished)
    return render_template('activerips.html', jobs=active_jobs)


@route_jobs.route('/changeparams')
@login_required
def changeparams():
    """
    For updating Config params or changing/correcting job.disctype manually
    """
    config_id = request.args.get('config_id')
    job = Job.query.get(config_id)
    config = job.config
    form = ChangeParamsForm(obj=config)
    return render_template('changeparams.html', title='Change Parameters', form=form, config=config)


@route_jobs.route('/list_titles')
@login_required
def list_titles():
    """
    The search results page

    This will display the returned search results from OMDB or TMDB from the users input search
    """
    title = request.args.get('title').strip() if request.args.get('title') else ''
    year = request.args.get('year').strip() if request.args.get('year') else ''
    job_id = request.args.get('job_id').strip() if request.args.get('job_id') else ''
    if job_id == "":
        app.logger.debug("list_titles - no job supplied")
        flash(constants.NO_JOB, "danger")
        raise ValidationError
    job = Job.query.get(job_id)
    form = TitleSearchForm(obj=job)
    search_results = ui_utils.metadata_selector("search", title, year)
    if search_results is None or 'Error' in search_results or (
            'Search' in search_results and len(search_results['Search']) < 1):
        app.logger.debug("No results found. Trying without year")
        flash(f"No search results found for {title} ({year})<br/> Trying without year", 'danger')
        search_results = ui_utils.metadata_selector("search", title, "")

    if search_results is None or 'Error' in search_results or (
            'Search' in search_results and len(search_results['Search']) < 1):
        flash(f"No search results found for {title}", 'danger')
    return render_template('list_titles.html', results=search_results, job_id=job_id,
                           form=form, title=title, year=year)


def _build_authenticated_api_context(mode):
    valid_data = {
        'j_id': request.args.get('job'),
        'searchq': request.args.get('q'),
        'logpath': cfg.arm_config['LOGPATH'],
        'fail': 'fail',
        'success': 'success',
        'joblist': 'joblist',
        'mode': mode,
        'config_id': request.args.get('config_id'),
        'notify_id': request.args.get('notify_id'),
        'notify_timeout': {'funct': json_api.get_notify_timeout, 'args': ('notify_timeout',)},
        'restart': {'funct': json_api.restart_ui, 'args': ()},
    }

    valid_modes = {
        'delete': {'funct': json_api.delete_job, 'args': ('j_id', 'mode')},
        'abandon': {'funct': json_api.abandon_job, 'args': ('j_id',)},
        'full': {'funct': json_api.generate_log, 'args': ('logpath', 'j_id')},
        'search': {'funct': json_api.search, 'args': ('searchq',)},
        'getfailed': {
            'funct': json_api.get_x_jobs,
            'args': (JobState.FAILURE.value,),
        },
        'getsuccessful': {
            'funct': json_api.get_x_jobs,
            'args': (JobState.SUCCESS.value,),
        },
        'fixperms': {'funct': ui_utils.fix_permissions, 'args': ('j_id',)},
        'joblist': {'funct': json_api.get_x_jobs, 'args': ('joblist',)},
        'send_item': {'funct': ui_utils.send_to_remote_db, 'args': ('j_id',)},
        'change_job_params': {'funct': json_api.change_job_params, 'args': ('config_id',)},
        'read_notification': {'funct': json_api.read_notification, 'args': ('notify_id',)},
        'notify_timeout': {'funct': json_api.get_notify_timeout, 'args': ('notify_timeout',)},
    }

    return valid_data, valid_modes


def _build_public_api_context(mode):
    valid_data = {
        'joblist': 'joblist',
        'mode': mode,
    }
    valid_modes = {
        'joblist': {'funct': json_api.get_x_jobs, 'args': ('joblist',)},
    }
    return valid_data, valid_modes


def _get_api_context(authenticated, mode):
    if authenticated:
        return _build_authenticated_api_context(mode)
    return _build_public_api_context(mode)


@route_jobs.route('/json', methods=['GET'])
def feed_json():
    """
    json mini API
    This is used for all api/ajax calls this makes thing easier to read/code for
    Adding a new function to the api is as simple as adding a new elif where GET[mode]
    is your call
    You can then add a function inside utils to deal with the request
    """
    authenticated = ui_utils.authenticated_state()
    mode = str(request.args.get('mode'))
    valid_data, valid_modes = _get_api_context(authenticated, mode)

    response_payload = {'mode': mode, 'success': False}

    handler = valid_modes.get(mode)
    if handler:
        args = [valid_data[arg] for arg in handler['args']]
        handler_response = handler['funct'](*args)
        if handler_response is not None:
            response_payload = handler_response

    response_payload['notes'] = json_api.get_notifications()
    return _json_response(response_payload, indent=4, sort_keys=True)


def _extract_batch_options(data):
    return {
        'job_ids': data.get('job_ids', []),
        'naming_style': data.get('naming_style', 'underscore'),
        'zero_padded': data.get('zero_padded', False),
        'consolidate': data.get('consolidate', False),
        'include_year': data.get('include_year', True),
        'outlier_resolution': data.get('outlier_resolution', {}),
        'selected_series_key': data.get('selected_series_key'),
        'force_series_override': data.get('force_series_override', False),
        'custom_series_name': data.get('custom_series_name'),
    }


def _prepare_preview_payload(br_module, options):
    preview = br_module.preview_batch_rename(**options)
    preview['naming_style'] = options['naming_style']
    preview['zero_padded'] = options['zero_padded']
    return preview


def _batch_preview(br_module, options):
    preview = _prepare_preview_payload(br_module, options)
    return _json_response(preview, default=str)


def _batch_execute(br_module, data, options, user_email):
    batch_id = data.get('batch_id') or br_module.generate_batch_id()
    preview = _prepare_preview_payload(br_module, options)

    result = br_module.execute_batch_rename(
        preview_data=preview,
        batch_id=batch_id,
        current_user_email=user_email,
    )
    result['batch_id'] = batch_id
    status = 200 if result.get('success') else 500
    return _json_response(result, status=status, default=str)


def _batch_rollback(br_module, data, user_email):
    batch_id = data.get('batch_id')
    if not batch_id:
        return _json_response(
            {'success': False, 'error': 'batch_id is required for rollback'},
            status=400,
        )

    result = br_module.rollback_batch_rename(
        batch_id=batch_id,
        current_user_email=user_email,
    )
    status = 200 if result.get('success') else 500
    return _json_response(result, status=status, default=str)


def _batch_recent(br_module, data):
    limit = data.get('limit', 10)
    batches = br_module.get_recent_batches(limit=limit)
    return _json_response({'success': True, 'batches': batches}, default=str)


def _resolve_user_email():
    if current_user and current_user.is_authenticated:
        return current_user.email
    return 'unknown'


@route_jobs.route('/batch_rename', methods=['POST'])
@login_required
def batch_rename_api():
    """
    Batch rename API endpoint for TV series disc folders

    Supports three actions:
    - 'preview': Generate preview of rename operation
    - 'execute': Perform the batch rename
    - 'rollback': Undo a previous batch rename

    Expected JSON payload for 'preview' and 'execute':
    {
        "action": "preview" | "execute",
        "job_ids": [1, 2, 3, ...],
        "naming_style": "underscore" | "hyphen" | "space",
        "zero_padded": true | false,
        "consolidate": true | false,
        "include_year": true | false,
        "outlier_resolution": {"job_id": "force" | "override" | "skip"},
        "batch_id": "uuid" (only for execute)
    }

    Expected JSON payload for 'rollback':
    {
        "action": "rollback",
        "batch_id": "uuid"
    }
    """
    from arm.ui import batch_rename as br

    try:
        data = request.get_json() or {}
    except Exception as exc:
        app.logger.error(f"Batch rename API payload error: {exc}", exc_info=True)
        return _json_response(
            {'success': False, 'error': 'Invalid JSON payload'},
            status=400,
        )

    action = data.get('action')
    user_email = _resolve_user_email()
    options = _extract_batch_options(data)

    handlers = {
        'preview': lambda: _batch_preview(br, options),
        'execute': lambda: _batch_execute(br, data, options, user_email),
        'rollback': lambda: _batch_rollback(br, data, user_email),
        'recent_batches': lambda: _batch_recent(br, data),
    }

    handler = handlers.get(action)
    if not handler:
        return _json_response(
            {'success': False, 'error': f'Unknown action: {action}'},
            status=400,
        )

    try:
        return handler()
    except Exception as exc:
        app.logger.error(f"Batch rename API error: {exc}", exc_info=True)
        return _json_response(
            {'success': False, 'error': 'An error occurred during batch rename operation'},
            status=500,
        )


def _process_tmdb_search_result(item, video_type):
    """Process a single TMDB search result item."""
    item_type = item.get('media_type', '')
    if not item_type:
        if 'title' in item:
            item_type = 'movie'
        elif 'name' in item:
            item_type = 'series'

    # Filter by video type
    if video_type == 'series' and item_type != 'series':
        return None
    if video_type == 'movie' and item_type != 'movie':
        return None

    # Get title and year
    if item_type == 'movie':
        title = item.get('title', 'Unknown')
        release_date = item.get('release_date', '')
        year = release_date[:4] if release_date else ''
    else:
        title = item.get('name', 'Unknown')
        first_air = item.get('first_air_date', '')
        year = first_air[:4] if first_air else ''

    # Get poster URL
    poster_path = item.get('poster_path', '')
    poster_url = (
        f"https://image.tmdb.org/t/p/w500{poster_path}"
        if poster_path else ''
    )

    return {
        'title': title,
        'year': year,
        'type': item_type,
        'imdb_id': item.get('imdb_id', ''),
        'tmdb_id': item.get('id', ''),
        'poster_url': poster_url,
        'plot': item.get('overview', '')
    }


def _process_omdb_search_result(item, video_type):
    """Process a single OMDb search result item."""
    item_type = item.get('Type', '').lower()

    # Filter by video type
    if video_type == 'series' and item_type != 'series':
        return None
    if video_type == 'movie' and item_type != 'movie':
        return None

    return {
        'title': item.get('Title', 'Unknown'),
        'year': item.get('Year', ''),
        'type': item.get('Type', ''),
        'imdb_id': item.get('imdbID', ''),
        'poster_url': item.get('Poster', ''),
        'plot': ''
    }


def _search_tmdb_provider(metadata, query, year, video_type):
    """Search TMDB provider and return processed results."""
    results = []
    search_results = metadata.tmdb_search(query, year)
    if search_results and 'results' in search_results:
        for item in search_results['results'][:10]:
            result = _process_tmdb_search_result(item, video_type)
            if result:
                results.append(result)
    return results


def _search_omdb_provider(metadata, query, year, video_type):
    """Search OMDb provider and return processed results."""
    results = []
    search_results = metadata.call_omdb_api(
        title=query,
        year=year if year else None
    )
    if search_results and 'Search' in search_results:
        for item in search_results['Search'][:10]:
            result = _process_omdb_search_result(item, video_type)
            if result:
                results.append(result)
    return results


def _search_metadata(query, video_type, year, provider, metadata):
    """Search metadata provider and return results."""
    if provider == 'tmdb':
        return _search_tmdb_provider(metadata, query, year, video_type)
    if provider == 'omdb':
        return _search_omdb_provider(metadata, query, year, video_type)
    return []


class CustomLookupRequestError(Exception):
    """Raised when the custom lookup request payload is invalid."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class CustomLookupApplyPayload:
    job_ids: list
    title: str
    year: str
    video_type: str
    imdb_id: str
    poster_url: str


def _assign_custom_lookup_metadata(job, title, year, video_type, imdb_id, poster_url):
    job.title = title
    job.title_manual = title
    job.year = year
    job.video_type = video_type
    job.imdb_id = imdb_id
    job.poster_url = poster_url
    job.hasnicetitle = True


def _determine_target_base(video_type):
    import os

    completed_path = cfg.arm_config.get('COMPLETED_PATH', '/home/arm/media/completed')
    folder_map = {'series': 'tv', 'movie': 'movies'}
    return os.path.join(completed_path, folder_map.get(video_type, 'unidentified'))


def _move_job_folder_if_needed(job, old_video_type, new_video_type, old_path):
    import os
    import shutil
    from datetime import datetime

    if old_video_type == new_video_type or not old_path or not os.path.exists(old_path):
        return False, old_path, None

    target_base = _determine_target_base(new_video_type)
    os.makedirs(target_base, exist_ok=True)

    folder_name = os.path.basename(old_path)
    new_path = os.path.join(target_base, folder_name)

    if os.path.exists(new_path) and new_path != old_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_path = os.path.join(target_base, f"{folder_name}_{timestamp}")
        app.logger.warning(
            f"Folder conflict detected, using timestamped name: {new_path}"
        )

    if new_path == old_path:
        return False, old_path, None

    try:
        shutil.move(old_path, new_path)
        job.path = new_path
        return True, new_path, None
    except Exception as exc:
        app.logger.error(
            f"Failed to move folder for job {job.job_id if hasattr(job, 'job_id') else 'unknown'}: {exc}",
            exc_info=True,
        )
        return False, old_path, str(exc)


def _apply_custom_lookup_to_job(job_id, title, year, video_type, imdb_id, poster_url):
    job = Job.query.get(int(job_id))
    if not job:
        return None, f'Job {job_id} not found'

    old_video_type = job.video_type
    old_path = job.path

    _assign_custom_lookup_metadata(job, title, year, video_type, imdb_id, poster_url)
    moved, new_path, move_error = _move_job_folder_if_needed(
        job,
        old_video_type,
        video_type,
        old_path,
    )

    if moved:
        app.logger.info(
            f"Moved job {job_id} from {old_video_type} to {video_type}: {old_path} -> {new_path}"
        )

    result = {
        'job_id': job_id,
        'title': title,
        'year': year,
        'type': video_type,
        'moved': moved,
        'old_path': old_path if moved else None,
        'new_path': new_path if moved else None,
    }

    if move_error:
        message = f'Job {job_id}: Metadata updated but folder move failed - {move_error}'
        return result, message

    return result, None


def _process_single_job_lookup(job_id, title, year, video_type, imdb_id, poster_url):
    """Process custom lookup for a single job and return result tuple."""
    try:
        job_result, job_error = _apply_custom_lookup_to_job(
            job_id,
            title,
            year,
            video_type,
            imdb_id,
            poster_url,
        )
        return job_result, job_error
    except Exception as exc:
        app.logger.error(f"Error updating job {job_id}: {exc}", exc_info=True)
        return None, f'Job {job_id}: Failed to apply custom lookup'


def _apply_custom_lookup_to_jobs(job_ids, title, year, video_type,
                                 imdb_id, poster_url):
    """Apply custom identification metadata to selected jobs."""

    updated_jobs = []
    errors = []

    for job_id in job_ids:
        job_result, job_error = _process_single_job_lookup(
            job_id, title, year, video_type, imdb_id, poster_url
        )
        if job_result:
            updated_jobs.append(job_result)
        if job_error:
            errors.append(job_error)

    return updated_jobs, errors


def _parse_custom_lookup_payload():
    try:
        return request.get_json() or {}
    except Exception as exc:
        app.logger.error(f"Batch custom lookup payload error: {exc}", exc_info=True)
        raise CustomLookupRequestError('Invalid request payload', status=400) from exc


def _handle_custom_lookup_action(metadata_module, data):
    action = data.get('action')
    if action == 'search':
        return _custom_lookup_search(metadata_module, data)
    if action == 'apply':
        return _custom_lookup_apply(data)
    raise CustomLookupRequestError(f'Unknown action: {action}', status=400)


def _custom_lookup_error(message, status=400):
    return _json_response({'success': False, 'error': message}, status=status)


def _custom_lookup_search(metadata_module, data):
    query = (data.get('query') or '').strip()
    if not query:
        return _custom_lookup_error('Search query is required', status=400)

    video_type = data.get('video_type', 'series')
    year = data.get('year', '')

    provider = cfg.arm_config.get('METADATA_PROVIDER', 'tmdb').lower()
    app.logger.info(
        "Custom lookup search: query='%s', type=%s, provider=%s",
        query,
        video_type,
        provider,
    )

    results = _search_metadata(query, video_type, year, provider, metadata_module)
    return _json_response(
        {'success': True, 'results': results, 'provider': provider},
        default=str,
    )


def _parse_apply_payload(data):
    job_ids = data.get('job_ids') or []
    if not job_ids:
        raise CustomLookupRequestError('No jobs selected', status=400)

    title = (data.get('title') or '').strip()
    if not title:
        raise CustomLookupRequestError('Title is required', status=400)

    return CustomLookupApplyPayload(
        job_ids=job_ids,
        title=title,
        year=data.get('year', ''),
        video_type=data.get('video_type', 'series'),
        imdb_id=data.get('imdb_id', ''),
        poster_url=data.get('poster_url', ''),
    )


def _commit_custom_lookup_changes(updated_jobs, title, video_type):
    if not updated_jobs:
        return None

    try:
        db.session.commit()
        app.logger.info(
            "Custom lookup applied to %d jobs: %s (%s)",
            len(updated_jobs),
            title,
            video_type,
        )
    except Exception as exc:
        db.session.rollback()
        app.logger.error(f"Database commit error: {exc}", exc_info=True)
        return _custom_lookup_error('Failed to save changes to database', status=500)

    return None


def _build_custom_lookup_response(updated_jobs, errors):
    return _json_response(
        {
            'success': True,
            'updated_count': len(updated_jobs),
            'updated_jobs': updated_jobs,
            'errors': errors,
        },
        default=str,
    )


def _custom_lookup_apply(data):
    try:
        payload = _parse_apply_payload(data)
    except CustomLookupRequestError as err:
        return _custom_lookup_error(str(err), status=err.status)

    updated_jobs, errors = _apply_custom_lookup_to_jobs(
        payload.job_ids,
        payload.title,
        payload.year,
        payload.video_type,
        payload.imdb_id,
        payload.poster_url,
    )

    commit_error = _commit_custom_lookup_changes(
        updated_jobs,
        payload.title,
        payload.video_type,
    )
    if commit_error:
        return commit_error

    return _build_custom_lookup_response(updated_jobs, errors)


@route_jobs.route('/batch_custom_lookup', methods=['POST'])
@login_required
def batch_custom_lookup_api():
    """
    Custom identification lookup API for batch operations.

    Supports two actions:
    - 'search': Search for title in TMDB/OMDb
    - 'apply': Apply custom identification to selected jobs

    Expected JSON payload for 'search':
    {
        "action": "search",
        "query": "Breaking Bad",
        "video_type": "series" | "movie",
        "year": "2008" (optional)
    }

    Expected JSON payload for 'apply':
    {
        "action": "apply",
        "job_ids": [1, 2, 3, ...],
        "title": "Breaking Bad",
        "year": "2008",
        "video_type": "series",
        "imdb_id": "tt0903747",
        "poster_url": "https://..."
    }
    """
    import arm.ui.metadata as metadata

    try:
        data = _parse_custom_lookup_payload()
        return _handle_custom_lookup_action(metadata, data)
    except CustomLookupRequestError as err:
        return _custom_lookup_error(str(err), status=err.status)
    except Exception as exc:
        app.logger.error(f"Batch custom lookup API error: {exc}", exc_info=True)
        return _custom_lookup_error(
            'An error occurred during custom lookup operation',
            status=500,
        )
