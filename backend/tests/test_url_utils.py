from devbase.desktop.url_utils import build_local_url, format_url_host


def test_format_url_host_normalizes_wildcard_and_ipv6_hosts() -> None:
    assert format_url_host("0.0.0.0") == "127.0.0.1"
    assert format_url_host("::") == "127.0.0.1"
    assert format_url_host("2001:db8::1") == "[2001:db8::1]"
    assert format_url_host("[2001:db8::1]") == "[2001:db8::1]"


def test_build_local_url_adds_encoded_token() -> None:
    assert build_local_url("127.0.0.1", 8000) == "http://127.0.0.1:8000/"
    assert build_local_url("0.0.0.0", 8000, "a+b") == (
        "http://127.0.0.1:8000/?token=a%2Bb"
    )
