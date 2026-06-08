from __future__ import annotations

from app.agent.mcp.web_search_server import (
    DuckDuckGoLiteParser,
    _normalize_result_href,
    _validate_public_http_url,
    handle_message,
)


def test_duckduckgo_result_href_is_unwrapped() -> None:
    href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdocs%3Fa%3D1"

    assert _normalize_result_href(href) == "https://example.com/docs?a=1"


def test_duckduckgo_lite_parser_extracts_result() -> None:
    parser = DuckDuckGoLiteParser()

    parser.feed(
        """
        <html>
          <a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com">Example</a>
          <td>Example snippet</td>
        </html>
        """
    )

    assert len(parser.results) == 1
    assert parser.results[0].title == "Example"
    assert parser.results[0].url == "https://example.com"
    assert parser.results[0].snippet == "Example snippet"


def test_fetch_url_blocks_local_network_addresses() -> None:
    for url in [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://192.168.1.1",
        "file:///C:/Users/test.txt",
    ]:
        try:
            _validate_public_http_url(url)
        except ValueError:
            continue
        raise AssertionError(f"should reject {url}")


def test_tools_list_response_contains_web_search_tools() -> None:
    response = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response is not None
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == {"web_search", "fetch_url"}
