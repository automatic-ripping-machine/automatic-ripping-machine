"""
API utility functions for jobs blueprint.

Contains helper functions for building API context objects
used in the JSON API endpoint.
"""

from flask import request

import arm.ui.utils as ui_utils
from arm.ui import json_api
from arm.models.job import JobState
import arm.config.config as cfg


def _build_authenticated_api_context(mode):
    """
    Build API context for authenticated users.

    Returns valid_data and valid_modes dictionaries containing
    available API operations and their handlers for authenticated users.

    :param mode: The API mode/operation requested
    :return: Tuple of (valid_data, valid_modes) dictionaries
    """
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
    """
    Build API context for public/unauthenticated users.

    Returns valid_data and valid_modes dictionaries containing
    limited API operations available to unauthenticated users.

    :param mode: The API mode/operation requested
    :return: Tuple of (valid_data, valid_modes) dictionaries
    """
    valid_data = {
        'joblist': 'joblist',
        'mode': mode,
    }
    valid_modes = {
        'joblist': {'funct': json_api.get_x_jobs, 'args': ('joblist',)},
    }
    return valid_data, valid_modes
