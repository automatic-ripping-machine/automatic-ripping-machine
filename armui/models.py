from armui import db


class Disc(db.Model):
    crc_id = db.Column(db.String(63), primary_key=True)
    label = db.Column(db.String(256))

    def __repr__(self):
        return '<Disc CRC {}>'.format(self.crc_id) 


class Rip(db.Model):
    p_id = db.Column(db.Integer, primary_key=True)
    arm_version = db.Column(db.String(20))
    disctype = db.Column(db.String(20))
    label = db.Column(db.String(256))
    title = db.Column(db.String(256))
    year = db.Column(db.Integer)
    rip_title_ms = db.Column(db.String(256))
    rip_title_omdb_id = db.Column(db.String(20))
    ripmethod = db.Column(db.String(10))
    mkv_args = db.Column(db.String(256))
    hb_preset_dvd = db.Column(db.Text)
    hb_preset_bd = db.Column(db.Text)
    hb_args_dvd = db.Column(db.Text)
    hb_args_bd = db.Column(db.Text)
    errors = db.Column(db.Text)
    logfile = db.Column(db.String(256))
    start_time = db.Column(db.DateTime)
    stop_time = db.Column(db.DateTime)
    rip_time = db.Column(db.Integer)
    status = db.Column(db.String(32))

    def __repr__(self):
        return '<Rip {}>'.format(self.label) 