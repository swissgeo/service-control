import pytest

from utils.identifier import (
    ALPHABET,
    dataservice_sgid_from_dataservice_id,
    dataset_sgid_from_dataset_id,
    distribution_sgid_from_dataset_sgid,
    nanoid,
    normalize,
    organization_sgid_from_abbreviation,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # basics
        ("Hello World", "hello-world"),
        ("", ""),
        # German umlauts / eszett (handled by UMLAUTS, not NFKD)
        ("Müller", "mueller"),
        ("Straße", "strasse"),
        ("Äpfel und Öl", "aepfel-und-oel"),
        ("ÄÖÜ", "aeoeue"),
        ("Zürich, Luzern & Bern", "zuerich-luzern-bern"),
        # other accents (handled by NFKD)
        ("Crème brûlée", "creme-brulee"),
        ("São Paulo", "sao-paulo"),
        # compatibility characters
        ("ﬁnale²", "finale2"),
        ("ＡＢＣ", "abc"),  # noqa: RUF001
        # separator handling
        ("  spaced   out  ", "spaced-out"),
        ("foo---bar", "foo-bar"),
        ("!!!hello!!!", "hello"),
        ("a_b.c/d", "a-b-c-d"),
        # particulary nasty
        ("Ünïcödé ﬁnale² – test!", "uenicoede-finale2-test"),  # noqa: RUF001
        # nothing usable left
        ("!!!", ""),
        ("日本語", ""),
    ],
)
def test_normalize(raw, expected):
    normalized = normalize(raw)
    assert normalized == expected
    assert normalize(normalized) == normalized


def test_nanoid():
    id_ = nanoid(10)
    assert len(id_) == 10
    assert all(char in ALPHABET for char in id_)


@pytest.mark.parametrize(
    ("dataset_id", "data_source", "expected"),
    [
        # Non-geodienste: strip ch.<provider>., normalise, no suffix
        (
            "ch.bafu.neophyten-portulak_heusenkraut",
            "bod-dataset",
            "dat_neophyten-portulak-heusenkraut",
        ),
        ("ch.bafu.foo.bar", "bod-dataset", "dat_foo-bar"),  # dots in body
        ("ch.bafu.Wärme_Übersicht", "bod-dataset", "dat_waerme-uebersicht"),  # umlauts, case
        # geodienste aggregate / broker datasets: "-kgk" suffix
        ("ch.bafu.some-dataset", "geodienste", "dat_some-dataset-kgk"),
        ("ch.kgk.some_dataset", "geodienste", "dat_some-dataset"),
        ("ch.kgk.waldreservate", "geodienste", "dat_waldreservate-kgk"),
        # geodienste part datasets: canton suffix
        ("ch.geodienste-zh.some-dataset", "geodienste", "dat_some-dataset-zh"),
        ("ch.geodienste-be.some_dataset", "geodienste", "dat_some-dataset-be"),
        ("ch.geodienste-ag.foo.bar", "geodienste", "dat_foo-bar-ag"),
        # The geodienste- prefix is only special for the geodienste source
        ("ch.geodienste-zh.some-dataset", "bod-dataset", "dat_some-dataset"),
        # other
        ("__missing__", "bod-dataset", "dat_missing"),
    ],
)
def test_dataset_sgid_from_dataset_id(dataset_id, data_source, expected):
    sgid = dataset_sgid_from_dataset_id(dataset_id, data_source)

    assert sgid == expected


def test_distribution_sgid_from_dataset_sgid():
    sgid = distribution_sgid_from_dataset_sgid("dat_neophyten-portulak-heusenkraut")
    first, second = sgid.rsplit("-", maxsplit=1)
    assert first == "dst_neophyten-portulak-heusenkraut"
    assert len(second) == 5
    assert all(char in ALPHABET for char in second)


def test_organization_sgid_from_abbreviation():
    assert organization_sgid_from_abbreviation("BAFU") == "org_bafu"


def test_dataservice_sgid_from_dataservice_id():
    assert dataservice_sgid_from_dataservice_id("wms-geoadminch") == "srv_wms-geoadminch"
    assert (
        dataservice_sgid_from_dataservice_id("wms-geodienste-themische_netze")
        == "srv_wms-geodienste-themische-netze"
    )
