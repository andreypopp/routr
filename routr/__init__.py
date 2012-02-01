""" `routr` package

Example usage::

    from routr import route, schema
    from webob import exc
    from myapp.utils import AuthRequired, XHROnly, GeoBlocking

    routing = route(
        route("myapp.views.index"),
        route("news", "myapp.views.news"),
        route("archive/{int:year}-{int:month}-{int:day}/", "myapp.views.arch"),
        route("forecast/{int}-{int}-{int}/", "myapp.views.forecast"),
        route(
            "api",
            route(
                "/news",
                "myapp.views.api.news",
                schema.params(user_id=schema.Integer, limit=schema.Integer),
            route("myapp.views.api.comments", "/comments"),
            [XHROnly]),
        [AuthRequired, GeoBlocking])

    adapter, view = routing(request, raise404=True)
    return adapter(view, request)

    router(
        "/news", "news_views",
        Params(limit=schema.Integer) + AuthRequired.user_id)

"""

from re import compile as re_compile
from webob import exc

__all__ = ("route", "NoMatchFound", "RouteConfigurationError")

class NoMatchFound(Exception):
    pass

class RouteNotFound(NoMatchFound):
    """ No route was matched for request"""

    response = exc.HTTPNotFound()

class RouteGuarded(NoMatchFound):
    """ There was matched routes but they were guarded

    :param response:
        underlying response from guard, usually it's instance of
        :class:``webob.exc.HTTPException``
    """

    def __init__(self, response):
        self.response = response

class RouteConfigurationError(Exception):
    """ Improperly configured routes"""

def route(*directives):
    """ Directive for configuring routes in application"""
    directives = list(directives)
    if not directives:
        raise RouteConfigurationError("empty 'route' statement")

    guards = directives.pop() if isinstance(directives[-1], list) else []

    def is_view_ref(d):
        return (
            isinstance(d, str)
            or hasattr(d, "__call__")
                and not isinstance(d, Route))

    # root directive
    if len(directives) == 1 and is_view_ref(directives[0]):
        view = directives[0]
        return RootEndpoint(ViewRef(view), guards)

    # endpoint directive
    elif (len(directives) == 2
            and isinstance(directives[0], str)
            and is_view_ref(directives[1])):
        prefix, view = directives
        return Endpoint(ViewRef(view), guards, prefix=prefix)

    # route list with prefix
    elif (len(directives) > 1
            and isinstance(directives[0], str)
            and all(isinstance(d, Route) for d in directives[1:])):
        prefix, routes = directives[0], directives[1:]
        return RouteList(routes, guards, prefix=prefix)

    # route list
    elif all(isinstance(d, Route) for d in directives):
        return RouteList(directives, guards)

    # error here
    else:
        # TODO: expand on this
        raise RouteConfigurationError("improper usage of 'route' directive")

class Route(object):
    """ Base class for routes"""

    def __init__(self, guards, prefix=None):
        self.guards = guards
        self.prefix = self.compile_prefix(prefix)

    def compile_prefix(self, prefix):
        if not prefix:
            return None
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        return re_compile(prefix)

    def match_prefix(self, path_info):
        if self.prefix is None:
            return path_info, {}
        m = self.prefix.match(path_info)
        if not m:
            raise RouteNotFound()
        return path_info[m.end():], m.groupdict()

    def __call__(self, request):
        """ Try to match route against ``request``

        If no route was matched the :class:``.NoMatchFound`` exception will be
        raised.

        :param request:
            :class:``webob.Request`` object to match against
        """
        path_info = request.path_info
        return self.match(path_info, request)

    def match(self, request):
        raise NotImplementedError()

class Endpoint(Route):
    """ Endpoint route"""

    def __init__(self, view, guards, prefix=None):
        super(Endpoint, self).__init__(guards, prefix)
        self.view = view

    def match(self, path_info, request):
        path_info, kwargs = self.match_prefix(path_info)
        if path_info:
            raise RouteNotFound()
        for guard in self.guards:
            guard_kwargs = guard(request)
            if guard_kwargs:
                kwargs.update(guard_kwargs)
        return (lambda view, request: view(**kwargs)), self.view

    def __repr__(self):
        return "%s(view=%r, guards=%r, prefix=%r)" % (
            self.__class__.__name__, self.view, self.guards,
            self.prefix.pattern if self.prefix else None)

    __str__ = __repr__

class RootEndpoint(Endpoint):

    def match_prefix(self, path_info):
        if not path_info or path_info == "/":
            return "", {}
        raise RouteNotFound()

class RouteList(Route):
    """ List of routes"""

    def __init__(self, routes, guards, prefix=None):
        super(RouteList, self).__init__(guards, prefix)
        self.routes = routes

    def match(self, path_info, request):
        path_info, _ = self.match_prefix(path_info)
        guarded = []
        for route in self.routes:
            try:
                adapter, view = route.match(path_info, request)
            except RouteNotFound:
                continue
            except exc.HTTPException, e:
                guarded.append(e)
                continue
            else:
                return adapter, view
        if guarded:
            # NOTE
            #   we raise now only first guard falure
            #   this is the place we might want more
            raise RouteGuarded(guarded[0])
        raise RouteNotFound()

    def __repr__(self):
        return "%s(routes=%r, guards=%r, prefix=%r)" % (
            self.__class__.__name__, self.routes, self.guards, self.prefix)

    __str__ = __repr__

class cached_property(object):
    """ Just like ``property`` but computed only once"""

    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        val = self.func(obj)
        obj.__dict__[self.__name__] = val
        return val

def import_string(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    For better debugging we recommend the new :func:`import_module`
    function to be used instead.

    :param import_name: the dotted name for the object to import.
    :param silent: if set to `True` import errors are ignored and
                   `None` is returned instead.
    :return: imported object

    :copyright: (c) 2011 by the Werkzeug Team
    """
    # force the import name to automatically convert to strings
    if isinstance(import_name, unicode):
        import_name = str(import_name)
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name:
            module, obj = import_name.rsplit('.', 1)
        else:
            return __import__(import_name)
        # __import__ is not able to handle unicode strings in the fromlist
        # if the module is a package
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        try:
            return getattr(__import__(module, None, None, [obj]), obj)
        except (ImportError, AttributeError):
            # support importing modules not yet set up by the parent module
            # (or package for that matter)
            modname = module + '.' + obj
            __import__(modname)
            return sys.modules[modname]
    except ImportError, e:
        if not silent:
            raise ImportStringError(import_name, e), None, sys.exc_info()[2]

class ImportStringError(ImportError):
    """Provides information about a failed :func:`import_string` attempt.

    :copyright: (c) 2011 by the Werkzeug Team
    """

    #: String in dotted notation that failed to be imported.
    import_name = None
    #: Wrapped exception.
    exception = None

    def __init__(self, import_name, exception):
        self.import_name = import_name
        self.exception = exception

        msg = (
            'import_string() failed for %r. Possible reasons are:\n\n'
            '- missing __init__.py in a package;\n'
            '- package or module path not included in sys.path;\n'
            '- duplicated package or module name taking precedence in '
            'sys.path;\n'
            '- missing module, class, function or variable;\n\n'
            'Debugged import:\n\n%s\n\n'
            'Original exception:\n\n%s: %s')

        name = ''
        tracked = []
        for part in import_name.replace(':', '.').split('.'):
            name += (name and '.') + part
            imported = import_string(name, silent=True)
            if imported:
                tracked.append((name, imported.__file__))
            else:
                track = ['- %r found in %r.' % (n, i) for n, i in tracked]
                track.append('- %r not found.' % name)
                msg = msg % (import_name, '\n'.join(track),
                             exception.__class__.__name__, str(exception))
                break

        ImportError.__init__(self, msg)

    def __repr__(self):
        return '<%s(%r, %r)>' % (self.__class__.__name__, self.import_name,
                                 self.exception)

class ViewRef(object):

    def __init__(self, view_ref):
        self.view_ref = view_ref

    @cached_property
    def view(self):
        if hasattr(self.view_ref, "__call__"):
            return self.view_ref
        return import_string(self.view_ref)

    def __call__(self, *args, **kwargs):
        return self.view(*args, **kwargs)

class Method(object):

    def __init__(self, *allowed):
        self.allowed = allowed

    def __call__(self, request):
        if not request.method in self.allowed:
            raise exc.HTTPMethodNotAllowed()

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, ", ".join(self.allowed))
