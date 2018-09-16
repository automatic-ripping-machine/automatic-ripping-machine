from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class TitleUpdateForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    year = StringField('Year')
    submit = SubmitField('Submit')