import inspect
import re
from enum import Enum
from fastapi import (
    APIRouter,
    FastAPI,
    Form,
    HTTPException,
    Request as BaseRequest,
    Response,
    UploadFile,
    Depends,
)
from inspect import Parameter, Signature, signature
from pydantic import BaseConfig, BaseModel
from pydantic.fields import ModelField
from pydantic.generics import GenericModel
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import Session
from starlette.datastructures import State
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Generic,
    List,
    Literal,
    Protocol,
    Type,
    TypeAlias,
    TypeVar,
    Union,
    runtime_checkable,
)
from uuid import UUID

from core.db import Base
from core.db.session import get_db
# from core.kafka import producer
from core.lib.exception_handlers import handle_integrity_error
from core.lib.exceptions import NotFound
# from core.lib.file import save_upload_file
from core.lib.permissions import BasePermission

NOT_FOUND_MESSAGE: str = "Resource not found"


class RequestState(State):
    db: Session
    user: Any | None


class Request(BaseRequest):
    state: RequestState  # type: ignore


# class SQLAlchemyBase(Base):
#     id: int | UUID
#     __tablename__: str
#     __name__: str
#     __call__: Callable[..., Base]
#     __singleton__: bool | None


T = TypeVar("T", bound=BaseModel)


class PaginationSchema(BaseModel):
    count: int
    page: int
    pages: int
    size: int


class PaginatedResponseSchema(GenericModel, Generic[T]):
    pagination: PaginationSchema
    results: List[T]


class SchemalessPaginatedResponseSchema(BaseModel):
    pagination: PaginationSchema
    results: List[dict | Any]

    class Config:
        orm_mode = True


# TODO Use functools.wraps
# TODO replace Any with a more specific return type
# TODO May be not use Protocol at all
# TODO Refactor into several files
# TODO Easy overriding of CRUD methods
# TODO MAYBE get, post, put, patch, delete methods in the viewset a la DRF


@runtime_checkable
class ViewSetProtocol(Protocol):
    schema: Type[BaseModel] | None
    read_schema: Type[BaseModel] | None
    get_schema_class: Callable[..., Any]
    get_queryset: Callable[..., Any]
    get_object: Callable[..., Any]
    get_create_response_schema: Callable[..., Type[BaseModel]]
    get_update_response_schema: Callable[..., Type[BaseModel]]
    db: Session
    model: Type[Base]
    request: Request
    action: str
    args: tuple[Any]
    kwargs: dict[str, Any]
    prefix: str
    is_singleton: bool
    sync_data: Callable[..., Any]


class ListViewSetProtocol(ViewSetProtocol, Protocol):
    list_schema: Type[BaseModel] | None
    page_size: int | None
    page_number: int = 1
    count: int
    paginate_queryset: Callable[..., Any]
    paginate_response: Callable[..., Any]
    get_list_data: Callable[..., Any]
    get_list_response_model: Callable[..., Any]
    filter_list_queryset: Callable[..., Any]
    list: Callable[..., Any]


class RetrieveViewSetProtocol(ViewSetProtocol, Protocol):
    retrieve_schema: Type[BaseModel] | None
    retrieve: Callable[..., Any]


class DeleteViewSetProtocol(ViewSetProtocol, Protocol):
    delete: Callable[..., Any]


class CreateViewProtocol(ViewSetProtocol, Protocol):
    create_schema: Type[BaseModel] | None
    _create_signature_for_upload_file: Callable[..., Signature]
    _create_wrapper: Callable[..., Callable[..., Any]]
    create_with_upload: Callable[..., Any]
    create: Callable[..., Any]


class UpdateViewProtocol(ViewSetProtocol, Protocol):
    update_schema: Type[BaseModel] | None
    _create_signature_for_upload_file: Callable[..., Signature]
    _update_wrapper: Callable[..., Callable[..., Any]]
    update_with_upload: Callable[..., Any]
    update: Callable[..., Any]


# class GenericViewSetProtocol(Protocol):


class ModelViewSetProtocol(
    ListViewSetProtocol,
    RetrieveViewSetProtocol,
    UpdateViewProtocol,
    CreateViewProtocol,
    DeleteViewSetProtocol,
    ViewSetProtocol,
    Protocol,
):
    pass


class ListMixin:
    page_size: int | None = 20

    def get_list_response_model(self: ListViewSetProtocol):
        schema = self.list_schema or self.read_schema or self.schema
        if not schema and self.schema is not False:
            raise NotImplementedError(
                "Either `list_schema` or `read_schema` or `schema` must be defined for List view."
            )
        if schema and self.page_size:
            return PaginatedResponseSchema[schema]
        elif schema:
            return List[schema]
        elif schema is False and self.page_size:
            return SchemalessPaginatedResponseSchema
        else:
            # TODO replace Any with a more specific return type SQlAlchemy object
            return List[dict | Any]

    def get_list_data(self, data):
        # schema = self.get_schema_class()
        # if not schema:
        #     return data.all()
        # Config = type(
        #     "Config", (), {
        #         "arbitrary_types_allowed": True,
        #         "orm_mode": True
        #     })
        # list_class = type('List',  (BaseModel,), {"__root__": (List[schema],),
        #                                           "Config": Config,
        #                                           })
        # return [schema_class(**obj.__dict__) for obj in data.all()]
        # return list_class.parse_obj(data.all())
        return data.all()

    def paginate_queryset(self: ListViewSetProtocol, queryset):
        if self.page_size:
            self.page_number = int(self.request.query_params.get("page", 1))
            self.count = queryset.count()
            queryset = queryset.limit(self.page_size).offset(
                (self.page_number - 1) * self.page_size
            )
        return queryset

    def paginate_response(self, data):
        count = self.count
        size = self.page_size
        pagination = {
            "count": count,
            "page": self.page_number,
            "pages": (count + (-count % size)) // size,  # round-up division
            "size": size,
        }
        response_data = {"pagination": pagination, "results": data}
        # if self.aggregate:
        #     response_data['aggregate'] = self.aggregate
        return response_data

    def filter_list_queryset(self, queryset):
        return queryset

    def _list_wrapper(
        self: ListViewSetProtocol, request: Request, db: Session = Depends(get_db)
    ):
        self.action = "list"
        self.db = db
        self.request = process_request(self, request)
        return self.list()

    def list(self: ListViewSetProtocol):
        qs = self.get_queryset()
        qs = self.filter_list_queryset(qs)
        if self.page_size:
            paged_data = self.paginate_queryset(qs)
            return self.paginate_response(self.get_list_data(paged_data))
        else:
            return self.get_list_data(qs)


class RetrieveMixin:
    def _retrieve_wrapper(
        self: RetrieveViewSetProtocol,
        id: int | UUID,
        request: Request,
        db: Session = Depends(get_db),
    ):
        self.action = "retrieve"
        self.db = db
        self.request = process_request(self, request)
        return self.retrieve()

    def retrieve(self: ViewSetProtocol):
        return self.get_object()


def process_request(viewset, request: Request) -> Request:
    if hasattr(viewset, "db") and viewset.db:
        request.state.db = viewset.db
    # access_token = request.headers.get("access-token")
    # if access_token:
    #     request.state.access_token = access_token
    #     user = get_current_user(access_token, viewset.db)
    #     if user:
    #         request.state.user = user
    #         request.user = user
    return request


class CreateMixin:
    def create(self: CreateViewProtocol, body: BaseModel):
        # TODO When schema is not provided?
        obj = self.model(**body.dict())
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def create_with_upload(
        self: CreateViewProtocol,
        request: Request,
        db: Session = Depends(get_db),
        **kwargs,
    ):
        self.action = "create"
        self.db = db
        self.request = process_request(self, request)
        model_kwargs = {}
        for field_name, field_value in kwargs.items():
            if field_value.__class__.__name__ == "UploadFile":
                # field_value = save_upload_file(field_value)
                pass
            model_kwargs[field_name] = field_value
        obj = self.model(**model_kwargs)
        self.db.add(obj)
        try:
            self.db.commit()
        except IntegrityError as exc:
            handle_integrity_error(self.db, exc)
        self.db.refresh(obj)
        return obj

    def _create_wrapper(self: CreateViewProtocol, schema: Type[BaseModel]):
        # If the schema contains UploadFile, generate a function and spread the pydantic
        # schema fields as function parameters
        # TODO Support list[UploadFile]
        if schema and any(
            field_value.type_ == UploadFile
            for field_value in schema.__fields__.values()
        ):
            func_sig = self._create_signature_for_upload_file(schema)

            def _create_(*args, **kwargs):
                """Create with file upload"""
                return self.create_with_upload(*args, **kwargs)

            _create_.__signature__ = func_sig
            _create_.view = self
            return _create_
        else:

            def _create(body: schema, request: Request, db: Session = Depends(get_db)):
                self.action = "create"
                self.db = db
                request = process_request(self, request)
                self.request = request
                try:
                    return self.create(body)
                except IntegrityError as exc:
                    handle_integrity_error(self.db, exc)

            _create.view = self
            return _create


class UpdateMixin:
    def update(self: UpdateViewProtocol, id: int | UUID, body: BaseModel):
        # When no fields are provided
        data: dict[Any, Any] = body.dict(exclude_unset=True)
        if data == {}:
            # raise 422 Error
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "loc": ["body"],
                        "msg": "At least one field from schema is required.",
                        "type": "value_error.missing",
                    }
                ],
            )
        # TODO When schema is not provided?
        self.db.query(self.model).filter(self.model.id == id).update(data)
        self.db.commit()

        return self.db.query(self.model).filter(self.model.id == id).first()  # type: ignore

    def initial_form_data(
        self: UpdateViewProtocol,
        id: int | UUID,
        request: Request,
        db: Session = Depends(get_db),
    ):
        self.action = "initial-form-data"
        self.db = db
        self.request = process_request(self, request)
        return self.get_object()

    def update_with_upload(
        self: UpdateViewProtocol,
        request: Request,
        db: Session = Depends(get_db),
        **kwargs,
    ):
        self.action = "update"
        self.db = db
        self.request = process_request(self, request)
        model_kwargs = {}
        for field_name, field_value in kwargs.items():
            if field_value.__class__.__name__ == "UploadFile":
                # field_value = save_upload_file(field_value)
                pass
            model_kwargs[field_name] = field_value
        obj_id = model_kwargs.pop("id")
        self.db.query(self.model).filter(self.model.id == obj_id).update(model_kwargs)
        self.db.commit()
        return self.db.query(self.model).filter(self.model.id == obj_id).first()

    def _update_wrapper(self: UpdateViewProtocol, schema: Type[BaseModel]):
        if schema and any(
            field_value.type_ == UploadFile
            for field_value in schema.__fields__.values()
        ):
            func_sig = self._create_signature_for_upload_file(schema, id_path=True)

            def _update_(*args, **kwargs):
                """Update with file upload"""
                return self.update_with_upload(*args, **kwargs)

            _update_.__signature__ = func_sig
            _update_.view = self
            return _update_
        else:

            def _update(
                id: int | UUID,
                body: schema,
                request: Request,
                db: Session = Depends(get_db),
            ):
                self.action = "update"
                self.db = db
                self.request = process_request(self, request)
                try:
                    return self.update(id, body)
                except IntegrityError as exc:
                    handle_integrity_error(self.db, exc)

            _update.view = self
            return _update


class DeleteMixin:
    def delete(
        self: ViewSetProtocol,
        id: int | UUID,
        request: Request,
        db: Session = Depends(get_db),
    ):
        self.action = "delete"

        self.db = db
        self.request = process_request(self, request)
        try:
            self.db.query(self.model).filter(self.model.id == id).delete()  # type: ignore
            self.db.commit()
        except IntegrityError as exc:
            handle_integrity_error(self.db, exc)
        return ""


# def action_func(viewset_instance: Any, action_function: Callable) -> Callable:
#     @wraps(action_function)
#     def wrapper(*args: Any, **kwargs: Any) -> Any:
#         return action_function(viewset_instance, *args, **kwargs)
#     return wrapper


class CreateMixinWithDBSync(CreateMixin):
    def create(self: CreateViewProtocol, body: BaseModel):
        obj = super().create(body)
        self.sync_data(obj.id, self.request.method, body)
        return obj


class UpdateMixinWithDBSync(UpdateMixin):
    def update(self: UpdateViewProtocol, id: int | UUID, body: BaseModel):
        obj = super().update(id, body)
        self.sync_data(id, self.request.method, body)
        return obj


class DeleteMixinWithDBSync(DeleteMixin):
    def delete(
        self: ViewSetProtocol,
        id: int | UUID,
        request: Request,
        db: Session = Depends(get_db),
    ):
        print(self, id)
        super().delete(id, request, db)
        self.sync_data(id, request.method)
        return ""


def action_func(viewset_instance: Any, func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        viewset_instance.request = (
            kwargs.get("request")
            if "request" in signature(func).parameters.keys()
            else kwargs.pop("request")
        )

        viewset_instance.response = (
            kwargs.get("response")
            if "response" in signature(func).parameters.keys()
            else kwargs.pop("response")
        )

        viewset_instance.db = (
            kwargs.get("db")
            if "db" in signature(func).parameters.keys()
            else kwargs.pop("db")
        )

        if viewset_instance.request:
            viewset_instance.request = process_request(
                viewset_instance, viewset_instance.request
            )

        viewset_instance.id = (
            kwargs.get("id")
            if "id" in signature(func).parameters.keys()
            else kwargs.pop("id", None)
        )

        if func.interceptor:
            response = func.interceptor(viewset_instance, func, *args, **kwargs)
        else:
            response = func(viewset_instance, *args, **kwargs)
        # for interceptor in func.interceptors:
        #     response = interceptor(viewset_instance, response)
        return response

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__func__ = func
    wrapper.is_action = True
    wrapper.view = viewset_instance
    return wrapper


# https://github.com/pydantic/pydantic/discussions/3089


class OptionalModel(BaseModel):
    class Config(BaseConfig):
        @classmethod
        def prepare_field(cls, field: ModelField) -> None:
            field.required = False
            super().prepare_field(field)


def get_rand():
    import string
    import secrets

    # initializing size of string
    N = 7

    res = ""
    # using secrets.choice()
    # generating secrets strings
    for _ in range(N):
        res += "".join(secrets.choice(string.ascii_uppercase + string.digits))
    return res


if TYPE_CHECKING:
    T = TypeVar("T")
    Partial: TypeAlias = Union[T]
else:

    class Partial:
        def __class_getitem__(cls, item):
            rand = get_rand()
            return type(f"Partial{rand}{item.__name__}", (item, OptionalModel), {})


class NotFoundDetail(BaseModel):
    msg: Literal[NOT_FOUND_MESSAGE]  # type: ignore
    type: Literal["not_found"]


class NotFoundErrorResponse(BaseModel):
    detail: list[NotFoundDetail]


class GenericViewSet:
    model = None
    args = None
    kwargs = None
    router = None
    schema = None
    list_schema = None
    retrieve_schema = None
    read_schema = None
    create_schema = None
    create_response_schema = None
    update_schema = None
    update_response_schema = None
    form_schema = None
    initial_form_schema = None
    action = None
    prefix = None
    db: Session  # Tests can override this
    is_singleton: bool = False
    authentication: bool = False
    permission_classes: List[Type[BasePermission]] = []

    @classmethod
    def add_to(cls, app: FastAPI, prefix=None, tag=None, tags=[]):
        router, viewset_instance = cls.as_view(prefix=prefix, tag=tag, tags=tags)
        app.include_router(router)
        return viewset_instance

    @classmethod
    def as_view(
        cls,
        *args: Any,
        prefix=None,
        tag=None,
        tags: list[str | Enum] = [],
        **kwargs: Any,
    ):
        self: ModelViewSetProtocol = cls(*args, **kwargs)  # type: ignore
        self.args = args
        self.kwargs = kwargs
        prefix = prefix or self.prefix
        if not prefix:
            if self.model:
                prefix = self.model.__name__
            else:
                prefix = (
                    self.__class__.__name__.replace("ViewSet", "")
                    .replace("Viewset", "")
                    .replace("viewset", "")
                )
            # change prefix from pascal case to kebab case
            # prefix = self.model.__name__
            prefix = re.sub("([A-Z]+)", r"-\1", prefix).lower().strip("-")
        if not tags:
            tag = tag or prefix.replace("-", " ").title()
            tags = [tag]
        router = APIRouter(prefix="/{}".format(prefix), tags=tags)

        self.is_singleton = (
            self.model
            and hasattr(self.model, "__singleton__")
            and self.model.__singleton__ is True
        )

        # Add custom actions to the router

        # Generate function names in the order they appear in the viewset
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        ordered_methods = sorted(methods, key=lambda x: inspect.getsourcelines(x[1])[1])
        names = [x[0] for x in ordered_methods]

        # Documenting 404 response for OpenAPI
        error_404_response = {"model": NotFoundErrorResponse}
        responses = {404: error_404_response}

        if self.permission_classes:
            self.authentication = True
            permission_dependencies = [Depends(x) for x in self.permission_classes]
        else:
            permission_dependencies = []

        # for name in dir(cls):
        for name in names:
            func = getattr(cls, name)
            if hasattr(func, "_is_action"):
                url_path = func.url_path if hasattr(func, "url_path") else ""
                detail = func.detail
                methods = func.methods
                extra_kwargs = func.extra_kwargs
                dependencies = func.dependencies

                if "permission_classes" in extra_kwargs:
                    permission_classes = extra_kwargs.pop("permission_classes")
                    if permission_classes:
                        func.permission_classes = permission_classes
                        dependencies.extend([Depends(x) for x in permission_classes])
                elif permission_dependencies:
                    dependencies.extend(permission_dependencies)

                if extra_kwargs.get("permission_key"):
                    func.permission_key = extra_kwargs.pop("permission_key")

                wrapped_func = action_func(cls(*args, **kwargs), func)

                # Update the signature to exclude the 'self' parameter
                original_signature = signature(func)
                new_parameters = [
                    param
                    for name, param in original_signature.parameters.items()
                    if not (name == "self" or name == "request")
                ]

                # if there is no id parameter for detail, add one
                if detail and "id" not in original_signature.parameters.keys():
                    new_parameters.insert(
                        0,
                        Parameter(
                            "id",
                            kind=Parameter.POSITIONAL_OR_KEYWORD,
                            annotation=int | UUID,
                        ),
                    )

                new_parameters.insert(
                    0,
                    Parameter(
                        "request",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=Request,
                    ),
                )

                new_parameters.insert(
                    0,
                    Parameter(
                        "response",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=Response,
                    ),
                )

                # Add `db: Session = Depends(get_db)` as a dependency parameter
                # if "db" not in original_signature.parameters.keys():
                new_parameters.append(
                    Parameter(
                        "db",
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=Session,
                        default=Depends(get_db),
                    ),
                )

                if not url_path:
                    action_name = name.replace("_", "-")
                else:
                    action_name = url_path

                # Include the custom action in the router
                if detail:
                    path = f"/{{id}}/{action_name}"

                    if "responses" in extra_kwargs:
                        extra_kwargs["responses"].update(responses)
                    else:
                        extra_kwargs["responses"] = responses
                else:
                    path = f"/{action_name}"

                wrapped_func.__signature__ = original_signature.replace(
                    parameters=new_parameters
                )

                router.add_api_route(
                    path,
                    endpoint=wrapped_func,
                    methods=methods,
                    dependencies=dependencies,
                    **extra_kwargs,
                )

        dependencies = []
        if permission_dependencies:
            dependencies = permission_dependencies

        # TODO Move this to SingletonModelViewSet
        if self.is_singleton:
            if hasattr(self, "retrieve"):
                router.add_api_route(
                    "",
                    endpoint=self.retrieve,
                    methods=["GET"],
                    response_model=self.get_schema_class("retrieve"),
                    dependencies=dependencies,
                )
            if hasattr(self, "update"):
                router.add_api_route(
                    "",
                    endpoint=self._update_wrapper(self.get_schema_class("update")),
                    methods=["PATCH"],
                    response_model=self.get_update_response_schema(),
                    dependencies=dependencies,
                )
        else:
            # TODO Move this to ModelViewSet
            if hasattr(self, "list"):
                router.add_api_route(
                    "",
                    endpoint=self._list_wrapper,
                    methods=["GET"],
                    response_model=self.get_list_response_model(),
                    dependencies=dependencies,
                )
            if hasattr(self, "retrieve"):
                router.add_api_route(
                    "/{id}",
                    endpoint=self._retrieve_wrapper,
                    methods=["GET"],
                    response_model=self.get_schema_class("retrieve"),
                    responses=responses,
                    dependencies=dependencies,
                )
            if hasattr(self, "create"):
                router.add_api_route(
                    "",
                    endpoint=self._create_wrapper(self.get_schema_class("create")),
                    methods=["POST"],
                    response_model=self.get_create_response_schema(),
                    status_code=201,
                    dependencies=dependencies,
                )
            if hasattr(self, "update"):
                router.add_api_route(
                    "/{id}",
                    endpoint=self._update_wrapper(self.get_schema_class("update")),
                    methods=["PATCH"],
                    response_model=self.get_update_response_schema(),
                    responses=responses,
                    dependencies=dependencies,
                )
            if hasattr(self, "initial_form_data"):
                router.add_api_route(
                    "/{id}/initial-form-data",
                    endpoint=self.initial_form_data,
                    methods=["GET"],
                    response_model=self.get_schema_class("initial_form_data"),
                    dependencies=dependencies,
                )
            if hasattr(self, "delete"):
                router.add_api_route(
                    "/{id}",
                    endpoint=self.delete,
                    status_code=204,
                    methods=["DELETE"],
                    responses=responses,
                    dependencies=dependencies,
                )

        return router, self

    def _create_signature_for_upload_file(
        self, schema: Type[BaseModel], id_path: bool = False
    ):
        parameters_with_defaults = [
            Parameter(
                "db",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Session,
                default=Depends(get_db),
            )
        ]
        parameters_without_defaults = [
            Parameter(
                "request", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=Request
            )
        ]
        if id_path:
            parameters_without_defaults.append(
                Parameter(
                    "id", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=int | UUID
                )
            )
        for field_name, field_value in schema.__fields__.items():
            param_kwargs: dict[str, Any] = {"kind": Parameter.POSITIONAL_OR_KEYWORD}
            data_type = field_value.type_
            if data_type == UploadFile:
                param_kwargs["annotation"] = UploadFile
                if not field_value.required:
                    param_kwargs["default"] = None
            elif field_value.default is not None:
                param_kwargs["annotation"] = field_value.type_
                param_kwargs["default"] = Form(field_value.default)
            elif not field_value.required:
                param_kwargs["annotation"] = field_value.type_
                param_kwargs["default"] = Form(None)
            else:
                param_kwargs["annotation"] = Annotated[field_value.type_, Form(...)]
            param = Parameter(field_name, **param_kwargs)
            if param_kwargs.get("default") is not None or not field_value.required:
                parameters_with_defaults.append(param)
            else:
                parameters_without_defaults.append(param)
        parameters = parameters_without_defaults + parameters_with_defaults
        return Signature(parameters)

    def get_queryset(self):
        return self.db.query(self.model)

    def get_create_response_schema(self) -> Type[BaseModel]:
        return self.create_response_schema or self.read_schema or self.schema

    def get_update_response_schema(self):
        return self.update_response_schema or self.read_schema or self.schema

    def get_schema_class(self, action: str | None = None):
        action = action or self.action
        if action == "list":
            schema = self.list_schema or self.read_schema or self.schema
            if not schema and self.schema is not False:
                raise NotImplementedError(
                    "Either `list_schema` or `read_schema` or `schema` must be defined "
                    "for List view."
                )
            return schema or None
        if action == "create":
            schema = self.create_schema or self.form_schema or self.schema
            if not schema:
                # if not schema and self.schema is not False:
                raise NotImplementedError(
                    "Either `schema` or `form_schema `or `create_schema` must be "
                    " defined for Create view."
                )
            return schema or None
        if action == "update":
            schema = self.update_schema or self.form_schema or self.schema
            if not schema:
                # if not schema and self.schema is not False:
                raise NotImplementedError(
                    "Either `schema` or `form_schema` or `update_schema` must be "
                    "defined for Update view."
                )
            return Partial[schema] if schema else None
        if action == "retrieve":
            schema = self.retrieve_schema or self.read_schema or self.schema
            if not schema and self.schema is not False:
                raise NotImplementedError(
                    "Either `retreive_schema` or `read_schema` or `schema` must be "
                    "defined for Retrieve view."
                )
            return schema or None
        if action == "initial_form_data":
            schema = (
                self.initial_form_schema
                or self.update_schema
                or self.form_schema
                or self.schema
            )
            if not schema and self.schema is not False:
                raise NotImplementedError(
                    "Either `initial_form_schema` or `update_schema` or `form_schema` "
                    "or `schema` must be defined for Retrieve view."
                )
            return schema or None

    get_schema = get_schema_class


class GenericModelViewSet(GenericViewSet):
    def get_object(self: ViewSetProtocol):
        # TODO Cache this to avoid multiple queries, return the same object
        # if it's already queried
        try:
            obj = (
                self.db.query(self.model)
                .filter(self.model.id == self.request.path_params["id"])
                .first()
            )
        except Exception as exc:
            if isinstance(exc, DataError):
                self.db.rollback()
                raise NotFound(exception_type="not_found", msg=NOT_FOUND_MESSAGE)
            raise exc
        if not obj:
            raise NotFound(exception_type="not_found", msg=NOT_FOUND_MESSAGE)
        return obj

    def __init__(self, *args, **kwargs) -> None:
        if not self.model:
            raise NotImplementedError("ModelViewSet must define a `model` attribute.")
        if hasattr(self, "fields"):
            raise NotImplementedError(
                "`fields` attribute is not implemented yet. Use schema instead."
            )
        super().__init__(*args, **kwargs)


class SingletonModelViewSet(GenericModelViewSet):
    def get_object(self: ViewSetProtocol):
        instance = self.db.query(self.model).first()
        if instance is None:
            default_data = (
                self.model.initial_data if hasattr(self.model, "initial_data") else {}
            )
            instance = self.model(**default_data)
            self.db.add(instance)
            self.db.commit()
        return instance

    def retrieve(
        self: ViewSetProtocol, request: Request, db: Session = Depends(get_db)
    ):
        self.action = "retrieve"
        self.request = request
        self.db = db
        return self.get_object()

    def update(
        self: ViewSetProtocol,
        body: BaseModel,
    ):
        # TODO Support file upload in singleton update
        # TODO MAYBE Use Update Mixin and just override the db update line by moving it
        # to a separate internal method
        # When no fields are provided
        data = body.dict(exclude_unset=True)
        if data == {}:
            # raise 422 Error
            raise HTTPException(
                status_code=422,
                detail=[
                    {
                        "loc": ["body"],
                        "msg": "At least one field from schema is required.",
                        "type": "value_error.missing",
                    }
                ],
            )
        self.db.query(self.model).update(data)
        self.db.commit()
        return self.db.query(self.model).first()

    def _update_wrapper(self: UpdateViewProtocol, schema: Type[BaseModel]):
        def _update(body: schema, request: Request, db: Session = Depends(get_db)):
            self.action = "update"
            self.request = request
            self.db = db
            return self.update(body)

        _update.view = self
        return _update


action_mapping = {
    "post": "create",
    "patch": "update",
    "delete": "delete",
}


# class GenericModelViewSetWithDBSync(GenericModelViewSet):
#     def sync_data(
#         self: ViewSetProtocol,
#         id: int | UUID,
#         method: str,
#         data: BaseModel | None = None,
#     ):
#         if method.lower() not in action_mapping:
#             return
#         topic_name = action_mapping[method.lower()] + "-" + self.model.__name__.lower()
#         if method != "DELETE":
#             if not data:
#                 raise ValueError("Data must be provided for sync_data")
#             data = data.dict(exclude_unset=True)
#             data["id"] = id
#             producer.send(
#                 topic_name,
#                 data,
#             )
#         else:
#             producer.send(
#                 topic_name,
#                 {"id": id},
#             )


class ModelViewSet(
    ListMixin, RetrieveMixin, CreateMixin, UpdateMixin, DeleteMixin, GenericModelViewSet
):
    pass


class ReadOnlyModelViewSet(ListMixin, RetrieveMixin, GenericModelViewSet):
    pass


# class ModelViewSetWithDBSync(
#     ListMixin,
#     RetrieveMixin,
#     CreateMixinWithDBSync,
#     UpdateMixinWithDBSync,
#     DeleteMixinWithDBSync,
#     GenericModelViewSetWithDBSync,
# ):
#     pass
