"""
ARM Forms Functions for:
    Main

Functions
    - SettingsForm
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, length


class SystemInfoLoad(FlaskForm):
    """
    A form for updating system information in ARM.

    This form is used to capture and validate ARM system information.

    Fields:
        name (StringField): system name
        cpu (StringField): system CPU details
        description (StringField): A short description of the system.

    Methods:
        validate_on_submit: Validates the form and checks if it was submitted.
        submit: Submit button to apply the settings changes.

    Usage:
        This form is used on the '/settings' page of the application to allow users to update system settings.
    """
    name = StringField('Server Name', validators=[DataRequired(),
                                                  length(max=100)])
    cpu = StringField('Server CPU', validators=[DataRequired(),
                                                length(max=100)])
    description = StringField('Description', validators=[DataRequired(),
                                                         length(max=200)])
    mem_total = FloatField('System Memory', validators=[DataRequired()])
    submit = SubmitField('Load Info')
