"""Forms used in the arm ui"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, \
    IntegerField, BooleanField, PasswordField, Form, FieldList, FormField, HiddenField
from wtforms.validators import DataRequired


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


class SettingsForm(FlaskForm):
    """settings form used on pages\n
              - /settings"""
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
    """UI settings form, used on pages\n
                  - /ui_settings"""
    index_refresh = IntegerField('index_refresh', validators=[DataRequired()])
    use_icons = StringField('use_icons')
    save_remote_images = StringField('save_remote_images')
    bootstrap_skin = StringField('bootstrap_skin', validators=[DataRequired()])
    language = StringField('language', validators=[DataRequired()])
    database_limit = IntegerField('database_limit', validators=[DataRequired()])
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
