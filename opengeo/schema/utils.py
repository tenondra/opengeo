import inspect
from functools import wraps

from graphene.utils.subclass_with_meta import SubclassWithMeta_Meta
from graphql import ResolveInfo
from graphql_jwt import exceptions

UNAUTHORIZED = "You do not have permission to perform this action."


def get_player_id(info: ResolveInfo):
    return str(info.context.user.id)


def make_request_test(test):
    def wrapper(info: ResolveInfo, *args, **kwargs):
        mutation = next((arg
                         for arg in args
                         if isinstance(arg, SubclassWithMeta_Meta)), None)
        return test(info=info, mutation=mutation, **kwargs)

    return wrapper


@make_request_test
def same_player_test(info, mutation, **kwargs):
    if mutation is not None:
        return get_player_id(info) == kwargs.get(mutation._meta.input_field_name).get("id")
    return get_player_id(info) == kwargs.get("id")


def apply_to_class(fn, method_names=None):
    """
    Decorator for applying a function to methods of a class
    :return:
    """
    if method_names is None:
        method_names = ["create", "update", "delete"]

    def decorate(cls):
        for name, method in inspect.getmembers(cls, inspect.ismethod):
            if name in method_names:
                setattr(cls, name, fn(method))
        return cls

    return decorate


def request_passes_test(test_func, exc=exceptions.PermissionDenied):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            info = next(arg for arg in args if isinstance(arg, ResolveInfo))
            if test_func(info, *args, **kwargs):
                return f(*args, **kwargs)
            raise exc

        return wrapper

    return decorator
