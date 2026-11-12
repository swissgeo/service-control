from organization.models import Attribution


def test_add_external_id():
    attribution = Attribution()
    attribution.add_external_id(Attribution.DataSource.GEODIENSTE, "b")
    attribution.add_external_id(Attribution.DataSource.BOD_CONTACT_ORGANIZATION, "a")
    attribution.add_external_id(Attribution.DataSource.BOD_CONTACT_ORGANIZATION, "a")

    assert attribution.external_ids == [
        {"source": Attribution.DataSource.BOD_CONTACT_ORGANIZATION, "id": "a"},
        {"source": Attribution.DataSource.GEODIENSTE, "id": "b"},
    ]
