import pytest
from config.settings_base import BadSchemeError, ensure_https


def test_ensure_https():
    with pytest.raises(BadSchemeError):
        ensure_https("my-domain.tech/logout")

    with pytest.raises(BadSchemeError):
        ensure_https("http://my-domain.tech/logout")

    got = ensure_https("https://my-domain.tech/logout")
    assert got == "https://my-domain.tech/logout"
