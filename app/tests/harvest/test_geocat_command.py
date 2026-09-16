from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from dataset.models import Dataset
from thesaurus.models import Concept

RESPONSE = b"""<?xml version="1.0" encoding="UTF-8"?>
<che:CHE_MD_Metadata
  xmlns:che="http://geocat.ch/che"
  xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
  xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0"
  xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  gco:isoType="mdb:MD_Metadata"
  xsi:schemaLocation="http://geocat.ch/che
  http://share-ech.ch/xmlns/eCH-0271/1.0.0/standards.iso.org/iso/19115/-3/eCH-0271-1-0-0.xsd">
  <mdb:identificationInfo>
    <che:CHE_MD_DataIdentification gco:isoType="mri:MD_DataIdentification">
      <mri:topicCategory>
        <mri:MD_TopicCategoryCode>environment</mri:MD_TopicCategoryCode>
      </mri:topicCategory>
      <mri:topicCategory>
        <mri:MD_TopicCategoryCode>utilitiesCommunication</mri:MD_TopicCategoryCode>
      </mri:topicCategory>
      <che:subTopicCategory>
        <che:CHE_MD_SubTopicCategoryCode
            codeList="http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CHE_MD_SubTopicCategoryCode"
            codeListValue="environment_EnvironmentalProtection"/>
      </che:subTopicCategory>
      <che:subTopicCategory>
        <che:CHE_MD_SubTopicCategoryCode
            codeList="http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml#CHE_MD_SubTopicCategoryCode"
            codeListValue="utilitiesCommunication_Utilities"/>
      </che:subTopicCategory>
    </che:CHE_MD_DataIdentification>
  </mdb:identificationInfo>
</che:CHE_MD_Metadata>
"""


@patch("harvest.management.commands.import_geocat.get", name="get")
def test_command_updates_dataset_ech_concepts(mock, db):
    out = StringIO()
    call_command("loaddata", "app/fixtures/ech0166.json", stdout=out)
    out = out.getvalue()
    assert "Installed" in out

    dataset = Dataset(
        dataset_id="ch.kgk.av",
        description_de="Abstract DE",
        description_en="Abstract EN",
        description_fr="Abstract FR",
        geocat_id="d929eef4-791d-4728-9d56-226b6952cf1f",
        title_short_de="Title DE",
        title_short_en="TITLE EN",
        title_short_fr="Title FR",
    )
    dataset.save()

    mock.return_value.status_code = 200
    mock.return_value.content = RESPONSE

    # ------
    # Create
    # ------
    out = StringIO()
    call_command("import_geocat", ech0166=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Getting eCH-0166 categories for dataset ch.kgk.av" in out
    assert "Adding ech0166: Environment, Nature to ch.kgk.av" in out
    assert "Adding ech0166: Environmental Protection to ch.kgk.av" in out
    assert "Adding ech0166: Utilities, Communication to ch.kgk.av" in out
    assert "Adding ech0166: Water and Waste Systems to ch.kgk.av" in out

    assert {(c.thesaurus.thesaurus_id, c.concept_id) for c in dataset.concepts.all()} == {
        ("ech0166", "environment"),
        ("ech0166", "environment_EnvironmentalProtection"),
        ("ech0166", "utilitiesCommunication"),
        ("ech0166", "utilitiesCommunication_Utilities"),
    }

    # ------
    # Update
    # ------
    dataset.concepts.remove(Concept.objects.get(concept_id="environment"))
    dataset.concepts.add(Concept.objects.get(concept_id="geoscientificInformation"))

    out = StringIO()
    call_command("import_geocat", ech0166=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Adding ech0166: Environment, Nature to ch.kgk.av" in out
    assert "Removing ech0166: Geosciences, Hazards from ch.kgk.av" in out

    # ------
    # Re-Run
    # ------
    out = StringIO()
    call_command("import_geocat", ech0166=True, verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Adding" not in out
    assert "Removing" not in out
