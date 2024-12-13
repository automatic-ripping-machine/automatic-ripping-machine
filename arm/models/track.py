from arm.ui import db


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
    status = db.Column(db.String(32))
    error = db.Column(db.Text)
    source = db.Column(db.String(32))
    process = db.Column(db.Boolean)

    def __init__(self, job_id, track_number, length, aspect_ratio,
                 fps, main_feature, source, basename, filename):
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
        self.ripped = False
        self.process = False

    def __repr__(self):
        return f'<Track {self.track_number}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.track_number
