class JobException(Exception):
    def __init__(self):
        self.status_code = 400
        self.detail = "Malformed data"


class JobNotFoundError(JobException):
    def __init__(self):
        self.status_code = 404
        self.detail = "Job Details Not Found"


class JobAlreadyExistError(JobException):
    def __init__(self):
        self.status_code = 409
        self.detail = "Job with those details already exists"

class UISettingsNotFoundError(JobException):
    def __init__(self):
        self.status_code = 404
        self.detail = "Ui Settings Not Found"