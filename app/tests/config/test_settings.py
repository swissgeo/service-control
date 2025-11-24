from config.settings_base import BadScheme
from config.settings_base import ensure_https
from pytest import raises


def test_ensure_https():

    with raises(BadScheme):
        ensure_https("my-domain.tech/logout")

    with raises(BadScheme):
        ensure_https("http://my-domain.tech/logout")

    got = ensure_https("https://my-domain.tech/logout")
    assert got == "https://my-domain.tech/logout"
