"""`planzilla serve`: the live view over the §12 data (FORMAT §9, §12)."""

import json
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from planzilla import cli
from planzilla.commands import serve, status
from tests.commands.test_status import tree
from tests.test_report import NOW, write_plan

HTML_DIR = Path(serve.__file__).parent.parent / "web"


def get(server, path: str) -> tuple[int, str, str]:
    """GET `path` from the running test server: (status, content type, body)."""
    url = f"http://127.0.0.1:{server.server_address[1]}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.headers["Content-Type"], response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.headers["Content-Type"], error.read().decode()


@pytest.fixture(params=["L", "S"])
def plan_path(request, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(status, "now", lambda: NOW)
    return write_plan(tmp_path, request.param)


@pytest.fixture
def server(plan_path):
    httpd = serve.make_server(plan_path, 0)
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join(5)


def test_state_json_is_the_section_12_schema(server):
    code, kind, body = get(server, "/state.json")
    assert (code, kind) == (200, "application/json; charset=utf-8")
    state = json.loads(body)
    assert list(state) == [
        "plan",
        "title",
        "status",
        "tier",
        "updated",
        "done",
        "total",
        "elapsed",
        "waves",
    ]
    assert state["plan"] == "demo"
    assert (state["title"], state["status"], state["done"], state["total"]) == (
        "Demo plan",
        "RUNNING",
        2,
        5,
    )
    assert [w["wave"] for w in state["waves"]] == [1, 2, 3]
    nodes = [n for w in state["waves"] for n in w["nodes"]]
    assert [n["id"] for n in nodes] == ["N01", "N02", "N03", "N04", "N05"]
    assert list(nodes[1]) == [
        "id",
        "title",
        "type",
        "status",
        "view",
        "try",
        "rp",
        "note",
        "last",
        "elapsed",
    ]
    assert nodes[1] == {
        "id": "N02",
        "title": "Parser",
        "type": "exec",
        "status": "DONE",
        "view": "done",
        "try": 2,
        "rp": 1,
        "note": "",
        "last": "verify: PASS",
        "elapsed": None,
    }


def test_root_serves_the_page(server):
    code, kind, body = get(server, "/")
    assert (code, kind) == (200, "text/html; charset=utf-8")
    assert body == (HTML_DIR / "index.html").read_text(encoding="utf-8")
    assert "<html" in body and "/state.json" in body


def test_a_status_flip_shows_on_the_next_get(server, plan_path):
    def statuses():
        nodes = json.loads(get(server, "/state.json")[2])["waves"]
        return {n["id"]: (n["status"], n["view"]) for w in nodes for n in w["nodes"]}

    assert statuses()["N03"] == ("RUNNING", "executing")
    graph = plan_path / "plan.md" if plan_path.is_dir() else plan_path
    graph.write_text(graph.read_text().replace("| RUNNING |", "| VERIFYING |"))
    assert statuses()["N03"] == ("VERIFYING", "verifying")


def test_unknown_paths_are_404_and_nothing_is_written(server, tmp_path):
    before = tree(tmp_path)
    for path in ["/nope", "/state.json/x", "/index.html", "/../plan.md", "/%2e%2e/x"]:
        assert get(server, path)[0] == 404
    get(server, "/")
    get(server, "/state.json")
    assert tree(tmp_path) == before


def test_state_json_ignores_a_query_string(server):
    assert get(server, "/state.json?t=1")[0] == 200


def test_an_unreadable_plan_is_a_500_not_a_crash(server, plan_path):
    graph = plan_path / "plan.md" if plan_path.is_dir() else plan_path
    graph.write_text("not a plan\n")
    assert get(server, "/state.json")[0] == 500
    assert get(server, "/")[0] == 200


def test_the_server_binds_loopback_only(server):
    assert server.server_address[0] == "127.0.0.1"


def test_run_prints_the_serving_line_and_stops_on_ctrl_c(plan_path, monkeypatch, capsys):
    def interrupt(self, *args):
        raise KeyboardInterrupt

    monkeypatch.setattr(serve.ThreadingHTTPServer, "serve_forever", interrupt)
    assert cli.main(["serve", "demo", "--port", "0"]) == 0
    out = capsys.readouterr()
    assert out.err == ""
    line = out.out.strip()
    assert line.startswith("serving demo on http://127.0.0.1:")
    assert line.endswith("/") and "\n" not in line


def test_run_exits_3_when_the_port_is_in_use(plan_path, capsys):
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        assert cli.main(["serve", "demo", "--port", str(port)]) == 3
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ")


def test_run_exits_2_for_an_unknown_plan(plan_path, capsys):
    assert cli.main(["serve", "zzz"]) == 2
    out = capsys.readouterr()
    assert out.out == "" and out.err.startswith("error: ")


def test_default_port_is_8765():
    args = cli.build_parser().parse_args(["serve", "demo"])
    assert args.port == 8765


def test_the_page_is_self_contained():
    page = (HTML_DIR / "index.html").read_text(encoding="utf-8")
    assert "http://" not in page and "https://" not in page
    assert "prefers-color-scheme: dark" in page
    assert "setInterval(poll, POLL_MS)" in page and "POLL_MS = 2000" in page
    for name in ["planning", "replanning", "executing", "verifying", "done", "blocked"]:
        assert f'"{name}"' in page
