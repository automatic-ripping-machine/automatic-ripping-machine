"""Keep a transaction's other changes across a "database is locked" retry

database_updater() and database_adder() roll the session back after a locked commit and try
again. A rollback discards everything the transaction held, not just the caller's own values:
Config fields set directly before database_updater(), a Notifications row added just before it,
or changes an autoflush already sent. collect() records them before the first try, and replay()
puts them back after each rollback.
"""
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, scoped_session

# Changes an autoflush already sent in the open transaction. A flush clears their attribute
# history, but a rollback still undoes them, so they are recorded as they are flushed.
FLUSHED = "arm_flushed_changes"


def _empty():
    return {"new": {}, "dirty": {}, "deleted": {}}


def _add(session, changes):
    for item in session.new:
        changes["new"][id(item)] = item
    for item in session.dirty:
        state = inspect(item)
        values = {attr.key: state.attrs[attr.key].history.added[0]
                  for attr in state.mapper.column_attrs if state.attrs[attr.key].history.added}
        if values:
            changes["dirty"].setdefault(id(item), (item, {}))[1].update(values)
    for item in session.deleted:
        changes["deleted"][id(item)] = item
    return changes


@event.listens_for(Session, "after_flush")
def _remember_flush(session, _context):
    # after_flush still sees the flushed objects and their attribute history
    _add(session, session.info.setdefault(FLUSHED, _empty()))


@event.listens_for(Session, "after_commit")
@event.listens_for(Session, "after_rollback")
def _forget_flush(session):
    session.info.pop(FLUSHED, None)


def collect(session, changes=None):
    """Every uncommitted change of the session, added to ``changes`` when given"""
    session = session() if isinstance(session, scoped_session) else session
    changes = changes or _empty()
    for kind, items in session.info.get(FLUSHED, _empty()).items():
        for key, value in items.items():
            if kind == "dirty":
                changes["dirty"].setdefault(key, (value[0], {}))[1].update(value[1])
            else:
                changes[kind][key] = value
    _add(session, changes)
    # An insert followed by a delete in this transaction has no net row to replay.
    # Re-adding it after rollback would resurrect it, and deleting a pending object
    # instead raises InvalidRequestError.
    cancelled = changes["new"].keys() & changes["deleted"].keys()
    for key in cancelled:
        for items in changes.values():
            items.pop(key, None)
    return changes


def replay(session, changes):
    """Re-apply collected changes after a rollback"""
    # Loading an expired attribute while restoring another row must not flush a
    # half-restored transaction.
    with session.no_autoflush:
        for item, values in changes["dirty"].values():
            for key, value in values.items():
                setattr(item, key, value)
        for item in changes["new"].values():
            session.add(item)
        for item in changes["deleted"].values():
            session.delete(item)
