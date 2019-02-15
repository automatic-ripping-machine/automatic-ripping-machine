from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, BooleanField
from wtforms.validators import DataRequired


class TitleSearchForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    year = StringField('Year')
    submit = SubmitField('Submit')


class ChangeParamsForm(FlaskForm):
    RIPMETHOD = SelectField('Rip Method', choices=[('mkv', 'mkv'), ('backup', 'backup')])
    MAINFEATURE = BooleanField('Main Feature', validators=[DataRequired()])
    MINLENGTH = IntegerField('Minimum Length')
    MAXLENGTH = IntegerField('Maximum Length')
    submit = SubmitField('Submit')