"""
ARM Forms Functions for:
    Authentication

Forms
    - SetupForm
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired


class SetupForm(FlaskForm):
    """
    A form for user authentication and password management.

    This form is used to capture and validate user credentials for logging in and updating passwords.

    Fields:
        username (StringField): The username or email address for user authentication.
        password (PasswordField): The password for user authentication.
        submit (SubmitField): A button to submit the form.

    Methods:
        validate_on_submit: Validates the form's data and checks if the form was submitted.

    Usage:
        This form is utilized on the following pages:
          - '/login': To authenticate users by collecting their username and password.
          - '/update_password': To update the user's password with their current credentials.

    Note:
        Both fields are required for form submission, and appropriate validation is applied to ensure that
        both username and password are provided.
    """
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    submit = SubmitField('Submit')
