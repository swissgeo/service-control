from django.db import IntegrityError

import pytest

from dataservice.models import Dataservice, LocalizedCapabilitiesUrlMixin


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


@pytest.mark.parametrize(
    ("sgid", "valid"),
    [
        ("srv_a", True),
        ("srv_foo-bar", True),
        ("srv_", False),  # empty body
        ("dst_foo", False),  # other prefix
        ("srv_Foo", False),  # uppercase
        ("srv_foo_bar", False),  # underscore in body
        ("srv_foo--bar", False),  # double hyphen
        ("srv_foo-", False),  # trailing hyphen
        ("srv_foo\n", False),  # trailing newline
        ("ch.bafu.neophyten-portulak_heusenkraut", False),  # raw BGDI layer name
    ],
)
def test_dataset_sgid_constraint(db, sgid, valid):
    if valid:
        Dataservice(sgid=sgid).save()
        assert Dataservice.objects.filter(sgid=sgid).exists()
    else:
        with pytest.raises(IntegrityError):
            Dataservice(sgid=sgid).save()
