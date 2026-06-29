from dataservice.models import LocalizedCapabilitiesUrlMixin


def test_localized_capabilities_url_mixin():
    class MyModel(LocalizedCapabilitiesUrlMixin):
        def __init__(
            self, capabilities_url: str, languages: list[str], default_language: str | None
        ) -> None:
            self.capabilities_url = capabilities_url
            self.languages = languages
            self.default_language = default_language

    assert MyModel("foo", ["de", "fr"], "de").localized_capabilities_url("de") == "foo"
    assert MyModel("foo/{lang}", ["de", "fr"], "de").localized_capabilities_url("de") == "foo/de"
    assert MyModel("foo/{lang}", ["de", "fr"], "de").localized_capabilities_url("fr") == "foo/fr"
    assert MyModel("foo/{lang}", ["de", "fr"], "de").localized_capabilities_url("it") == "foo/de"
    assert MyModel("foo/{lang}", [], "de").localized_capabilities_url("de") == "foo/de"
    assert MyModel("foo/{lang}", [], "").localized_capabilities_url("de") == "foo/"

    assert MyModel("foo/{lang3}", ["de", "fr"], "de").localized_capabilities_url("de") == "foo/deu"
    assert MyModel("foo/{lang3}", ["de", "fr"], "de").localized_capabilities_url("fr") == "foo/fra"
    assert MyModel("foo/{lang3}", ["de", "fr"], "de").localized_capabilities_url("it") == "foo/deu"
    assert MyModel("foo/{lang3}", [], "de").localized_capabilities_url("de") == "foo/deu"
    assert MyModel("foo/{lang3}", [], "").localized_capabilities_url("de") == "foo/"
