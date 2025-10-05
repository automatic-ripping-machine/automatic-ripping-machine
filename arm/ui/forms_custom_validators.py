"""custom validators used in UI Forms"""
from wtforms import Form, Field
from wtforms.validators import IPAddress
from wtforms import ValidationError
from os import path


class IPAddress_custom(IPAddress):
    """Custom IP address validator that allows X.X.X.X values."""
    def __init__(self, exception="x.x.x.x", message=None, ipv4=True, ipv6=False, ):
        self.message = message or "Invalid IP address. Use X.X.X.X to ignore."
        self.exception = exception.lower()
        super().__init__(message=self.message, ipv4=ipv4, ipv6=ipv6)

    def __call__(self, form, field):
        if isinstance(field.data, str):
            field_value = field.data.strip()
            if field_value.lower() == "x.x.x.x":
                return
        super().__call__(form, field)


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
        self.message = message or ("The path specified does not exist.")

    def __call__(self, form: Form, field: Field):
        field_data = field.data.strip()
        if not path.exists(field_data):
            raise ValidationError(f"{self.message}\r\n {field}")


class validate_umask():
    """Custom validator to check  if a given umask is valid.
    """
    def __init__(self):
        self.message = "Umask must be a valid int between 0 and 4095. or 0o000 to 0o777"
    
    def __call__(self, form: Form, field: Field):
        value = field.data
        try:
            # Accept both '002' and '0o002' formats
            if value.startswith("0o"):
                umask_int = int(value, 8)
                if not (0 <= umask_int <= 0o777):
                    raise ValidationError("Invalid umask: must be a valid octal between 0o000 and 0o777.")
            else:
                if isinstance(value, int):
                    umask_int = value
                else:
                    raise ValidationError(self.message)
            if not (0 <= umask_int <= 4095):
                raise ValidationError(self.message)
        except ValueError:
            raise ValidationError(self.message)


class validate_non_manditory_string():
    """
    Validator for a non field that CAN be empty, 
    but cannot: 
        contain only whitespace,
        HTML tags,
        non-ASCII characters, or non-printable characters.    
    """
    def __init__(self):
        self.message = "CAN be empty, but cannot: contain only whitespace, \
            HTML tags, non-ASCII characters, or non-printable characters."

    def __call__(self, form: Form, field: Field):
        original_length = len(field.data)
        if original_length > 0:
            text = field.data.replace('<p>', '').replace('</p>', '').replace('&nbsp;', '')\
                             .replace('&ensp;', '').replace('&emsp;', '').replace('<br>', '')
            if len(text) == 0:
                raise ValidationError(f"{field.name} {self.message} it contains, only HTML tags.")
            # check for non-ASCII characters
            if not all(ord(c) < 128 for c in text):
                raise ValidationError(f"{field.name} {self.message} it contains non-ASCII characters.")
            # check for non-printable chara cters
            if not all(c.isprintable() for c in text):
                raise ValidationError(f"{field.name}  {self.message} it contains non-printable characters.")
            # remove whitespace
            text = text.strip().replace("\t", "").replace("\n", "").replace("\r", "").replace("\f", "").replace("\v", "")
            if len(text) == 0:
                raise ValidationError(f"{field.name} {self.message} it contains only whitespace.")
