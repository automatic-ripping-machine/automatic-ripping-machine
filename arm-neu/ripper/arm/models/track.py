from arm_contracts.enums import TrackStatus, SkipReason

from arm.database import db


class Track(db.Model):
    """ Holds all the individual track details for each job """
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
    status = db.Column(
        db.Enum(TrackStatus, name="track_status_enum",
                native_enum=False, validate_strings=True,
                values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    error = db.Column(db.Text)
    source = db.Column(db.String(32))
    process = db.Column(db.Boolean)
    enabled = db.Column(db.Boolean, default=True)
    skip_reason = db.Column(
        db.Enum(SkipReason, name="track_skip_reason_enum",
                native_enum=False, validate_strings=True,
                values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    chapters = db.Column(db.Integer, default=0)
    filesize = db.Column(db.BigInteger, default=0)
    # Per-track title metadata (nullable — inherits job-level when null)
    title = db.Column(db.String(256), nullable=True)
    year = db.Column(db.String(4), nullable=True)
    imdb_id = db.Column(db.String(15), nullable=True)
    poster_url = db.Column(db.String(256), nullable=True)
    video_type = db.Column(db.String(20), nullable=True)
    # Episode metadata from TVDB matching
    episode_number = db.Column(db.String(10), nullable=True)
    episode_name = db.Column(db.String(256), nullable=True)
    # User-specified output filename (overrides pattern rendering)
    custom_filename = db.Column(db.String(512), nullable=True)

    def __init__(self, job_id, track_number, length, aspect_ratio,
                 fps, main_feature, source, basename, filename,
                 chapters=0, filesize=0):
        """Return a track object"""
        self.job_id = job_id
        self.track_number = track_number
        self.length = length
        self.aspect_ratio = aspect_ratio
        self.fps = fps
        self.main_feature = main_feature
        self.source = source
        self.basename = basename
        self.filename = filename
        self.status = TrackStatus.pending.value
        self.ripped = False
        # process=None means "not yet decided"; the serializer at
        # arm/api/v1/jobs.py:_track_to_dict treats NULL as True so the
        # disc-review widget can render fresh tracks as rippable until
        # the rip path explicitly sets True/False (process_single_tracks
        # for manual-mode, the all-tracks loop for auto-mode, or
        # apply_makemkv_skips for tracks MakeMKV refuses).
        # If we set False here, fresh-from-prescan tracks would render
        # as 'skip' in the review UI for the entire wait phase.
        self.process = None
        self.enabled = True
        self.chapters = chapters
        self.filesize = filesize

    def __repr__(self):
        return f'<Track {self.track_number}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.track_number
