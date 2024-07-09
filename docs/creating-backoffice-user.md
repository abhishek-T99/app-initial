```bash
python
```

```python
from apps.backoffice.models import StaffUser
from core.db.session import get_db_context

with get_db_context() as db:
    obj = StaffUser.create(db, phone_number='9851138343', send_email=False)
print(obj.plain_password)
```

If username is not passed to `StaffUser.create`, `phone_number` is used as the username.\
The plaintext password is not saved to the database. It is only returned so that password can be viewed or share for one-time. This password can not be viewed or retrieved again.
