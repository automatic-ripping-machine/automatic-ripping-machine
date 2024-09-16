"""
ARM Forms Functions for:
    Database

Forms
    - DBUpdate
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class DBUpdate(FlaskForm):
    """
        A form for the database upgrade

        This form is used to validate the request made by a user when upgrading the database

        Fields:
            dbfix (StringField): Database fix
            submit (SubmitField): A button to submit the form.

        Methods:
            validate_on_submit: Validates the form's data and checks if the form was submitted.

        Usage:
            This form is utilized on the following pages:
              - '/db_update': Called when a database update is requested from /index

        Note:
            None
        """
    dbfix = StringField('dbfix', validators=[DataRequired()])
    submit = SubmitField('Submit')
