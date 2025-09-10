from typing import List
"""Forms used in the arm ui"""
from flask_wtf import FlaskForm
from wtforms import Form, Field, StringField, SubmitField, SelectField, \
    IntegerField, BooleanField, PasswordField, FieldList, \
    FormField, HiddenField, FloatField, RadioField
from wtforms.validators import DataRequired, Optional, ValidationError, IPAddress, InputRequired  # pyright: ignore[reportUnusedImport, reportUnusedExpression]
from os import path
import arm.config.config as cfg
from arm.ui import app
import arm.ui.utils as ui_utils
# Custom Validators go here:
from .forms_custom_validators import validate_path_exists, validate_umask, validate_non_manditory_string  # pyright: ignore[reportUnusedImport, reportUnusedExpression]
# You cannot create cannot create a dynamic form without importing the required validators, but then the compiler complains they are not used.
# The above line ignores those errors.


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
    MAINFEATURE = BooleanField(label='Main Feature: ', validators=[DataRequired()])
    MINLENGTH = IntegerField(label='Minimum Length: ', validators=[DataRequired()])
    MAXLENGTH = IntegerField(label='Maximum Length: ', validators=[DataRequired()])
    submit = SubmitField('Submit')

def SettingsForm() -> FlaskForm:
    """ A Function that returns a class instance.
        It buids the class based on on the comments.json and RipperFormConfig
        (Comments.json to make sure a central location exists for user comments)
        The SettingsForm class is originally empty, but fields are added using setattr
        ripperFormConfig should have a dict per field: 
            defaultForInternalUse (Default / field value type indicator): 
            commentForInternalUse: included in the ripperFormConfig to make it easier to design the form in json.
            dataValidation: DataRequired, ValidationError, IPAddress, \
                InputRequired, validate_non_manditory_string, validate_umask, validate_path_exists
            **formFieldType**: RadioField (Experimental), SelectField, IntegerField, \ 
                FloatField (Untested), StringField
    Raises:
        Exception: Unknown FIeld type

    Returns:
        FlaskForm: SettingsForm
    """
    # I don't care that this class is too complex, if someone can think up a more elegant way to do this,
    # happyily replace my code.
    class SettingsForm(FlaskForm):
        submit = SubmitField('Submit')
    
    dictFormFields = ui_utils.generate_ripperFormSettings()
    comments = ui_utils.generate_comments()
    if isinstance(dictFormFields, str):
        app.logger.exception(f"Unable to generate the Settings Form, RipperForm config was problematic: {dictFormFields}")
        raise Exception(f"Unable to generate the Settings Form, RipperForm config was problematic: {dictFormFields}")
    if isinstance(comments, str):
        app.logger.exception(f"Unable to generate the Settings Form, RipperForm config was problematic: {comments}")
        raise Exception(f"Unable to generate the Settings Form, RipperForm config was problematic: {comments}")

    for key, value in dictFormFields.items():
        # Infer the type of form field based on the value type
        # app.logger.debug(f"Inferring form field type for {key}: {type(value['defaultForInternalUse'])}")
        if key in comments:
            commentValue = str(comments[key])
        else:
            app.logger.warning(f"Comment not found for {key}, using empty string")
            commentValue = ""
        if commentValue is None:  # type: ignore
            commentValue = "" 
        fieldDefault = value["defaultForInternalUse"]
        fieldType = value["formFieldType"]
        # The next is a bit tricky, getting a list of data validations, setting them up as objects
        # or functions depending on what was passed
        # app.logger.debug(f"commentValue: {commentValue}, fieldDefault: {fieldDefault}, fieldType: {fieldType}")
        if isinstance(value['dataValidation'], list) and len(value['dataValidation']) > 0:
            possible_validators = value['dataValidation']
            validators: List[Field]|None = []
            # DataRequired, ValidationError, IPAddress, validate_path_exists, validate_umask validate_non_manditory_string
            for x in possible_validators:
                if x == "validate_path_exists":
                    app.logger.debug(f"Adding validate_path_exists to {key}")
                    # validators.append(validate_path_exists)
                elif x == "validate_umask":
                    app.logger.debug(f"Adding validate_umask to {key}")
                    # validators.append(validate_umask)
                elif x == "validate_non_manditory_string":
                    app.logger.debug(f"Adding validate_non_manditory_string to {key}")
                    # validators.append(validate_non_manditory_string)
                else:
                    try:
                        n_v_c = globals()[x]
                        n_v_c = n_v_c()
                        validators.append(n_v_c)
                    except Exception as e:
                        app.logger.warning(f"Error adding validator {x} to {key}: {e}")
            app.logger.debug(f"validators: {validators}")
        else:
            validators = None

        if isinstance(fieldDefault, bool) and fieldType == "SelectField":
            f = SelectField(label=key.replace("_", " "),
                            description=commentValue,
                            # default=str(fieldDefault).title(),
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
                            # default=str(fieldDefault).title(),
                            render_kw={'title':commentValue},
                            validators=validators,
                            choices=[
                                ('True', 'True'),
                                ('False', 'False')
                                ],
                        )
        elif fieldType == "RadioFeild":
            # SelectField with a list of choices
            if not isinstance(fieldDefault, list):
                app.logger.exception(f"Expected fieldDefault to be a list for {key}, got {type(fieldDefault)}")
                raise Exception(f"Expected fieldDefault to be a list for {key}, got {type(fieldDefault)}")
            paired_list = ui_utils.listCoPairedIntoTuple(fieldDefault)
            f = RadioField(label=key.replace("_", " "),
                            description=commentValue,
                            # default=str(fieldDefault),
                            render_kw={'title':commentValue},
                            validators=validators,
                            choices=paired_list,
                        )
        elif fieldType == "SelectField":
            # SelectField with a list of choices
            if not isinstance(fieldDefault, list):
                app.logger.exception(f"Expected fieldDefault to be a list for {key}, got {type(fieldDefault)}")
                raise Exception(f"Expected fieldDefault to be a list for {key}, got {type(fieldDefault)}")
            paired_list = ui_utils.listCoPairedIntoTuple(fieldDefault)
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
                            # default=int(fieldDefault),
                            validators=validators,
                            render_kw={'title':commentValue}
                        )
        elif fieldType == "FloatField":
            f = FloatField(label=key.replace("_", " "),
                            description=commentValue,
                            # default=float(fieldDefault),
                            validators=validators,
                            render_kw={'title':commentValue}
                        )
        elif fieldType == "StringField":
            f = StringField(label=key.replace("_", " "),
                            description=commentValue,
                            # default=str(fieldDefault),
                            validators=validators,
                            render_kw={'title':commentValue}
                        )
        else:
            app.logger.warning(f"Unknown type for {key}: {type(value)}, returning StringField")
            raise Exception(f"Unknown type for {key}: {type(value)}, returning StringField")
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
