#!/usr/bin/python3
"""Lint a devops-owned nginx proxy file or upstream file.

    nginx-proxy-lint --proxies   FILE [--conf-d /etc/nginx/conf.d]
    nginx-proxy-lint --upstreams FILE

Exit 0 when clean, 1 when there are violations (printed as file:line: message),
2 on a parse error. Standard library only. `nginx -t` still runs afterwards;
this catches what `nginx -t` cannot: valid config that silently drops the
shared headers or weakens the infra-owned protections.

Why these rules exist: nginx drops ALL inherited add_header / proxy_set_header /
proxy_hide_header the moment a location sets one. A location that needs its own
must include the matching snippet first (see the role README, "Proxy files").
"""
import argparse
import os
import sys

# Directives that belong to the infra layer, never to a proxy file.
FORBIDDEN = {
    "http", "events", "server", "upstream", "map", "geo", "geoip2", "split_clients",
    "listen", "server_name", "load_module", "user", "pid", "worker_processes",
    "limit_req", "limit_conn", "limit_req_zone", "limit_conn_zone",
    "set_real_ip_from", "real_ip_header", "real_ip_recursive",
    "access_log", "error_log", "log_format", "proxy_cache_path",
    "ssl_certificate", "ssl_certificate_key", "ssl_protocols", "ssl_ciphers",
    "ssl_reject_handshake", "ssl_stapling", "ssl_dhparam", "ssl_session_cache",
}
FORBIDDEN_PREFIXES = ("lua_", "js_", "perl", "ssl_")

STANDARD_PROXY_HEADERS = {
    "upgrade", "connection", "x-forwarded-host", "x-forwarded-server",
    "x-forwarded-for", "x-real-ip", "host",
}
STANDARD_SECURITY_HEADERS = {
    "x-content-type-options", "strict-transport-security", "x-frame-options",
}
# Optional snippets that call add_header internally.
ADD_HEADER_SNIPPETS = {"noindex.conf", "nocache.conf", "cors.conf"}

UPSTREAM_ALLOWED = {
    "server", "keepalive", "keepalive_requests", "keepalive_time",
    "keepalive_timeout", "least_conn", "ip_hash", "hash", "random", "zone",
    "least_time", "queue",
}

MAX_BYTES = 1024 * 1024


class Node:
    def __init__(self, name, args, line, children=None):
        self.name = name
        self.args = args
        self.line = line
        self.children = children  # None for a simple directive


class ParseError(Exception):
    pass


def tokenize(text):
    """Yield (token, line). Tokens: words, ';', '{', '}'. Quotes are stripped."""
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
        elif c.isspace():
            i += 1
        elif c == "#":
            while i < n and text[i] != "\n":
                i += 1
        elif c in ";{}":
            yield c, line
            i += 1
        elif c in "\"'":
            q, start, buf = c, line, []
            i += 1
            while i < n and text[i] != q:
                if text[i] == "\\" and i + 1 < n:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == "\n":
                    line += 1
                buf.append(text[i])
                i += 1
            if i >= n:
                raise ParseError("line %d: unterminated quote" % start)
            i += 1
            yield "".join(buf), start
        else:
            start = i
            while i < n and not text[i].isspace() and text[i] not in ";{}":
                i += 1
            yield text[start:i], line


def parse(text):
    toks = list(tokenize(text))
    pos = 0

    def block(depth):
        nonlocal pos
        out = []
        while pos < len(toks):
            tok, line = toks[pos]
            if tok == "}":
                if depth == 0:
                    raise ParseError("line %d: unexpected '}'" % line)
                pos += 1
                return out
            if tok in ";{":
                raise ParseError("line %d: unexpected '%s'" % (line, tok))
            name, nline, args = tok, line, []
            pos += 1
            while pos < len(toks) and toks[pos][0] not in ";{}":
                args.append(toks[pos][0])
                pos += 1
            if pos >= len(toks):
                raise ParseError("line %d: '%s' is missing ';' or '{'" % (nline, name))
            end, _ = toks[pos]
            if end == "}":
                raise ParseError("line %d: '%s' is missing ';'" % (nline, name))
            pos += 1
            if end == ";":
                out.append(Node(name, args, nline))
            else:
                out.append(Node(name, args, nline, block(depth + 1)))
        if depth:
            raise ParseError("unexpected end of file: missing '}'")
        return out

    return block(0)


def forbidden(name):
    return name in FORBIDDEN or name.startswith(FORBIDDEN_PREFIXES)


def check_includes(nodes, conf_d, errors):
    allowed = tuple(os.path.join(conf_d, d) + "/" for d in ("snippets", "optional"))
    for nd in nodes:
        if nd.name == "include" and nd.args and not nd.args[0].startswith(allowed):
            errors.append((nd.line, "include of %s is not allowed; only files under "
                           "%s/snippets/ and %s/optional/" % (nd.args[0], conf_d, conf_d)))
        if nd.children:
            check_includes(nd.children, conf_d, errors)


def check_forbidden(nodes, errors):
    for nd in nodes:
        if forbidden(nd.name):
            errors.append((nd.line, "'%s' is managed by the infrastructure role, "
                           "not by proxy files" % nd.name))
        if nd.children:
            check_forbidden(nd.children, errors)


def check_header_scopes(nodes, conf_d, errors, top=True):
    """Apply the inheritance rules to each location/if block."""
    pheaders = os.path.join(conf_d, "snippets", "proxy_headers.conf")
    sheaders = os.path.join(conf_d, "snippets", "security_headers.conf")
    for nd in nodes:
        if nd.children is None:
            continue
        if nd.name in ("location", "if"):
            incs = [c.args[0] for c in nd.children if c.name == "include" and c.args]
            has_p = pheaders in incs
            has_s = sheaders in incs
            uses_add = any(c.name == "add_header" for c in nd.children) or any(
                os.path.basename(i) in ADD_HEADER_SNIPPETS for i in incs)
            for c in nd.children:
                if c.name in ("proxy_set_header", "proxy_hide_header") and not has_p:
                    errors.append((c.line, "%s in a location drops all shared proxy "
                                   "headers; add `include %s;` first" % (c.name, pheaders)))
                elif c.name == "proxy_set_header" and c.args and \
                        c.args[0].lower() in STANDARD_PROXY_HEADERS:
                    hint = (" (set $upstream_host to change Host and the upstream SNI)"
                            if c.args[0].lower() == "host" else "")
                    errors.append((c.line, "proxy_set_header %s duplicates a header the "
                                   "snippet already sets%s" % (c.args[0], hint)))
                if c.name == "add_header" and not has_s:
                    errors.append((c.line, "add_header in a location drops all shared "
                                   "security headers; add `include %s;` first" % sheaders))
                elif c.name == "add_header" and c.args and \
                        c.args[0].lower() in STANDARD_SECURITY_HEADERS:
                    errors.append((c.line, "add_header %s duplicates a header the "
                                   "snippet already sets" % c.args[0]))
            if uses_add and not has_s and not any(
                    c.name == "add_header" for c in nd.children):
                errors.append((nd.line, "includes an add_header snippet without `include "
                               "%s;`; the shared security headers would be dropped" % sheaders))
        check_header_scopes(nd.children, conf_d, errors, False)


def lint_proxies(tree, conf_d):
    errors = []
    check_forbidden(tree, errors)
    check_includes(tree, conf_d, errors)
    check_header_scopes(tree, conf_d, errors)
    return errors


def lint_upstreams(tree):
    errors = []
    for nd in tree:
        if nd.name != "upstream" or nd.children is None:
            errors.append((nd.line, "only upstream { } blocks are allowed in an "
                           "upstreams file, found '%s'" % nd.name))
            continue
        for c in nd.children:
            if c.name not in UPSTREAM_ALLOWED:
                errors.append((c.line, "'%s' is not allowed inside an upstream block" % c.name))
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    kind = ap.add_mutually_exclusive_group(required=True)
    kind.add_argument("--proxies", action="store_true")
    kind.add_argument("--upstreams", action="store_true")
    ap.add_argument("file")
    ap.add_argument("--conf-d", default="/etc/nginx/conf.d")
    a = ap.parse_args()
    conf_d = a.conf_d.rstrip("/")

    try:
        if os.path.getsize(a.file) > MAX_BYTES:
            print("%s: file is larger than %d bytes" % (a.file, MAX_BYTES), file=sys.stderr)
            return 1
        with open(a.file, encoding="utf-8") as fh:
            tree = parse(fh.read())
    except (OSError, UnicodeDecodeError) as exc:
        print("%s: %s" % (a.file, exc), file=sys.stderr)
        return 2
    except ParseError as exc:
        print("%s: parse error: %s" % (a.file, exc), file=sys.stderr)
        return 2

    errors = lint_proxies(tree, conf_d) if a.proxies else lint_upstreams(tree)
    for line, msg in sorted(errors):
        print("%s:%d: %s" % (a.file, line, msg), file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
