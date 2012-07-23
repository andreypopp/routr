Cookbook
========

There are a lot of possibilities and variations in usage of ``routr`` -- this
page tries to provide some useful examples.

Argument injection
------------------

How to decide when to pass ``request`` as an argument to a function? You can
analyze function signature for that -- use :func:`routr.utils.inject_arguments`
function which can inject needed arguments into arguments' tuple::

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
                template = target.endpoint.annotations.get('template', 't.html')
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
