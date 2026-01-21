import pytest
from django.core.exceptions import ValidationError
from utils.fields import CustomSlugField


def test_custom_slug_field():
    field = CustomSlugField()

    valid = "ch.astra.projektierungszonen-nationalstrassen_v2_0.oereb"
    assert field.clean(valid, None) == valid

    for invalid in ("CH", "?", "!", "ü"):
        with pytest.raises(ValidationError):
            field.clean(invalid, None)
