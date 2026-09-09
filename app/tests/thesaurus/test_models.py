from django.db import IntegrityError

import pytest

from thesaurus.models import Concept, Thesaurus


def test_keyword_unique_per_thesaurus(db):
    thesaurus_1 = Thesaurus.objects.create(thesaurus_id="thesaurus.1")
    thesaurus_2 = Thesaurus.objects.create(thesaurus_id="thesaurus.2")

    Concept.objects.create(concept_id="http://example/concept#1", thesaurus=thesaurus_1)
    Concept.objects.create(concept_id="http://example/concept#1", thesaurus=thesaurus_2)
    with pytest.raises(IntegrityError):
        Concept.objects.create(concept_id="http://example/concept#1", thesaurus=thesaurus_2)
