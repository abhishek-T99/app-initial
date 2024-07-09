from datetime import date, datetime
from uuid import UUID

from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from apps.user.schemas.manage import (
    UserListSchema,
    UserLoginSessionRecord,
    UserReadSchema, )
from core.db.session import get_db
from core.lib.decorators import action
from core.lib.exceptions import BadRequest
from core.lib.permissions import IsBackofficeUser
from core.lib.viewsets import (
    GenericViewSet,
    ListMixin,
    ListViewSetProtocol,
    ModelViewSet,
    UpdateViewProtocol,
)
from ..models import User, UserLoginSession


class ManageUserViewSet(ModelViewSet):
    model = User
    read_schema = UserReadSchema
    list_schema = UserListSchema
    schema = UserReadSchema
    permission_classes = [IsBackofficeUser]

    def update(self: UpdateViewProtocol, id: int | UUID, body: BaseModel):
        res = super().update(id, body)
        return res
    
    def _list_wrapper(
            self: ListViewSetProtocol,
            request: Request,
            search: str,
            db: Session = Depends(get_db),
    ):
        return super()._list_wrapper(request, db)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if "search" in self.request.query_params:
            q = f"%{self.request.query_params['search']}%"
            # Case-insensitive queryset filter by User's name or phone number
            queryset = queryset.filter(
                or_(self.model.name.ilike(q), self.model.phone_number.ilike(q))
            )
        return queryset
    
    def filter_list_queryset(self, queryset):
        return queryset.order_by(self.model.name)
    
    @action(detail=True, method="POST")
    def unblock(self):
        obj = self.get_object()
        obj.is_locked = False
        self.db.commit()
        return {}
