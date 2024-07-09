from fastapi import HTTPException
from psycopg2.errors import ForeignKeyViolation, UniqueViolation

from core.lib.exceptions import ForeignKeyProtectedException, InvalidForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


def handle_integrity_error(db: Session, e: IntegrityError):
    db.rollback()
    if isinstance(e.orig, ForeignKeyViolation):
        msg = e.orig.pgerror
        if msg:
            if "is still referenced from" in msg:
                # find constraint from msg
                constraint = msg.split('foreign key constraint "')[1].split('"')[0]
                raise ForeignKeyProtectedException(constraint=constraint)
            else:
                start_index = msg.find('present in table "') + len('present in table "')
                end_index = msg.find('"', start_index)
                referenced_table = msg[start_index:end_index]
                raise InvalidForeignKey(table=referenced_table)
        else:
            raise InvalidForeignKey()
    elif isinstance(e.orig, UniqueViolation):
        msg = str(e.orig)
        try:
            key = msg.split('Key ("')[1].split('"')[0]
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "loc": ["body", key],
                        "msg": f"Duplicate value for {key}",
                        "type": "value_error.duplicate",
                    }
                ],
            )
        except IndexError:
            try:
                key = msg.split("Key (")[0].split('"')[1]
                if key.endswith("_key"):
                    key = key.split("_")[1]
                if key.endswith("_uc"):
                    key = key.split("_")[0]
                if "pkey" in key:
                    raise IndexError
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "loc": ["body", key],
                            "msg": f"Duplicate value for {key}",
                            "type": "value_error.duplicate",
                        }
                    ],
                )
            except IndexError:
                raise HTTPException(
                    status_code=422,
                    detail=[
                        {
                            "loc": ["body", "id"],
                            "msg": "Duplicate value for a field.",
                            "type": "value_error.duplicate",
                        }
                    ],
                )
    else:
        raise e
