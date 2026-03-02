"""
Batch Rename History Model
Tracks the history of batch rename operations for auditing and rollback.
"""
import datetime
from datetime import timezone

from arm.ui import db


class BatchRenameHistory(db.Model):
    """
    Class to hold the batch rename history for tracking and rollback
    """
    __tablename__ = 'batch_rename_history'

    history_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    batch_id = db.Column(db.String(64), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.job_id'), nullable=False)
    old_path = db.Column(db.String(512), nullable=False)
    new_path = db.Column(db.String(512), nullable=False)
    old_folder_name = db.Column(db.String(256), nullable=False)
    new_folder_name = db.Column(db.String(256), nullable=False)
    series_name = db.Column(db.String(256))
    disc_identifier = db.Column(db.String(32))
    consolidated_under_series = db.Column(db.Boolean, default=False)
    series_parent_folder = db.Column(db.String(256))
    renamed_by = db.Column(db.String(64), nullable=False)
    renamed_at = db.Column(db.DateTime, nullable=False)
    rolled_back = db.Column(db.Boolean, default=False)
    rollback_at = db.Column(db.DateTime)
    rollback_by = db.Column(db.String(64))
    rename_success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    naming_style = db.Column(db.String(32))
    zero_padded = db.Column(db.Boolean)

    def __init__(self, batch_id=None, job_id=None, old_path=None, new_path=None,
                 old_folder_name=None, new_folder_name=None, renamed_by=None,
                 series_name=None, disc_identifier=None,
                 consolidated_under_series=False, series_parent_folder=None,
                 naming_style=None, zero_padded=False):
        self.batch_id = batch_id
        self.job_id = job_id
        self.old_path = old_path
        self.new_path = new_path
        self.old_folder_name = old_folder_name
        self.new_folder_name = new_folder_name
        self.renamed_by = renamed_by
        self.renamed_at = datetime.datetime.now(timezone.utc)
        self.series_name = series_name
        self.disc_identifier = disc_identifier
        self.consolidated_under_series = consolidated_under_series
        self.series_parent_folder = series_parent_folder
        self.naming_style = naming_style
        self.zero_padded = zero_padded
        self.rename_success = True
        self.rolled_back = False

    def __repr__(self):
        return '<BatchRenameHistory {}>'.format(self.history_id)

    def __str__(self):
        """Returns a string of the object"""
        return_string = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            return_string = return_string + "(" + str(attr) + "=" + str(value) + ") "
        return return_string

    def get_d(self):
        """Returns a dict of the object"""
        return_dict = {}
        for key, value in self.__dict__.items():
            if '_sa_instance_state' not in key:
                return_dict[str(key)] = str(value)
        return return_dict
