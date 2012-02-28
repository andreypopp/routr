.. routr documentation master file, created by
   sphinx-quickstart on Mon Feb  6 01:05:27 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

routr -- lightweight request routing for WebOb
==============================================

Routr provides a set of tools to map WebOb request to an artbitrary Python
object. It was designed with following points in mind:

* *Non-intrusiveness* -- there're no "frameworkish" things, just a mechanism to
  map request to Python object. How to setup request processing is completely up
  to you.

* *Extensibility* -- routing mechanism designed to be extremely extendable, you
  can define *guards* for your routes, provide *annotations* to them or even
  replace parts of routing mechanism by your own implementations.

* *Declarativeness* -- configuration process is designed to be declarative. That
  means routes are readable and easy to understand and follow. Routr also
  provides a way to automatically generate documentation from routes (via Sphinx
  extension).

* *Composability* -- routes defined with routr are composable -- you can mix and
  match them to compose more sofisticated routing structures.

Basic usage
-----------

I'll just give you an example WSGI application with no explanations -- code is
better than words here::

  from routr import route, POST, GET
  from myapp.views import list_news, get_news, create_news
  from myapp.views import get_comments, create_comment

  routes = route("news",
    route(GET,  "/",                  list_news),
    route(POST, "/",                  create_news),
    route(GET,  "/{id:int}/",         get_news),
    route(GET,  "/{id:int}/comments", get_comments),
    route(POST, "/{id:int}/comments", create_comment),
    )

You use :func:`routr.route` function to define your routes, then you can
dispatch request against them::

  from routes.exc import NoMatchFound
  from webob import Request, exc

  def application(environ, start_response):
    request = Request(environ)
    try:
      trace = routes(request)
      view = trace.target
      args, kwargs = trace.args, trace.kwargs
      response = view(*args, **kwargs)
    except NoMatchFound, e:
      response = e.response
    except exc.HTTPException, e:
      response = e
    return response(environ, start_response)

Note that neither of these are not dictating you how to build your application
-- you're completely free about how to structure and organize your application's
code.

Trace object
------------

The result of matching routes is a :class:`routr.Trace` object:

.. autoclass:: routr.Trace

Reversing routes
----------------

To allow route reversal you must provide ``name`` keyword argument to
:func:`routr.route` directive::

  routes = route("/page/{id:int}", myview, name="myview")

Then you are allowed to call ``reverse(name, *args, **kwargs)`` method on
``routes``::

  routes.reverse("myview", 43, q=12) # produces "/page/43?q=12"

Matching query string
---------------------

You can match against query string parameters with :mod:`routr.schema` module
which exposes :class:`routr.schema.QueryParams` guard::

  from routr import route
  from routr.schema import QueryParams, Int, Optional, String

  routes = route("/", myview,
      guards=[QueryParams(query=String, page=Optional(Int))])

Class :class:`routr.schema.QueryParams` represents a guard which processes
request's query string and validates it against predefined schema.

Writing arbitrary tests for routes -- guards
--------------------------------------------

Route guards are callables which take ``request`` as its single argument and
return a dict of params which then collected and accumulated by
:class:`routr.Trace` object or raise a :class:`webob.exc.HTTPException`.

Annotations
-----------

You can annotate any route with arbitrary objects, :func:`routr.route` accepts
``**kwargs`` arguments and all of those (except ``name`` and ``guards`` which
have special meaning) will be passed to :class:`routr.Route` constructor so you
can access it via :class:`routr.Trace` object after matching::

  ...
  routes = route("/", myview, middleware=[mymiddelware])
  ...
  trace = routes(request)
  trace.endpoint.annotations["middleware"]
  ...

Note that :class:`routr.Trace` objects also provide access for parent routes of
endpoint route via ``Trace.routes`` attribute so you can accumulate annotations
along the matched path. This, for example, can be useful for implementing
middleware system like Django does but this allows only fire some middleware on
those routes which was annotated correspondingly.

Generating documentation from routes
------------------------------------

Let's suppose we have following routes defined:

.. literalinclude:: ./examples.py

We want to generate documentation from these definitions. For that purpose
there's ``autoroutr`` directive which is built on top of `sphinx-httpdomain`_::

  .. autoroutr:: examples:routes

That gives us as a result:

  .. autoroutr:: examples:routes

Directive ``autoroutr`` also supports ``:include:`` and ``:exclude:`` options
which allow to include or exclude routes using `glob pattern`_ syntax.

.. _sphinx-httpdomain: http://pypi.python.org/pypi/sphinx-http-domain
.. _glob pattern: http://en.wikipedia.org/wiki/Glob_(programming)

Reporting bugs and working on routr
-----------------------------------

Development takes place at `GitHub`_, you can clone source code repository with
the following command::

  % git clone git://github.com/andreypopp/routr.git

In case submitting patch or GitHub pull request please ensure you have
corresponding tests for your bugfix or new functionality.

.. _Github: http://github.com/andreypopp/routr

API reference
-------------

.. module:: routr

Module :mod:`routr` contains :func:`routr.route` function which is used as a
primary way to define routes:

.. autofunction:: routr.route

.. autofunction:: routr.include

.. autofunction:: routr.plug

.. autoclass:: routr.Trace

For the complete reference, these are classes which are constructed by
:func:`routr.route`:

.. autoclass:: routr.Route
   :members: match, reverse

.. autoclass:: routr.RouteGroup

.. autoclass:: routr.Endpoint

.. autoclass:: routr.RootEndpoint

.. module:: routr.schema

Module :mod:`routr.schema` contains predefined :class:`routr.schema.QueryParams`
guard and helper utilites:

.. autoclass:: routr.schema.QueryParams

.. autoclass:: routr.schema.Optional

Also :mod:`routr.schema` module re-exports :mod:`colander` package, so you can
import any colander class or function right from there.
