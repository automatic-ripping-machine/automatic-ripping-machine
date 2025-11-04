"""
Batch Rename Utility Functions
Core logic for batch renaming TV series discs using disc labels.
This module provides preview, execute, and rollback operations and
maintains an audit trail via the BatchRenameHistory model.
"""

import os
import shutil
import logging
import uuid
import re
from datetime import datetime
from pathlib import Path

from arm.ui import db
from arm.models.job import Job
from arm.models.batch_rename_history import BatchRenameHistory
from arm.ripper.utils import (
    parse_disc_label_for_identifiers,
    normalize_series_name,
    fix_job_title,
)
import arm.config.config as cfg


def generate_batch_id():
    """Generate a unique batch ID for grouping related rename operations."""

    return str(uuid.uuid4())


def _validate_path_safety(path, base_directory=None):
    """
    Validate that a path is safe and within the allowed directory.
    Prevents path traversal attacks.

    Args:
        path: Path to validate
        base_directory: Optional base directory to restrict to (defaults to COMPLETED_PATH)

    Returns:
        Normalized, validated path

    Raises:
        ValueError: If path is invalid or contains traversal attempts
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Get base directory from config if not provided
    if base_directory is None:
        base_directory = cfg.arm_config.get('COMPLETED_PATH', '/home/arm/media/completed')

    # Sanitize inputs to prevent path traversal before resolving
    if '..' in str(path) or '..' in str(base_directory):
        raise ValueError("Path contains suspicious patterns")

    # Convert to absolute paths and resolve any symlinks
    try:
        base_path = Path(base_directory).resolve(strict=False)
        target_path = Path(path).resolve(strict=False)
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")

    # Ensure the target path is within the base directory
    try:
        target_path.relative_to(base_path)
    except ValueError:
        raise ValueError(f"Path traversal detected: {path} is outside allowed directory {base_directory}")

    # Check for suspicious patterns
    path_str = str(target_path)
    if '..' in path_str or path_str.startswith('/'):
        raise ValueError(f"Suspicious path pattern detected: {path}")

    return str(target_path)


def _prepare_preview_job(
    job,
    naming_style,
    zero_padded,
    consolidate,
    parent_folder,
    consistency,
    outlier_resolution,
    seen_paths,
    force_series_name=None,
):
    """Build preview data for a single job while enforcing path safety."""

    result = {
        'item': None,
        'errors': [],
        'conflicts': [],
        'skipped': False,
    }

    resolution_map = outlier_resolution or {}
    resolution = resolution_map.get(str(job.job_id))

    if resolution == 'skip':
        result['skipped'] = True
        return result

    # Use force_series_name if provided (from series selection)
    series_override = force_series_name
    if resolution == 'force' and not series_override:
        series_override = consistency.get('primary_series')

    name_result = compute_new_folder_name(
        job,
        naming_style,
        zero_padded,
        series_override,
    )

    old_path = job.path
    try:
        old_path = _validate_path_safety(old_path)
    except ValueError as err:
        result['errors'].append(
            f"Job {job.job_id}: Invalid path - {str(err)}"
        )
        return result

    old_folder_name = os.path.basename(old_path)
    new_folder_name = re.sub(r'[\\/]', '_', name_result['folder_name'])

    base_path = os.path.dirname(old_path)
    if consolidate and parent_folder:
        new_path = os.path.normpath(
            os.path.join(base_path, parent_folder, new_folder_name)
        )
    else:
        new_path = os.path.normpath(
            os.path.join(base_path, new_folder_name)
        )

    try:
        new_path = _validate_path_safety(new_path)
    except ValueError as err:
        result['errors'].append(
            f"Job {job.job_id}: Invalid target path - {str(err)}"
        )
        return result

    if new_path in seen_paths:
        result['conflicts'].append({
            'job_id': job.job_id,
            'new_path': new_path,
            'conflict_with': seen_paths[new_path],
            'reason': 'Duplicate target path',
        })
    elif os.path.exists(new_path) and new_path != old_path:
        result['conflicts'].append({
            'job_id': job.job_id,
            'new_path': new_path,
            'reason': 'Target path already exists',
        })

    seen_paths[new_path] = job.job_id

    result['item'] = {
        'job_id': job.job_id,
        'title': job.title,
        'label': job.label,
        'old_path': old_path,
        'new_path': new_path,
        'old_folder_name': old_folder_name,
        'new_folder_name': new_folder_name,
        'series_name': name_result['series_name'],
        'disc_identifier': name_result['disc_identifier'],
        'parse_success': name_result['parse_success'],
        'fallback': name_result['fallback'],
        'consolidated': consolidate,
        'parent_folder': parent_folder if consolidate else None,
    }

    return result


def _prepare_execute_paths(item):
    """Validate and, if needed, adjust rename paths for execution."""

    job_id = item['job_id']

    try:
        old_path = _validate_path_safety(item['old_path'])
        new_path = _validate_path_safety(item['new_path'])
    except ValueError as err:
        return None, None, None, f"Job {job_id}: Invalid path - {str(err)}"

    new_folder_name = item['new_folder_name']

    if os.path.exists(new_path) and new_path != old_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base, ext = os.path.splitext(new_path)
        adjusted_path = f'{base}_{timestamp}{ext}'
        try:
            adjusted_path = _validate_path_safety(adjusted_path)
        except ValueError as err:
            logging.error(f"Path validation failed for timestamped path: {err}")
            return (
                None,
                None,
                None,
                f"Job {job_id}: Invalid timestamped path - {str(err)}",
            )

        logging.warning(
            f'Conflict detected for {old_path}, using timestamped name: {adjusted_path}'
        )
        new_folder_name = os.path.basename(adjusted_path)
        new_path = adjusted_path

    return old_path, new_path, new_folder_name, None


def _ensure_parent_directory(new_path, job_id):
    """Ensure the parent directory exists for consolidated renames."""

    parent_path = os.path.dirname(new_path)
    try:
        parent_path = _validate_path_safety(parent_path)
    except ValueError as err:
        logging.error(f"Path validation failed for parent path: {err}")
        return f"Job {job_id}: Invalid parent path - {str(err)}"

    os.makedirs(parent_path, exist_ok=True)
    return None


def apply_naming_style(name, style='underscore'):
    """Apply naming style to a normalized series name.

    style options: 'underscore', 'hyphen', 'space'
    """

    if style == 'hyphen':
        return name.replace('_', '-').lower()
    if style == 'space':
        return name.replace('_', ' ')

    # Default: underscore
    return name


def apply_zero_padding(identifier, pad=False):
    """Apply zero-padding to disc identifier tokens (S, D, E)."""

    if not pad or not identifier:
        return identifier

    # Replace S1 with S01, D1 with D01, E1 with E01
    padded = re.sub(r'S(\d)(?=\D|$)', r'S0\1', identifier)
    padded = re.sub(r'D(\d)(?=\D|$)', r'D0\1', padded)
    padded = re.sub(r'E(\d)(?=\D|$)', r'E0\1', padded)
    return padded


def validate_job_selection(job_ids):
    """Validate that selected jobs exist and are suitable for renaming.

    Returns dict with keys: valid, jobs, errors, warnings.
    """

    result = {
        'valid': True,
        'jobs': [],
        'errors': [],
        'warnings': [],
    }

    if not job_ids:
        result['valid'] = False
        result['errors'].append('No jobs selected')
        return result

    for job_id in job_ids:
        try:
            job = Job.query.get(int(job_id))
            if not job:
                result['errors'].append(f'Job {job_id} not found')
                result['valid'] = False
                continue

            # Check completion status
            if job.status not in ('success', 'fail'):
                msg = (
                    f"Job {job_id} ({job.title}) is not completed "
                    f"(status: {job.status})"
                )
                result['warnings'].append(msg)

            # Check output path
            if not job.path or not os.path.exists(job.path):
                result['errors'].append(
                    f'Job {job_id} ({job.title}) has no valid output path'
                )
                result['valid'] = False
                continue

            # Check video type
            if job.video_type != 'series':
                result['warnings'].append(
                    f"Job {job_id} ({job.title}) is not a TV series "
                    f"(type: {job.video_type})"
                )

            result['jobs'].append(job)

        except Exception as exc:  # pragma: no cover - defensive
            msg = f'Error validating job {job_id}: {exc}'
            result['errors'].append(msg)
            result['valid'] = False

    return result


def detect_series_consistency(jobs):
    """Determine if all jobs belong to the same series.

    Prioritizes title_manual (custom lookup) over title/imdb_id for grouping.

    Returns dict: consistent (bool), primary_series, primary_series_id,
    outliers (list), series_groups (list of all detected series).
    """

    result = {
        'consistent': True,
        'primary_series': None,
        'primary_series_id': None,
        'outliers': [],
        'series_groups': [],
    }

    if not jobs:
        return result

    # Group by title_manual (if set), then imdb_id, then title
    series_map = {}
    series_metadata = {}

    for job in jobs:
        # Prioritize custom lookup name
        manual_title = getattr(job, 'title_manual', None)
        if manual_title and manual_title.strip():
            key = f"manual:{manual_title.strip()}"
            display_name = manual_title.strip()
            has_manual = True
        elif job.imdb_id:
            key = f"imdb:{job.imdb_id}"
            display_name = job.title or job.imdb_id
            has_manual = False
        else:
            key = f"title:{job.title}"
            display_name = job.title
            has_manual = False

        series_map.setdefault(key, []).append(job)

        # Store metadata for each series group
        if key not in series_metadata:
            series_metadata[key] = {
                'display_name': display_name,
                'imdb_id': job.imdb_id,
                'has_manual_title': has_manual,
                'key': key,
            }

    # Sort groups: manual titles first, then by size
    def sort_key(k):
        meta = series_metadata[k]
        return (
            1 if meta['has_manual_title'] else 0,  # Manual titles first
            len(series_map[k])  # Then by group size
        )

    sorted_keys = sorted(series_map.keys(), key=sort_key, reverse=True)
    primary_key = sorted_keys[0]
    primary_meta = series_metadata[primary_key]

    result['primary_series'] = primary_meta['display_name']
    result['primary_series_id'] = primary_meta['imdb_id']
    result['primary_series_key'] = primary_key

    # Build series_groups for frontend
    for key in sorted_keys:
        meta = series_metadata[key]
        job_list = series_map[key]
        result['series_groups'].append({
            'key': key,
            'display_name': meta['display_name'],
            'imdb_id': meta['imdb_id'],
            'has_manual_title': meta['has_manual_title'],
            'job_count': len(job_list),
            'job_ids': [j.job_id for j in job_list],
        })

    # Mark outliers (jobs not in primary group)
    result['consistent'] = len(series_map) == 1

    if not result['consistent']:
        for key, job_list in series_map.items():
            if key == primary_key:
                continue
            meta = series_metadata[key]
            for job in job_list:
                result['outliers'].append({
                    'job_id': job.job_id,
                    'title': meta['display_name'],
                    'imdb_id': job.imdb_id,
                    'label': job.label,
                    'series_key': key,
                })

    return result


def compute_new_folder_name(
    job, naming_style='underscore', zero_padded=False, force_series_name=None
):
    """Compute a proposed folder name for a job using the disc label.

    Returns dict with folder_name, series_name, disc_identifier, parse_success,
    and fallback flag.
    """

    result = {
        'folder_name': None,
        'series_name': None,
        'disc_identifier': None,
        'parse_success': False,
        'fallback': False,
    }

    # Determine series name (force override > manual > title)
    if force_series_name:
        series_name = force_series_name
    elif getattr(job, 'title_manual', None):
        series_name = job.title_manual
    else:
        series_name = job.title

    result['series_name'] = series_name

    # Parse disc identifier from label
    disc_identifier = parse_disc_label_for_identifiers(job.label)
    if disc_identifier:
        result['disc_identifier'] = disc_identifier
        result['parse_success'] = True

        if zero_padded:
            disc_identifier = apply_zero_padding(disc_identifier, True)
            result['disc_identifier'] = disc_identifier

        normalized_name = normalize_series_name(series_name)
        normalized_name = apply_naming_style(normalized_name, naming_style)

        result['folder_name'] = f"{normalized_name}_{disc_identifier}"
        return result

    # Fallback to existing naming
    result['fallback'] = True
    result['folder_name'] = fix_job_title(job)
    # Use f-string logging consistent with rest of codebase
    logging.warning(
        f"Could not parse disc label '{job.label}' for job {job.job_id}, using fallback naming"
    )

    return result


def compute_series_parent_folder(job, include_year=True):
    """Return the parent folder name for consolidation.

    Optionally include the year if available.
    """

    series_name = (
        job.title_manual if getattr(job, 'title_manual', None) else job.title
    )
    if include_year and job.year and job.year != '0000' and job.year != '':
        return f"{series_name} ({job.year})"

    return series_name


def preview_batch_rename(
    job_ids,
    naming_style='underscore',
    zero_padded=False,
    consolidate=False,
    include_year=True,
    outlier_resolution=None,
    selected_series_key=None,
    force_series_override=False,
):
    """Generate a preview of the batch rename operation.

    Returns a dict containing items, conflicts, warnings, errors, and series
    information.

    Args:
        selected_series_key: Key of the series to use for all jobs (from series selection UI)
        force_series_override: If True, force all jobs to use the selected series name
    """

    preview = {
        'valid': True,
        'items': [],
        'conflicts': [],
        'errors': [],
        'warnings': [],
        'series_info': {},
        'outliers': [],
        'requires_series_selection': False,
    }

    validation = validate_job_selection(job_ids)
    if not validation['valid']:
        preview['valid'] = False
        preview['errors'] = validation['errors']
        preview['warnings'] = validation['warnings']
        return preview

    jobs = validation['jobs']
    preview['warnings'].extend(validation['warnings'])

    consistency = detect_series_consistency(jobs)
    preview['series_info'] = consistency

    # Check if user needs to select a series
    if not consistency['consistent'] and not selected_series_key and not force_series_override:
        preview['requires_series_selection'] = True
        preview['outliers'] = consistency['outliers']
        preview['warnings'].append(
            f"Multiple series detected ({len(consistency['series_groups'])} groups). "
            "Please select which series to use for batch rename."
        )
        # Don't generate preview items yet - wait for user selection
        return preview

    # Determine which series name to use
    force_series_name = None
    if selected_series_key:
        # Find the selected series group
        selected_group = next(
            (g for g in consistency['series_groups'] if g['key'] == selected_series_key),
            None
        )
        if selected_group:
            force_series_name = selected_group['display_name']
            logging.info(
                f"Batch rename using selected series: {force_series_name} "
                f"(key: {selected_series_key})"
            )

    if not consistency['consistent']:
        preview['outliers'] = consistency['outliers']

    parent_folder = None
    if consolidate and jobs:
        # Use the first job from selected series or primary series
        primary_job = jobs[0]
        if force_series_name:
            # Override the job's title for parent folder calculation
            original_title = primary_job.title
            original_manual = getattr(primary_job, 'title_manual', None)
            primary_job.title = force_series_name
            primary_job.title_manual = force_series_name
            parent_folder = compute_series_parent_folder(primary_job, include_year)
            # Restore original values
            primary_job.title = original_title
            primary_job.title_manual = original_manual
        else:
            parent_folder = compute_series_parent_folder(primary_job, include_year)
        # Sanitize parent_folder to remove path separators
        parent_folder = re.sub(r'[\\/]', '_', parent_folder)
        preview['series_info']['parent_folder'] = parent_folder

    resolution_map = outlier_resolution or {}
    seen_paths = {}
    for job in jobs:
        job_result = _prepare_preview_job(
            job,
            naming_style,
            zero_padded,
            consolidate,
            parent_folder,
            consistency,
            resolution_map,
            seen_paths,
            force_series_name=force_series_name,
        )

        preview['errors'].extend(job_result['errors'])
        preview['conflicts'].extend(job_result['conflicts'])

        if job_result.get('skipped'):
            continue

        if job_result.get('item'):
            preview['items'].append(job_result['item'])

    if preview['conflicts']:
        preview['warnings'].append(
            f'Found {len(preview["conflicts"])} path conflicts. '
            'These will be resolved with timestamps.'
        )

    return preview


def execute_batch_rename(preview_data, batch_id, current_user_email):
    """Execute the batch rename operation based on preview data."""

    result = {
        'success': True,
        'renamed_count': 0,
        'failed_count': 0,
        'errors': [],
        'history_ids': [],
    }

    if not preview_data.get('valid') or not preview_data.get('items'):
        result['success'] = False
        result['errors'].append('Invalid preview data or no items to rename')
        return result

    for item in preview_data['items']:
        try:
            job_id = item['job_id']
            old_path, new_path, new_folder_name, path_error = _prepare_execute_paths(item)

            if path_error:
                result['failed_count'] += 1
                result['errors'].append(path_error)
                continue

            if item.get('consolidated') and item.get('parent_folder'):
                parent_error = _ensure_parent_directory(new_path, job_id)
                if parent_error:
                    result['failed_count'] += 1
                    result['errors'].append(parent_error)
                    continue

            shutil.move(old_path, new_path)
            logging.info(
                f"BATCH RENAME - Job {job_id}: "
                f"'{old_path}' -> '{new_path}' "
                f"(Series: {item.get('series_name', 'Unknown')})"
            )

            job = Job.query.get(job_id)
            if job:
                job.path = new_path
                db.session.add(job)

            history = BatchRenameHistory(
                batch_id=batch_id,
                job_id=job_id,
                old_path=old_path,
                new_path=new_path,
                old_folder_name=item['old_folder_name'],
                new_folder_name=new_folder_name,
                renamed_by=current_user_email,
                series_name=item.get('series_name'),
                disc_identifier=item.get('disc_identifier'),
                consolidated_under_series=item.get('consolidated'),
                series_parent_folder=item.get('parent_folder'),
                naming_style=preview_data.get('naming_style', 'underscore'),
                zero_padded=preview_data.get('zero_padded', False),
            )
            history.rename_success = True
            db.session.add(history)

            result['renamed_count'] += 1
            result['history_ids'].append(history.history_id)
            item['new_path'] = new_path
            item['new_folder_name'] = new_folder_name

        except Exception as exc:  # pragma: no cover - runtime errors logged
            error_msg = f"Failed to rename job {item['job_id']}: {str(exc)}"
            logging.error(error_msg)
            result['errors'].append(error_msg)
            result['failed_count'] += 1
            result['success'] = False

            try:
                history = BatchRenameHistory(
                    batch_id=batch_id,
                    job_id=item['job_id'],
                    old_path=item['old_path'],
                    new_path=item['new_path'],
                    old_folder_name=item['old_folder_name'],
                    new_folder_name=item['new_folder_name'],
                    renamed_by=current_user_email,
                    series_name=item.get('series_name'),
                    disc_identifier=item.get('disc_identifier'),
                )
                history.rename_success = False
                history.error_message = str(exc)
                db.session.add(history)
            except Exception as hist_err:  # pragma: no cover - defensive
                logging.error(
                    f'Failed to record history for failed rename: {hist_err}'
                )

    try:
        db.session.commit()
        logging.info(
            f"Batch rename completed: {result['renamed_count']} successful, {result['failed_count']} failed"
        )
    except Exception as exc:  # pragma: no cover - DB issues handled
        db.session.rollback()
        result['success'] = False
        result['errors'].append(f'Database commit failed: {str(exc)}')
        logging.error(f'Database commit failed during batch rename: {exc}')

    return result


def rollback_batch_rename(batch_id, current_user_email):
    """Rollback a batch rename operation using history records."""

    result = {
        'success': True,
        'rolled_back_count': 0,
        'failed_count': 0,
        'errors': [],
    }

    try:
        history_records = (
            BatchRenameHistory.query.filter_by(
                batch_id=batch_id, rolled_back=False, rename_success=True
            )
            .all()
        )

        if not history_records:
            result['success'] = False
            result['errors'].append(
                f'No records found for batch {batch_id} or already rolled back'
            )
            return result

        for record in reversed(history_records):
            try:
                if not os.path.exists(record.new_path):
                    result['errors'].append(
                        f'Cannot rollback job {record.job_id}: new path no longer exists'
                    )
                    result['failed_count'] += 1
                    continue

                shutil.move(record.new_path, record.old_path)
                logging.info(
                    f'Rolled back: {record.new_path} -> {record.old_path}'
                )

                job = Job.query.get(record.job_id)
                if job:
                    job.path = record.old_path
                    db.session.add(job)

                record.rolled_back = True
                record.rollback_at = datetime.utcnow()
                record.rollback_by = current_user_email
                db.session.add(record)

                result['rolled_back_count'] += 1

            except Exception as exc:  # pragma: no cover - runtime errors
                error_msg = (
                    f'Failed to rollback job {record.job_id}: {exc}'
                )
                logging.error(error_msg)
                result['errors'].append(error_msg)
                result['failed_count'] += 1
                result['success'] = False

        db.session.commit()
        logging.info(
            f"Rollback completed: {result['rolled_back_count']} reversed, {result['failed_count']} failed"
        )

    except Exception as exc:  # pragma: no cover - DB issues handled
        db.session.rollback()
        result['success'] = False
        result['errors'].append(f'Rollback failed: {exc}')
        logging.error(f'Rollback failed: {exc}')

    return result


def get_recent_batches(limit=10):
    """Return a list of recent batch operations with summary info."""

    try:
        batches = db.session.query(
            BatchRenameHistory.batch_id,
            db.func.max(BatchRenameHistory.renamed_at).label('latest_rename'),
            db.func.count(BatchRenameHistory.history_id).label('record_count'),
            db.func.sum(
                db.case(
                    [(BatchRenameHistory.rolled_back.is_(True), 1)], else_=0
                )
            ).label('rolled_back_count'),
        )
        batches = (
            batches.group_by(BatchRenameHistory.batch_id)
            .order_by(db.desc('latest_rename'))
            .limit(limit)
            .all()
        )

        result = []
        for batch in batches:
            sample_record = (
                BatchRenameHistory.query
                .filter_by(batch_id=batch.batch_id)
                .first()
            )

            fully_rolled_back = (
                batch.rolled_back_count == batch.record_count
            )
            partially_rolled_back = (
                batch.rolled_back_count > 0
                and batch.rolled_back_count < batch.record_count
            )

            result.append(
                {
                    'batch_id': batch.batch_id,
                    'renamed_at': batch.latest_rename,
                    'renamed_by': (
                        sample_record.renamed_by if sample_record else None
                    ),
                    'record_count': batch.record_count,
                    'rolled_back_count': batch.rolled_back_count,
                    'fully_rolled_back': fully_rolled_back,
                    'partially_rolled_back': partially_rolled_back,
                }
            )

        return result

    except Exception as exc:  # pragma: no cover - logging and return empty
        logging.error(f'Error getting recent batches: {exc}')
        return []
