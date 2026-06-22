import json
from json import loads
from pathlib import Path
from typing import Any, Literal

from requests import get

from django.core.management.base import CommandParser

from harvest.models import OrganizationMapping, PrefixLookupTable
from harvest.utils import (
    AGGREGATE_PROVIDER_CONTACT,
    AGGREGATE_PROVIDER_ID,
    AGGREGATE_PROVIDER_ORGANIZATION,
    CANTONAL_PROVIDER_ORGANIZATIONS,
)
from organization.models import Contact, Organization
from utils.command import CustomBaseCommand

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
            "--services-endpoint",
            default="https://geodienste.ch/info/services.json",
            help=(
                "Services information (JSON) endpoint URL. Can also be a path to a local folder "
                "with one JSON file per language: services_de.json, services_fr.json, "
                "services_it.json"
            ),
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default="60",
            help="Timeout when calling services information (JSON) endpoint",
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

        languages = set()

        if options["organizations"] or options["contacts"]:
            languages.add("de")

        services = {}
        if languages:
            services = self.get_services(
                options["services_endpoint"], languages, options["timeout"]
            )
        if not services:
            self.print_warning("No services available, aborting")
            return

        # Handle sub-commands
        if options["organizations"]:
            self.import_organizations(services, options["clean"])
        if options["contacts"]:
            self.import_contacts(services, options["clean"])

    # ##########################################################################
    def get_services(self, services_endpoint: str, languages: set[Language], timeout: int) -> dict:
        """Download the service information as JSON from the provided endpoint URL for each
        requested language. Transform the result to be indexable by provider and base topic.

        The URL might alternatively be a path to a local JSON file.
        """

        result = {}
        for language in languages:
            try:
                filename = Path(services_endpoint) / f"services_{language}.json"
                with open(filename) as file:
                    result[language] = loads(file.read())
                continue
            except:  # noqa: E722, S110
                pass

            try:
                url = f"{services_endpoint}?language={language}"
                response = get(url, timeout=timeout)
                response.raise_for_status()
                result[language] = response.json()
            except Exception as e:  # noqa: BLE001
                self.print_error(f"Failed to retreive services: {e}")
                return {}

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
        entry is given.

        The provider ID is:
        - for cantonal providers: "LU", "BE", etc.
        - for brokers: "BFE", etc.
        - for aggregate providers: "KGK"

        """
        if service:
            return service["broker"] or service["canton"]

        return AGGREGATE_PROVIDER_ID

    def organization_id(self, provider_id: str) -> str:
        """Returns the organization ID for the given provider ID.

        The organization ID is:
        - for cantonal providers: "ch.geodienste-lu", "ch.geodienste-be", etc.
        - for brokers: "ch.bfe", etc.
        - for aggregate providers: "ch.kgk"

        """
        if provider_id in CANTONAL_PROVIDER_ORGANIZATIONS:
            return f"ch.geodienste-{provider_id.lower()}"

        return f"ch.{provider_id.lower()}"

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
