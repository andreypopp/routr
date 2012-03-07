"""

    routr.resource -- Exposing data model as container-resource REST API
    ====================================================================

"""

from routr import route
from routr import GET, POST, PUT, DELETE, PATCH

__all__ = ("resource",)

def resource(res, name=None):
    name = name or (res.__name__ if hasattr(res, "__name__") else str(res))
    collection_methods = [route(m, getattr(res, mn), name="%s-%s" % (mn, name))
        for mn, m in _collection_methods.items() if hasattr(res, mn)]
    resource_methods = [route(m, getattr(res, mn), name="%s-%s" % (mn, name))
        for mn, m in _resource_methods.items() if hasattr(res, mn)]
    return route(*collection_methods, route("{id}", *resource_methods))

_collection_methods = {
    "list": GET,
    "create": POST
    }

_resource_methods = {
    "get": GET,
    "replace": PUT,
    "update": PATCH,
    "delete": DELETE
    }
