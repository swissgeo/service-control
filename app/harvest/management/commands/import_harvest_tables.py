import json
from typing import TYPE_CHECKING, Any

import boto3
import environ

from django.core.management.base import CommandParser
from django.db.models import Q

from dataservice.models import GeoadminFeaturesDataservice, WMSDataservice, WMTSDataservice
from dataset.models import Dataset, DatasetToContact, DatasetToUnit
from distribution.models import (
    Distribution,
    ExternalGeoadminFeaturesDistribution,
    ExternalGeoJSONDistribution,
    ExternalWMSDistribution,
    ExternalWMTSDistribution,
)
from harvest.import_models import (
    ContactList,
    DatasetImport,
    KeywordList,
    LayersJSImport,
    OrganizationImport,
    ParsingError,
)
from harvest.models import DatasetToContactMapping, DatasetToUnitMapping
from organization.models import Contact, Organization, Unit
from thesaurus.models import Keyword, Thesaurus
from utils.command import CustomBaseCommand

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBClient


env = environ.Env()


class Command(CustomBaseCommand):
    """Import data from DynamoDB harvesting tables.

    This command imports data from DynamoDB harvesting tables. It currently supports importing
    organizations, but can be extended to import other entities in the future.

    """

    help = "Importing data from DynamoDB harvesting tables. "
    "Currently supports importing organizations."

    def add_arguments(self, parser: CommandParser) -> None:
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        # Select entities to import
        parser.add_argument(
            "--organizations",
            action="store_true",
            help="Import organizations",
        )
        parser.add_argument(
            "--datasets",
            action="store_true",
            help="Import datasets",
        )
        parser.add_argument(
            "--distributions",
            action="store_true",
            help="Import datasets",
        )
        parser.add_argument(
            "--keywords",
            action="store_true",
            help="Import keywords",
        )
        parser.add_argument(
            "--contacts",
            action="store_true",
            help="Import contacts",
        )

        parser.add_argument(
            "--target-env",
            type=str,
            choices=["dev", "int", "prod"],
            default="dev",
            help="Specify the target environment",
        )

        parser.add_argument(
            "--profile",
            type=str,
            nargs="?",
            default=None,
            help="Specify the profile name (only needed locally)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""
        profile = options.get("profile")
        if profile and profile != "default":
            self.session = boto3.Session(profile_name=profile)
        else:
            self.session = boto3.Session()

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        # Handle sub-commands
        if options["organizations"]:
            self.import_organizations(*args, **options)
        if options["datasets"]:
            self.import_datasets(*args, **options)
        if options["distributions"]:
            self.import_distributions(*args, **options)
        if options["keywords"]:
            self.import_keywords(*args, **options)
        if options["contacts"]:
            self.import_contacts(*args, **options)

    # ##########################################################################
    def import_organizations(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success("Importing organizations")

        dynamodb_client: DynamoDBClient = self.session.client(
            "dynamodb", region_name="eu-central-1"
        )
        paginator = dynamodb_client.get_paginator("scan")

        obsolete = set(
            Organization.objects.filter(
                data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION
            ).values_list("organization_id", flat=True)
        )

        for page in paginator.paginate(TableName=f"harvest-providers-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    import_org = OrganizationImport.from_dynamodb_item(item)
                    self.print_success(
                        f"Parsed organization: {import_org.provider_id} - {import_org.name_de}"
                    )
                except ParsingError as e:
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                obsolete.discard(import_org.provider_id)

                # check if we have an existing object with the same provider_id
                # if yes, get it from db and update values,
                # if not, create a new object
                try:
                    org = Organization.objects.get(
                        organization_id=import_org.provider_id,
                        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
                    )
                except Organization.DoesNotExist:
                    self.print(
                        f"Organization with provider_id {import_org.provider_id} does not exist yet"
                        ", creating a new one."
                    )
                    org = Organization(
                        data_source=Organization.DATA_SOURCE_CHOICE_BOD_CONTACT_ORGANIZATION,
                        **import_org.model_dump(by_alias=True),
                    )
                else:
                    self.print(
                        f"Organization with provider_id {import_org.provider_id} already exists, "
                        "updating."
                    )
                    for field in import_org:
                        setattr(org, field[0], field[1])

                org.save()

        if obsolete:
            self.print_warning(f"Obsolete organizations found: {', '.join(obsolete)}")

    # ##########################################################################
    def import_datasets(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success("Importing datasets")

        dynamodb_client: DynamoDBClient = self.session.client(
            "dynamodb", region_name="eu-central-1"
        )
        paginator = dynamodb_client.get_paginator("scan")

        obsolete = set(
            Dataset.objects.filter(data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET).values_list(
                "dataset_id", flat=True
            )
        )

        mappings = DatasetToUnitMapping.table()

        for page in paginator.paginate(TableName=f"harvest-datasets-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    import_ds = DatasetImport.from_dynamodb_item(item)
                    self.print_success(
                        f"Parsed dataset: {import_ds.dataset_id} - {import_ds.title_de}"
                    )
                except Exception as e:  # noqa: BLE001
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                obsolete.discard(import_ds.dataset_id)

                # Create dataset
                ds, _ = Dataset.objects.get_or_create(
                    dataset_id=import_ds.dataset_id,
                    data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET,
                    defaults={
                        "title_short_de": import_ds.title_de,
                        "title_short_fr": import_ds.title_fr,
                        "title_short_en": import_ds.title_en,
                        "title_short_it": import_ds.title_it,
                        "title_short_rm": import_ds.title_rm,
                        "description_de": import_ds.description_de,
                        "description_fr": import_ds.description_fr,
                        "description_en": import_ds.description_en,
                        "description_it": import_ds.description_it,
                        "description_rm": import_ds.description_rm,
                        "geocat_id": import_ds.geocat_id,
                    },
                )

                ds.title_short_de = import_ds.title_de
                ds.title_short_fr = import_ds.title_fr
                ds.title_short_en = import_ds.title_en
                ds.title_short_it = import_ds.title_it
                ds.title_short_rm = import_ds.title_rm
                ds.description_de = import_ds.description_de
                ds.description_fr = import_ds.description_fr
                ds.description_en = import_ds.description_en
                ds.description_it = import_ds.description_it
                ds.description_rm = import_ds.description_rm
                ds.geocat_id = import_ds.geocat_id

                ds.save()

                # Link unit
                unit = mappings.match(import_ds.dataset_id)
                if not unit:
                    if not import_ds.provider:
                        self.print_warning(f"Dataset {import_ds.dataset_id} has no provider")
                        continue

                    org_id = import_ds.provider[0]
                    if not (org := Organization.objects.filter(organization_id=org_id).first()):
                        self.print_warning(f"No organization {org_id}")
                        continue

                    if not (unit := org.unit_set.filter(unit_id=Unit.DEFAULT_UNIT_ID).first()):  # type:ignore[unresolved-attribute]
                        self.print_warning(f"Organization {org_id} has no default unit")
                        continue

                DatasetToUnit.objects.filter(dataset=ds, role="owner").delete()
                DatasetToUnit.objects.create(dataset=ds, unit=unit, role="owner")

        if obsolete:
            self.print_warning(f"Obsolete datasets found: {', '.join(obsolete)}")

    # ##########################################################################
    def import_distributions(self, *args: Any, **options: Any) -> None:  # noqa: ARG002, C901, PLR0912
        # Note: This method is quite complex (the linter complains about it).
        # For now we prioritize having a working version to import the data,
        # even if it's not perfectly clean.

        self.print_success("Importing distributions")

        dynamodb_client: DynamoDBClient = self.session.client(
            "dynamodb", region_name="eu-central-1"
        )
        paginator = dynamodb_client.get_paginator("scan")

        # Try to fetch the Geoadmin WMTS dataservice, which is needed to create WMTS distributions.
        try:
            wmts_dataservice = WMTSDataservice.objects.get(dataservice_id="wmts-geoadminch")
        except WMTSDataservice.DoesNotExist:
            self.print_error(
                "No Geoadmin WMTS Dataservice found, try to load fixtures first "
                "(./manage.py loaddata fixtures/dataservice.json)"
            )
            return

        try:
            wms_dataservice = WMSDataservice.objects.get(dataservice_id="wms-geoadminch")
        except WMSDataservice.DoesNotExist:
            self.print_error(
                "No Geoadmin WMTS Dataservice found, try to load fixtures first "
                "(./manage.py loaddata fixtures/dataservice.json)"
            )
            return

        try:
            geoadminfeature_dataservice = GeoadminFeaturesDataservice.objects.get(
                dataservice_id="api3features-geoadminch"
            )
        except Dataset.DoesNotExist:
            self.print_error(
                "No Geoadmin Features Dataservice found, try to load fixtures first "
                "(./manage.py loaddata fixtures/dataservice.json"
            )
            return

        for page in paginator.paginate(TableName=f"harvest-layers-js-{options['target_env']}"):
            for item in page["Items"]:
                try:
                    ljs = LayersJSImport.from_dynamodb_item(item)
                    self.print_success(f"Parsed layers_js: {ljs.layer_id}")
                except Exception as e:  # noqa: BLE001
                    self.print_error(f"Failed to parse item: {item}. Error: {e}")

                try:
                    dataset = Dataset.objects.get(dataset_id=ljs.layer_id)
                except Dataset.DoesNotExist:
                    self.print_error(f"No Dataset found for layer_id {ljs.layer_id}")
                    continue

                # If the layertype is WMTS we create a WMTS and WMS distribution,
                # if it's WMS only a WMS distribution
                if ljs.layertype == "wmts":
                    dist = self.import_wmts_distribution(ljs, dataset, wmts_dataservice)
                    # Set the preferred distribution to WMTS for WMTS layers
                    dataset.preferred_distribution = dist
                    dataset.save()

                if ljs.layertype in ["wms", "wmts"]:
                    dist = self.import_wms_distribution(ljs, dataset, wms_dataservice)
                    # If the preferred distribution is not set yet, we set it to the WMS
                    # distribution
                    if not dataset.preferred_distribution:
                        dataset.preferred_distribution = dist
                        dataset.save()

                if ljs.layertype == "geojson":
                    dist = self.import_geojson_distribution(ljs, dataset)
                    # If the preferred distribution is not set yet,
                    # we set it to the GeoJSON distribution. Currently,
                    # layers of type geojson only have a GeoJSON distribution.
                    if not dataset.preferred_distribution:
                        dataset.preferred_distribution = dist
                        dataset.save()

                if ljs.tooltip or ljs.searchable:
                    # We also create a Geoadmin Features distribution for layers with tooltip=true
                    dist = self.import_api3features_distribution(
                        ljs, dataset, geoadminfeature_dataservice
                    )

    def import_wmts_distribution(
        self, ljs: LayersJSImport, dataset: Dataset, wmts_dataservice: WMTSDataservice
    ) -> Distribution:

        wmts_distribution_id = ljs.layer_id + ":wmts"
        self.print(f"Importing WMTS Distribution {wmts_distribution_id}")

        dist, _ = ExternalWMTSDistribution.objects.get_or_create(
            distribution_id=wmts_distribution_id,
            dataset=dataset,
            wmts_layer_name=ljs.layer_id,
        )
        dist.dataservice = wmts_dataservice
        dist.data_source = Distribution.DATA_SOURCE_CHOICE_BOD_LAYERS_JS
        dist.title = "WMTS Layer"

        # opacity must be between 0 (excluded) and 1 (included)
        if ljs.opacity and ljs.opacity <= 1 and ljs.opacity > 0:
            dist.opacity = ljs.opacity
        dist.save()
        return dist

    def import_wms_distribution(
        self, ljs: LayersJSImport, dataset: Dataset, wms_dataservice: WMSDataservice
    ) -> Distribution:

        wms_distribution_id = ljs.layer_id + ":wms"
        self.print(f"Importing WMS Distribution {wms_distribution_id}")

        dist, _ = ExternalWMSDistribution.objects.get_or_create(
            distribution_id=wms_distribution_id,
            dataset=dataset,
            wms_layer_name=ljs.layer_id,
        )
        dist.dataservice = wms_dataservice
        dist.data_source = Distribution.DATA_SOURCE_CHOICE_BOD_LAYERS_JS
        dist.title = "WMS Layer"

        # opacity must be between 0 (excluded) and 1 (included)
        if ljs.opacity and ljs.opacity <= 1 and ljs.opacity > 0:
            dist.opacity = ljs.opacity

        if ljs.wms_gutter:
            dist.gutter = ljs.wms_gutter
        dist.save()
        return dist

    def import_geojson_distribution(self, ljs: LayersJSImport, dataset: Dataset) -> Distribution:

        geojson_distribution_id = ljs.layer_id + ":geojson"
        self.print(f"Importing GeoJSON Distribution {geojson_distribution_id}")

        dist, _ = ExternalGeoJSONDistribution.objects.get_or_create(
            distribution_id=geojson_distribution_id,
            dataset=dataset,
            defaults={"geojson_url_de": ljs.geojson_url_de},
        )
        dist.data_source = Distribution.DATA_SOURCE_CHOICE_BOD_LAYERS_JS
        dist.title = "GeoJSON Layer"
        dist.geojson_url_de = ljs.geojson_url_de
        dist.geojson_url_fr = ljs.geojson_url_fr
        dist.geojson_url_it = ljs.geojson_url_it
        dist.geojson_url_en = ljs.geojson_url_en
        dist.geojson_url_rm = ljs.geojson_url_rm
        # The geojson style URL is not stored in the layers_js table,
        # but we can construct it from the layer_id
        # (see https://github.com/geoadmin/mf-chsdi3/blob/master/chsdi/models/bod.py#L142)
        # Note: we always reference prod env here
        dist.style_url = "https://api3.geo.admin.ch/static/vectorStyles/" + ljs.layer_id + ".json"
        dist.save()
        return dist

    def import_api3features_distribution(
        self,
        ljs: LayersJSImport,
        dataset: Dataset,
        geoadminfeature_dataservice: GeoadminFeaturesDataservice,
    ) -> Distribution:

        geoadminfeature_distribution_id = ljs.layer_id + ":api3features"
        self.print(f"Importing Geoadmin Features Distribution {geoadminfeature_distribution_id}")

        dist, _ = ExternalGeoadminFeaturesDistribution.objects.get_or_create(
            distribution_id=geoadminfeature_distribution_id,
            dataset=dataset,
            layer_id=ljs.layer_id,
        )
        dist.dataservice = geoadminfeature_dataservice
        dist.data_source = Distribution.DATA_SOURCE_CHOICE_BOD_LAYERS_JS
        dist.title = "Geoadmin Features"
        # Note: This information is not relyable in the layers_js table. There are
        # layers with searchable=true that return 404 for search requests on ../SearchServer
        # with `type=features`, which indicates that they are not actually queryable.
        dist.queryable = ljs.searchable
        # Note: This distribution is only created if tooltip=true in layers_js
        # so this automatically means the layer is 'renderable' (i.e. has a html tooltip),
        # but we set it explicitly here for clarity.
        dist.renderable = ljs.tooltip
        dist.save()
        return dist

    # ##########################################################################
    def import_keywords(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success("Importing keywords")

        dynamodb_client: DynamoDBClient = self.session.client(
            "dynamodb", region_name="eu-central-1"
        )

        query = Dataset.objects.filter(data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET)
        for dataset in query.iterator():
            self.print(f"Processing {dataset.dataset_id}")

            response = dynamodb_client.get_item(
                TableName=f"harvest-keywords-{options['target_env']}",
                Key={"dataset_id": {"S": dataset.dataset_id}},
            )
            item = response.get("Item")

            if not item:
                self.print("Dataset %s has no keyword harvest table entry", dataset.dataset_id)
                continue

            try:
                item_keywords = KeywordList.from_dynamodb_item(item)
            except ParsingError as e:
                self.print_error(
                    "Failed to parse keyword list for dataset %s: %s", dataset.dataset_id, e
                )
                continue

            keywords = set()
            for item_keyword in item_keywords.keywords:
                if not item_keyword.thesaurus_id or not item_keyword.concept:
                    continue

                thesaurus, _ = Thesaurus.objects.get_or_create(
                    thesaurus_id=item_keyword.thesaurus_id
                )
                keyword, _ = Keyword.objects.get_or_create(
                    thesaurus=thesaurus,
                    keyword_id=item_keyword.concept,
                    defaults={
                        "label_de": item_keyword.translation_de,
                        "label_fr": item_keyword.translation_fr,
                        "label_en": item_keyword.translation_en,
                        "label_it": item_keyword.translation_it,
                        "label_rm": item_keyword.translation_rm,
                    },
                )
                keywords.add(keyword)

            dataset.keywords.set(keywords)

    # ##########################################################################
    def import_contacts(self, *args: Any, **options: Any) -> None:  # noqa: ARG002,C901

        self.print_success("Importing contacts")

        dynamodb_client: DynamoDBClient = self.session.client(
            "dynamodb", region_name="eu-central-1"
        )

        mappings = DatasetToContactMapping.table()

        query = Dataset.objects.filter(data_source=Dataset.DATA_SOURCE_CHOICE_BOD_DATASET)
        for dataset in query.iterator():
            self.print(f"Processing {dataset.dataset_id}")

            response = dynamodb_client.get_item(
                TableName=f"harvest-contacts-{options['target_env']}",
                Key={"dataset_id": {"S": dataset.dataset_id}},
            )
            item = response.get("Item")

            if not item:
                self.print("Dataset %s has no contact harvest table entry", dataset.dataset_id)
                continue

            try:
                item_contacts = ContactList.from_dynamodb_item(item)
            except ParsingError as e:
                self.print_error(
                    "Failed to parse contact list for dataset %s: %s", dataset.dataset_id, e
                )
                continue

            DatasetToContact.objects.filter(dataset=dataset).delete()
            for item_contact in item_contacts.contacts:
                role = item_contact.role

                contact = mappings[role].match(dataset.dataset_id) if role in mappings else None
                if not contact:
                    organization = self.find_organization(
                        acronym_de=item_contact.org_acronym_de,
                        acronym_fr=item_contact.org_acronym_fr,
                        name_de=item_contact.org_name_de,
                        name_fr=item_contact.org_name_fr,
                    )

                    if not organization:
                        self.print_error(
                            f"Organization of role {role} not found for dataset {dataset}"
                        )
                        continue

                    contact = self.find_contact(
                        organization=organization,
                        name_de=item_contact.position_name_de,
                        name_fr=item_contact.position_name_fr,
                    )

                if not contact:
                    email = None
                    if item_contact.contact_electronic_mail_addresses:
                        email = item_contact.contact_electronic_mail_addresses[0]
                        if len(item_contact.contact_electronic_mail_addresses) > 1:
                            self.print_warning("Multiple emails not supported")

                    online_resource = None
                    if item_contact.online_resources:
                        online_resource = item_contact.online_resources[0]
                        if len(item_contact.online_resources) > 1:
                            self.print_warning("Multiple online ressources not supported")

                    country = item_contact.contact_country
                    country = country if country and len(country) == 2 else None  # noqa:PLR2004
                    if item_contact.contact_country and not country:
                        self.print_warning(f"Invalid country code {item_contact.contact_country}")

                    self.print(f"Creating contact for organization {organization}")
                    contact = Contact.objects.create(
                        organization=organization,
                        name_de=item_contact.position_name_de,
                        name_fr=item_contact.position_name_fr,
                        name_en=item_contact.position_name_en,
                        name_it=item_contact.position_name_it,
                        name_rm=item_contact.position_name_rm,
                        email=email,
                        phone=item_contact.contact_voice,
                        address_administrative_area=item_contact.contact_administrative_area,
                        address_delivery_point=item_contact.contact_delivery_point,
                        address_postal_code=item_contact.contact_postal_code,
                        address_city=item_contact.contact_city,
                        address_country=country,
                        url_de=getattr(online_resource, "url_de", None),
                        url_fr=getattr(online_resource, "url_fr", None),
                        url_en=getattr(online_resource, "url_en", None),
                        url_it=getattr(online_resource, "url_it", None),
                        url_rm=getattr(online_resource, "url_rm", None),
                    )

                DatasetToContact.objects.create(dataset=dataset, contact=contact, role=role)

    def find_organization(
        self,
        acronym_de: str | None,
        acronym_fr: str | None,
        name_de: str | None,
        name_fr: str | None,
    ) -> Organization | None:
        """Find an organization which best matches the given acronyms or name.

        Returns None if none found.
        """

        query = Q()
        if acronym_de:
            query |= Q(acronym_de=acronym_de)
        if acronym_fr:
            query |= Q(acronym_fr=acronym_fr)
        if name_de:
            query |= Q(name_de__icontains=name_de)
        if name_fr:
            query |= Q(name_fr__icontains=name_fr)

        if not query.children:
            return None

        return Organization.objects.filter(query).first()

    def find_contact(
        self,
        organization: Organization,
        name_de: str | None,
        name_fr: str | None,
    ) -> Contact | None:
        """Find a contact which best matches the given names.

        Returns None if none found but a name was given. If no name was given, returns any contact
        of the given organization with no name (default contact)."""

        if name_de or name_fr:
            query = Q()
            if name_de:
                query |= Q(name_de=name_de)
            if name_fr:
                query |= Q(name_fr=name_fr)
            query &= Q(organization=organization)

            return Contact.objects.filter(query).first()

        return Contact.objects.filter(
            (Q(name_de__isnull=True) | Q(name_de="")) & (Q(name_fr__isnull=True) | Q(name_fr=""))
        ).first()
