from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from extraction.client import ExtractionError, extract_quotes, load_base_url, load_settings
from extraction.schema import extraction_json_schema


def _reply(content: str, finish_reason: str = "stop") -> dict:
    return {"choices": [{"finish_reason": finish_reason, "message": {"role": "assistant", "content": content}}]}


def _quotes(*numbers: str) -> str:
    return json.dumps({"quotes": [{"quote_number": number} for number in numbers]})


class FakeModelServer:
    """A real HTTP server, so the tests cover the actual request and response."""

    def __init__(self):
        self.status = 200
        self.body = json.dumps(_reply(_quotes("Q-1")))
        self.requests: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                fake.requests.append(
                    {"path": self.path, "headers": dict(self.headers), "json": json.loads(self.rfile.read(length))}
                )
                body = fake.body.encode()
                self.send_response(fake.status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.http = HTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self.http.server_port}/v1"
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def close(self):
        if self.http is not None:
            self.http.shutdown()
            self.http.server_close()
            self.http = None


@pytest.fixture
def server():
    fake = FakeModelServer()
    yield fake
    fake.close()


# --- the request ----------------------------------------------------------------


def test_posts_to_the_chat_completions_path_under_the_base_url(server):
    extract_quotes("doc", base_url=server.base_url)
    assert server.requests[0]["path"] == "/v1/chat/completions"


def test_a_trailing_slash_on_the_base_url_is_harmless(server):
    extract_quotes("doc", base_url=server.base_url + "/")
    assert server.requests[0]["path"] == "/v1/chat/completions"


def test_sends_the_document_text_to_the_model(server):
    extract_quotes("Quote #: Q-77 for 8 servers", base_url=server.base_url)
    messages = server.requests[0]["json"]["messages"]
    assert messages[-1] == {"role": "user", "content": "Quote #: Q-77 for 8 servers"}


def test_sends_the_file_name_with_the_document(server):
    # Original file names hold the quote number, which a spreadsheet export may not.
    extract_quotes("| Qty | Item |", base_url=server.base_url, source_name="Quote 7700012345.xlsx")
    assert server.requests[0]["json"]["messages"][-1]["content"] == "File name: Quote 7700012345.xlsx\n\n| Qty | Item |"


def test_a_revision_in_the_file_name_counts_as_written(server):
    server.body = json.dumps(_reply(json.dumps({"quotes": [{"quote_number": "Q-1", "revision": "3"}]})))
    [draft] = extract_quotes("Quote Q-1", base_url=server.base_url, source_name="Q-1 rev 3.pdf")
    assert draft.revision == "3"


def test_constrains_the_output_to_the_draft_schema(server):
    extract_quotes("doc", base_url=server.base_url)
    response_format = server.requests[0]["json"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["schema"] == extraction_json_schema()


def test_asks_for_deterministic_output(server):
    extract_quotes("doc", base_url=server.base_url)
    assert server.requests[0]["json"]["temperature"] == 0


# --- the response ---------------------------------------------------------------


def _one_cpu(cpu: dict) -> str:
    component = {"component_type": "cpu", "cpu": cpu}
    return json.dumps({"quotes": [{"quote_number": "Q-1", "items": [{"description": "1U", "components": [component]}]}]})


def test_a_property_with_an_empty_value_is_read_as_unknown(server):
    server.body = json.dumps(
        _reply(
            _one_cpu(
                {
                    "manufacturer": {"value": "AMD", "basis": "stated", "reason": None},
                    "tdp_w": {"value": None, "basis": "inferred", "reason": "not stated"},
                }
            )
        )
    )
    cpu = extract_quotes("doc", base_url=server.base_url)[0].items[0].components[0].cpu
    assert cpu.manufacturer.value == "AMD"
    assert cpu.tdp_w is None


def test_drafts_are_cleaned_before_they_are_returned(server):
    server.body = json.dumps(_reply(_one_cpu({"tdp_w": {"value": 225, "basis": "inferred", "reason": "known"}})))
    assert extract_quotes("doc", base_url=server.base_url)[0].items[0].components[0].cpu.tdp_w is None


def test_a_revision_is_checked_against_the_document_sent(server):
    server.body = json.dumps(_reply(json.dumps({"quotes": [{"quote_number": "Q-1", "revision": "7"}]})))
    assert extract_quotes("Quote Q-1", base_url=server.base_url)[0].revision is None
    assert extract_quotes("Quote Q-1 rev 7", base_url=server.base_url)[0].revision == "7"


def test_only_property_objects_are_emptied(server):
    # A "value" key elsewhere, without a "basis", is left alone for the schema to judge.
    server.body = json.dumps(_reply(_one_cpu({"model": {"value": None}})))
    with pytest.raises(ExtractionError, match="schema"):
        extract_quotes("doc", base_url=server.base_url)


def test_one_document_can_produce_several_drafts(server):
    server.body = json.dumps(_reply(_quotes("Q-1", "Q-2")))
    drafts = extract_quotes("doc", base_url=server.base_url)
    assert [draft.quote_number for draft in drafts] == ["Q-1", "Q-2"]


def test_a_document_with_no_quotes_produces_no_drafts(server):
    server.body = json.dumps(_reply(_quotes()))
    assert extract_quotes("doc", base_url=server.base_url) == []


# --- failures -------------------------------------------------------------------


def test_a_server_error_is_reported(server):
    server.status = 500
    server.body = "internal error"
    with pytest.raises(ExtractionError, match="500"):
        extract_quotes("doc", base_url=server.base_url)


def test_an_unreachable_server_is_reported(server):
    base_url = server.base_url
    server.close()
    with pytest.raises(ExtractionError, match="reach"):
        extract_quotes("doc", base_url=base_url, timeout=2)


def test_an_unexpected_response_shape_is_reported(server):
    server.body = json.dumps({"unexpected": True})
    with pytest.raises(ExtractionError, match="response"):
        extract_quotes("doc", base_url=server.base_url)


def test_output_cut_off_at_the_token_limit_is_reported_as_truncated(server):
    server.body = json.dumps(_reply('{"quotes": [', finish_reason="length"))
    with pytest.raises(ExtractionError, match="cut off"):
        extract_quotes("doc", base_url=server.base_url)


def test_output_that_is_not_json_is_reported(server):
    server.body = json.dumps(_reply("not json"))
    with pytest.raises(ExtractionError, match="JSON"):
        extract_quotes("doc", base_url=server.base_url)


def test_output_that_breaks_the_schema_is_reported(server):
    server.body = json.dumps(_reply(json.dumps({"quotes": [{"surprise": 1}]})))
    with pytest.raises(ExtractionError, match="schema"):
        extract_quotes("doc", base_url=server.base_url)


def test_failures_never_repeat_quote_content(server):
    # Error messages end up in terminals and logs, and quotes can be confidential.
    server.body = json.dumps(_reply(json.dumps({"quotes": [{"quote_date": "SECRET-VALUE"}]})))
    with pytest.raises(ExtractionError) as schema_failure:
        extract_quotes("doc", base_url=server.base_url)
    assert "SECRET-VALUE" not in str(schema_failure.value)

    server.body = json.dumps(_reply("SECRET-VALUE"))
    with pytest.raises(ExtractionError) as json_failure:
        extract_quotes("doc", base_url=server.base_url)
    assert "SECRET-VALUE" not in str(json_failure.value)

    server.status = 500
    server.body = "SECRET-VALUE"
    with pytest.raises(ExtractionError) as http_failure:
        extract_quotes("doc", base_url=server.base_url)
    assert "SECRET-VALUE" not in str(http_failure.value)


# --- where the model's address comes from ---------------------------------------


def test_base_url_comes_from_the_environment_first(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("MODEL_BASE_URL=http://from-file/v1\n")
    monkeypatch.setenv("MODEL_BASE_URL", "http://from-environment/v1")
    assert load_base_url(env_file) == "http://from-environment/v1"


def test_base_url_falls_back_to_the_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('# the model server\n\nOTHER=1\nMODEL_BASE_URL="http://from-file/v1"\n')
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    assert load_base_url(env_file) == "http://from-file/v1"


def test_a_missing_base_url_says_how_to_fix_it(monkeypatch, tmp_path):
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    with pytest.raises(ExtractionError, match="MODEL_BASE_URL"):
        load_base_url(tmp_path / ".env")


def test_extract_quotes_uses_the_configured_base_url(server, monkeypatch):
    monkeypatch.setenv("MODEL_BASE_URL", server.base_url)
    assert [draft.quote_number for draft in extract_quotes("doc")] == ["Q-1"]


# --- servers that need a key or a model name --------------------------------------


def test_no_key_and_no_model_name_are_sent_unless_configured(server):
    extract_quotes("doc", base_url=server.base_url)
    request = server.requests[0]
    assert "Authorization" not in request["headers"]
    assert "model" not in request["json"]


def test_the_api_key_is_sent_as_a_bearer_token(server):
    extract_quotes("doc", base_url=server.base_url, api_key="k-123")
    assert server.requests[0]["headers"]["Authorization"] == "Bearer k-123"


def test_the_model_name_is_sent_when_given(server):
    extract_quotes("doc", base_url=server.base_url, model="qwen3.8-27b")
    assert server.requests[0]["json"]["model"] == "qwen3.8-27b"


def test_key_and_model_come_from_the_settings(server, monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"MODEL_BASE_URL={server.base_url}\nMODEL_API_KEY=k-from-file\nMODEL_NAME=qwen3.8-27b\n")
    for name in ("MODEL_BASE_URL", "MODEL_API_KEY", "MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)
    extract_quotes("doc", settings=load_settings(env_file))
    request = server.requests[0]
    assert request["headers"]["Authorization"] == "Bearer k-from-file"
    assert request["json"]["model"] == "qwen3.8-27b"


def test_settings_from_the_environment_win_over_the_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("MODEL_BASE_URL=http://from-file/v1\nMODEL_API_KEY=from-file\nMODEL_NAME=from-file\n")
    monkeypatch.setenv("MODEL_API_KEY", "from-environment")
    monkeypatch.setenv("MODEL_NAME", "from-environment")
    settings = load_settings(env_file)
    assert (settings.api_key, settings.model) == ("from-environment", "from-environment")


def test_key_and_model_are_optional_settings(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("MODEL_BASE_URL=http://from-file/v1\n")
    for name in ("MODEL_BASE_URL", "MODEL_API_KEY", "MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)
    settings = load_settings(env_file)
    assert (settings.base_url, settings.api_key, settings.model) == ("http://from-file/v1", None, None)


def test_a_rejected_key_says_which_setting_to_check(server):
    server.status = 401
    with pytest.raises(ExtractionError, match="MODEL_API_KEY"):
        extract_quotes("doc", base_url=server.base_url, api_key="wrong")


def test_the_key_never_appears_in_errors(server):
    server.status = 401
    with pytest.raises(ExtractionError) as failure:
        extract_quotes("doc", base_url=server.base_url, api_key="k-SECRET")
    assert "k-SECRET" not in str(failure.value)
