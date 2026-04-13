from django.forms import ModelForm

from organization.models import Contact


def test_object_stored_as_expected_for_valid_input(organization):
    contact_in = {
        "organization": organization,
        "name_de": "Name (DE)",
        "name_fr": "Name (FR)",
        "name_en": "Name (EN)",
        "name_it": "Name (IT)",
        "name_rm": "Name (RM)",
        "email": "test@example.org",
        "phone": "+123456789",
        "address_administrative_area": "Administrative Area",
        "address_delivery_point": "Delivery Point",
        "address_postal_code": "Postal Code",
        "address_city": "City",
        "address_country": "CO",
        "url_de": "https://example.org/de",
        "url_fr": "https://example.org/fr",
        "url_en": "https://example.org/en",
        "url_it": "https://example.org/it",
        "url_rm": "https://example.org/rm",
    }
    Contact.objects.create(**contact_in)

    contacts = Contact.objects.all()

    assert len(contacts) == 1

    actual = Contact.objects.last()
    assert organization == actual.organization
    assert contact_in["name_de"] == actual.name_de
    assert contact_in["name_fr"] == actual.name_fr
    assert contact_in["name_en"] == actual.name_en
    assert contact_in["name_it"] == actual.name_it
    assert contact_in["name_rm"] == actual.name_rm
    assert contact_in["email"] == actual.email
    assert contact_in["phone"] == actual.phone
    assert contact_in["address_administrative_area"] == actual.address_administrative_area
    assert contact_in["address_delivery_point"] == actual.address_delivery_point
    assert contact_in["address_postal_code"] == actual.address_postal_code
    assert contact_in["address_city"] == actual.address_city
    assert contact_in["address_country"] == actual.address_country
    assert contact_in["url_de"] == actual.url_de
    assert contact_in["url_fr"] == actual.url_fr
    assert contact_in["url_en"] == actual.url_en
    assert contact_in["url_it"] == actual.url_it
    assert contact_in["url_rm"] == actual.url_rm


def test_object_created_in_db_with_optional_fields_null(organization):
    contact = {
        "organization": organization,
    }
    Contact.objects.create(**contact)

    contacts = Contact.objects.all()

    assert len(contacts) == 1

    actual = Contact.objects.last()
    assert organization == actual.organization


# No mandatory fields (yet)
# def test_raises_exception_when_creating_db_object_with_mandatory_field_null(db):
#     with pytest.raises(ValidationError):
#         Contact.objects.create(name_de=None)


def test_form_valid_for_blank_optional_field(organization):
    class ContactForm(ModelForm):
        class Meta:
            model = Contact
            fields = "__all__"  # noqa: DJ007

    data = {
        "organization": organization,
    }
    form = ContactForm(data)

    assert form.is_valid() is True


# No mandatory fields (yet)
# def test_form_invalid_for_blank_mandatory_field(organization):
#     class ContactForm(ModelForm):
#         class Meta:
#             model = Contact
#             fields = "__all__"

#     data = {
#         "organization": organization,
#         "name_en": "",  # empty but mandatory field
#     }
#     form = ContactForm(data)

#     assert form.is_valid() is False


def test_save_updates_records(organization):
    model_fields = {
        "organization": organization,
        "name_de": "Name (DE)",
    }
    Contact.objects.create(**model_fields)
    actual = Contact.objects.first()
    assert actual.name_de == "Name (DE)"

    actual.name_de = "Name"
    actual.save()
    updated = Contact.objects.first()
    assert updated.name_de == "Name"


def test_delete_deletes_records(organization):
    model_fields = {
        "organization": organization,
    }

    Contact.objects.create(**model_fields)
    actual = Contact.objects.first()

    actual.delete()

    assert not Contact.objects.first()
