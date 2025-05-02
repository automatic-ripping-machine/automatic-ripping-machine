"""Forms used in the arm ui"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, \
    IntegerField, BooleanField, PasswordField, Form, FieldList, \
    FormField, HiddenField, FloatField
from wtforms.validators import DataRequired, ValidationError, IPAddress
from os import path
import arm.config.config as cfg
from arm.ui import app

def validate_path_exists(field):
    if not path.exists(field.data):
        raise ValidationError(f"The path specified does not exist:\r\n {field}")

class TitleSearchForm(FlaskForm):
    """Main title search form used on pages\n
      - /titlesearch
      - /customTitle
      - /list_titles"""
    title = StringField('Title', validators=[DataRequired()])
    year = StringField('Year')
    submit = SubmitField('Submit')


class ChangeParamsForm(FlaskForm):
    """Change config parameters form, used on pages\n
          - /changeparams"""
    RIPMETHOD = SelectField('Rip Method: ', choices=[('mkv', 'mkv'), ('backup', 'backup')])
    DISCTYPE = SelectField('Disc Type: ', choices=[('dvd', 'DVD'), ('bluray', 'Blu-ray'),
                                                   ('music', 'Music'), ('data', 'Data')])
    # "music", "dvd", "bluray" and "data"
    MAINFEATURE = BooleanField('Main Feature: ')
    MINLENGTH = IntegerField('Minimum Length: ')
    MAXLENGTH = IntegerField('Maximum Length: ')
    submit = SubmitField('Submit')

# class SettingsForm():
#     """settings form used on pages\n
#               - /settings"""    
#     # def  __init__(self):
#     name = 'Ripper Settings'

#     submit = SubmitField('Submit')       

    # Developing a dynamic rebuild of the Settings form, based on the information in the yaml
    # MANUAL_WAIT = SelectField('Manual Wait', choices=[('True','True'),('False','False')])
    # DATE_FORMAT = StringField('DATE_FORMAT', validators=[DataRequired()])
    # HB_PRESET_DVD = StringField('HB_PRESET_DVD', validators=[DataRequired()])
    # HB_PRESET_BD = StringField('HB_PRESET_BD', validators=[DataRequired()])
    # HANDBRAKE_CLI = StringField('HANDBRAKE_CLI', validators=[DataRequired(),validate_path_exists])
    # DBFILE = StringField('DBFILE', validators=[DataRequired(),validate_path_exists])
    # LOGPATH = StringField('LOGPATH', validators=[DataRequired(),validate_path_exists])
    # INSTALLPATH = StringField('INSTALLPATH', validators=[DataRequired(),validate_path_exists])
    # RAW_PATH = StringField('RAW_PATH', validators=[DataRequired(), validate_path_exists])
    # TRANSCODE_PATH = StringField('TRANSCODE_PATH', validators=[DataRequired(), validate_path_exists])
    # COMPLETED_PATH = StringField('COMPLETED_PATH', validators=[DataRequired(),validate_path_exists])
    # submit = SubmitField('Submit')

def SettingsForm(dictFormFields:dict):
    class SettingsForm(FlaskForm):
        submit = SubmitField('Submit')
        
    for key, value in dictFormFields.items():
        #Infer the type of form field based on the value type
        app.logger.debug(f"Inferring form field type for {key}: {type(value)}")
        if isinstance(value, bool):
            f = BooleanField(label=key,
                        description=key.replace("_", " "),
                        default=value)
        elif isinstance(value, int):
            f = IntegerField(label=key,
                        description=key.replace("_", " "),
                        default=value)
        elif isinstance(value, float):
            f = FloatField(label=key,
                        description=key.replace("_", " "),
                        default=value)
        elif isinstance(value, str):
            f = StringField(label=key,
                        description=key.replace("_", " "),
                        default=value)
        else:
            app.logger.warning(f"Unknown type for {key}: {type(value)}, returning StringField")
            f = StringField(label=key,
                        description=key.replace("_", " "),
                        default=str(value))  # fallback
        setattr(SettingsForm, key, f)
    return SettingsForm()


class UiSettingsForm(FlaskForm):
    """UI settings form, used on pages\n
                  - /ui_settings"""
    index_refresh = IntegerField('Index Refresh Period', validators=[DataRequired()])
    use_icons = SelectField('Use Icons',
                             validators=[DataRequired()],
                             choices=[
                                 ('True', 'True'),
                                 ('False', 'False')
                             ],
                             )
    save_remote_images = SelectField('Save Remote Images',
                             validators=[DataRequired()],
                             choices=[
                                 ('True', 'True'),
                                 ('False', 'False')
                             ],
                             )
    bootstrap_skin = StringField('Which bootstrap skin', validators=[DataRequired()])
    language = StringField('language for Web UI', validators=[DataRequired()])
    database_limit = IntegerField('Job Display limit', validators=[DataRequired()])
    notify_refresh = IntegerField('notify_refresh', validators=[DataRequired()])
    submit = SubmitField('Submit')


class SetupForm(FlaskForm):
    """Login/admin account creation on pages\n
      - /login
      - /update_password"""
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class AbcdeForm(FlaskForm):
    """abcde config form used on pages\n
              - /settings"""
    abcdeConfig = StringField('abcdeConfig', validators=[DataRequired()])
    submit = SubmitField('Submit')


class SystemInfoDrives(FlaskForm):
    """
    SystemInformation Form, to update system drive name (nickname) and description
      - /systeminfo
      - /settings
    """
    id = IntegerField('Drive ID', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    drive_mode = SelectField('Drive Mode',
                             validators=[DataRequired()],
                             choices=[
                                 ('auto', 'Auto'),
                                 ('manual', 'Manual')
                             ],
                             )
    submit = SubmitField('Submit')


class DBUpdate(FlaskForm):
    """
    Update or re-install the arm DB file
      - /db_update  (called from /index)
    """
    dbfix = StringField('dbfix', validators=[DataRequired()])
    submit = SubmitField('Submit')


class TrackForm(Form):
    """
    ID and Checkbox status for fields in TrackFormDynamic
    """
    track_ref = HiddenField('ID')
    checkbox = BooleanField('Checkbox')


class TrackFormDynamic(FlaskForm):
    """
    Dynamic form for Job Tracks
    - /jobdetail (called by jobs)
    """
    track_ref = FieldList(FormField(TrackForm), min_entries=1)
