import json
import re
from decimal import Decimal
from json import loads
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from iso639 import Lang
from lxml import etree  # ty:ignore[unresolved-import]
from requests import get

from django.core.management.base import CommandParser

from dataservice.models import Dataservice, OGCAPIStacDataservice, WMSDataservice
from dataset.models import Dataset, DatasetToContact, DatasetToDataset, DatasetToUnit
from distribution.models import Distribution, ExternalStacDistribution, ExternalWMSDistribution
from harvest.models import (
    DatasetMapping,
    DatasetToContactMapping,
    DatasetToUnitMapping,
    OrganizationMapping,
    PrefixLookupTable,
)
from harvest.utils import (
    AGGREGATE_PROVIDER_CONTACT,
    AGGREGATE_PROVIDER_ID,
    AGGREGATE_PROVIDER_ORGANIZATION,
    CANTONAL_PROVIDER_ORGANIZATIONS,
)
from organization.models import Contact, Organization, Unit
from thesaurus.models import Keyword, Thesaurus
from thesaurus.utils import ThesaurusLookup
from utils.command import CustomBaseCommand

# Note: The services API only supports German, French and Italian - no English. Also two kind of
#       language codes are used: two-letter ISO 639-1 for API parameters and three-letter ISO 639-3
#       for WMS/WFS/OGC Feature API server URLs.
ISO639_1 = Literal["de", "fr", "it"]
ISO639_3 = Literal["deu", "fra", "ita"]


class Command(CustomBaseCommand):
    """Import data from geodienste.ch."""

    help = "Import data from geodienste.ch."

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)

        parser.add_argument(
            "--organizations",
            action="store_true",
            help="Import organizations",
        )
        parser.add_argument(
            "--contacts",
            action="store_true",
            help="Import contacts",
        )
        parser.add_argument(
            "--datasets",
            action="store_true",
            help="Import datasets",
        )
        parser.add_argument(
            "--keywords",
            action="store_true",
            help="Import keywords",
        )
        parser.add_argument(
            "--distributions",
            action="store_true",
            help="Import distributions",
        )

        parser.add_argument(
            "--endpoint",
            default="https://geodienste.ch",
            help="Endpoint base URL.",
        )
        parser.add_argument(
            "--directory",
            help=(
                "Path to a local folder containing the response of the services information and "
                "viewer config API. It expects one JSON file per language: "
                "services_[de/fr/it].json, viewer_config_[de/fr/it].json."
            ),
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default="60",
            help="Timeout when calling services information (JSON) endpoint",
        )

        parser.add_argument(
            "--gemet-thesaurus",
            default="https://www.geocat.ch/geonetwork/srv/api/registries/vocabularies/external.theme.gemet",
            help="URL to the thesaurus / RDF containing the GEMET keywords.",
        )
        parser.add_argument(
            "--geocat-thesaurus",
            default="https://www.geocat.ch/geonetwork/srv/api/registries/vocabularies/local.theme.geocat.ch",
            help="URL to the thesaurus / RDF containing the GEOCAT keywords.",
        )

        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean up",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        """Main entry point of command."""

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options, default=str)}")

        services = {}
        services, configs = self.get_services(
            options["endpoint"], options["directory"], options["timeout"]
        )
        if not services or not configs:
            self.print_warning("No services/configurations available, aborting")
            return

        # Handle sub-commands
        clean = options["clean"]
        if options["organizations"]:
            self.import_organizations(services, clean)
        if options["contacts"]:
            self.import_contacts(services, clean)
        if options["datasets"]:
            self.import_datasets(services, clean)
        if options["keywords"]:
            self.import_keywords(services, options["gemet_thesaurus"], options["geocat_thesaurus"])
        if options["distributions"]:
            self.import_distributions(configs, clean)

    # ##########################################################################
    def get_services(self, endpoint: str, directory: str, timeout: int) -> tuple[dict, dict]:
        """Download the service information and viewer configuration as JSON from the provided
        endpoint URL or load them from the given directory for each requested language.

        Note that the services API only supports German, French and Italian - but not English. The
        viewer configuration on the other hand also supports English, but falls back mostly to
        German.

        Transform the services result to be indexable by provider and base topic.
        """

        services = {}
        configs = {}

        # Load from local files
        if directory:
            path = Path(directory)
            if not path.exists():
                self.print_error(f"{directory} does not exist")
                return {}, {}

            for language in ("de", "fr", "it"):
                services[language] = self.read_json_file(path / f"services_{language}.json")

            for language in ("de", "fr", "it", "en"):
                configs[language] = self.read_json_file(path / f"viewer_config_{language}.json")

        # Load from remote endpoint
        else:
            for language in ("de", "fr", "it"):
                services[language] = self.read_json_url(
                    f"{endpoint}/info/services.json?language={language}", timeout
                )

            for language in ("de", "fr", "it", "en"):
                configs[language] = self.read_json_url(
                    f"{endpoint}/info/viewer_config?language={language}", timeout
                )

        # Check if everything is there
        if any(service is None for service in services.values()) or any(
            config is None for config in configs.values()
        ):
            return {}, {}

        # Transform the result
        for language in ("de", "fr", "it"):
            services[language] = {
                self.service_key(service): service for service in services[language]["services"]
            }

        return services, configs

    def read_json_file(self, filename: Path) -> dict | None:
        """Reads the given JSON file."""
        if not filename.exists():
            self.print_error(f"{filename} does not exist")
            return None

        try:
            with open(filename) as file:
                return loads(file.read())
        except Exception as e:  # noqa: BLE001
            self.print_error(f"Failed to load file {filename}: {e}")
            return None

    def read_json_url(self, url: str, timeout: int) -> dict | None:
        """Reads the given JSON response."""
        try:
            response = get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:  # noqa: BLE001
            self.print_error(f"Failed to retreive {url}: {e}")
            return None

    def service_key(self, service: dict) -> str:
        """Returns the key under which the given service entry will be available in the transformed
        services dict.

        See also get_services.
        """

        return "{}.{}".format(self.provider_id(service), service["base_topic"])

    def provider_id(self, service: dict | None = None) -> str:
        """Returns the provider ID from the given service entry or aggregate provider if no service
        entry is given. This corresponds to the values received from the API and are generally upper
        case.

        The provider ID is:
        - for cantons: "LU", "BE", etc.
        - for brokers: "BFE", etc.
        - for aggregate provider: "KGK"

        """
        if service:
            return service["broker"] or service["canton"]

        return AGGREGATE_PROVIDER_ID

    def organization_id(self, provider_id: str) -> str:
        """Returns the organization ID for the given provider ID. This follows the naming scheme
        used for the service-control entities elsewhere (i.e. lowercase with a prefix).

        The organization ID is:
        - for cantons: "ch.geodienste-lu", "ch.geodienste-be", etc.
        - for brokers: "ch.bfe", etc.
        - for aggregate organization: "ch.kgk"

        """
        if provider_id in CANTONAL_PROVIDER_ORGANIZATIONS:
            return f"ch.geodienste-{provider_id.lower()}"

        return f"ch.{provider_id.lower()}"

    def dataset_id(self, service: dict, aggregate: bool) -> str:
        """Returns the dataset ID for the given service entry. Returns the dataset ID for the
        aggregate dataset of the given service entry if aggregate=True. This follows the naming
        scheme used for the service-control entities elsewhere.

        The dataset ID is:
        - for cantons: "ch.geodienste-lu.av", "ch.geodienste-be.av", etc.
        - for brokers: "ch.elektrische_anlagen_ueber_36kv", etc.
        - for aggregate organization: "ch.kgk.av", etc.

        """
        provider_id = self.provider_id(None if aggregate else service)
        organization_id = self.organization_id(provider_id)
        return "{}.{}".format(organization_id, service["base_topic"].lower())

    def cleanup_objects(
        self,
        cls: type[Dataset | Dataservice | Distribution | Contact | Organization],
        processed: set[str],
        clean: bool,
    ) -> tuple[int, int]:
        """Cleanup organizations

        - Check for data source IDs referenced in the organizations but not present anymore in the
          geodienste Services Information API; optionally clean them
        - Check for obsolete organizations, i.e. organizations created by this command but with no
          data source ID reference; optionally delete them

        """

        existing = cls.objects.existing_data_source_ids(cls.DataSource.GEODIENSTE)
        name = cls.__name__.lower()

        if removed := existing - processed:
            if clean:
                for data_source_id in removed:
                    self.print_warning(
                        f"Removing obsolete data_source_id ({name}) {data_source_id}"
                    )
                    cls.objects.remove_data_source_id(data_source_id)
            else:
                ids = sorted(str(r) for r in removed)
                self.print_warning(f"Removed data_source_ids ({name}) found: {', '.join(ids)}")

        obsolete = cls.objects.filter(
            data_source=cls.DataSource.GEODIENSTE,
            data_source_ids=[],
        )
        if obsolete.count():
            if clean:
                for obj in obsolete:
                    self.print_warning(f"Removing obsolete {name} {obj}")
                    obj.delete()
            else:
                ids = sorted(str(obj) for obj in obsolete)
                self.print_warning(f"Obsolete {name}s found: {', '.join(ids)}")

        return len(removed), len(obsolete)

    # ##########################################################################
    def import_organizations(self, services: dict, clean: bool) -> None:
        """Import organizations.

        There is one organization per canton + FL + aggregate provider.

        Uses the provider as provided by the API as data source ID (e.g. "LU" or "BFE") or "KGK"
        for the aggregate provider.

        """

        self.print_success("Importing organizations")

        mappings = OrganizationMapping.table()

        metrics = {
            "organizations.created": 0,
            "organizations.updated": 0,
            "contacts.removed": 0,
            "contacts.obsoleted": 0,
        }

        processed = set()

        # Aggregate provider
        provider_id = self.provider_id()
        created, updated = self.import_organization(
            provider_id, AGGREGATE_PROVIDER_ORGANIZATION, mappings
        )
        metrics["organizations.created"] += created
        metrics["organizations.updated"] += updated
        processed.add(provider_id)

        # Cantonal provider
        for provider_id, attributes in CANTONAL_PROVIDER_ORGANIZATIONS.items():
            created, updated = self.import_organization(
                provider_id,
                attributes,
                mappings,
            )
            metrics["organizations.created"] += created
            metrics["organizations.updated"] += updated
            processed.add(provider_id)

        # Broker
        provider_ids = {
            service["broker"] for service in services["de"].values() if service["broker"]
        }
        for provider_id in provider_ids:
            attributes = {
                "name_de": provider_id,
                "name_fr": provider_id,
                "name_en": provider_id,
                "name_it": provider_id,
                "name_rm": provider_id,
                "acronym_de": provider_id,
                "acronym_fr": provider_id,
                "acronym_en": provider_id,
                "acronym_it": provider_id,
                "acronym_rm": provider_id,
            }
            created, updated = self.import_organization(provider_id, attributes, mappings)
            metrics["organizations.created"] += created
            metrics["organizations.updated"] += updated
            processed.add(provider_id)

        (
            metrics["organizations.removed"],
            metrics["organizations.obsoleted"],
        ) = self.cleanup_objects(Organization, processed, clean)

        self.print_success(f"Organization import completed. Metrics: {metrics}")

    def import_organization(
        self, provider_id: str, attributes: dict, mappings: PrefixLookupTable
    ) -> tuple[int, int]:
        """Create an organization with the given values if not yet existing, or update if necessary.

        Returns the number of created and updated organizations.
        """

        created, updated = False, False

        Organization.objects.remove_data_source_id(provider_id)

        organization_id = self.organization_id(provider_id)
        org, mapping = mappings.match(provider_id)
        update = mapping.update if mapping else True
        if org:
            self.print(f"Mapping found for provider_id {provider_id}: {org}")
        else:
            org = Organization.objects.filter(
                organization_id=organization_id,
                data_source=Organization.DataSource.GEODIENSTE,
            ).first()
            if org:
                self.print(f"Organization with organization_id {organization_id} already exists")
            else:
                update = False
                created = True
                self.print(
                    f"Organization with organization_id {organization_id} does not exist"
                    " yet, creating a new one"
                )
                org = Organization(
                    organization_id=organization_id,
                    data_source=Organization.DataSource.GEODIENSTE,
                    data_source_ids=[provider_id],
                    **attributes,
                )
                org.save()

        if update:
            for key, value in attributes.items():
                if value != getattr(org, key):
                    updated = True
                    setattr(org, key, value)

            if updated:
                org.save()
                self.print(f"Organization {org} updated")

        org.add_data_source_id(provider_id)
        org.save()

        return 1 if created else 0, 1 if updated else 0

    # ##########################################################################
    def import_contacts(self, services: dict, clean: bool) -> None:
        """Import contacts.

        Each organization may have a conton-wide contact and one contact per dataset. The contacts
        are not structured but rather text.

        Removes obsolete contacts.

        Uses a combination of provider ID and base topic as provided by the API as data source ID,
        e.g. "LU.av" for the specialist/owner contact or "LU", "KGK", etc. for the geo/custodian
        contact.
        """

        self.print_success("Importing contacts")

        mappings = OrganizationMapping.table()

        metrics = {
            "contacts.created": 0,
            "contacts.updated": 0,
            "contacts.removed": 0,
            "contacts.obsoleted": 0,
        }

        processed = set()

        # Aggregate
        provider_id = self.provider_id()
        data_source_id = provider_id
        created, updated = self.import_contact(
            provider_id=provider_id,
            data_source_id=provider_id,
            attributes=AGGREGATE_PROVIDER_CONTACT,
            mappings=mappings,
        )
        metrics["contacts.created"] += created
        metrics["contacts.updated"] += updated
        processed.add(data_source_id)

        # Cantonal and broker
        for service in services["de"].values():
            provider_id = self.provider_id(service)

            # canton-wide contact
            if legacy_contact := (service["contact_geo"] or "").strip():
                data_source_id = provider_id
                created, updated = self.import_contact(
                    provider_id=provider_id,
                    data_source_id=provider_id,
                    attributes={"legacy_contact": legacy_contact},
                    mappings=mappings,
                )
                metrics["contacts.created"] += created
                metrics["contacts.updated"] += updated
                processed.add(data_source_id)

            # specialist contact
            if legacy_contact := (service["contact_specialist_department"] or "").strip():
                data_source_id = f"{provider_id}.{service['base_topic']}"
                created, updated = self.import_contact(
                    provider_id=provider_id,
                    data_source_id=data_source_id,
                    attributes={"legacy_contact": legacy_contact},
                    mappings=mappings,
                )
                metrics["contacts.created"] += created
                metrics["contacts.updated"] += updated
                processed.add(data_source_id)

        (
            metrics["contacts.removed"],
            metrics["contacts.obsoleted"],
        ) = self.cleanup_objects(Contact, processed, clean)

        self.print_success(f"Contact import completed. Metrics: {metrics}")

    def import_contact(
        self, provider_id: str, data_source_id: str, attributes: dict, mappings: PrefixLookupTable
    ) -> tuple[int, int]:
        """Create a contact with the given values if not yet existing, or update if necessary.

        Returns the number of created and updated organizations.
        """

        organization, mapping = mappings.match(provider_id)
        update = mapping.update if mapping else True
        if organization:
            self.print(f"Mapping found for provider_id {provider_id}: {organization}")
        else:
            organization_id = self.organization_id(provider_id)
            organization = Organization.objects.filter(
                organization_id=organization_id, data_source=Organization.DataSource.GEODIENSTE
            ).first()
        if not organization:
            self.print(
                f"Organization with organization_id {organization_id} does not exist, skipping"
            )
            return 0, 0

        contact = Contact.objects.filter(
            data_source=Contact.DataSource.GEODIENSTE, data_source_ids__contains=[data_source_id]
        ).first()
        if contact:
            self.print(f"Contact {data_source_id} for organization {organization} already exists")
        else:
            self.print(
                f"Contact {data_source_id} for organization {organization} does not"
                " exist yet, creating a new one"
            )
            Contact(
                organization=organization,
                data_source=Contact.DataSource.GEODIENSTE,
                data_source_ids=[data_source_id],
                **attributes,
            ).save()
            return 1, 0

        updated = False
        if update:
            for key, value in attributes.items():
                if getattr(contact, key) != value:
                    setattr(contact, key, value)
                    updated = True
        if updated:
            contact.save()
            self.print(f"Contact {data_source_id} for organization {organization} updated")

        return 0, 1 if updated else 0

    # ##########################################################################
    def import_datasets(self, services: dict, clean: bool) -> None:  # noqa: PLR0915
        """Imports datasets.

        For each basic topic,
        - there is an aggregate dataset and one dataset for each provider
        - both datasets are connected via a dataset to dataset relationship (part)
        - for both datasets, the default unit of the aggregation/cantonal/broker organization is
          added as maintainer.
        - for the aggregate dataset, the aggregate contact is added as custodian. For the part
          dataset, there is optionally a custodian and a owner contact.

        Uses a combination of provider ID and base topic as provided by the API as data source ID,
        e.g. "KGK.av" for the aggregate dataset and "LU.av" for the part dataset.
        """
        self.print_success("Importing dataset")

        dataset_mappings = DatasetMapping.table()
        organization_mappings = OrganizationMapping.table()
        unit_mappings = DatasetToUnitMapping.table()
        contact_mappings = DatasetToContactMapping.table()

        aggregated = {}

        metrics = {
            "datasets.created": 0,
            "datasets.updated": 0,
            "datasets.removed": 0,
            "datasets.obsoleted": 0,
            "datasets.connected": 0,
            "dataset_units.created": 0,
            "dataset_units.removed": 0,
            "dataset_contacts.created": 0,
            "dataset_contacts.removed": 0,
        }

        processed = set()

        # Add a legacy contact to the record, since the OAR export currently uses legacy contacts
        legacy_aggregate_contacts = [
            {
                "org_name": contact.organization.name_de,
                "org_name_de": contact.organization.name_de,
                "org_name_fr": contact.organization.name_fr,
                "org_name_en": contact.organization.name_en,
                "org_name_it": contact.organization.name_it,
                "org_name_rm": contact.organization.name_rm,
                "org_acronym": contact.organization.acronym_de,
                "org_acronym_de": contact.organization.acronym_de,
                "org_acronym_fr": contact.organization.acronym_fr,
                "org_acronym_en": contact.organization.acronym_en,
                "org_acronym_it": contact.organization.acronym_it,
                "org_acronym_rm": contact.organization.acronym_rm,
                "contact_voice": contact.phone,
                "contact_city": contact.address_city,
                "contact_postal_code": contact.address_postal_code,
                "contact_country": contact.address_country,
                "contact_electronic_mail_addresses": [contact.email],
                "contact_delivery_point": contact.address_delivery_point,
                "online_resources": [
                    {
                        "url": contact.url_de,
                        "url_de": contact.url_de,
                        "url_fr": contact.url_fr,
                        "url_en": contact.url_en,
                        "url_it": contact.url_it,
                        "url_rm": contact.url_rm,
                    }
                ],
                "role": "custodian",
            }
            for contact in Contact.objects.filter(
                organization__organization_id=self.organization_id(self.provider_id())
            ).all()
        ]

        for key, service in services["de"].items():
            common = {
                "title_short_de": service["topic_title"],
                "title_short_en": service["topic_title"],
                "title_short_fr": services["fr"][key]["topic_title"],
                "title_short_it": services["it"][key]["topic_title"],
                "description_de": service["abstract"],
                "description_en": service["abstract"],
                "description_fr": services["fr"][key]["abstract"],
                "description_it": services["it"][key]["abstract"],
            }
            # Dataset: Aggregate
            base_topic = service["base_topic"]
            aggregate_dataset_id = self.dataset_id(service, aggregate=True)
            aggregate = aggregated.get(aggregate_dataset_id)
            if not aggregate:
                provider_id = self.provider_id()
                data_source_id = f"{provider_id}.{base_topic}"
                processed.add(data_source_id)
                extra: dict = {
                    **common,
                    "legacy_contacts": legacy_aggregate_contacts,
                    "legacy_part_info_url_de": f"{service['website']}?locale=de#info_cantons",
                    "legacy_part_info_url_fr": f"{service['website']}?locale=fr#info_cantons",
                    "legacy_part_info_url_it": f"{service['website']}?locale=it#info_cantons",
                }
                aggregate, created, updated = self.import_dataset(
                    aggregate_dataset_id,
                    data_source_id,
                    dataset_mappings,
                    geocat_id=service["meta_data"].get("dataset_url", "").split("/")[-1],
                    **extra,
                )
                aggregated[aggregate_dataset_id] = aggregate
                metrics["datasets.created"] += created
                metrics["datasets.updated"] += updated

                # Unit: Maintainer of Aggregate
                created, removed = self.import_dataset_unit(
                    aggregate,
                    provider_id,
                    DatasetToUnit.Role.MAINTAINER,
                    unit_mappings,
                    organization_mappings,
                )
                metrics["dataset_units.created"] += created
                metrics["dataset_units.removed"] += removed

                # Contact: Custodian of Aggregate
                created, removed = self.import_dataset_contact(
                    aggregate,
                    provider_id,
                    DatasetToContact.Role.CUSTODIAN,
                    contact_mappings.get(DatasetToContact.Role.CUSTODIAN),
                )
                metrics["dataset_contacts.created"] += created
                metrics["dataset_contacts.removed"] += removed

            # Dataset: Part
            provider_id = self.provider_id(service)
            data_source_id = f"{provider_id}.{base_topic}"
            processed.add(data_source_id)
            part, created, updated = self.import_dataset(
                self.dataset_id(service, aggregate=False),
                data_source_id,
                dataset_mappings,
                **common,
            )
            metrics["datasets.created"] += created
            metrics["datasets.updated"] += updated

            # Relationship: Part --> Aggregate
            if not part.related_datasets(DatasetToDataset.Role.PART, reverse=True).first():
                relationship = DatasetToDataset(
                    subject=part, role=DatasetToDataset.Role.PART, object=aggregate
                )
                relationship.save()
                self.print(f"Adding relationship '{relationship}'")
                metrics["datasets.connected"] += 1

            # Unit: Maintainer of Part
            created, removed = self.import_dataset_unit(
                part,
                provider_id,
                DatasetToUnit.Role.MAINTAINER,
                unit_mappings,
                organization_mappings,
            )
            metrics["dataset_units.created"] += created
            metrics["dataset_units.removed"] += removed

            # Contact: Owner of Part
            created, removed = self.import_dataset_contact(
                part,
                data_source_id,
                DatasetToContact.Role.OWNER,
                contact_mappings.get(DatasetToContact.Role.OWNER),
            )
            metrics["dataset_contacts.created"] += created
            metrics["dataset_contacts.removed"] += removed

            # Contact: Custodian of Part
            created, removed = self.import_dataset_contact(
                part,
                provider_id,
                DatasetToContact.Role.CUSTODIAN,
                contact_mappings.get(DatasetToContact.Role.CUSTODIAN),
            )
            metrics["dataset_contacts.created"] += created
            metrics["dataset_contacts.removed"] += removed

        (
            metrics["datasets.removed"],
            metrics["datasets.obsoleted"],
        ) = self.cleanup_objects(Dataset, processed, clean)

        self.print_success(f"Dataset import completed. Metrics: {metrics}")

    def import_dataset(
        self,
        dataset_id: str,
        data_source_id: str,
        dataset_mappings: PrefixLookupTable,
        **kwargs: dict,
    ) -> tuple[Dataset, int, int]:
        """Create a dataset with the given values if not yet existing, or update if necessary.

        Returns the dataset and number of created and updated datasets.
        """

        dataset, mapping = dataset_mappings.match(dataset_id)
        update = mapping.update if mapping else True
        if dataset:
            self.print(f"Dataset mapping found for dataset_id {dataset_id}: {dataset}")
        else:
            dataset = Dataset.objects.filter(
                dataset_id=dataset_id, data_source=Dataset.DataSource.GEODIENSTE
            ).first()
            if dataset:
                self.print(f"Dataset with dataset_id {dataset_id} already exists")
            if not dataset:
                self.print(
                    f"Dataset with dataset_id {dataset_id} does not exist yet, creating a new one"
                )
                dataset = Dataset(
                    dataset_id=dataset_id,
                    data_source_ids=[data_source_id],
                    data_source=Dataset.DataSource.GEODIENSTE,
                    **kwargs,
                )
                dataset.save()
                return dataset, 1, 0

        updated = False
        if update:
            for key, value in kwargs.items():
                if value != getattr(dataset, key):
                    updated = True
                    setattr(dataset, key, value)
        if updated:
            self.print(f"Dataset with dataset_id {dataset_id} changed, updating")
            dataset.save()
        return dataset, 0, 1 if updated else 0

    def import_dataset_unit(
        self,
        dataset: Dataset,
        provider_id: str,
        role: DatasetToUnit.Role,
        unit_mappings: PrefixLookupTable,
        organization_mappings: PrefixLookupTable,
    ) -> tuple[int, int]:
        """Create dataset unit with the given values if not yet existing.

        Returns a tuple (number of created dataset units, number of removed dataset units).
        """

        organization_id = self.organization_id(provider_id)
        dataset_id = dataset.dataset_id
        unit, _ = unit_mappings.match(dataset_id)
        if unit:
            self.print(f"Unit mapping found for dataset_id {dataset_id}: {unit}")
        else:
            organization, _ = organization_mappings.match(provider_id)
            if organization:
                self.print(f"Mapping found for provider_id {provider_id}: {organization}")
            else:
                organization = Organization.objects.filter(organization_id=organization_id).first()
            if not organization:
                self.print_warning(
                    f"Organization with organization_id {organization_id} does not exist"
                )
                return 0, 0

            unit = Unit.objects.filter(
                organization=organization, unit_id=Unit.DEFAULT_UNIT_ID
            ).first()
            if not unit:
                self.print_warning(f"Organization {organization} has no default unit")
                return 0, 0

        found = False
        added, removed = 0, 0
        existing = DatasetToUnit.objects.filter(dataset=dataset, role=role).all()
        for dataset_unit in existing:
            if dataset_unit.unit == unit:
                self.print(f"Dataset unit {dataset_unit} already exists")
                found = True
            else:
                self.print(f"Removing obsolete dataset unit {dataset_unit}")
                dataset_unit.delete()
                removed += 1
        if not found:
            dataset_unit = DatasetToUnit(dataset=dataset, unit=unit, role=role)
            dataset_unit.save()
            self.print(f"Creating dataset unit {dataset_unit}")
            added += 1

        return added, removed

    def import_dataset_contact(
        self,
        dataset: Dataset,
        data_source_id: str,
        role: DatasetToContact.Role,
        contact_mappings: PrefixLookupTable | None,
    ) -> tuple[int, int]:
        """Create dataset contacts with the given values if not yet existing, or update if
        necessary.

        Returns a tuple (number of created dataset contacts, number of removed dataset contacts).
        """

        dataset_id = dataset.dataset_id
        contact = None
        if contact_mappings:
            contact, _ = contact_mappings.match(dataset_id)
        if contact:
            self.print(
                f"Contact mapping found for dataset_id {dataset_id} and role {role}: {contact}"
            )
        else:
            contact = Contact.objects.filter(data_source_ids__contains=[data_source_id]).first()
            if not contact:
                return 0, 0

        found = False
        added, removed = 0, 0
        existing = set(DatasetToContact.objects.filter(dataset=dataset, role=role).all())
        for dataset_contact in existing:
            if dataset_contact.contact == contact:
                self.print(f"Dataset contact {dataset_contact} already exists")
                found = True
            else:
                self.print(f"Removing obsolete dataset contact {dataset_contact}")
                dataset_contact.delete()
                removed += 1
        if not found:
            dataset_contact = DatasetToContact(dataset=dataset, contact=contact, role=role)
            dataset_contact.save()
            self.print(f"Creating dataset contact {dataset_contact}")
            added += 1

        return added, removed

    # ##########################################################################
    def import_keywords(self, services: dict, gemet_thesaurus: str, geocat_thesaurus: str) -> None:  # noqa: C901
        """Import keywords.

        There are three types of keywords / thesauri:

        - GEMET:      These are currently only present in the German response and should correspond
                      to the German translation of concepts defined in the according thesaurus on
                      geocat.ch.
        - Geocat:     These are currently only present in the Geocat response and should correspond
                      to the German translation of concepts defined in the according thesaurus on
                      geocat.ch.
        - Geodienste: These are present in all languages, but are not yet present in a thesaurus and
                      do not correspond to each other by order. Not yet supported.

        Replaces all keywords of the corresponding aggregate and cantonal dataset.

        No keywords and thesauri are updated or cleaned.

        """
        self.print_success("Importing keywords")

        mappings = DatasetMapping.table()

        metrics = {
            "thesauri.created": 0,
            "keywords.created": 0,
        }

        # Load thesauri
        gemet, gemet_lookup, created = self.load_thesaurus(
            "geonetwork.thesaurus.external.theme.gemet", gemet_thesaurus
        )
        metrics["thesauri.created"] += 1 if created else 0

        geocat, geocat_lookup, created = self.load_thesaurus(
            "geonetwork.thesaurus.local.theme.geocat.ch", geocat_thesaurus
        )
        metrics["thesauri.created"] += 1 if created else 0

        if not gemet_lookup or not geocat_lookup:
            self.print_error("Could not load all required thesauri")
            return

        processed = set()

        for service in services["de"].values():
            # Get aggregate dataset if not yet processed
            base_topic = service["base_topic"]
            aggregate = None
            update_aggregate = True
            if base_topic not in processed:
                processed.add(base_topic)
                dataset_id = self.dataset_id(service, aggregate=True)
                aggregate, mapping = mappings.match(dataset_id)
                update_aggregate = mapping.update if mapping else True
                if aggregate:
                    self.print(f"Dataset mapping found for dataset_id {dataset_id}: {aggregate}")
                else:
                    aggregate = Dataset.objects.filter(dataset_id=dataset_id).first()
                if not aggregate:
                    self.print(f"Dataset with dataset_id {dataset_id} does not exist, skipping")

            # Get cantonal dataset
            dataset_id = self.dataset_id(service, aggregate=False)
            part, mapping = mappings.match(dataset_id)
            update_part = mapping.update if mapping else True
            if part:
                self.print(f"Dataset mapping found for dataset_id {dataset_id}: {part}")
            else:
                part = Dataset.objects.filter(dataset_id=dataset_id).first()
            if not part:
                self.print(f"Dataset with dataset_id {dataset_id} does not exist, skipping")

            if not aggregate and not part:
                continue

            # Create keywords
            gemet_keywords, created = self.create_keywords(
                service["keywords_gemet"] or "", gemet, gemet_lookup
            )
            metrics["keywords.created"] += created

            geocat_keywords, created = self.create_keywords(
                service["keywords_geocat"] or "", geocat, geocat_lookup
            )
            metrics["keywords.created"] += created

            # Replace dataset keywords
            keywords = gemet_keywords + geocat_keywords
            if aggregate and update_aggregate:
                aggregate.keywords.set(keywords)
            if part and update_part:
                part.keywords.set(keywords)

        self.print_success(f"Keyword import completed. Metrics: {metrics}")

    def load_thesaurus(
        self, thesaurus_id: str, url: str
    ) -> tuple[Thesaurus, ThesaurusLookup | None, bool]:
        """Create or get the thesaurus database model and load the lookup.

        Return a tuple with the thesaurus, lookup and if the thesaurus has been created.
        """
        thesaurus, created = Thesaurus.objects.get_or_create(thesaurus_id=thesaurus_id)
        if created:
            self.print(f"Thesaurus {thesaurus_id} created")

        self.print(f"Loading lookup table / RDF from {url}")
        lookup = ThesaurusLookup.build(url)
        if not lookup:
            self.print_error("Failed to load GEMET thesaurus from URL")

        return thesaurus, lookup, created

    def create_keywords(
        self, keyword_strings: str, thesaurus: Thesaurus, lookup: ThesaurusLookup
    ) -> tuple[list[Keyword], int]:
        """Lookup the given list of comma-seprated keywords and create the keywords in the DB if
        not yet existing.

        Returns the keywords and the number of created keywords.
        """

        keywords = []
        created = 0
        for token in keyword_strings.split(","):
            term = token.strip()
            if not term:
                continue

            concept, translations = lookup.find_concept(term)
            if not concept:
                self.print_warning(f"Keyword {term} not found in thesaurus {lookup}")
            elif "de" not in translations:
                self.print_warning(f"Keyword {term} has no German translation")
            elif "fr" not in translations:
                self.print_warning(f"Keyword {term} has no French translation")
            elif "en" not in translations:
                self.print_warning(f"Keyword {term} has no English translation")
            else:
                keyword = thesaurus.keyword_set.filter(keyword_id=concept).first()  # ty:ignore[unresolved-attribute]
                if not keyword:
                    self.print(
                        f"Adding keyword {concept} / {translations} to thesaurus {thesaurus}"
                    )
                    keyword = Keyword(
                        thesaurus=thesaurus,
                        keyword_id=concept,
                        label_de=translations["de"],
                        label_fr=translations["fr"],
                        label_en=translations["en"],
                        label_it=translations.get("it"),
                        label_rm=translations.get("rm"),
                    )
                    keyword.save()
                    created += 1
                keywords.append(keyword)

        return keywords, created

    # ##########################################################################
    def import_distributions(self, configs: dict, clean: bool) -> None:
        """Import the distributions and dataservices used by the aggregate datasets.

        Ensures that per aggregate dataset (base topic):
        - one default WMS data service is created (or updated)
        - one default external WMS distribution for the data is created (or updated)

        Also ensures that the additional av data services and WMS distributions are created or
        updated.

        """

        self.print_success("Importing distributions")

        mappings = DatasetMapping.table()

        metrics = {
            "dataservices.created": 0,
            "dataservices.updated": 0,
            "datservices.removed": 0,
            "datservices.obsoleted": 0,
            "distributions.created": 0,
            "distributions.updated": 0,
            "distributions.removed": 0,
            "distributions.obsoleted": 0,
        }

        processed = set()
        for base_topic in configs["de"]:
            processed.add(base_topic)

            # Dataset
            dataset_id = self.dataset_id({"base_topic": base_topic}, aggregate=True)
            dataset, _ = mappings.match(dataset_id)
            if dataset:
                self.print(f"Dataset mapping found for dataset_id {dataset_id}: {dataset}")
            else:
                dataset = Dataset.objects.filter(dataset_id=dataset_id).first()
                if not dataset:
                    self.print_warning(f"No dataset {dataset_id}")
                    continue

            languages = [Lang(pt3=lang).pt1 for lang in configs["de"][base_topic]["languages"]]

            # Data Service and Distributions
            ds_created, ds_updated, dist_created, dist_updated = (
                self.import_dataservices_and_distributions(
                    dataset=dataset,
                    dataservice_name=base_topic,
                    availability=True,
                    stac=True,
                    distribution_id=f"{dataset_id}:wms",
                    base_topic=base_topic,
                    languages=languages,  # ty:ignore[invalid-argument-type]
                    config_de=configs["de"][base_topic]["default"],
                    config_fr=configs["fr"][base_topic]["default"],
                    config_it=configs["it"][base_topic]["default"],
                    config_en=configs["en"][base_topic]["default"],
                    preferred_distribution=True,
                )
            )
            metrics["dataservices.created"] += ds_created
            metrics["dataservices.updated"] += ds_updated
            metrics["distributions.created"] += dist_created
            metrics["distributions.updated"] += dist_updated

            # AV is a special case where the derivates returned by the API don't correspond to
            # different topic versions but rather to different representations with their own WMS.
            # We'll add them here as (non-preferred) distributions as well.
            if base_topic == "av":
                for number, (title_de, config_de) in enumerate(
                    configs["de"][base_topic]["derivates"].items()
                ):
                    # Parse the WMS url to get a nice name similar to the base topic
                    match = re.match(r".*/db/(.*)_0/deu.*", config_de["wms"])
                    if not match:
                        self.print_error(f"Unexpected WMS url {config_de['wms']}")
                        continue

                    name = match.group(1)
                    if name == "av":
                        continue

                    title_fr = next(
                        title
                        for title, value in configs["fr"][base_topic]["derivates"].items()
                        if f"/{name}_0" in value["wms"]
                    )
                    title_it = next(
                        title
                        for title, value in configs["it"][base_topic]["derivates"].items()
                        if f"/{name}_0" in value["wms"]
                    )
                    titles_and_descriptions = {
                        "title_de": title_de.split(":")[1][:-1].strip(),
                        "title_fr": title_fr.split(":")[1][:-1].strip(),
                        "title_it": title_it.split(":")[1][:-1].strip(),
                        "title_en": None,
                        "description_de": dataset.description_de,
                        "description_fr": dataset.description_fr,
                        "description_it": dataset.description_it,
                        "description_en": dataset.description_en,
                        "description_rm": dataset.description_rm,
                    }

                    ds_created, ds_updated, dist_created, dist_updated = (
                        self.import_dataservices_and_distributions(
                            dataset=dataset,
                            dataservice_name=name,
                            availability=False,
                            stac=False,
                            distribution_id=f"{dataset_id.replace('av', name)}:wms",
                            base_topic=base_topic,
                            languages=languages,  # ty:ignore[invalid-argument-type]
                            config_de=config_de,
                            config_fr=list(configs["fr"][base_topic]["derivates"].values())[number],
                            config_it=list(configs["it"][base_topic]["derivates"].values())[number],
                            config_en=list(configs["en"][base_topic]["derivates"].values())[number],
                            preferred_distribution=False,
                            titles_and_descriptions=titles_and_descriptions,
                        )
                    )
                    metrics["dataservices.created"] += ds_created
                    metrics["dataservices.updated"] += ds_updated
                    metrics["distributions.created"] += dist_created
                    metrics["distributions.updated"] += dist_updated

        (
            metrics["dataservices.removed"],
            metrics["dataservices.obsoleted"],
        ) = self.cleanup_objects(Dataservice, processed, clean)

        (
            metrics["distributions.removed"],
            metrics["distributions.obsoleted"],
        ) = self.cleanup_objects(Distribution, processed, clean)

        self.print_success(f"Distribution import completed. Metrics: {metrics}")

    def import_dataservices_and_distributions(  # noqa: PLR0913, PLR0917
        self,
        dataset: Dataset,
        dataservice_name: str,
        availability: bool,
        stac: bool,
        distribution_id: str,
        base_topic: str,
        languages: list[ISO639_1],
        config_de: dict,
        config_fr: dict,
        config_it: dict,
        config_en: dict,
        preferred_distribution: bool,
        titles_and_descriptions: dict | None = None,
    ) -> tuple[int, int, int, int]:
        """Creates the dataservices and all necessary distributions for the given layer
        layer.

        Returns a tuple with the number of created dataservices, updated dataservices, created
        distributions and updated distributions.
        """
        ds_created, ds_updated, dist_created, dist_updated = 0, 0, 0, 0

        # Data dataservice
        capabilities_url = config_de["wms"].replace(
            "/deu", "/{lang3}?SERVICE=WMS&REQUEST=GetCapabilities"
        )
        dataservice, created, updated = self.import_wms_data_service(
            dataservice_id=f"wms-geodienste-{dataservice_name}",
            data_source_id=base_topic,
            languages=languages,
            default_language="de",
            capabilities_url=capabilities_url,
            title=f"WMS geodienste.ch {dataservice_name}",
        )
        ds_created += created
        ds_updated += updated

        # Data distribution
        # TODO: The distribution ID (set similarly to the ones from the BOD) is not a valid slug
        layer_names = {
            "de": config_de["layers"][0]["name"],
            "fr": config_fr["layers"][0]["name"],
            "it": config_it["layers"][0]["name"] if "it" in languages else None,
            "en": config_en["layers"][0]["name"] if "en" in languages else None,
        }
        titles_and_descriptions = (
            titles_and_descriptions
            or self.get_wms_layer_title_and_description(capabilities_url, layer_names, dataset)
        )
        distribution, created, updated = self.import_wms_distribution(
            distribution_id=distribution_id,
            data_source_id=base_topic,
            dataset=dataset,
            dataservice=dataservice,
            wms_layer_name_de=layer_names["de"],
            wms_layer_name_fr=layer_names["fr"],
            wms_layer_name_it=layer_names["it"],
            wms_layer_name_en=layer_names["en"],
            wms_layer_name_rm=None,
            opacity=Decimal(str(config_de["layers"][0]["opacity"])),
            **titles_and_descriptions,
        )
        dist_created += created
        dist_updated += updated

        if preferred_distribution and dataset.preferred_distribution != distribution:
            self.print(f"Setting {distribution} as preferred distribution for dataset {dataset}")
            dataset.preferred_distribution = distribution
            dataset.save()

        # Additional distributions
        for number, alt_de in enumerate(config_de["swissgeo_distributions"]):
            alt_fr = config_fr["swissgeo_distributions"][number]
            alt_it = config_it["swissgeo_distributions"][number]
            alt_en = config_en["swissgeo_distributions"][number]
            layer_names = {
                "de": alt_de["name"],
                "fr": alt_fr["name"],
                "it": alt_it["name"] if "it" in languages else None,
                "en": alt_en["name"] if "en" in languages else None,
            }
            _, created, updated = self.import_wms_distribution(
                distribution_id=distribution_id.replace(":wms", f"-{alt_de['name']}:wms"),
                data_source_id=base_topic,
                dataset=dataset,
                dataservice=dataservice,
                wms_layer_name_de=layer_names["de"],
                wms_layer_name_fr=layer_names["fr"],
                wms_layer_name_it=layer_names["it"],
                wms_layer_name_en=layer_names["en"],
                wms_layer_name_rm=None,
                opacity=Decimal(str(alt_de["opacity"])),
                **self.get_wms_layer_title_and_description(capabilities_url, layer_names, dataset),
            )
            dist_created += created
            dist_updated += updated

        # Availability dataservice and distribution
        if availability:
            parts = urlsplit(config_de["wms"])
            dataservice_availability, created, updated = self.import_wms_data_service(
                dataservice_id=f"wms-geodienste-{dataservice_name}-availability",
                data_source_id=base_topic,
                languages=["de", "fr", "it", "en"],
                default_language="de",
                capabilities_url=(
                    f"{parts.scheme}://{parts.netloc}/db/availability/{base_topic}/portrayal/{{lang3}}"
                    "?SERVICE=WMS&REQUEST=GetCapabilities"
                ),
                title=f"WMS geodienste.ch {dataservice_name} (availability)",
            )
            ds_created += created
            ds_updated += updated

            _, created, updated = self.import_wms_distribution(
                distribution_id=distribution_id.replace(":wms", "-availability:wms"),
                data_source_id=base_topic,
                dataset=dataset,
                dataservice=dataservice_availability,
                title_de="Verfügbarkeit",
                title_en="Availability",
                title_fr="Disponibilité",
                title_it="Disponibilità",
                description_de="Kantonalen Verfügbarkeit der Daten.",
                description_en="Availability of data at cantonal level.",
                description_fr="Disponibilité des données au niveau cantonal.",
                description_it="Disponibilità dei dati a livello cantonale.",
                wms_layer_name_de="availability_cantons",
                wms_layer_name_fr="availability_cantons",
                wms_layer_name_it="availability_cantons",
                wms_layer_name_en="availability_cantons",
                wms_layer_name_rm=None,
                meta_information=True,
            )
            dist_created += created
            dist_updated += updated

        # STAC distribution
        if stac:
            created, updated = self.import_stac_distribution(
                distribution_id=distribution_id.replace(":wms", ":stac"),
                data_source_id=base_topic,
                dataset=dataset,
                stac_collection_id=base_topic,
                title_de="STAC Download Collection",
                title_fr="STAC Download Collection",
                title_it="STAC Download Collection",
                title_en="STAC Download Collection",
                title_rm="STAC Download Collection",
            )
            dist_created += created
            dist_updated += updated

        return ds_created, ds_updated, dist_created, dist_updated

    def import_wms_data_service(
        self, dataservice_id: str, data_source_id: str, **kwargs
    ) -> tuple[WMSDataservice, int, int]:
        """Ensures that the WMS dataservice with the given ID exists and that it has the given
        attributes.

        Returns a tuple with the dataservice and the number of created and updated dataservices.

        """
        dataservice = WMSDataservice.objects.filter(dataservice_id=dataservice_id).first()
        if dataservice:
            self.print(f"Dataservice with dataservice_id {dataservice_id} already exists")
        else:
            self.print(
                f"Dataservice with dataservice_id {dataservice_id} does not exist yet, "
                "creating a new one"
            )
            dataservice = WMSDataservice(
                dataservice_id=dataservice_id,
                data_source=Dataservice.DataSource.GEODIENSTE,
                data_source_ids=[data_source_id],
                **kwargs,
            )
            dataservice.save()
            return dataservice, 1, 0

        updated = False
        for key, value in kwargs.items():
            if value != getattr(dataservice, key):
                updated = True
                setattr(dataservice, key, value)
        if updated:
            self.print(f"Dataservice with dataservice_id {dataservice_id} changed")
            dataservice.save()
            return dataservice, 0, 1

        return dataservice, 0, 0

    def import_wms_distribution(
        self, distribution_id: str, data_source_id: str, **kwargs
    ) -> tuple[ExternalWMSDistribution, int, int]:
        """Ensures that the external WMS distribution with the given ID exists and that it has the
        given attributes.

        Returns a tuple with the distribution and the number of created and updated distributions.

        """
        distribution = ExternalWMSDistribution.objects.filter(
            distribution_id=distribution_id
        ).first()
        if distribution:
            self.print(f"Distribution with distribution_id {distribution_id} already exists")
        else:
            self.print(
                f"Distribution with distribution_id {distribution_id} does not exist yet, "
                "creating a new one"
            )
            distribution = ExternalWMSDistribution(
                distribution_id=distribution_id,
                data_source=Distribution.DataSource.GEODIENSTE,
                data_source_ids=[data_source_id],
                **kwargs,
            )
            distribution.save()
            return distribution, 1, 0

        updated = False
        for key, value in kwargs.items():
            if value != getattr(distribution, key):
                updated = True
                setattr(distribution, key, value)
        if updated:
            self.print(f"Distribution with distribution_id {distribution_id} changed")
            distribution.save()
            return distribution, 0, 1

        return distribution, 0, 0

    def get_wms_layer_title_and_description(
        self,
        capabilities_url: str,
        layer_names: dict,
        dataset: Dataset,
    ) -> dict:
        """Fetches the title and description of a layer from the WMS GetCapabilities. Falls back
        to the dataset title and description in case of generic data layers as these are not
        meaningful.

        Returns a dictionary with titles and descriptions or an empty dict in case of an error.
        """

        if layer_names["de"] == "daten":
            return {
                "title_de": dataset.title_short_de,
                "title_fr": dataset.title_short_fr,
                "title_en": dataset.title_short_en,
                "title_it": dataset.title_short_it,
                "title_rm": dataset.title_short_rm,
                "description_de": dataset.description_de,
                "description_fr": dataset.description_fr,
                "description_en": dataset.description_en,
                "description_it": dataset.description_it,
                "description_rm": dataset.description_rm,
            }

        def get_tag(root: etree._Element, tag_name: str) -> str:
            tag = root.find(f"{{http://www.opengis.net/wms}}{tag_name}")
            if tag is not None:
                return (tag.text or "").strip()
            return ""

        result = {}
        try:
            for lang, layer_name in layer_names.items():
                if not layer_name:
                    continue

                url = capabilities_url.replace("{lang3}", Lang(pt1=lang).pt3)
                response = get(url, timeout=self.options["timeout"])
                response.raise_for_status()
                root = etree.fromstring(response.content)
                for layer in root.iter("{http://www.opengis.net/wms}Layer"):
                    name = get_tag(layer, "Name")
                    if name.strip() != layer_name:
                        continue
                    result[f"title_{lang}"] = get_tag(layer, "Title")
                    result[f"description_{lang}"] = get_tag(layer, "Abstract")

        except Exception as e:  # noqa: BLE001
            self.print_error(f"Failed to retreive {url}: {e}")
            return {}

        return result

    def import_stac_distribution(
        self, distribution_id: str, data_source_id: str, **kwargs
    ) -> tuple[int, int]:
        """Ensures that the external STAC dataservice and distribution with the given ID exists and
        that it has the given attributes.

        Returns a tuple with the number of created and updated distributions.

        """

        dataservice = OGCAPIStacDataservice.objects.filter(dataservice_id="stac-geodienste").first()
        if not dataservice:
            self.print_warning("Dataservice stac-geodienste not found, import fixtures first")
            return 0, 0

        distribution = ExternalStacDistribution.objects.filter(
            distribution_id=distribution_id
        ).first()
        if distribution:
            self.print(f"Distribution with distribution_id {distribution_id} already exists")
        else:
            self.print(
                f"Distribution with distribution_id {distribution_id} does not exist yet, "
                "creating a new one"
            )
            distribution = ExternalStacDistribution(
                distribution_id=distribution_id,
                data_source=Distribution.DataSource.GEODIENSTE,
                data_source_ids=[data_source_id],
                dataservice=dataservice,
                **kwargs,
            )
            distribution.save()
            return 1, 0

        updated = False
        for key, value in kwargs.items():
            if value != getattr(distribution, key):
                updated = True
                setattr(distribution, key, value)
        if updated:
            self.print(f"Distribution with distribution_id {distribution_id} changed")
            distribution.save()
            return 0, 1

        return 0, 0
