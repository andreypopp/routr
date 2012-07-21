"""

    routr.static -- serve static files
    ==================================

    This module provides shortcut for defining routes which serve static files
    from directory and uses :mod:`webob.static` to serve static files.

"""

from os.path import join
from webob.static import FileApp
from routr import route, GET

__all__ = ("static",)

def static(prefix, directory):
    """ Define a route which serves static files"""
    if prefix.endswith("/"):
        prefix = prefix[:-1]
    return route(GET, "%s/{path:path}" % prefix, make_static_view(directory))

def make_static_view(directory):
    def static_view(request, path):
        """ View for serving static files"""
        return FileApp(join(directory, path))(request)
    static_view.static_view = True
    return static_view
