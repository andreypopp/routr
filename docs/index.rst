.. routr documentation master file, created by
   sphinx-quickstart on Mon Feb  6 01:05:27 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

routr -- lightweight request routing for WebOb
==============================================

Routr is a solution for mapping WSGI request (more specifically -- WebOb
request) to Python code. It provides:

* Non-intrusiveness -- routr allows you to map request on a plain Python
  function thus not requiring you to write separate "view-level" API for your
  application.

* Declarativeness -- you configure routes in completely declarative fashion,
  it means routes are readable and easy to understand and follow. Routr also
  provides a way to generate documentation from your definitions (via Sphinx
  extension).

* Extensibility -- you can make your routes extensible through plug-in
  mechanisms or allow your routes to be included into application written by
  others.

Usage
-----

I'll just give you an example WSGI application with no explanations -- code is
better than words here, so the basic usage is::

  from routr import route, POST,
  from myapp.views import list_news, get_news, create_news
  from myapp.views import get_comments, create_comment

  routes = route("news",
    route("/", list_news),
    route(POST, "/", create_news),
    route("/{id:int}/", get_news),
    route("/{id:int}/comments", get_comments),
    route(POST, "/{id:int}/comments", create_comment),
    )

You just use :func:`routr.route` function to define your routes, then you can
dispatch request against them::

  from routes.exc import NoMatchFound
  from webob import Request, exc

  def application(environ, start_response):
    request = Request(environ)
    try:
      (args, kwargs), view = routes(request)
      response = view(*args, **kwargs)
    except NoMatchFound, e:
      response = e.response
    except exc.HTTPException, e:
      response = e
    return response(environ, start_response)

This is an example of WSGI application using WebOb and routr.

Note that neither of these are not dictating you how to build your application
-- you're completely free about how to structure and organize your application's
code.

Matching query string
---------------------

Reversing routes
----------------

Writing arbitrary tests for routes -- guards
--------------------------------------------

Generating documentation from routes
------------------------------------

Let's suppose we have the following routes defined in our app:

.. literalinclude:: ./examples.py

Now we want to generate documentation from these definitions, we can use
``autoroutr`` directive which is built on top of `sphinx-httpdomain`_::

  .. autoroutr:: examples:routes

This gives us the following:

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
