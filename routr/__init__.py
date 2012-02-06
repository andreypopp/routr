"""

    routr -- define routes
    ======================

"""

from webob import exc as webobexc

from routr.schema import URLPattern
from routr.utils import import_string, cached_property
from routr.exc import NoMatchFound, NoURLPatternMatched, RouteGuarded
from routr.exc import RouteConfigurationError, InvalidRoutePattern

__all__ = ("route",)

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
    """ Base class for routes

    :param guards:
        a list of guards for route
    :param prefix:
        URL prefix to match for route
    """

    def __init__(self, guards, prefix=None):
        self.guards = guards
        self.prefix = self.compile_prefix(prefix)

    def compile_prefix(self, prefix):
        if not prefix:
            return None
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        return URLPattern(prefix)

    def match_prefix(self, path_info):
        if self.prefix is None:
            return path_info, ()
        return self.prefix.match(path_info)

    def match_guards(self, request):
        kwargs = {}
        for guard in self.guards:
            guard_kwargs = guard(request)
            if guard_kwargs:
                kwargs.update(guard_kwargs)
        return kwargs

    def __call__(self, request):
        """ Try to match route against ``request``

        If no route was matched the :class:`routr.exc.NoMatchFound` exception
        will be raised.

        :param request:
            :class:`webob.Request` object to match route against
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
        path_info, args = self.match_prefix(path_info)
        if path_info:
            raise NoURLPatternMatched()
        kwargs = self.match_guards(request)
        return (args, kwargs), self.view

    def __repr__(self):
        return "%s(view=%r, guards=%r, prefix=%r)" % (
            self.__class__.__name__, self.view, self.guards,
            self.prefix.pattern if self.prefix else None)

    __str__ = __repr__

class RootEndpoint(Endpoint):
    """ Root route endpoint"""

    def match_prefix(self, path_info):
        if not path_info or path_info == "/":
            return "", ()
        raise NoURLPatternMatched()

class RouteList(Route):
    """ Route which represents a list of other routes

    Can have its own ``guards`` and URL ``prefix``.
    """

    def __init__(self, routes, guards, prefix=None):
        super(RouteList, self).__init__(guards, prefix)
        self.routes = routes

    def match(self, path_info, request):
        path_info, args = self.match_prefix(path_info)
        guarded = []
        kwargs = self.match_guards(request)
        for route in self.routes:
            try:
                (r_args, r_kwargs), view = route.match(path_info, request)
            except NoURLPatternMatched:
                continue
            except webobexc.HTTPException, e:
                guarded.append(e)
                continue
            else:
                kwargs.update(r_kwargs)
                args = args + r_args
                return (args, kwargs), view
        if guarded:
            # NOTE
            #   we raise now only first guard falure
            #   this is the place we might want more
            raise RouteGuarded(guarded[0])
        raise NoURLPatternMatched()

    def __repr__(self):
        return "%s(routes=%r, guards=%r, prefix=%r)" % (
            self.__class__.__name__, self.routes, self.guards, self.prefix)

    __str__ = __repr__

class ViewRef(object):
    """ View reference

    :param view_ref:
        import spec or callable to reference to
    """

    def __init__(self, view_ref):
        self.view_ref = view_ref

    @cached_property
    def view(self):
        if hasattr(self.view_ref, "__call__"):
            return self.view_ref
        return import_string(self.view_ref)

    @property
    def __doc__(self):
        return self.view.__doc__

    def __call__(self, *args, **kwargs):
        return self.view(*args, **kwargs)
