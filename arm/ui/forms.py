"""Forms used in the arm ui"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, \
    IntegerField, BooleanField, PasswordField, Form, FieldList, \
    FormField, HiddenField, FloatField, RadioField, IntegerRangeField
from wtforms.validators import DataRequired, ValidationError, IPAddress, InputRequired
from os import path
import arm.config.config as cfg
from arm.ui import app
import arm.ui.utils as ui_utils
import json

### Custom Validators

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

def validate_non_manditory_string(form, field):
    originalLength = len(field.data)
    if originalLength > 0:
        text = field.data.replace('<p>','').replace('</p>','').replace('&nbsp;','')\
                         .replace('&ensp;','').replace('&emsp;','').replace('<br>','')
        if len(text) == 0:
            raise ValidationError("Field must not contain only HTML tags.")
        # check for non-ASCII characters
        if not all(ord(c) < 128 for c in text):
            raise ValidationError("Field must not contain non-ASCII characters.")
        # check for non-printable characters
        if not all(c.isprintable() for c in text):
            raise ValidationError("Field must not contain non-printable characters.")
        # remove whitespace
        text = text.strip().replace("\t","").replace("\n","").replace("\r","").replace("\f","").replace("\v","")
        if len(text) == 0:
            raise ValidationError("Field must not contain only whitespace.")


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

def SettingsForm():
    class SettingsForm(FlaskForm):
        submit = SubmitField('Submit')
    
    # move the ripper form settings config into ui.utils
    # in this function, read the comments and the ripperFormConfigyou
    dictFormFields = ui_utils.generate_ripperFormSettings()
    comments = ui_utils.generate_comments()
    # request.form.to_dict() returns a dict with the form fields and the value. All as strings on empty.
    # so we need to return a form with default values populated
    # postRequestDict

    for key, value in dictFormFields.items():
        # if postRequestDict is not None:
        #     if key == 'csrf_token':
        #         # Skip the CSRF token field
        #         continue
        # #Infer the type of form field based on the value type
        # app.logger.debug(f"Inferring form field type for {key}: {type(value['defaultForInternalUse'])}")
        # ripperFormConfig should have a dict per field: defaultForInternalUse, commentForInternalUse, dataValidation, formFieldType
        if key in comments:
            commentValue = comments[key]
        else:
            app.logger.warning(f"Comment not found for {key}, using empty string")
            commentValue = ""
        if commentValue is None: commentValue = ""
        fieldDefault = value["defaultForInternalUse"]
        fieldType = value["formFieldType"]
        # The next is a bit tricky, getting a list of data validations, setting them up as objects
        # or functions depending on what was passed
        # app.logger.debug(f"commentValue: {commentValue}, fieldDefault: {fieldDefault}, fieldType: {fieldType}")
        if isinstance(value['dataValidation'], list) and len(value['dataValidation']) > 0:
            possible_validators = value['dataValidation']
            validators = []
            # DataRequired, ValidationError, IPAddress, validate_path_exists, validate_umask validate_non_manditory_string
            for x in possible_validators:
                if x == "validate_path_exists":
                    validators.append(validate_path_exists)
                elif x == "validate_umask":
                    validators.append(validate_umask)
                elif x == "validate_non_manditory_string":
                    validators.append(validate_non_manditory_string)
                else:
                    try:
                        n_v_c = globals()[x]
                        n_v_c = n_v_c()
                        validators.append(n_v_c)
                    except Exception as e:
                        app.logger.warning(f"Error adding validator {x} to {key}: {e}")
        else:
            validators = None
        app.logger.debug(f"validators: {validators}")
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
        elif isinstance(fieldDefault, bool) and fieldType == "RadioField":
            f = RadioField(label=key.replace("_", " "),
                        description=commentValue,
                        default=str(fieldDefault).title(),
                        render_kw={'title':commentValue},
                        validators=validators,
                        choices=[
                            ('True', 'True'),
                            ('False', 'False')
                            ],
                        )
        elif fieldType == "RadioFeild":
            # SelectField with a list of choices
            paired_list = [(x, x) for x in fieldDefault]
            f = RadioField(label=key.replace("_", " "),
                        description=commentValue,
                        # default=str(fieldDefault),
                        render_kw={'title':commentValue},
                        validators=validators,
                        choices=paired_list,
                        )
        elif fieldType == "SelectField":
            # SelectField with a list of choices
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
