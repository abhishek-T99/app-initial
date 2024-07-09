# Database Conventions

*   Use `Base` class from `core.lib.models` for SQLAlchemy Model declarative base.
*   Do not use Enums for database field. Use String instead. Use Enums on schema.
*   Do not use `default` kwarg to define `Column`s in tables. Use `server_default` instead. Example:

```python
from sqlalchemy import Boolean, Column, Integer, false
from core.lib.models import SingletonBase
class DeviceBindSetting(SingletonBase):
    id = Column(Integer, primary_key=True, index=True)
    enable_id_number_validation = Column(Boolean, server_default=false())
```

*   For Singleton Models, make sure default values are defined in the model
