"""ExpectedTitle: a title we expect to find on the disc, sourced from metadata.

Populated at identification time. Used downstream by the track filter
(Layer C, deferred) and by the matcher (already consumes episode runtimes).

Generic shape covers single-feature movies (1 row), TV series (N rows
per episode), and anthology / multi-feature discs (N rows per work).
"""
from datetime import datetime

from arm.database import db


class ExpectedTitle(db.Model):
    __tablename__ = "expected_title"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.Integer, db.ForeignKey("job.job_id"), nullable=False, index=True
    )
    source = db.Column(db.String(16), nullable=False)
    title = db.Column(db.String(256), nullable=True)
    season = db.Column(db.Integer, nullable=True)
    episode_number = db.Column(db.Integer, nullable=True)
    external_id = db.Column(db.String(32), nullable=True)
    runtime_seconds = db.Column(db.Integer, nullable=True)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        ep = (
            f" S{self.season}E{self.episode_number:02d}"
            if self.season is not None and self.episode_number is not None
            else ""
        )
        return f"<ExpectedTitle {self.source}:{self.title}{ep} {self.runtime_seconds}s>"
