from arm.database import db


class AppState(db.Model):
    """Singleton table (one row, id=1) for global application state.

    Follows the same pattern as UISettings — a single-row table for
    app-wide toggles that need to survive restarts and be queryable
    from both the ripper and the UI.
    """
    __tablename__ = 'app_state'

    id = db.Column(db.Integer, primary_key=True)
    ripping_paused = db.Column(db.Boolean, default=False, nullable=False)
    setup_complete = db.Column(db.Boolean, default=False, nullable=False)
    makemkv_key_valid = db.Column(db.Boolean, nullable=True, default=None)
    makemkv_key_checked_at = db.Column(db.DateTime, nullable=True, default=None)

    @classmethod
    def get(cls):
        """Return the singleton row, creating it if it doesn't exist.

        Handles the race condition where two threads both see None and
        try to insert: the loser's commit fails, so we retry the read.
        """
        state = cls.query.get(1)
        if state is not None:
            return state
        try:
            state = cls(id=1, ripping_paused=False, setup_complete=False)
            db.session.add(state)
            db.session.commit()
            return state
        except Exception:
            # Another thread likely created the row - rollback and re-read
            db.session.rollback()
            state = cls.query.get(1)
            if state is not None:
                return state
            raise  # genuinely broken - let caller handle it

    def __repr__(self):
        return f'<AppState ripping_paused={self.ripping_paused} setup_complete={self.setup_complete}>'
