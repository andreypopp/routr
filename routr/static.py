"""

    routr.static -- serve static assets
    ===================================

    This module provides shortcut for defining routes which serve static assets
    from directory and uses :mod:`webob.static` to serve static files.

"""

from os.path import join
from webob import Response
from webob.static import FileApp
from routr import route, GET

__all__ = ('static',)

class _ForceResponse(Response):

    def __init__(self, underlying):
        self.underlying = underlying

    def __call__(self, environ, start_response):
        return self.underlying(environ, start_response)

def static(prefix, directory, **kw):
    """ Define a route which serves static assets

    :param prefix:
        URL prefix on which to serve static assets
    :param directory:
        directory from which to serve static assets
    """
    if prefix.endswith('/'):
        prefix = prefix[:-1]
    kw['static_view'] = True
    return route(
        GET, '%s/{path:path}' % prefix,
        make_static_view(directory), **kw)

def make_static_view(directory):
    def static_view(request, path):
        """ View for serving static files"""
        return _ForceResponse(FileApp(join(directory, path))(request))
    static_view.static_view = True # b/c
    return static_view
