"""Forms used in the arm ui"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, \
    IntegerField, BooleanField, PasswordField, Form, FieldList, \
    FormField, HiddenField, FloatField
from wtforms.validators import DataRequired, ValidationError, IPAddress
from os import path
import arm.config.config as cfg
from arm.ui import app
import json

def validate_path_exists(form, field):
    if not path.exists(field.data):
        raise ValidationError(f"The path specified does not exist:\r\n {field}")

def validate_umask(form, field):
    value = field.data
    try:
        # Accept both '002' and '0o002' formats
        if value.startswith("0o"):
            umask_int = int(value, 8)
        else:
            umask_int = int(value, 8)

        if not (0 <= umask_int <= 0o777):
            raise ValidationError("Umask must be a valid octal between 000 and 777.")
    except ValueError:
        raise ValidationError("Invalid octal number format.")

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
    MAINFEATURE = BooleanField('Main Feature: ', DataRequired())
    MINLENGTH = IntegerField('Minimum Length: ', DataRequired())
    MAXLENGTH = IntegerField('Maximum Length: ', DataRequired())
    submit = SubmitField('Submit')

ripperSettingsConfigFile = '/opt/arm/arm/ui/ripperFormConfig.json'
def SettingsForm(postRequestDict=None):
    class SettingsForm(FlaskForm):
        submit = SubmitField('Submit')
    
    with open(ripperSettingsConfigFile, 'r') as ripperFormConfig:
        dictFormFields = json.load(ripperFormConfig)
    # request.form.to_dict() returns a dict with the form fields and the value. All as strings on empty.
    # so we need to return a form with default values populated
    # postRequestDict

    for key, value in dictFormFields.items():
        if postRequestDict is not None:
            if key == 'csrf_token':
                # Skip the CSRF token field
                continue
        #Infer the type of form field based on the value type
        app.logger.debug(f"Inferring form field type for {key}: {type(value)}")
        # ripperFormConfig should have a dict per field: default, comment, dataValidation, formFieldType
        commentValue = dictFormFields[key]["comment"]
        if commentValue is None: commentValue = ""
        if postRequestDict is not None:
            fieldDefault = postRequestDict[key]
        else:
            fieldDefault = dictFormFields[key]["default"]
        if commentValue is None: commentValue = ""
        fieldType = dictFormFields[key]["formFieldType"]
        # The next is a bit tricky, getting a list of data validations, setting them up as objects
        # or functions depending on what was passed
        if isinstance(dictFormFields[key]['dataValidation'], list) and len(dictFormFields[key]['dataValidation']) > 0:
            validators = dictFormFields[key]['dataValidation']
            for x in validators:
                if x == "validate_path_exists":
                    validators.remove(x)
                    validators.append(validate_path_exists)
                elif x == "validate_umask":
                    validators.remove(x)
                    validators.append(validate_umask)
                else:
                    try:
                        n_v_c = globals()[x]
                        n_v_c = n_v_c()
                        validators.remove(x)
                        validators.append(n_v_c)
                    except Exception as e:
                        app.logger.warning(f"Error adding validator {x} to {key}: {e}")
        else:
            validators = None
        

        if isinstance(fieldDefault, bool) and fieldType == "SelectField":
            f = SelectField(label=key.replace("_", " "),
                        description=commentValue,
                        default=str(fieldDefault).title(),
                        render_kw={'title':commentValue},
                        validators=validators,
                        choices=[
                            ('True', 'True'),
                            ('False', 'False')
                            ],
                        )
        elif fieldType == "SelectField":
            paired_list = [(x, x) for x in fieldDefault]
            f = SelectField(label=key.replace("_", " "),
                        description=commentValue,
                        # default=str(fieldDefault),
                        render_kw={'title':commentValue},
                        validators=validators,
                        choices=paired_list,
                        )
        elif fieldType == "IntegerField":
            f = IntegerField(label=key.replace("_", " "),
                        description=commentValue,
                        default=int(fieldDefault),
                        validators=validators,
                        render_kw={'title':commentValue}
                        )
        elif fieldType == "FloatField":
            f = FloatField(label=key.replace("_", " "),
                        description=commentValue,
                        default=float(fieldDefault),
                        validators=validators,
                        render_kw={'title':commentValue}
                        )
        elif fieldType == "StringField":
            f = StringField(label=key.replace("_", " "),
                        description=commentValue,
                        default=str(fieldDefault),
                        validators=validators,
                        render_kw={'title':commentValue}
                        )
        else:
            app.logger.warning(f"Unknown type for {key}: {type(value)}, returning StringField")
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
