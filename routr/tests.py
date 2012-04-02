"""

    routr.tests -- test suite
    =========================

"""

from unittest import TestCase
from webob import Request, exc

from routr.schema import String, Int, opt, qs
from routr import Route, Endpoint, RootEndpoint, RouteGroup, URLPattern
from routr import route, RouteConfigurationError
from routr import POST, GET
from routr.exc import (
    NoURLPatternMatched, RouteGuarded, MethodNotAllowed, RouteReversalError)

__all__ = ()

class TestRouting(TestCase):

    def assertNoMatch(self, r, url):
        if isinstance(url, Request):
            self.assertRaises(NoURLPatternMatched, r, url)
        else:
            self.assertRaises(NoURLPatternMatched, r, Request.blank(url))

class TestRootEnpoint(TestRouting):

    def test_reverse(self):
        r = route("target", name="news")
        self.assertEqual(r.reverse("news"), "/")
        self.assertRaises(RouteReversalError, r.reverse, "news2")

    def test_match(self):
        r = route("target")
        req = Request.blank("/")
        tr = r(req)
        self.assertEqual(len(tr.routes), 1)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "target"))

    def test_no_match(self):
        def target():
            return "hello"
        r = route(target)
        req = Request.blank("/news")
        self.assertRaises(NoURLPatternMatched, r, req)

class TestEndpoint(TestRouting):

    def test_reverse(self):
        r = route("news", "target", name="news")
        self.assertEqual(r.reverse("news"), "/news")
        self.assertRaises(RouteReversalError, r.reverse, "news2")

        r = route("news/{id:int}/", "target", name="news")
        self.assertEqual(r.reverse("news", 42), "/news/42/")
        self.assertRaises(RouteReversalError, r.reverse, "news2")

    def test_match(self):
        r = route("news", "target")
        req = Request.blank("/news")
        tr = r(req)
        self.assertEqual(len(tr.routes), 1)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "target"))

    def test_no_match(self):
        self.assertNoMatch(
            route("news", "target"),
            "/new")
        self.assertNoMatch(
            route("news", "target"),
            "/newsweek")

    def test_method(self):
        r = route(POST, "news", "target")
        req = Request.blank("/news", {"REQUEST_METHOD": "POST"})
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "target"))

        self.assertRaises(
            MethodNotAllowed,
            r, Request.blank("/news", {"REQUEST_METHOD": "DELETE"}))

    def test_param_pattern_int(self):
        r = route("/news/{id:int}/", "target")
        req = Request.blank("/news/42/")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((42,), {}, "target"))

        self.assertNoMatch(r, Request.blank("/news/"))
        self.assertNoMatch(r, Request.blank("/news/a/"))
        self.assertNoMatch(r, Request.blank("/news//"))
        self.assertNoMatch(r, Request.blank("/news/122"))

        r = route("/news/{a:int}/{b:int}/{c:int}/", "target")
        req = Request.blank("/news/42/41/40/")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((42, 41, 40), {}, "target"))

    def test_param_pattern_string(self):
        r = route("/news/{id:string}/", "target")

        req = Request.blank("/news/42/")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((u"42",), {}, "target"))

        req = Request.blank("/news/abcdef-12/")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((u"abcdef-12",), {}, "target"))

    def test_param_pattern_path(self):
        r = route("/news/{p:path}", "target")

        req = Request.blank("/news/42/news")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((u"42/news",), {}, "target"))

        r = route("/news/{p:path}/comments", "target")

        req = Request.blank("/news/42/news/comments")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((u"42/news",), {}, "target"))

    def test_param_guard(self):
        r = route(
            "/news/{id:int}/", "target",
            guards=qs(q=opt(String), page=opt(Int)))

        req = Request.blank("/news/42/")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((42,), {}, "target"))

        req = Request.blank("/news/42/?q=search")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs.items(), tr.target),
            ((42,), [("q", "search")], "target"))

        req = Request.blank("/news/42/?q=search&page=100")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs.items(), tr.target),
            ((42,), [("q", "search"), ("page", 100)], "target"))

        self.assertRaises(
            exc.HTTPBadRequest,
            r, Request.blank("/news/42/?q=search&page=aa"))

class TestRouteGroup(TestRouting):

    def test_reverse(self):
        r = route("api",
            route("news", "news", name="news"),
            route("comments", "comments", name="comments"))
        self.assertEqual(r.reverse("news"), "/api/news")
        self.assertEqual(r.reverse("comments"), "/api/comments")
        self.assertRaises(RouteReversalError, r.reverse, "a")

        r = route("api",
            route("news/{id}/", "news", name="news"),
            route("comments", "comments", name="comments"))
        self.assertEqual(r.reverse("news", "hello"), "/api/news/hello/")

        r = route("api",
            route(GET, "news", name="get-news"),
            route(POST, "news", name="create-news"))
        self.assertEqual(r.reverse("get-news"), "/api")
        self.assertEqual(r.reverse("create-news"), "/api")

    def test_reverse_empty_pattern(self):
        r = route(route("news", name="news"))
        self.assertEqual(r.reverse("news"), "/")

    def test_simple(self):
        r = route(
            route("news", "news"),
            route("comments", "comments"))

        req = Request.blank("/news")
        tr = r(req)
        self.assertEqual(len(tr.routes), 2)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "news"))

        req = Request.blank("/comments")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "comments"))

        self.assertNoMatch(r, "/newsweeek")
        self.assertNoMatch(r, "/ne")

    def test_group_inexact_pattern(self):
        r = route("news",
                route("{id:int}",
                    route("comments", "view")))
        req = Request.blank("/news/42/comments")
        tr = r(req)
        self.assertEqual(
                (tr.args, tr.kwargs, tr.endpoint.target),
                ((42,), {}, "view"))

        r = route("news/{id:int}",
                route("comments", "view"))
        req = Request.blank("/news/42/comments")
        tr = r(req)
        self.assertEqual(
                (tr.args, tr.kwargs, tr.endpoint.target),
                ((42,), {}, "view"))

        r = route("news",
                route("{id:int}/comments", "view"))
        req = Request.blank("/news/42/comments")
        tr = r(req)
        self.assertEqual(
                (tr.args, tr.kwargs, tr.endpoint.target),
                ((42,), {}, "view"))

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
                route("news", "api_news"),
                route("comments", "api_comments")),
            route("news", "news"),
            route("comments", "comments"))

        req = Request.blank("/news")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "news"))

        req = Request.blank("/comments")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "comments"))

        req = Request.blank("/api/news")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "api_news"))

        req = Request.blank("/api/comments")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "api_comments"))

    def test_by_method(self):
        r = route("api",
            route(GET, "news_get"),
            route(POST, "news_post"))

        req = Request.blank("/api", {"REQUEST_METHOD": "POST"})
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "news_post"))

        req = Request.blank("/api")
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "news_get"))

    def test_method_inner(self):
        r = route(
            route("news", "news"),
            route(GET, "comments", "comments_get"),
            route(POST, "comments", "comments_post"))

        req = Request.blank("/news", {"REQUEST_METHOD": "GET"})
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "news"))

        req = Request.blank("/news", {"REQUEST_METHOD": "POST"})
        self.assertRaises(
            RouteGuarded,
            r, req)

        req = Request.blank("/comments", {"REQUEST_METHOD": "POST"})
        tr = r(req)
        self.assertEqual(
            (tr.args, tr.kwargs, tr.target),
            ((), {}, "comments_post"))

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
        r = route("myapp.mytarget")
        self.assertEqual(r.pattern, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, RootEndpoint)
        self.assertEqual(r.target, "myapp.mytarget")

    def test_root_endpoint_func(self):
        def target():
            pass
        r = route(target)
        self.assertEqual(r.pattern, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, RootEndpoint)
        self.assertEqual(r.target, target)

    def test_root_endpoint_guards(self):
        r = route("myapp.mytarget", guards=["guard"])
        self.assertEqual(r.pattern, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, Endpoint)
        self.assertEqual(r.target, "myapp.mytarget")

    def test_endpoint(self):
        r = route("news", "myapp.mytarget")
        self.assertNotEqual(r.pattern, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, Endpoint)
        self.assertEqual(r.target, "myapp.mytarget")

    def test_endpoint_func(self):
        def target():
            pass
        r = route("news", target)
        self.assertNotEqual(r.pattern, None)
        self.assertEqual(r.guards, [])
        self.assertIsInstance(r, Endpoint)
        self.assertEqual(r.target, target)

    def test_endpoint_guards(self):
        r = route("news", "myapp.mytarget", guards=["guard"])
        self.assertNotEqual(r.pattern, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, Endpoint)
        self.assertEqual(r.target, "myapp.mytarget")

    def test_route_list_no_pattern(self):
        r = route(
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"))
        self.assertEqual(r.guards, [])
        self.assertEqual(r.pattern, None)
        self.assertIsInstance(r, RouteGroup)

    def test_route_list_no_pattern_guards(self):
        r = route(
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"),
            guards=["guard"])
        self.assertEqual(r.guards, ["guard"])
        self.assertEqual(r.pattern, None)
        self.assertIsInstance(r, RouteGroup)

    def test_route_list(self):
        r = route("api",
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"))
        self.assertEqual(r.guards, [])
        self.assertNotEqual(r.pattern, None)
        self.assertIsInstance(r, RouteGroup)

    def test_route_list_guards(self):
        r = route("api",
            route("news", "myapp.api.news"),
            route("comments", "myapp.api.comments"),
            guards=["guard"])
        self.assertNotEqual(r.pattern, None)
        self.assertEqual(r.guards, ["guard"])
        self.assertIsInstance(r, RouteGroup)

    def test_invalid_routes(self):
        self.assertRaises(RouteConfigurationError, route)

class TestURLPattern(TestCase):

    def test_int(self):
        p = URLPattern("/a/{id:int}/b/")
        self.assertTrue(not p.is_exact)
        self.assertEqual(p.match("/a/42/b/"), ('', (42,)))

    def test_str(self):
        p = URLPattern("/a/{id}/b/")
        self.assertTrue(not p.is_exact)
        self.assertEqual(p.match("/a/42/b/"), ('', ("42",)))

        p = URLPattern("/a/{id:str}/b/")
        self.assertTrue(not p.is_exact)
        self.assertEqual(p.match("/a/42/b/"), ('', ("42",)))

        p = URLPattern("/a/{id:string}/b/")
        self.assertTrue(not p.is_exact)
        self.assertEqual(p.match("/a/42/b/"), ('', ("42",)))

    def test_path(self):
        p = URLPattern("/a/{id:path}/b/")
        self.assertTrue(not p.is_exact)
        self.assertEqual(p.match("/a/42/43/b/"), ('', ("42/43",)))

    def test_any(self):
        p = URLPattern("/a/{id:any(aaa, bbb, ccc)}/b/")
        self.assertTrue(not p.is_exact)
        self.assertEqual(p.match("/a/aaa/b/"), ('', ("aaa",)))
        self.assertEqual(p.match("/a/bbb/b/"), ('', ("bbb",)))
        self.assertEqual(p.match("/a/ccc/b/"), ('', ("ccc",)))
        self.assertRaises(NoURLPatternMatched, p.match, "/a")
        self.assertRaises(NoURLPatternMatched, p.match, "/a/abc/b/")
