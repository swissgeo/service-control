import json
from json import loads
from typing import Any

from requests import get

from django.core.management.base import CommandParser

from harvest.models import OrganizationMapping
from harvest.utils import CANTONS
from organization.models import Contact, Organization
from utils.command import CustomBaseCommand


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
            help="Services information (JSON) endpoint URL. Can also be a path to a local file.",
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

        services = {}
        if options["organizations"] or options["contacts"]:
            services = self.get_services(options["services_endpoint"], options["timeout"])
        if not services:
            self.print_warning("No services available, aborting")
            return

        # Handle sub-commands
        if options["organizations"]:
            self.import_organizations(services)
        if options["contacts"]:
            self.import_contacts(services, options["clean"])

    # ##########################################################################
    def get_services(self, services_endpoint: str, timeout: int) -> dict:
        """Download the service information as JSON from the provided endpoint URL.

        The URL might alternatively be a path to a local JSON file.
        """

        try:
            with open(services_endpoint) as f:
                return loads(f.read())
        except:  # noqa: E722, S110
            pass

        try:
            response = get(services_endpoint, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:  # noqa: BLE001
            self.print_error(f"Failed to retreive services: {e}")

        return {}

    # ##########################################################################
    def import_organizations(self, services: dict) -> None:
        """Import organizations.

        There is one organization per canton + FL.
        """

        self.print_success("Importing organizations")

        mappings = OrganizationMapping.table()

        metrics = {"organizations.created": 0}

        provider_ids = {
            service.get("broker") or service.get("canton")
            for service in services.get("services", [])
        }
        for provider_id in provider_ids:
            organization_id = f"ch.{provider_id.lower()}"

            Organization.objects.remove_data_source_id(provider_id)

            org, _ = mappings.match(provider_id)
            if org:
                self.print(f"Mapping found for provider_id {provider_id}: {org}")
            else:
                org = Organization.objects.filter(
                    organization_id=organization_id,
                    data_source=Organization.DataSource.GEODIENSTE,
                ).first()
                if org:
                    self.print(
                        f"Organization with organization_id {organization_id} already exists"
                    )
                else:
                    self.print(
                        f"Organization with organization_id {organization_id} does not exist"
                        " yet, creating a new one."
                    )
                    org = Organization(
                        organization_id=organization_id,
                        data_source=Organization.DataSource.GEODIENSTE,
                        data_source_ids=[provider_id],
                        name_de=CANTONS[provider_id]["de"]
                        if provider_id in CANTONS
                        else provider_id,
                        name_fr=CANTONS[provider_id]["fr"]
                        if provider_id in CANTONS
                        else provider_id,
                        name_en=CANTONS[provider_id]["en"]
                        if provider_id in CANTONS
                        else provider_id,
                        name_it=CANTONS[provider_id]["it"]
                        if provider_id in CANTONS
                        else provider_id,
                        name_rm=CANTONS[provider_id]["rm"]
                        if provider_id in CANTONS
                        else provider_id,
                        acronym_de=provider_id,
                        acronym_fr=provider_id,
                        acronym_en=provider_id,
                        acronym_it=provider_id,
                        acronym_rm=provider_id,
                    )
                    org.save()
                    metrics["organizations.created"] += 1

            org.add_data_source_id(provider_id)
            org.save()

        self.write_command_metrics(metrics)
        self.print_success(f"Organization import completed. Metrics: {metrics}")

    # ##########################################################################
    def import_contacts(self, services: dict, clean: bool) -> None:
        """Import contacts.

        Each organization may have a conton-wide contact and one contact per dataset. The contacts
        are not structured but rather text.

        Removes obsolete contacts.
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

        for service in services.get("services", []):
            provider_id = service.get("broker") or service.get("canton")
            organization_id = f"ch.{provider_id.lower()}"

            org, _ = mappings.match(provider_id)
            if org:
                self.print(f"Mapping found for provider_id {provider_id}: {org}")
            else:
                org = Organization.objects.filter(
                    organization_id=organization_id,
                    data_source=Organization.DataSource.GEODIENSTE,
                ).first()
            if not org:
                self.print(
                    f"Organization with organization_id {organization_id} does not exist, skipping"
                )
                continue

            fields = (
                ("contact_geo", None),
                ("contact_specialist_department", "base_topic"),
            )
            for contact_field, data_source_id_field in fields:
                if text := (service.get(contact_field) or "").strip():
                    data_source_id = (
                        f"{provider_id}.{service.get(data_source_id_field, contact_field)}"
                    )

                    processed.add(data_source_id)

                    contact = org.contact_set.filter(  # ty:ignore[unresolved-attribute]
                        data_source_ids__contains=[data_source_id]
                    ).first()
                    if contact:
                        self.print(
                            f"Contact {data_source_id} for organization {org} already exists"
                        )
                    else:
                        self.print(
                            f"Contact {data_source_id} for organization {org} does not"
                            " exist yet, creating a new one."
                        )
                        contact = Contact(
                            organization=org,
                            data_source=Contact.DataSource.GEODIENSTE,
                            legacy_contact=text,
                        )
                        metrics["contacts.created"] += 1
                    if contact.legacy_contact != text:
                        self.print(
                            f"Contact {data_source_id} for organization {org} changed, updating"
                        )
                        contact.legacy_contact = text
                        metrics["contacts.updated"] += 1

                    Contact.objects.remove_data_source_id(data_source_id)
                    contact.add_data_source_id(data_source_id)
                    contact.save()

        (
            metrics["contacts.removed"],
            metrics["contacts.obsoleted"],
        ) = self.cleanup_contacts(processed, clean)

        self.write_command_metrics(metrics)
        self.print_success(f"Contact import completed. Metrics: {metrics}")

    def cleanup_contacts(self, processed: set, clean: bool) -> tuple[int, int]:
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
