"""

    routr -- define routes
    ======================

"""

import re
from urllib import urlencode
from pkg_resources import iter_entry_points

from webob.exc import HTTPException
from routr.utils import import_string, cached_property
from routr.exc import (
    NoMatchFound, NoURLPatternMatched, RouteGuarded,
    MethodNotAllowed, RouteConfigurationError, InvalidRoutePattern,
    RouteReversalError)

__all__ = (
    "route", "include", "plug"
    "Route", "Endpoint", "RootEndpoint", "RouteGroup",
    "GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "TRACE")

GET = "GET"
POST = "POST"
PUT = "PUT"
DELETE = "DELETE"
HEAD = "HEAD"
OPTIONS = "OPTIONS"
TRACE = "TRACE"

_http_methods = set([GET, POST, PUT, DELETE, HEAD, OPTIONS, TRACE])

def include(spec):
    """ Include routes by ``spec``

    :param spec:
        asset specification which points to :class:`.Route` instance
    """
    r = import_string(spec)
    if not isinstance(r, Route):
        raise RouteConfigurationError(
            "route included by '%s' isn't a route" % spec)
    return r

def plug(name):
    """ Plug routes by ``setuptools`` entry points, identified by ``name``

    :param name:
        entry point name to query routes
    """
    routes = []
    for p in iter_entry_points("routr", name=name):
        r = p.load()
        if not isinstance(r, Route):
            raise RouteConfigurationError(
                "entry point '%s' doesn't point at Route instance" % p)
        routes.append(r)
    return RouteGroup(routes, [])

def route(*directives, **kwargs):
    """ Directive for configuring routes in application"""
    directives = list(directives)
    if not directives:
        raise RouteConfigurationError()

    guards = directives.pop() if isinstance(directives[-1], list) else []

    if not directives:
        raise RouteConfigurationError()

    method = directives.pop(0) if directives[0] in _http_methods else None

    if not directives:
        raise RouteConfigurationError()

    def is_view_ref(d):
        return (
            isinstance(d, str)
            or hasattr(d, "__call__")
                and not isinstance(d, Route))

    name = kwargs.pop("name", None)

    # root directive
    if len(directives) == 1 and is_view_ref(directives[0]):
        view = directives[0]
        return RootEndpoint(ViewRef(view), method or GET, name, guards)

    # endpoint directive
    elif (len(directives) == 2
            and isinstance(directives[0], str)
            and is_view_ref(directives[1])):
        prefix, view = directives
        return Endpoint(
            ViewRef(view), method or GET, name, guards, prefix=prefix)

    # route list with prefix
    elif (len(directives) > 1
            and isinstance(directives[0], str)
            and all(isinstance(d, Route) for d in directives[1:])):
        prefix, routes = directives[0], directives[1:]
        if method:
            raise RouteConfigurationError(
                "'method' doesn't make sense for route groups")
        return RouteGroup(routes, guards, prefix=prefix)

    # route list
    elif all(isinstance(d, Route) for d in directives):
        if method:
            raise RouteConfigurationError(
                "'method' doesn't make sense for route groups")
        return RouteGroup(directives, guards)

    # error here
    else:
        # TODO: expand on this
        raise RouteConfigurationError("improper usage of 'route' directive")

class Route(object):
    """ Base class for routes

    :param guards:
        a list of guards
    :param prefix:
        pattern for URL prefix
    """

    def __init__(self, guards, prefix=None):
        self.guards = guards
        self.prefix = self.compile_prefix(prefix)

    @property
    def pattern(self):
        return self.prefix.pattern if self.prefix else None

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
        """ Match ``request`` against route

        Returns route target and collected ``*args`` and ``**kwargs``.

        :rtype:
            ``((tuple(), dict()), object)``

        :raises routr.exc.NoURLPatternMatched:
            if no route was matched by URL
        :raises routr.exc.RouteGuarded:
            if route was guarded by one or more guards
        :raises routr.exc.MethodNotAllowed:
            if method isn't allowed for matched route
        """
        raise NotImplementedError()

    def reverse(self, name, *args, **kwargs):
        """ Reverse route with ``name`` using ``*args`` as pattern parameters
        and ``**kwargs`` as query string parameters

        :raises routr.exc.RouteReversalError:
            if no reversal can be computed for given arguments
        """
        raise NotImplementedError()

class Endpoint(Route):
    """ Endpoint route

    Associated with some object ``view`` which will be returned in case of
    successful match and a ``method`` which matches against request's method.

    Additional to :class:`.Route` params are:

    :param view:
        object to associate with route
    :param method:
        HTTP method associate with route
    :param name:
        optional name, should be provided if reversal of this route is needed,
        otherwise ``None`` is allowed
    """

    def __init__(self, view, method, name, guards, prefix=None):
        super(Endpoint, self).__init__(guards, prefix)
        self.view = view
        self.method = method
        self.name = name

    def match(self, path_info, request):
        path_info, args = self.match_prefix(path_info)
        if path_info:
            raise NoURLPatternMatched()
        if self.method != request.method:
            raise MethodNotAllowed()
        kwargs = self.match_guards(request)
        return (args, kwargs), self.view

    def reverse(self, name, *args, **kwargs):
        if name != self.name:
            raise RouteReversalError()
        url = self.prefix.reverse(*args) if self.prefix else "/"
        if kwargs:
            url += "?" + urlencode(kwargs)
        return url

    def __repr__(self):
        return "%s(view=%r, guards=%r, prefix=%r)" % (
            self.__class__.__name__, self.view, self.guards,
            self.prefix.pattern if self.prefix else None)

    __str__ = __repr__

class RootEndpoint(Endpoint):
    """ Endpoint route with no prefix"""

    def match_prefix(self, path_info):
        if not path_info or path_info == "/":
            return "", ()
        raise NoURLPatternMatched()

class RouteGroup(Route):
    """ Route which represents a group of other routes

    Can have its own ``guards`` and a URL ``prefix``.

    Additional to :class:`.Route` params are:

    :param routes:
        a list of :class:`Route` objects
    """

    def __init__(self, routes, guards, prefix=None):
        super(RouteGroup, self).__init__(guards, prefix)
        self.routes = routes

    def index(self):
        """ Return mapping from route name to actual route"""
        idx = {}
        for r in self.routes:
            if isinstance(r, Endpoint) and r.name:
                if r.name in idx:
                    raise RouteConfigurationError(
                        "route this name '%s' already defined")
                idx[r.name] = self.prefix + r.prefix
            elif isinstance(r, RouteGroup):
                ridx = r.index()
                if set(ridx) & set(idx):
                    raise RouteConfigurationError(
                        "route this name '%s' already defined")
                for (n, u) in ridx.items():
                    idx[n] = self.prefix + u
        return idx

    @cached_property
    def _cached_index(self):
        return self.index()

    def reverse(self, name, *args, **kwargs):
        if not name in self._cached_index:
            raise RouteReversalError()
        url = self._cached_index[name].reverse(*args)
        if kwargs:
            url += "?" + urlencode(kwargs)
        return url

    def match(self, path_info, request):
        path_info, args = self.match_prefix(path_info)
        guarded = []
        kwargs = self.match_guards(request)
        for route in self.routes:
            try:
                (r_args, r_kwargs), view = route.match(path_info, request)
            except NoURLPatternMatched:
                continue
            except MethodNotAllowed, e:
                guarded.append(e)
                continue
            except HTTPException, e:
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

class URLPattern(object):

    _type_re = re.compile("{([a-z]+)}")

    _typemap = {
        "": ("[^/]+", None),
        "str": ("[^/]+", None),
        "string": ("[^/]+", None),
        "path": (".*", None),
        "int": ("[0-9]+", int),
    }

    def __init__(self, pattern):
        self.pattern = pattern

        self._compiled = None
        self._names = None

    @cached_property
    def is_exact(self):
        return self._type_re.search(self.pattern) is None

    @cached_property
    def compiled(self):
        if self._compiled is None:
            self.compile()
        return self._compiled

    @cached_property
    def _pattern_len(self):
        return len(self.pattern)

    def compile(self):
        if self.is_exact:
            return

        names = []
        compiled = ""
        last = 0
        for n, m in enumerate(self._type_re.finditer(self.pattern)):
            compiled += re.escape(self.pattern[last:m.start()])
            typ = m.group(1)
            if not typ in self._typemap:
                raise InvalidRoutePattern(self.pattern)
            r, c = self._typemap[typ]
            name = "_gpt%d" % n
            names.append((name, c))
            compiled += "(?P<%s>%s)" % (name, r)
            last = m.end()
        compiled += re.escape(self.pattern[last:])

        self._compiled = re.compile(compiled)
        self._names = names

    def reverse(self, *args):
        if self.is_exact:
            return self.pattern

        r = self.pattern
        for arg in args:
            r = self._type_re.sub(str(arg), self.pattern, 1)
        if self._type_re.search(r):
            raise RouteReversalError()
        return r

    def match(self, path_info):
        if self.is_exact:
            if not path_info.startswith(self.pattern):
                raise NoURLPatternMatched()
            return path_info[self._pattern_len:], ()

        m = self.compiled.match(path_info)
        if not m:
            raise NoURLPatternMatched()
        groups = m.groupdict()
        try:
            args = tuple(
                c(groups[n]) if c else groups[n]
                for (n, c) in self._names)
        except ValueError:
            raise NoURLPatternMatched()
        return path_info[m.end():], args

    def __add__(self, o):
        if o is None:
            return self
        return URLPattern(join(self.pattern, o.pattern))

    def __radd__(self, o):
        if o is None:
            return self
        return URLPattern(join(o.pattern, self.pattern))

    def __repr__(self):
        return "<routr.URLPattern %s>" % self.pattern

def join(a, b):
    a = a or ""
    b = b or ""
    return a.rstrip("/") + "/" + b.lstrip("/")
