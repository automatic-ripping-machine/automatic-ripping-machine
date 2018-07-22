from armui import db


class Disc(db.Model):
    crc_id = db.Column(db.String(63), primary_key=True)
    disctype = db.Column(db.String(20))
    label = db.Column(db.String(256))

    def __repr__(self):
        return '<Disc CRC {}>'.format(self.crc_id) 


class Job(db.Model):
    job_id = db.Column(db.Integer, primary_key=True)
    arm_version = db.Column(db.String(20))
    crc_id = db.Column(db.String(63))
    logfile = db.Column(db.String(256))
    start_time = db.Column(db.DateTime)
    stop_time = db.Column(db.DateTime)
    job_length = db.Column(db.Integer)
    status = db.Column(db.String(32))
    title = db.Column(db.String(256))
    year = db.Column(db.Integer)
    new_title = db.Column(db.String(256))
    new_year = db.Column(db.Integer)

    def __repr__(self):
        return '<Job {}>'.format(self.label) 


class Movie(db.Model):
    movid_id = db.Column(db.Integer, primary_key=True)
    imdb_id = db.Column(db.String(256))
    title = db.Column(db.String(256))
    year = db.Column(db.Integer)
    title_ms = db.Column(db.String(256))
    title_omdb_id = db.Column(db.String(20))

    def __repr__(self):
        return '<Movie {}>'.format(self.label) 