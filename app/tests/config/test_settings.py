from config.settings_base import ensure_https


def test_ensure_https(client):

    got = ensure_https("my-domain.tech/logout")
    assert got == "https://my-domain.tech/logout"

    got = ensure_https("http://my-domain.tech/logout")
    assert got == "https://my-domain.tech/logout"
