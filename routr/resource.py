"""

    routr.resource -- Exposing data model as container-resource REST API
    ====================================================================

"""

from routr import route
from routr import GET, POST, PUT, DELETE, PATCH

__all__ = ("resource", "Resource")

class Resource(object):

    cls = NotImplemented
    schema = NotImplemented
    name = NotImplemented

    def list(self, rng):
        pass

    def create(self, data):
        pass

    def get(self, id):
        pass

    def replace(self, id, data):
        pass

    def update(self, id, data):
        pass

    def delete(self, id):
        pass

def resource(res):
    return route(
        route(GET,          res.list,       name="list-%s"      % res.name),
        route(POST,         res.create,     name="create-%s"    % res.name),
        route("{id}",
            route(GET,      res.get,        name="get-%s"       % res.name),
            route(UPDATE,   res.replace,    name="replace-%s"   % res.name),
            route(PATCH,    res.update,     name="update-%s"    % res.name),
            route(DELETE,   res.delete,     name="delete-%s"    % res.name)))
