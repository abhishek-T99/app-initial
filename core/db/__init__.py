import os
from datetime import datetime, time
from typing import Any

from sqlalchemy import event, TypeDecorator, DateTime, Time
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapper, DeclarativeBase

from core.config import config


class DateTimeField(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return value.astimezone()
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=None)
        return value


class TimeField(TypeDecorator):
    impl = Time(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=config.default_timezone)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=None)
        return value


def load_models(service_name: str | None = None):
    print("Loading models...")
    base_dir = config.base_dir
    # auto import all classes in models.py from the folders app.*
    # loop through all top level directories inside the apps folder
    if service_name and service_name != "gateway":
        service_dir_root = os.path.join(base_dir, "services", service_name)
        if os.path.exists(os.path.join(service_dir_root, "routes.py")):
            __import__(f"services.{service_name}.routes", globals(), locals(), [], 0)
    else:
        app_dir_root = os.path.join(base_dir, "apps")
        for app_dir in os.listdir(app_dir_root):
            model_file = os.path.join(app_dir_root, app_dir, "models.py")
            if os.path.isfile(model_file):
                # import all classes from the models.py file
                __import__(f"apps.{app_dir}.models", globals(), locals(), [], 0)
    print("Done loading models.")


class Base(DeclarativeBase):
    type_annotation_map = {
        datetime: DateTimeField,
        time: TimeField,
    }

    id: Any
    metadata: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        tablename = cls.__name__.lower()
        if "test" not in cls.__module__.lower():
            app_name = cls.__module__.strip().split(".", 1)[1].split(".")[0].lower()
            tablename = app_name + "_" + cls.__name__.lower()
        return tablename


class CachedBase(DeclarativeBase):
    id: Any
    metadata: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


@event.listens_for(Mapper, "before_configured", once=True)
def before_mapper_configure(*args, **kwargs):
    print("Initializing Mapper Configurations...")
    load_models(config.service_name)
