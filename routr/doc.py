"""

    wk.doc -- extension for generating documentation with sphinx
    ============================================================

"""

import sys

try:
    import docutils
except ImportError:
    print >> sys.stderr, "docutils should be installed for routr.doc"
    raise

try:
    import sphinx
except ImportError:
    print >> sys.stderr, "sphinx should be installed for routr.doc"
    raise

try:
    from sphinxcontrib import httpdomain
except ImportError:
    print >> sys.stderr, \
        "sphinxcontrib-httpdomain should be installed for routr.doc"
    raise

from fnmatch import fnmatchcase

from docutils import nodes
from docutils.statemachine import ViewList

from sphinx.util.compat import Directive
from sphinx.util.docstrings import prepare_docstring
from sphinx.util.nodes import nested_parse_with_titles
from sphinxcontrib import httpdomain

from routr.utils import import_string, cached_property
from routr import RouteGroup

__all__ = ("AutoRoutrDirective",)

def traverse_routes(route, path=None):
    """ Traverse routes by flatten them"""
    path = path or route.pattern.pattern or "/"
    if isinstance(route, RouteGroup):
        return [(m, p, r)
            for subroute in route.routes
            for (m, p, r) in traverse_routes(
                subroute,
                path=join_path(path, subroute))]
    else:
        return [(route.method, path, route)]

def join_path(a, r):
    if not r.pattern:
        return a
    b = r.pattern.pattern
    if a.endswith("/"):
        a = a[:-1]
    if b.startswith("/"):
        b = b[1:]
    return a + "/" + b

def http_directive(method, path, content):
    """ Construct line for http directive from httpdomain

    :copyright: (c) Hong Minhee
    """
    method = method.lower().strip()
    if isinstance(content, basestring):
        content = content.splitlines()
    yield ""
    yield ".. http:%s:: %s" % (method, path)
    yield ""
    for line in content:
        yield "   " + line
    yield ""

class AutoRoutrDirective(Directive):
    """ Directive for generating docs from routr routes

    Based on code from httpdomain.autoflask by Hong Minhee.
    """

    has_content = True
    requied_argument = 1
    option_spec = {
        "include": str,
        "exclude": str,
    }

    @cached_property
    def include_patterns(self):
        if "include" in self.options:
            return [x.strip() for x in self.options["include"].split(",")]
        return []

    @cached_property
    def exclude_patterns(self):
        if "exclude" in self.options:
            return [x.strip() for x in self.options["exclude"].split(",")]
        return []

    def allowed(self, path):
        return (
            (not self.include_patterns
            or any(fnmatchcase(path, x) for x in self.include_patterns))
                and
            (not self.exclude_patterns
            or all(not fnmatchcase(path, x) for x in self.exclude_patterns)))

    def make_rst(self):
        routes = import_string(self.content.data[0])
        for method, path, route in traverse_routes(routes):
            if not self.allowed(path):
                continue
            if isinstance(route.target, basestring):
                try:
                    target = import_string(route.target)
                except ImportError:
                    print >> sys.stderr, "cannot import %s" % route.target
                    continue
            else:
                target = route.target
            docstring = prepare_docstring(target.__doc__ or "")
            for line in http_directive(method, path, docstring):
                yield line

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, "<autoroutr>")
        nested_parse_with_titles(self.state, result, node)
        return node.children

def setup(app):
    if "http" not in app.domains:
        httpdomain.setup(app)
    app.add_directive("autoroutr", AutoRoutrDirective)

