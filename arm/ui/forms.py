from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, BooleanField, validators  # noqa: F401
from wtforms.validators import DataRequired


class TitleSearchForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    year = StringField('Year')
    submit = SubmitField('Submit')


class CustomTitleForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    year = StringField('Year')
    submit = SubmitField('Submit')


class ChangeParamsForm(FlaskForm):
    RIPMETHOD = SelectField('Rip Method: ', choices=[('mkv', 'mkv'), ('backup', 'backup')])
    DISCTYPE = SelectField('Disc Type: ', choices=[('dvd', 'DVD'), ('bluray', 'Bluray'),
                                                   ('music', 'Music'), ('data', 'Data')])
    # "music", "dvd", "bluray" and "data"
    MAINFEATURE = BooleanField('Main Feature')
    # MAINFEATURE = SelectField('Main Feature: ', choices=[(1, 'Yes'), (0, 'No')])
    MINLENGTH = IntegerField('Minimum Length: ')
    MAXLENGTH = IntegerField('Maximum Length: ')
    submit = SubmitField('Submit')


class SettingsForm(FlaskForm):
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
