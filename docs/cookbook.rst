Cookbook
========

There are a lot of possibilities, variations and patterns of usage of ``routr``
-- this page tries to provide some useful blocks as a foundation for your custom
routing solution.

Argument injection
------------------

How to decide when to pass ``request`` as an argument to a function? You can
analyze function signature for that -- use :func:`routr.utils.inject_arguments`
function which can inject needed arguments into arguments' tuple based on
function signature::

    from webob.dec import wsgify
    from routr import GET, route
    from routr.utils import inject_arguments

    def needs_request(request, id):
        ...

    def do_not_need_request(id):
        ...

    routes = route(
        route(GET, '/a/{id}', needs_request),
        route(GET, '/b/{id}', do_not_need_request),
        )

    @wsgify
    def app(request):
        trace = routes(request)
        args = inject_arguments(trace.target, trace.args, request=request)
        return trace.target(*args, **trace.kwargs)

This way function which have ``request`` positional argument in its signature
will be passed a ``request`` object.

Renderer pattern
----------------

You want your functions to return only data and want to decide how to serialize
it based on ``Accept`` header of a ``request``::

    from webob import Response
    from webob.exc import HTTPBadRequest
    from webob.dec import wsgify
    from routr import GET, route

    def list():
        return [...]

    def get(id):
        return {...}

    routes = route(
      route(GET, '/news',       list, template='list.html'),
      route(GET, '/news/{id}',  get,  template='get.html'),
      )

    @wsgify
    def app(request):
        trace = routes(request)
        response = trace.target(*trace.args, **trace.kwargs)
        if not isinstance(response, Response):
            best = request.accept.best_match(['application/json', 'text/html'])
            if best == 'application/json':
                response = Response(json=response)
            elif best == 'text/html':
                template = target.endpoint.annotations.get('template')
                if not template:
                    raise HTTPBadRequest('invalid Accept header')
                response = Response(template.render(response))
            else:
                raise HTTPBadRequest('invalid Accept header')
        return response

That way functions can return only plain data, not a :class:`webob.Response`
object and based on Accept header of a ``request`` WSGI application will
serialize data into ``application/json`` or either ``text/html`` format. The
latter will be serialized using template which is set by ``template`` annotation
on a corresponding route.

Augmenting HTTP method detection
---------------------------------

Some javascript libraries have compatibility shim for older browser which do not
support methods like PUT or DELETE in XHR -- it emulates DELETE and PUT methods
by calling POST with method passed as GET parameter. You can teach ``routr`` how
to spot this behaviour by using subclassing :class:`webob.Request` object::

    from webob import Request as BaseRequest

    class Request(BaseRequest):

        @property
        def method(self):
            orig_method = super(Request, self).method
            if orig_method == 'POST':
                emul_method = self.GET.get('_method').upper()
                if emul_method in ('PUT', 'DELETE'):
                    return emul_method
            return orig_method
