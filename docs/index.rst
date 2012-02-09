.. routr documentation master file, created by
   sphinx-quickstart on Mon Feb  6 01:05:27 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

routr -- lightweight request routing for WebOb
==============================================

Routr was built to solve the problem of mapping WebOb request to Python code
providing:

* Declarative configuration -- all configuration done in declarative fashion, so
  you can even generate documentation from your application's routes.

* Non-intrusiveness -- you can map request to plain Python function thus
  you're not required to write separate view layer for your application.

Usage
-----

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
