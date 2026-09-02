"""
Devtools service - server-side UI inspection.

Renders ARM pages through Flask's test client (login and CSRF bypassed by
the route adapter), parses the HTML into a light DOM and stores stable
snapshots under the log path so the host can read them.
"""
from __future__ import annotations

import hashlib
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from config import config as cfg

from ui.devtools.adapters import route_adapter

_INTERACTIVE_TAGS = {"a", "button", "input", "select", "textarea", "form"}
_SECTION_TAGS = {"h1", "h2", "h3", "h4", "nav", "main", "section", "form"}
_INTERACTIVE_LIMIT = 50

_ARTIFACT_ROOT = Path(cfg.arm_config.get("LOGPATH", "/arm/logs/")).expanduser() / "devtools" / "artifacts"


class _Node:
    """A light DOM node: tag, attributes and children."""

    def __init__(self, tag: str, attrs: dict[str, str]):
        self.tag = tag
        self.attrs = attrs
        self.children: list[_Node] = []
        self.texts: list[str] = []

    def text_content(self) -> str:
        """Return this node's text plus its children's."""
        return " ".join([*self.texts, *(child.text_content() for child in self.children)]).strip()

    def selector(self) -> str:
        """Return a usable selector for this node."""
        if self.attrs.get("id"):
            return f"#{self.attrs['id']}"
        if self.attrs.get("data-testid"):
            return f"[data-testid='{self.attrs['data-testid']}']"
        classes = [c for c in self.attrs.get("class", "").split() if c]
        if len(classes) >= 2:
            return f"{self.tag}.{classes[0]}.{classes[1]}"
        return self.tag


class _TreeBuilder(HTMLParser):
    """Build a _Node tree from HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag.lower(), {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag.lower() not in {"br", "hr", "img", "input", "meta", "link"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.stack[-1].texts.append(text)


def parse_html(html_text: str) -> _Node:
    """Parse HTML into a node tree."""
    builder = _TreeBuilder()
    builder.feed(html_text)
    builder.close()
    return builder.root


def _walk(node: _Node, predicate, limit: int | None = None) -> list[_Node]:
    """Collect descendants matching the predicate."""
    found = []
    for child in node.children:
        if predicate(child):
            found.append(child)
            if limit is not None and len(found) >= limit:
                return found
        found.extend(_walk(child, predicate, None if limit is None else limit - len(found)))
        if limit is not None and len(found) >= limit:
            return found
    return found


def _visible_sections(root: _Node) -> list[dict[str, Any]]:
    """Summarise headings and structural sections."""
    sections = []
    for node in _walk(root, lambda n: n.tag in _SECTION_TAGS):
        text = node.text_content()
        if text:
            sections.append({"tag": node.tag, "selector": node.selector(), "text": text[:200]})
    return sections[:60]


def _interactive_elements(root: _Node) -> list[dict[str, Any]]:
    """Summarise links, buttons and form controls."""
    elements = []
    for node in _walk(root, lambda n: n.tag in _INTERACTIVE_TAGS, _INTERACTIVE_LIMIT):
        text = node.text_content()
        elements.append({
            "tag": node.tag,
            "selector": node.selector(),
            "text": text[:120],
            "attrs": {key: value[:80] for key, value in node.attrs.items() if key in ("href", "name", "type", "value", "placeholder", "action", "method")},
        })
    return elements


def _title(root: _Node) -> str | None:
    for node in _walk(root, lambda n: n.tag == "title"):
        return node.text_content()
    return None


def _stable_snapshot_id(route: str, content: str) -> str:
    digest = hashlib.sha1(f"{route}\n{content}".encode("utf-8")).hexdigest()
    return f"view-{route.lstrip('/').replace('/', '-')}-{digest[:12]}"


def _write_snapshot(snapshot_id: str, payload: dict[str, Any], html: str) -> tuple[Path | None, str | None]:
    """
    Write the snapshot html and json payload to the artifact root.

    Writes via a temp file + os.replace, which only needs directory write
    permission - earlier runs by another user (e.g. root) cannot block
    re-snapshots of identical content.

    Returns:
        tuple: (json path or None, error string or None) - the snapshot
        payload itself is never lost to an artifact write failure
    """
    try:
        _ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        html_tmp = _ARTIFACT_ROOT / f"{snapshot_id}.html.tmp"
        json_tmp = _ARTIFACT_ROOT / f"{snapshot_id}.json.tmp"
        html_tmp.write_text(html, encoding="utf-8")
        json_tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
        os.replace(html_tmp, _ARTIFACT_ROOT / f"{snapshot_id}.html")
        os.replace(json_tmp, _ARTIFACT_ROOT / f"{snapshot_id}.json")
        return _ARTIFACT_ROOT / f"{snapshot_id}.json", None
    except OSError as error:
        return None, str(error)


def load_snapshot(snapshot_id: str) -> dict[str, Any]:
    """Load a stored snapshot payload."""
    path = _ARTIFACT_ROOT / f"{snapshot_id}.json"
    if not path.is_file():
        raise ValueError(f"No snapshot with id '{snapshot_id}'")
    return json.loads(path.read_text(encoding="utf-8"))


def capture_view(path: str = "/", query: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Render an ARM page and return a snapshot summary.

    Args:
        path: URL path to render (default /)
        query: optional query parameters

    Returns:
        dict: snapshot id, route, title, sections, interactive elements
    """
    rendered = route_adapter.fetch_path(path, query_string=query)
    html = rendered.get("html", "")
    root = parse_html(html)
    snapshot_id = _stable_snapshot_id(rendered.get("path", path), html)
    payload = {
        "snapshot_id": snapshot_id,
        "route": rendered.get("path", path),
        "status_code": rendered.get("status_code"),
        "endpoint": rendered.get("endpoint"),
        "title": _title(root),
        "visible_sections": _visible_sections(root),
        "interactive_elements": _interactive_elements(root),
        "html_length": len(html),
    }
    artifact_path, artifact_error = _write_snapshot(snapshot_id, payload, html)
    payload["artifact"] = str(artifact_path) if artifact_path else None
    if artifact_error:
        payload["artifact_error"] = artifact_error
    return payload


def inspect_element(
    snapshot_id: str | None = None,
    path: str | None = None,
    selector: str | None = None,
    visible_text: str | None = None,
    test_id: str | None = None,
) -> dict[str, Any]:
    """
    Inspect one element in a snapshot by selector, text or test id.

    Args:
        snapshot_id: stored snapshot to use; when absent, re-render path
        path: URL path to render when snapshot_id is absent (default /)
        selector: CSS-ish selector (#id, .class, tag, [attr=value])
        visible_text: match elements whose text contains this
        test_id: match data-testid

    Returns:
        dict: matching elements
    """
    if not any((selector, visible_text, test_id)):
        raise ValueError("selector, visible_text or test_id is required")
    if snapshot_id:
        payload = load_snapshot(snapshot_id)
        html = (_ARTIFACT_ROOT / f"{snapshot_id}.html").read_text(encoding="utf-8")
    else:
        payload = capture_view(path or "/")
        html = (_ARTIFACT_ROOT / f"{payload['snapshot_id']}.html").read_text(encoding="utf-8")
    root = parse_html(html)

    def matches(node: _Node) -> bool:
        if selector:
            node_sel = node.selector()
            if not (node_sel == selector or selector.lstrip("#.") in (node.attrs.get("id"), *node.attrs.get("class", "").split())):
                return False
        if test_id and node.attrs.get("data-testid") != test_id:
            return False
        if visible_text and visible_text.lower() not in node.text_content().lower():
            return False
        return True

    elements = []
    for node in _walk(root, matches, 20):
        elements.append({
            "tag": node.tag,
            "selector": node.selector(),
            "text": node.text_content()[:300],
            "attrs": dict(node.attrs),
            "children_count": len(node.children),
        })
    return {"snapshot_id": payload["snapshot_id"], "route": payload["route"], "count": len(elements), "elements": elements}


def find_element_by_text(text: str, path: str | None = None, snapshot_id: str | None = None) -> dict[str, Any]:
    """
    Find elements whose text contains the given string.

    Args:
        text: text to search for
        path: URL path to render when snapshot_id is absent
        snapshot_id: stored snapshot to use

    Returns:
        dict: matching elements
    """
    return inspect_element(snapshot_id=snapshot_id, path=path, visible_text=text)


def reload_dev_view(path: str = "/", query: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Re-render a route and return a fresh snapshot.

    Args:
        path: URL path to render
        query: optional query parameters

    Returns:
        dict: fresh snapshot payload
    """
    return capture_view(path=path, query=query)


def compare_view_states(before_id: str, after_id: str) -> dict[str, Any]:
    """
    Compare two snapshots' sections and interactive elements.

    Args:
        before_id: earlier snapshot id
        after_id: later snapshot id

    Returns:
        dict: added/removed sections and elements
    """
    before = load_snapshot(before_id)
    after = load_snapshot(after_id)

    def key_section(item: dict[str, Any]) -> str:
        return f"{item.get('tag')}|{item.get('text', '')[:60]}"

    def key_element(item: dict[str, Any]) -> str:
        return f"{item.get('tag')}|{item.get('selector')}|{item.get('text', '')[:40]}"

    before_sections = {key_section(item) for item in before.get("visible_sections", [])}
    after_sections = {key_section(item) for item in after.get("visible_sections", [])}
    before_elements = {key_element(item) for item in before.get("interactive_elements", [])}
    after_elements = {key_element(item) for item in after.get("interactive_elements", [])}
    return {
        "before_id": before_id,
        "after_id": after_id,
        "sections_added": sorted(after_sections - before_sections),
        "sections_removed": sorted(before_sections - after_sections),
        "elements_added": sorted(after_elements - before_elements),
        "elements_removed": sorted(before_elements - after_elements),
    }
