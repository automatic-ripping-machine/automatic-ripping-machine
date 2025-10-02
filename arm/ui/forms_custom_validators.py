"""custom validators used in UI Forms"""
from wtforms import Form, Field
from wtforms.validators import IPAddress
from wtforms import ValidationError
from os import path

class IPAddress_custom(IPAddress):
    """Custom IP address validator that allows X.X.X.X values."""
    
    def __init__(self, form, field):
        field_value = field.data.strip()
        if isinstance(field_value,str):
            if field_value.lower() == "x.x.x.x":
                return
        super().__init__(form, field)


class validate_path_exists():
    """Custom validator to check that a given path exists.
    either folder or file.
    """
    def __init__(self, must_exist=True, message=None):
        """
        :param must_exist: If True, the path must exist on the filesystem.
        :param message: Custom error message.
        """
        self.must_exist = must_exist
        self.message = message or (f"The path specified does not exist.")
    
    def __call__(self, form: Form, field: Field):
        field_data = field.data.strip()
        if not path.exists(field_data):
            raise ValidationError(f"{self.message}\r\n {field}")


def validate_umask(form: Form, field: Field):
    """Custom validator to check  if a given umask is valid.
    
    Keyword arguments:
    form -- description 
    field -- the field to validate
    Return: ValidationError if umask is not valid
    """    
    value = field.data
    try:
        # Accept both '002' and '0o002' formats
        if value.startswith("0o"):
            umask_int = int(value, 8)
            if not (0 <= umask_int <= 0o777):
                raise ValidationError("Invalid umask: must be a valid octal between 000 and 7777.")
        else:
            umask_int = int(value)
            if not (0 <= umask_int <= 777):
                raise ValidationError("Umask must be a valid int between 0 and 4095.")
    except ValueError:
        raise ValidationError("Invalid octal number format.")


def validate_non_manditory_string(form: Form, field: Field):
    originalLength = len(field.data)
    if originalLength > 0:
        text = field.data.replace('<p>', '').replace('</p>', '').replace('&nbsp;', '')\
                         .replace('&ensp;', '').replace('&emsp;', '').replace('<br>', '')
        if len(text) == 0:
            raise ValidationError("Field must not contain only HTML tags.")
        # check for non-ASCII characters
        if not all(ord(c) < 128 for c in text):
            raise ValidationError("Field must not contain non-ASCII characters.")
        # check for non-printable chara cters
        if not all(c.isprintable() for c in text):
            raise ValidationError("Field must not contain non-printable characters.")
        # remove whitespace
        text = text.strip().replace("\t", "").replace("\n", "").replace("\r", "").replace("\f", "").replace("\v", "")
        if len(text) == 0:
            raise ValidationError("Field must not contain only whitespace.")
