"""
ARM Forms Functions for:
    Authentication

Functions
    - SettingsForm
    - UiSettingsForm
    - AbcdeForm
    - SystemInfoDrives
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import DataRequired


class SettingsForm(FlaskForm):
    """
    A form for updating system settings in the application.

    This form is used to capture and validate settings related to the application's configuration.
    It includes fields for various paths and settings, and ensures that all required fields are filled in.

    Fields:
        MANUAL_WAIT (StringField): Represents whether manual wait is enabled.
        DATE_FORMAT (StringField): The format for displaying dates.
        HB_PRESET_DVD (StringField): The HandBrake preset for DVDs.
        HB_PRESET_BD (StringField): The HandBrake preset for Blu-rays.
        HANDBRAKE_CLI (StringField): The path to the HandBrake CLI executable.
        DBFILE (StringField): The path to the database file.
        LOGPATH (StringField): The path where log files are stored.
        INSTALLPATH (StringField): The path where the application is installed.
        RAW_PATH (StringField): The path to raw files.
        TRANSCODE_PATH (StringField): The path for transcoding files.
        COMPLETED_PATH (StringField): The path for completed files.

    Methods:
        validate_on_submit: Validates the form and checks if it was submitted.
        submit: Submit button to apply the settings changes.

    Usage:
        This form is used on the '/settings' page of the application to allow users to update system settings.
    """
    MANUAL_WAIT = StringField('MANUAL_WAIT', validators=[DataRequired()])
    DATE_FORMAT = StringField('DATE_FORMAT', validators=[DataRequired()])
    HB_PRESET_DVD = StringField('HB_PRESET_DVD', validators=[DataRequired()])
    HB_PRESET_BD = StringField('HB_PRESET_BD', validators=[DataRequired()])
    HANDBRAKE_CLI = StringField('HANDBRAKE_CLI', validators=[DataRequired()])
    DBFILE = StringField('DBFILE', validators=[DataRequired()])
    LOGPATH = StringField('LOGPATH', validators=[DataRequired()])
    INSTALLPATH = StringField('INSTALLPATH', validators=[DataRequired()])
    RAW_PATH = StringField('RAW_PATH', validators=[DataRequired()])
    TRANSCODE_PATH = StringField('TRANSCODE_PATH', validators=[DataRequired()])
    COMPLETED_PATH = StringField('COMPLETED_PATH', validators=[DataRequired()])
    submit = SubmitField('Submit')


class UiSettingsForm(FlaskForm):
    """
    A form for configuring user interface settings.

    This form is used to capture and validate various UI settings that can be adjusted by the user.

    Fields:
        index_refresh (IntegerField): The interval (in seconds) for refreshing the index.
        use_icons (StringField): Option to enable or disable the use of icons in the UI.
        save_remote_images (StringField): Option to save images from remote sources.
        bootstrap_skin (StringField): The theme or skin for Bootstrap styling.
        language (StringField): The language setting for the UI.
        database_limit (IntegerField): The maximum number of entries allowed in the database.
        notify_refresh (IntegerField): The interval (in seconds) for refreshing notifications.
        submit (SubmitField): A button to submit the form.

    Validators:
        - `DataRequired()`: Ensures that the fields `index_refresh`, `bootstrap_skin`, `language`,
                `database_limit`, and `notify_refresh` are provided.

    Usage:
        This form is utilized on the following page:
          - '/settings': To adjust and save user interface settings.

    Note:
        Fields not explicitly marked with `DataRequired()` are optional and may be left empty.
    """
    index_refresh = IntegerField('index_refresh', validators=[DataRequired()])
    use_icons = StringField('use_icons')
    save_remote_images = StringField('save_remote_images')
    bootstrap_skin = StringField('bootstrap_skin', validators=[DataRequired()])
    language = StringField('language', validators=[DataRequired()])
    database_limit = IntegerField('database_limit', validators=[DataRequired()])
    notify_refresh = IntegerField('notify_refresh', validators=[DataRequired()])
    submit = SubmitField('Submit')


class AbcdeForm(FlaskForm):
    """
    Form for configuring ABCDE settings.

    This form is used to input and validate configuration settings for ABCDE.

    Fields:
        abcdeConfig (StringField): The configuration string for ABCDE. This field is required.
        submit (SubmitField): A button to submit the form.

    Validators:
        - `DataRequired()`: Ensures that the `abcdeConfig` field is provided.

    Usage:
        This form is used on the following page:
          - '/settings': To configure ABCDE settings.

    Note:
        The `abcdeConfig` field must be filled out before submitting the form.
    """
    abcdeConfig = StringField('abcdeConfig', validators=[DataRequired()])
    submit = SubmitField('Submit')


class SystemInfoDrives(FlaskForm):
    """
    Form for updating system drive information.

    This form allows users to input and validate information related to system drives,
    including updating the drive's nickname and description.

    Fields:
        id (IntegerField): The unique identifier for the system drive. This field is required.
        description (StringField): A description or nickname for the system drive. This field is required.
        submit (SubmitField): A button to submit the form.

    Validators:
        - `DataRequired()`: Ensures that both the `id` and `description` fields are provided.

    Usage:
        This form is used on the following pages:
          - '/systeminfo': To update system drive details.
          - '/settings': To configure system drive settings.

    Note:
        Both the `id` and `description` fields must be filled out before submitting the form.
    """
    id = IntegerField('id', validators=[DataRequired()])
    description = StringField('description', validators=[DataRequired()])
    submit = SubmitField('Submit')
