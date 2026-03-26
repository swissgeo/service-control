import logging

from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from pystac_client import Client

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.template.defaultfilters import slugify
from django.utils.translation import pgettext_lazy as _

from dataset.models import Dataset
from distribution.models import ExternalStacDistribution
from utils.fields import CustomSlugField

logger = logging.getLogger(__name__)

_context = "Dataservice Module"


class DataserviceManager(PolymorphicManager):
    def get_by_natural_key(self, dataservice_id: str) -> models.Model:
        return self.get(dataservice_id=dataservice_id)


class Dataservice(PolymorphicModel):
    """Dataservice model."""

    dataservice_id = CustomSlugField(_(_context, "External ID"), unique=True, max_length=100)

    title = models.CharField(_(_context, "Title"), max_length=128)
    openapi_spec_url = models.URLField(
        _(_context, "OpenAPI Specification URL"),
        max_length=500,
        blank=True,
        null=True,
    )
    documentation_url_de = models.URLField(
        _(_context, "Documentation URL (DE)"),
        max_length=500,
        blank=True,
        null=True,
    )
    documentation_url_fr = models.URLField(
        _(_context, "Documentation URL (FR)"),
        max_length=500,
        blank=True,
        null=True,
    )
    documentation_url_en = models.URLField(
        _(_context, "Documentation URL (EN)"),
        max_length=500,
        blank=True,
        null=True,
    )
    documentation_url_it = models.URLField(
        _(_context, "Documentation URL (IT)"),
        max_length=500,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_(_context, "Created at"),
        help_text=_(_context, "Date and time when the dataservice was created"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_(_context, "Updated at"),
        help_text=_(_context, "Date and time when the dataservice was last updated"),
    )

    objects = DataserviceManager()

    class Meta:
        verbose_name = _("Dataservice Model", "Dataservice")
        verbose_name_plural = _("Dataservice Model", "Dataservices")

    def __str__(self) -> str:
        return self.dataservice_id

    def save(self, *args, **kwargs) -> None:
        if not self.dataservice_id:
            self.dataservice_id = slugify(self.title)

        super().save(*args, **kwargs)

    def natural_key(self) -> tuple:
        return (self.dataservice_id,)

    @property
    def service_type(self) -> str:
        raise NotImplementedError(
            "Subclasses of Dataservice must implement the service_type property"
        )


class WMSDataservice(Dataservice):
    languages = ArrayField(
        models.CharField(
            max_length=32,
        ),
        verbose_name=_(_context, "Supported Languages"),
        help_text=_(_context, "List of supported languages for the WMS Dataservice"),
    )
    capabilities_url = models.URLField(
        _(_context, "Capabilities URL"),
        max_length=500,
        help_text=_(
            _context,
            "URL to the capabilities document of the WMS Dataservice. "
            "The URL can contain the following placeholders: {lang} for the "
            "different languages in which the WMS is available.",
        ),
    )

    class Meta:
        verbose_name = _("WMS Dataservice", "WMS Dataservices")
        verbose_name_plural = _("WMS Dataservice", "WMS Dataservices")

    @property
    def service_type(self) -> str:
        return "ogc:wms"


class WMTSDataservice(Dataservice):
    variable_epsg_list = ArrayField(
        models.IntegerField(),
        verbose_name=_(_context, "List of supported CRS (EPSG codes)"),
        help_text=_(
            _context,
            "List of the EPSG codes for the supported CRS of the WMTS Dataservice "
            "if {epsg} placeholder is used in the capabilities URL.",
        ),
    )
    capabilities_url = models.URLField(
        _(_context, "Capabilities URL"),
        max_length=500,
        help_text=_(
            _context,
            "URL to the capabilities document of the WTMS Dataservice. "
            "The URL can contain the following placeholders: {epsg} for the "
            "different supported EPSG code.",
        ),
    )

    class Meta:
        verbose_name = _("WMTS Dataservice", "WMTS Dataservices")
        verbose_name_plural = _("WMTS Dataservice", "WMTS Dataservices")

    @property
    def service_type(self) -> str:
        return "ogc:wmts"


class WFSDataservice(Dataservice):
    class Meta:
        verbose_name = _("WFS Dataservice", "WFS Dataservices")
        verbose_name_plural = _("WFS Dataservice", "WFS Dataservices")

    @property
    def service_type(self) -> str:
        return "ogc:wfs"


class OGCAPIFeaturesDataservice(Dataservice):
    class Meta:
        verbose_name = _("OGC API Features Dataservice", "OGC API Features Dataservices")
        verbose_name_plural = _("OGC API Features Dataservice", "OGC API Features Dataservices")

    @property
    def service_type(self) -> str:
        return "ogcapi:features"


class OGCAPIStacDataservice(Dataservice):
    landing_page_url = models.URLField(
        _(_context, "Landing Page URL"),
        max_length=500,
        blank=True,
        null=True,
        help_text=_(_context, "URL to the landing page of the OGC API STAC Dataservice"),
    )

    class Meta:
        verbose_name = _("OGC API STAC Dataservice", "OGC API STAC Dataservices")
        verbose_name_plural = _("OGC API STAC Dataservice", "OGC API STAC Dataservices")

    @property
    def service_type(self) -> str:
        return "ogcapi:stac"

    def sync_from_capabilities(self, default_dataset_id: str = "ORPHANAGE") -> None:
        """Evaluate the capabilities to detect distributions.

        We try to map STAC collection_ids automatically to datasets. If no matching
        dataset is found, the distribution is added to the default dataset (if given).
        """

        processed = set()

        orphanage_dataset = Dataset.objects.get(dataset_id=default_dataset_id)

        # Get managed collections from STAC API
        client = Client.open(self.landing_page_url)
        for collection in client.collection_search().collections():
            collection_id = collection.id
            processed.add(collection_id)

            # check if distribution with this collection_id already exists
            try:
                distribution = ExternalStacDistribution.objects.get(
                    stac_collection_id=collection_id,
                    dataservice=self,
                )
                logger.debug(
                    "Distribution for collection_id %s already exists, "
                    "skipping creation for dataservice %s.",
                    collection_id,
                    self.dataservice_id,
                )
            except ExternalStacDistribution.DoesNotExist:
                # try to find a dataset with the same geocat_id as the collection_id
                dataset = Dataset.objects.filter(dataset_id=collection_id).first()

                if not dataset:
                    logger.warning(
                        "No dataset found for collection_id %s, "
                        "adding distribution to default dataset %s.",
                        collection_id,
                        default_dataset_id,
                    )
                    dataset = orphanage_dataset

                # create new distribution
                ExternalStacDistribution.objects.create(
                    distribution_id=f"{collection_id}:stac",
                    dataset=dataset,
                    title="STAC Download Collection",
                    data_source="service-capabilities",
                    dataservice=self,
                    stac_collection_id=collection_id,
                )
                logger.info(
                    f"Added distribution for collection_id {collection_id} to "
                    f"dataset {dataset.dataset_id} from dataservice {self.dataservice_id}."
                )
            else:
                # If the distribution is linked to the orphanage dataset, we check if there's
                # a dataset now matching the collection_id and link it to this dataset if found

                if distribution.dataset == orphanage_dataset:
                    dataset = Dataset.objects.filter(dataset_id=collection_id).first()
                    if dataset:
                        distribution.dataset = dataset
                        distribution.save()
                        logger.info(
                            f"Updated distribution for collection_id {collection_id} to "
                            f"dataset {dataset.dataset_id} from dataservice {self.dataservice_id}."
                        )


class GeoadminFeaturesDataservice(Dataservice):
    class Meta:
        verbose_name = _("Geoadmin Features Dataservice", "Geoadmin Features Dataservices")
        verbose_name_plural = _("Geoadmin Features Dataservice", "Geoadmin Features Dataservices")

    @property
    def service_type(self) -> str:
        return "geoadmin:features"
