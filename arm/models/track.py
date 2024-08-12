from models.arm_models import ARMModel
from ui.ui_setup import db


class Track(ARMModel):
    """
    ARM Database Model - Track

    This class holds details about individual tracks associated with a job,
    including track ID, job ID, track number, length, aspect ratio, frames per second (FPS),
    main feature status, filenames, ripped status, track status, error details, and source.

    Database Table:
        track

    Attributes:
        track_id (int): The unique identifier for the track.
        job_id (int): The ID of the job associated with the track.
        track_number (str): Track number.
        length (int): Length of the track.
        aspect_ratio (str): Aspect ratio of the track.
        fps (float): Frames per second (FPS) of the track.
        main_feature (bool): Indicates if the track is the main feature.
        basename (str): Base name of the track.
        filename (str): Original filename of the track.
        orig_filename (str): Original filename of the track before modification.
        new_filename (str): New filename of the track after modification.
        ripped (bool): Indicates if the track has been ripped.
        status (str): Current status of the track.
        error (str): Details of any error encountered with the track.
        source (str): Source of the track.

    Relationships:
        job (relationship): Relationship to the job associated with the track.
    """
    __tablename__ = 'track'

    track_id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.job_id'))
    track_number = db.Column(db.String(4))
    length = db.Column(db.Integer)
    aspect_ratio = db.Column(db.String(20))
    fps = db.Column(db.Float)
    main_feature = db.Column(db.Boolean)
    basename = db.Column(db.String(256))
    filename = db.Column(db.String(256))
    orig_filename = db.Column(db.String(256))
    new_filename = db.Column(db.String(256))
    ripped = db.Column(db.Boolean)
    status = db.Column(db.String(32))
    error = db.Column(db.Text)
    source = db.Column(db.String(32))

    def __init__(self, job_id: int, track_number: str, length: int, aspect_ratio: str,
                 fps: float, main_feature: bool, source: str, basename: str, filename: str):
        self.job_id = job_id
        self.track_number = track_number
        self.length = length
        self.aspect_ratio = aspect_ratio
        self.fps = fps
        self.main_feature = main_feature
        self.source = source
        self.basename = basename
        self.filename = filename
        self.ripped = False
