"""Transaction replay preserves the final uncommitted unit of work."""
import pytest
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.orm import Session, declarative_base

from arm.ui import pending_changes

Base = declarative_base()


class Item(Base):
    __tablename__ = "retry_item"
    id = Column(Integer, primary_key=True)
    name = Column(String)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value
    engine.dispose()


def retry(session):
    changes = pending_changes.collect(session)
    session.rollback()
    pending_changes.replay(session, changes)
    session.commit()


def test_replay_keeps_new_updated_and_deleted_rows(session):
    old, removed = Item(name="old"), Item(name="remove")
    session.add_all([old, removed])
    session.commit()
    old.name = "new value"
    session.delete(removed)
    session.add(Item(name="inserted"))
    retry(session)
    assert sorted(session.scalars(select(Item.name))) == ["inserted", "new value"]


def test_insert_flushed_then_deleted_is_not_resurrected(session):
    item = Item(name="cancelled")
    session.add(item)
    session.flush()
    session.delete(item)
    session.flush()
    retry(session)
    assert list(session.scalars(select(Item))) == []


def test_insert_flushed_then_modified_keeps_final_value(session):
    item = Item(name="initial")
    session.add(item)
    session.flush()
    item.name = "final"
    retry(session)
    assert list(session.scalars(select(Item.name))) == ["final"]


def test_replay_keeps_latest_value_across_multiple_flushes(session):
    item = Item(name="committed")
    session.add(item)
    session.commit()
    item.name = "first"
    session.flush()
    item.name = "second"
    session.flush()
    item.name = "last"
    retry(session)
    assert list(session.scalars(select(Item.name))) == ["last"]


@pytest.mark.parametrize("finish", ["commit", "rollback"])
def test_old_transaction_is_not_replayed(session, finish):
    session.add(Item(name="old transaction"))
    session.flush()
    getattr(session, finish)()
    changes = pending_changes.collect(session)
    assert not any(changes.values())
