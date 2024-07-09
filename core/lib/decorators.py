import inspect
from typing import Any, Callable, List, Optional, Type
from fastapi import Form

from pydantic.fields import ModelField
from pydantic.main import BaseModel


# TODO Make the decorator take anything that add_api_route takes, response_model, status_code, etc.
# TODO Use functool.wraps
def action(
    detail: bool = False,
    action_code: Optional[int | str] = None,
    methods: Optional[List[str]] = None,
    url_path: Optional[str] = None,
    method: Optional[str] = None,
    interceptor: Optional[Any] = None,
    **kwargs: Any,
) -> Callable:
    """
    Mark a ViewSet method as a routable action.

    `@action`-decorated functions will be used to add additional method-based behaviors
    on the routed action.

    :param methods: A list of HTTP method names this action responds to.
                    Defaults to GET only.
    :param detail: Required. Determines whether this action applies to
                   instance/detail requests or collection/list requests.
    :param url_path: Define the URL segment for this action. Defaults to the
                     name of the method decorated.
    :param action_code: The action code for this action.  This is used to
                        generate the action name and URL segment if not
                        provided.
    :param method: The HTTP method name this action responds to.  This is
                     equivalent to setting `methods=[method]`.
    :param interceptor: The interceptor class to use for this action. This is
                        just additional decorators that will be applied to the
                        view function.
    :param kwargs: Additional properties to set on the view.  This can be used
                   to override viewset-level settings. Also, any additional
                    keyword arguments will be passed to the FastAPI `add_api_route`
                    function.
    """

    def decorator(func: Callable) -> Callable:
        func._is_action = True
        func.detail = detail
        func.methods = methods
        func.url_path = url_path
        if method:
            func.methods = [method]
        func.extra_kwargs = kwargs
        func.action_name = func.__name__
        if action_code is not None:
            func.__name__ += f" (F-{action_code})"
        func.dependencies = []
        func.interceptor = interceptor
        func.url_path = url_path
        return func

    return decorator


def as_form(cls: Type[BaseModel]):
    """
    Decorator function to convert a pydantic model into a form representation.
    Args:
    cls (Type[BaseModel]): The pydantic model class to be converted.
    Returns:
    Type[BaseModel]: The modified pydantic model class with an added `as_form` method.
    Raises:
    None
    my_form = MyModel.as_form()
    """
    new_parameters = []
    for _, model_field in cls.__fields__.items():
        model_field: ModelField
        new_parameters.append(
            inspect.Parameter(
                model_field.alias,
                inspect.Parameter.POSITIONAL_ONLY,
                default=Form(...)
                if model_field.required
                else Form(model_field.default),
                annotation=model_field.outer_type_,
            )
        )

    async def as_form_func(**data):
        return cls(**data)

    sig = inspect.signature(as_form_func)
    sig = sig.replace(parameters=new_parameters)
    as_form_func.__signature__ = sig
    setattr(cls, "as_form", as_form_func)

    return cls
