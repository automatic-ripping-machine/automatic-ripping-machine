from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, BooleanField, PasswordField, validators
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
    RIPMETHOD = SelectField('Rip Method', choices=[('mkv', 'mkv'), ('backup', 'backup')])
    #MAINFEATURE = BooleanField('Main Feature', validators=[DataRequired()])
    MAINFEATURE = BooleanField('Main Feature')
    MINLENGTH = IntegerField('Minimum Length')
    MAXLENGTH = IntegerField('Maximum Length')
    submit = SubmitField('Submit')

class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    submit = SubmitField('Submit')