"""Forms used in the arm ui"""
from flask_wtf import FlaskForm
from wtforms import Form, Field
from wtforms.validators import ValidationError
from os import path

def validate_path_exists(form:Form, field:Field):
    if not path.exists(field.data):
        raise ValidationError(f"The path specified does not exist:\r\n {field}")

def validate_umask(form:Form, field:Field):
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

def validate_non_manditory_string(form:Form, field:Field):
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

