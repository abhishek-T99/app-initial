from core.db.session import get_db_context

from .models import StaffUser

with get_db_context() as db:
    obj = StaffUser.create(
        db,
        username="boadmin@admin.com",
        phone_number="",
        name="Backoffice Admin",
        send_email=False,
    )
    obj.is_superuser = True
    db.commit()
    db.refresh(obj)
    print(obj.plain_password)
    print("Superadmin created")
