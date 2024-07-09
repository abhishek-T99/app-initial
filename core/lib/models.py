from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base
from core.db.session import get_db_context


class ConsumerBase(Base):
    __abstract__ = True

    @classmethod
    def create(cls, data: dict):
        with get_db_context() as db:
            [data.pop(key) for key in data.copy() if key not in dir(cls)]
            db.add(cls(**data))
            db.commit()

    @classmethod
    def update(cls, data):
        with get_db_context() as db:
            [data.pop(key) for key in data.copy() if key not in dir(cls)]
            db.query(cls).filter_by(id=data["id"]).update(data)
            db.commit()

    @classmethod
    def delete(cls, data):
        with get_db_context() as db:
            db.query(cls).filter_by(id=data["id"]).delete()
            db.commit()


class SingletonBase(Base):
    __abstract__ = True
    __singleton__ = True

    initial_data = {}

    @classmethod
    def get(cls, session):
        # TODO Use KV store for this
        instance = session.query(cls).first()
        if instance is None:
            instance = cls(**cls.initial_data)
            session.add(instance)
            session.commit()
        return instance


class ConsumerSingletonBase(SingletonBase):
    __abstract__ = True

    @classmethod
    def create(cls, data):
        with get_db_context() as db:
            db.add(cls(**data))
            db.commit()

    @classmethod
    def update(cls, data):
        with get_db_context() as db:
            db.query(cls).filter_by(id=data["id"]).update(data)
            db.commit()


class TimeStampModel(Base):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
