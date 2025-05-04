"""Forms used in the arm ui"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, \
    IntegerField, BooleanField, PasswordField, Form, FieldList, FormField, HiddenField, \
    FormField, FloatField
from wtforms.validators import DataRequired, ValidationError, IPAddress, Optional
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
    MAINFEATURE = BooleanField('Main Feature: ', DataRequired)
    MINLENGTH = IntegerField('Minimum Length: ', DataRequired())
    MAXLENGTH = IntegerField('Maximum Length: ', DataRequired())
    submit = SubmitField('Submit')


def SettingsForm(dictFormFields:dict, comments ={}):
    class SettingsForm(FlaskForm):
        submit = SubmitField('Submit')
        
    for key, value in dictFormFields.items():
        #Infer the type of form field based on the value type
        app.logger.debug(f"Inferring form field type for {key}: {type(value)}")
        # Just in case the comment is empty, we will get the value for it, and
        # if none, set it to string
        comm_value = comments.get(key)
        if comm_value is None: comm_value = ""
        
        if isinstance(value, bool):
            f = BooleanField(label=key.replace("_", " "),
                        description=comm_value,
                        default=value,
                        render_kw={'title':comm_value}
                        )
        elif isinstance(value, int):
            f = IntegerField(label=key.replace("_", " "),
                        description=comm_value,
                        default=value,
                        render_kw={'title':comm_value}
                        )
        elif isinstance(value, float):
            f = FloatField(label=key.replace("_", " "),
                        description=comm_value,
                        default=value,
                        render_kw={'title':comm_value}
                        )
        elif isinstance(value, str):
            f = StringField(label=key.replace("_", " "),
                        description=comm_value,
                        default=value,
                        render_kw={'title':comm_value}
                        )
            # if "binary to call" in comments[key] or "Path to" in comments[key]:
                # f.validators([DataRequired(),validate_path_exists()])
        else:
            app.logger.warning(f"Unknown type for {key}: {type(value)}, returning StringField")
            f = StringField(label=key.replace("_", " "),
                        description=comm_value,
                        default=str(value),
                        render_kw={'title':comm_value}
                        )  # fallback
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
    """"
    ARM User Login form.
    This form is used on:
      - /login

    Fields:
        username (StringField): The user's username (required).
        password (PasswordField): The user's password (required).
        submit (SubmitField): Button to submit the login form.
    """
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class PasswordReset(FlaskForm):
    """
    Password reset form.
    This form is used on:
      - /update_password (for authenticated users to change their password)

    Fields:
        username (StringField): The user's username (required).
        old_password (PasswordField): The user's current password (required).
        new_password (PasswordField): The new password to set (required).
        submit (SubmitField): Button to submit the form.
    """
    username = StringField('username', validators=[DataRequired()])
    old_password = PasswordField('password', validators=[DataRequired()])
    new_password = PasswordField('password', validators=[DataRequired()])
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
    description = StringField('Description', validators=[Optional()])
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
