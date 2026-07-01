import json
from json import loads
from pathlib import Path
from typing import Any, Literal

from requests import get

from django.core.management.base import CommandParser

from dataset.models import Dataset, DatasetToContact, DatasetToDataset, DatasetToUnit
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

# The services API only supports German, French and Italian - no English!
Language = Literal["de", "fr", "it"]


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
            "--services-endpoint",
            default="https://geodienste.ch/info/services.json",
            help="Services information (JSON) endpoint URL.",
        )
        parser.add_argument(
            "--services-directory",
            help=(
                "Path to a local folder containing the response of the services information (JSON) "
                "endpoint URL. It expects one JSON file per language: services_de.json, "
                "services_fr.json, services_it.json. Useful for local development."
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

    def handle(self, *args: Any, **options: Any) -> None:  # noqa:ARG002
        """Main entry point of command."""

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options, default=str)}")

        # Some entities like organizations and contacts have no localized contents, it is sufficient
        # to just use the German response from the API. For localized content on the other hand, we
        # need to query German, French and Italian (no English available!).
        languages: set[Language] = set()
        if options["organizations"] or options["contacts"] or options["keywords"]:
            languages.add("de")
        if options["datasets"]:
            languages.update({"de", "fr", "it"})

        services = {}
        if languages:
            services = self.get_services(
                options["services_endpoint"],
                options["services_directory"],
                languages,
                options["timeout"],
            )
        if not services:
            self.print_warning("No services available, aborting")
            return

        # Handle sub-commands
        if options["organizations"]:
            self.import_organizations(services, options["clean"])
        if options["contacts"]:
            self.import_contacts(services, options["clean"])
        if options["datasets"]:
            self.import_datasets(services, options["clean"])
        if options["keywords"]:
            self.import_keywords(services, options["gemet_thesaurus"], options["geocat_thesaurus"])

    # ##########################################################################
    def get_services(
        self,
        services_endpoint: str,
        services_directory: str,
        languages: set[Language],
        timeout: int,
    ) -> dict:
        """Download the service information as JSON from the provided endpoint URL or load the from
        the given directory for each requested language.

        Transform the result to be indexable by provider and base topic.
        """

        result = {}

        # Load from local files
        if services_directory:
            path = Path(services_directory)
            if not path.exists():
                self.print_error(f"{services_directory} does not exist")
                return {}

            for language in sorted(languages):
                filename = path / f"services_{language}.json"
                if not filename.exists():
                    self.print_error(f"{services_directory} does not exist")
                    return {}

                try:
                    with open(filename) as file:
                        result[language] = loads(file.read())
                except Exception as e:  # noqa: BLE001
                    self.print_error(f"Failed to load file {filename}: {e}")
                    return {}

        # Load from remote endpoint
        else:
            for language in sorted(languages):
                try:
                    url = f"{services_endpoint}?language={language}"
                    response = get(url, timeout=timeout)
                    response.raise_for_status()
                    result[language] = response.json()
                except Exception as e:  # noqa: BLE001
                    self.print_error(f"Failed to retreive services: {e}")
                    return {}

        # Transform the result
        for language in languages:
            result[language] = {
                self.service_key(service): service for service in result[language]["services"]
            }

        return result

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

    def dataset_id(self, service: dict, aggregate: bool = False) -> str:
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
        ) = self.cleanup_organizations(processed, clean)

        self.write_command_metrics(metrics)
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

    def cleanup_organizations(self, processed: set[str], clean: bool) -> tuple[int, int]:
        """Cleanup organizations

        - Check for data source IDs referenced in the organizations but not present anymore in the
          geodienste Services Information API; optionally clean them
        - Check for obsolete organizations, i.e. organizations created by this command but with no
          data source ID reference; optionally delete them

        """

        existing = Organization.objects.existing_data_source_ids(Organization.DataSource.GEODIENSTE)

        if removed := existing - processed:
            if clean:
                for data_source_id in removed:
                    self.print_warning(
                        f"Removing obsolete data_source_id (organization) {data_source_id}"
                    )
                    Organization.objects.remove_data_source_id(data_source_id)
            else:
                ids = sorted(str(r) for r in removed)
                self.print_warning(f"Removed data_source_ids (provider) found: {', '.join(ids)}")

        obsolete = Organization.objects.filter(
            data_source=Organization.DataSource.GEODIENSTE,
            data_source_ids=[],
        )
        if obsolete.count():
            if clean:
                for organization in obsolete:
                    self.print_warning(f"Removing obsolete organization {organization}")
                    organization.delete()
            else:
                ids = sorted(str(c) for c in obsolete)
                self.print_warning(f"Obsolete organizations found: {', '.join(ids)}")

        return len(removed), len(obsolete)

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
        ) = self.cleanup_contacts(processed, clean)

        self.write_command_metrics(metrics)
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

    def cleanup_contacts(self, processed: set[str], clean: bool) -> tuple[int, int]:
        """Cleanup contacts

        - Check for data source IDs referenced in the contacts but not present anymore in the
          geodienste Services Information API; optionally clean them
        - Check for obsolete contacts, i.e. contacts created by this command but with no
          data source ID reference; optionally delete them

        """

        existing = Contact.objects.existing_data_source_ids(Contact.DataSource.GEODIENSTE)

        if removed := existing - processed:
            if clean:
                for data_source_id in removed:
                    self.print_warning(
                        f"Removing obsolete data_source_id (contact) {data_source_id}"
                    )
                    Contact.objects.remove_data_source_id(data_source_id)
            else:
                ids = sorted(str(r) for r in removed)
                self.print_warning(f"Removed data_source_ids (provider) found: {', '.join(ids)}")

        obsolete = Contact.objects.filter(
            data_source=Contact.DataSource.GEODIENSTE,
            data_source_ids=[],
        )
        if obsolete.count():
            if clean:
                for contact in obsolete:
                    self.print_warning(f"Removing obsolete contact {contact}")
                    contact.delete()
            else:
                ids = sorted(str(c) for c in obsolete)
                self.print_warning(f"Obsolete contacts found: {', '.join(ids)}")

        return len(removed), len(obsolete)

    # ##########################################################################
    def import_datasets(self, services: dict, clean: bool) -> None:
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
                aggregate, created, updated = self.import_dataset(
                    aggregate_dataset_id,
                    data_source_id,
                    dataset_mappings,
                    geocat_id=service["meta_data"].get("dataset_url", "").split("/")[-1],
                    **common,
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
                self.dataset_id(service),
                data_source_id,
                dataset_mappings,
                **common,
            )
            metrics["datasets.created"] += created
            metrics["datasets.updated"] += updated

            # Relationship: Part --Child--> Aggregate
            if not part.related_datasets(DatasetToDataset.Role.CHILD, reverse=True).first():
                relationship = DatasetToDataset(
                    subject=part, role=DatasetToDataset.Role.CHILD, object=aggregate
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

            # TODO: preferred_distribution

        (
            metrics["datasets.removed"],
            metrics["datasets.obsoleted"],
        ) = self.cleanup_datasets(processed, clean)

        self.write_command_metrics(metrics)
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

    def cleanup_datasets(self, processed: set[str], clean: bool) -> tuple[int, int]:
        """Cleanup datasets

        - Check for data source IDs referenced in the datasets but not present anymore in the
          geodienste Services Information API; optionally clean them
        - Check for obsolete datasets, i.e. datasets created by this command but with no
          data source ID reference; optionally delete them

        """

        existing = Dataset.objects.existing_data_source_ids(Dataset.DataSource.GEODIENSTE)

        if removed := existing - processed:
            if clean:
                for data_source_id in removed:
                    self.print_warning(
                        f"Removing obsolete data_source_id (dataset) {data_source_id}"
                    )
                    Dataset.objects.remove_data_source_id(data_source_id)
            else:
                ids = sorted(str(r) for r in removed)
                self.print_warning(f"Removed data_source_ids (dataset) found: {', '.join(ids)}")

        obsolete = Dataset.objects.filter(
            data_source=Dataset.DataSource.GEODIENSTE,
            data_source_ids=[],
        )
        if obsolete.count():
            if clean:
                for dataset in obsolete:
                    self.print_warning(f"Removing obsolete dataset {dataset}")
                    dataset.delete()
            else:
                ids = sorted(str(c) for c in obsolete)
                self.print_warning(f"Obsolete datasets found: {', '.join(ids)}")

        return len(removed), len(obsolete)

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
            dataset_id = self.dataset_id(service)
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

        self.write_command_metrics(metrics)
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
