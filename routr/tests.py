""" Tests for `routr`"""

from unittest import TestCase
from webob import Request, exc

from routr.schema import Method
from routr import RouteNotFound, RouteGuarded
from routr import Route, Endpoint, RootEndpoint, RouteList
from routr import route, ViewRef, RouteConfigurationError

__all__ = ()

class TestRouting(TestCase):

    def assertNoMatch(self, r, url):
        if isinstance(url, Request):
            self.assertRaises(RouteNotFound, r, url)
        else:
            self.assertRaises(RouteNotFound, r, Request.blank(url))

class TestRootEnpoint(TestRouting):

    def test_match(self):
        def view():
            return "hello"
        r = route(view)
        req = Request.blank("/")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "hello")

    def test_no_match(self):
        def view():
            return "hello"
        r = route(view)
        req = Request.blank("/news")
        self.assertRaises(RouteNotFound, r, req)

class TestEndpoint(TestRouting):

    def test_match(self):
        def view():
            return "hello"
        r = route("news", view)
        req = Request.blank("/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "hello")

    def test_no_match(self):
        self.assertNoMatch(
            route("news", "view"),
            "/new")
        self.assertNoMatch(
            route("news", "view"),
            "/newsweek")

    def test_guard(self):
        def view():
            return "hello"
        r = route("news", view, [Method("GET", "POST")])

        req = Request.blank("/news", {"REQUEST_METHOD": "POST"})
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "hello")

        self.assertRaises(
            exc.HTTPMethodNotAllowed,
            r, Request.blank("/news", {"REQUEST_METHOD": "DELETE"}))

class TestRouteList(TestRouting):

    def test_simple(self):
        def news():
            return "news"
        def comments():
            return "comments"

        r = route(
            route("news", news),
            route("comments", comments))

        req = Request.blank("/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "news")

        req = Request.blank("/comments")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "comments")

        self.assertNoMatch(r, "/newsweeek")
        self.assertNoMatch(r, "/ne")

    def test_complex_match(self):
        def news():
            return "news"
        def comments():
            return "comments"
        def api_news():
            return "api_news"
        def api_comments():
            return "api_comments"

        r = route(
            route("api",
                route("news", api_news),
                route("comments", api_comments)),
            route("news", news),
            route("comments", comments))

        req = Request.blank("/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "news")

        req = Request.blank("/comments")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "comments")

        req = Request.blank("/api/news")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "api_news")

        req = Request.blank("/api/comments")
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "api_comments")

    def test_guards_inner(self):
        def news():
            return "news"
        def comments_get():
            return "comments_get"
        def comments_post():
            return "comments_post"

        r = route(
            route("news", news, [Method("GET")]),
            route("comments", comments_get, [Method("GET")]),
            route("comments", comments_post, [Method("POST")]))

        req = Request.blank("/news", {"REQUEST_METHOD": "GET"})
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "news")

        req = Request.blank("/news", {"REQUEST_METHOD": "POST"})
        self.assertRaises(
            RouteGuarded,
            r, req)

        req = Request.blank("/comments", {"REQUEST_METHOD": "POST"})
        (args, kwargs), view = r(req)
        self.assertEqual(view(*args, **kwargs), "comments_post")

        req = Request.blank("/comments", {"REQUEST_METHOD": "DELETE"})
        self.assertRaises(
            RouteGuarded,
            r, req)

        self.assertNoMatch(r, "/newsweeek")
        self.assertNoMatch(r, "/ne")

    def test_guards(self):
        pass

class TestRouteDirective(TestCase):

    def test_root_endpoint(self):
        r = route("myapp.myview")
        self.assertEqual(r.prefix, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, RootEndpoint)
        self.assertIsInstance(r.view, ViewRef)
        self.assertEqual(r.view.view_ref, "myapp.myview")

    def test_root_endpoint_func(self):
        def view():
            pass
        r = route(view)
        self.assertEqual(r.prefix, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, RootEndpoint)
        self.assertIsInstance(r.view, ViewRef)
        self.assertEqual(r.view.view_ref, view)

    def test_root_endpoint_guards(self):
        r = route("myapp.myview", ["guard"])
        self.assertEqual(r.prefix, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, Endpoint)
        self.assertIsInstance(r.view, ViewRef)
        self.assertEqual(r.view.view_ref, "myapp.myview")

    def test_endpoint(self):
        r = route("news", "myapp.myview")
        self.assertNotEqual(r.prefix, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, Endpoint)
        self.assertIsInstance(r.view, ViewRef)
        self.assertEqual(r.view.view_ref, "myapp.myview")

    def test_endpoint_func(self):
        def view():
            pass
        r = route("news", view)
        self.assertNotEqual(r.prefix, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, Endpoint)
        self.assertIsInstance(r.view, ViewRef)
        self.assertEqual(r.view.view_ref, view)

    def test_endpoint_guards(self):
        r = route("news", "myapp.myview", ["guard"])
        self.assertNotEqual(r.prefix, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, Endpoint)
        self.assertIsInstance(r.view, ViewRef)
        self.assertEqual(r.view.view_ref, "myapp.myview")

    def test_route_list_no_prefix(self):
        r = route(
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"))
        self.assertEqual(r.guards, [])
        self.assertEqual(r.prefix, None)
        self.assertIsInstance(r, RouteList)

    def test_route_list_no_prefix_guards(self):
        r = route(
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"),
            ["guard"])
        self.assertEqual(r.guards, ["guard"])
        self.assertEqual(r.prefix, None)
        self.assertIsInstance(r, RouteList)

    def test_route_list(self):
        r = route("api",
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"))
        self.assertEqual(r.guards, [])
        self.assertNotEqual(r.prefix, None)
        self.assertIsInstance(r, RouteList)

    def test_route_list_guards(self):
        r = route("api",
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"),
            ["guard"])
        self.assertNotEqual(r.prefix, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, RouteList)

    def test_invalid_routes(self):
        self.assertRaises(RouteConfigurationError, route)
