from typing import List
"""Forms used in the arm ui"""
from flask_wtf import FlaskForm
from wtforms import Form, Field, StringField, SubmitField, SelectField, \
    IntegerField, BooleanField, PasswordField, FieldList, \
    FormField, HiddenField, FloatField, RadioField
from wtforms.validators import DataRequired, Optional
from wtforms.validators import ValidationError, IPAddress, InputRequired  # noqa: F401
from arm.ui import app
import arm.ui.utils as ui_utils
# Custom Validators go here:
from .forms_custom_validators import IPAddress_custom, validate_path_exists, \
    validate_umask, validate_non_manditory_string  # noqa: F401
# You cannot create cannot create a dynamic form without importing the required validators,
# but then the compiler complains they are not used, the above line ignores those errors.

listDefault = ['True', 'False']


def create_object_instance(class_name: str) -> object:
    """Create a an object based on the name passed.
    Used originally to create validators dynamically.
    Raises:
        Exception: Unknown object type
    Args:
        validatorName (str): Name of the validator to create
    Returns:
        object: Validator object
    """
    if class_name is None:
        return None
    try:
        class_definition = globals().get(class_name)
        if class_definition is None:
            raise ValueError(f"Unknown validator: {class_name}")
        if not callable(class_definition):
            raise ValueError(f"Validator {class_name} is not callable")
        validator_instance = class_definition()
        return validator_instance
    except Exception as e:
        app.logger.warning(f"Error creating validator {class_name}: {e}")


def create_list_of_validator_obj(list_of_validator_names: List[str], field_name:str) -> List[object]:
    """Create a list of validator objects based on the names passed.
    Used to create validators dynamically.
    Raises:
        Exception: Unknown Validator type
    Args:
        list_of_validator_names (List[str]): List of validator names to create
    Returns:
        List[object]: List of validator objects
    """
    possible_validators = list_of_validator_names
    validators: List[object] = []
    # To save scrolling up, here is a list of the imported validators:
    #   DataRequired, ValidationError, IPAddress, validate_path_exists,
    #   IPAddress_custom, validate_umask validate_non_manditory_string
    for x in possible_validators:
            validator_instance = create_object_instance(class_name=x)
            validators.append(validator_instance)
    app.logger.debug(f"Validators gathered for field {field_name}: {validators} ")
    return validators


def create_single_choice_field(
        field_type: str,
        key: str,
        comment_value: str,
        validators: List[object] | None,
        choices_paired_list: List[tuple[str, str]] | None = None) -> SelectField | RadioField:
    """Create a single choice field, either SelectField or RadioField
    """
    if choices_paired_list is None:
        choices_paired_list = ui_utils.list_copaired_into_tuple(listDefault)
    if not isinstance(choices_paired_list[0], tuple):
        app.logger.warning(f"Expected a list of tuples for {key}, got {type(choices_paired_list[0])}")
        # I am going to assume that the list is a list of strings, and convert it to a list of tuples
        choices_paired_list = ui_utils.list_copaired_into_tuple(choices_paired_list)
    if field_type == "SelectField":
        return SelectField(
                label=key.replace("_", " "),
                description=comment_value,
                render_kw={'title': comment_value},
                validators=validators,
                choices=choices_paired_list,
            )
    if field_type == "RadioField":
        return RadioField(
                label=key.replace("_", " "),
                description=comment_value,
                render_kw={'title': comment_value},
                validators=validators,
                choices=choices_paired_list,
            )


def form_field_chooser(
        field_type: str,
        field_default: str | int | float | bool | list[str] | None,
        key: str,
        comment_value: str,
        validators: List[object] | None,
        ) -> Field:
    """
    FormFieldChooser
        Create a field based on the type passed (Inferance).
        Used by SettingsForm to create fields dynamically.
        Hopefully this should make the 'SettingsForm' function a bit less complex.

    Raises:
        ValueError: Unknown Field type

    Args:
        fieldType (str): create [SelectField, RadioField, IntegerField, FloatField, StringField]
        fieldDefault (str): default value for the field
        key (str): field name
        commentValue (str): Field description for tooltip
        validators (list|None): list of validators to apply to the field
        choices_paired_list (list|bool|None): list of tuples for select field choices. Could also be None, or Booleans

    Returns:
        Field
    """
    key = key.replace("_", " ")
    if isinstance(field_default, bool) and field_type in ("SelectField", "RadioField"):
        f = create_single_choice_field(
            field_type=field_type,
            key=key,
            comment_value=comment_value,
            validators=validators,
            choices_paired_list=None
            )
        return f

    if field_type in ("SelectField", "RadioField"):
        # SelectField with a list of choices
        if not isinstance(field_default, list):
            app.logger.exception(f"Expected fieldDefault to be a list for {key}, got {type(field_default)}")
            raise ValueError(f"Expected fieldDefault to be a list for {key}, got {type(field_default)}")
        paired_list = ui_utils.list_copaired_into_tuple(field_default)
        f = create_single_choice_field(
            field_type=field_type,
            key=key,
            comment_value=comment_value,
            validators=validators,
            choices_paired_list=paired_list
            )
        return f

    if field_type == "IntegerField":
        return IntegerField(
            label=key,
            description=comment_value,
            # default=int(fieldDefault),
            validators=validators,
            render_kw={'title': comment_value}
            )
    elif field_type == "FloatField":
        return FloatField(
            label=key,
            description=comment_value,
            # default=float(fieldDefault),
            validators=validators,
            render_kw={'title': comment_value}
        )
    elif field_type == "StringField":
        return StringField(
            label=key,
            description=comment_value,
            # default=str(fieldDefault),
            validators=validators,
            render_kw={'title': comment_value}
        )
    else:
        app.logger.warning(f"Unknown type for {key}: {type(field_type)}, returning StringField")
        return StringField(
            label=key,
            description=comment_value,
            # default=str(fieldDefault),
            validators=validators,
            render_kw={'title': comment_value}
        )


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
            dataValidation: DataRequired, ValidationError, IPAddress,
                InputRequired, validate_non_manditory_string, validate_umask, validate_path_exists
            **formFieldType**: RadioField (Experimental), SelectField, IntegerField,
                FloatField (Untested), StringField
    Raises:
        Exception: Unknown Field type
        ValueError: RipperFormConfig or comments.json was problematic
    Returns:
        FlaskForm: SettingsForm
    """
    # I don't care that this class is too complex, if someone can think up a more elegant way to do this,
    # happyily replace my code.
    class SettingsForm(FlaskForm):
        submit = SubmitField('Submit')

    dict_form_fields = ui_utils.generate_ripper_form_settings()
    comments = ui_utils.generate_comments()
    if isinstance(dict_form_fields, str):
        app.logger.exception(f"Settings Form failed, RipperForm config was problematic: {dict_form_fields}")
        raise ValueError(f"Settings Form failed, RipperForm config was problematic: {dict_form_fields}")
    if isinstance(comments, str):
        app.logger.exception(f"Settings Form failed, RipperForm config was problematic: {comments}")
        raise ValueError(f"Settings Form failed, RipperForm config was problematic: {comments}")

    for key, value in dict_form_fields.items():
                
        field_default = value["defaultForInternalUse"]
        field_type = value["formFieldType"]

        if key in comments:
            comment_value = str(comments[key])
        else:
            app.logger.warning(f"Comment not found for {key}, using empty string")
            comment_value = ""
        if comment_value is None:  # type: ignore
            comment_value = ""
        
        # Getting a list of data validations, setting them up as instances of object
        if isinstance(value['dataValidation'], list) and len(value['dataValidation']) > 0:
            validators = []
            validators = create_list_of_validator_obj(value['dataValidation'], field_name=key)
        else:
            validators = None
        f = form_field_chooser(
            field_type=field_type,
            field_default=field_default,
            key=key,
            comment_value=comment_value,
            validators=validators
            )
        setattr(SettingsForm, key, f)
    app.logger.debug("SettingsForm created with fields")
    return SettingsForm()


class UiSettingsForm(FlaskForm):
    """UI settings form, used on pages\n
                  - /ui_settings"""
    index_refresh = IntegerField('Index Refresh Period', validators=[DataRequired()])
    use_icons = SelectField(
        'Use Icons',
        validators=[DataRequired()],
        choices=[
            ('True', 'True'),
            ('False', 'False')
        ],
    )
    save_remote_images = SelectField(
        'Save Remote Images',
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
