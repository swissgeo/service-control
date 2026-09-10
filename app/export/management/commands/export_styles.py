import json
from decimal import Decimal
from typing import Any

import boto3
import environ
from botocore.client import Config

from django.core.management.base import CommandParser

from distribution.models import (
    Distribution,
    ExternalGeoJSONDistribution,
    ExternalWMSDistribution,
    ExternalWMTSDistribution,
)
from export.models import MaplibreRasterLayer, MaplibreStyle, PaintConfig
from utils.command import CustomBaseCommand

env = environ.Env()

OAS_PREFIX = "api/oas/v0"
ENV_HOSTNAME_POSTFIX = "dev.sgdi.tech"
OAS_BASE_URL = f"https://services.{ENV_HOSTNAME_POSTFIX}/{OAS_PREFIX}"


class Command(CustomBaseCommand):
    """Export styles to static s3 bucket."""

    help = "OAS static style management"

    def add_arguments(self, parser: CommandParser) -> None:
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        # Sub-commands
        sub = parser.add_subparsers(dest="command", required=False, help="Sub-commands")

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Just print what would be done, don't actually upload",
        )
        parser.add_argument(
            "--profile",
            type=str,
            default="default",
            help="AWS CLI profile to use for authentication (default: 'default')",
        )
        parser.add_argument(
            "--target-env",
            type=str,
            choices=["dev", "int", "prod"],
            default="dev",
            help="Specify the target environment",
        )
        parser.add_argument(
            "--wms",
            action="store_true",
            help="Export WMS distribution styles",
        )
        parser.add_argument(
            "--wmts",
            action="store_true",
            help="Export WMTS distribution styles",
        )
        parser.add_argument(
            "--geojson",
            action="store_true",
            help="Export GeoJSON distribution styles",
        )

        clean = sub.add_parser("clean", help="Delete static files from S3 buckets")
        clean.add_argument(
            "--batch-size", type=int, default=1000, help="Number of files to delete per batch"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""
        profile = options.get("profile")
        if profile and profile != "default":
            self.session = boto3.Session(profile_name=profile)  # pylint: disable=attribute-defined-outside-init
        else:
            self.session = boto3.Session()  # pylint: disable=attribute-defined-outside-init

        # S3 client configuration
        client_access_kwargs = {
            "region_name": "eu-central-1",
            "config": Config(signature_version="s3v4"),
        }
        self.s3_client = self.session.client("s3", **client_access_kwargs)  # ty: ignore[no-matching-overload]

        # derive bucket name from target environment
        self.oastyles_s3_bucket = f"oa-styles-static-{options['target_env']}-swissgeo"

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {json.dumps(options)}")

        if options["command"] == "clean":
            self.do_clean(*args, **options)
        else:
            self.do_export(*args, **options)

    # ##########################################################################
    def do_export(self, *args: Any, **options: Any) -> None:
        self.print_success(f"Exporting styles to {self.oastyles_s3_bucket}...")

        # If none of --wms/--wmts/--geojson were given, export all types (default behaviour)
        export_all = not (options["wms"] or options["wmts"] or options["geojson"])

        nr_objs = 0
        if export_all or options["wmts"]:
            nr_objs += self.export_wmts(*args, **options)
        if export_all or options["wms"]:
            nr_objs += self.export_wms(*args, **options)
        if export_all or options["geojson"]:
            nr_objs += self.export_geojson(*args, **options)

        self.print_success(f"Exported {nr_objs} objects to {self.oastyles_s3_bucket}.")

    # ##########################################################################
    def export_wmts(self, *args: Any, **options: Any) -> int:  # noqa: ARG002
        # WMTS Distributions can have an opacity different from 1.0, this would render
        # to a style like
        # {
        #   "layers": [
        #     {
        #       "id": "ch.bakom.uplink1000:wmts",
        #       "source": "wmts.geo.admin.ch",
        #       "type": "raster",
        #       "paint": {
        #         "raster_opacity": 0.75
        #       }
        #     }
        #   ]
        # }
        nr_objs = 0
        for distribution in ExternalWMTSDistribution.objects.all():
            if distribution.opacity >= 1.0:
                continue
            key = self.style_key(distribution)
            style = MaplibreStyle(
                layers=[
                    MaplibreRasterLayer(
                        id=f"{distribution.distribution_id}",
                        source="wmts.geo.admin.ch",
                        type="raster",
                        paint=PaintConfig(raster_opacity=distribution.opacity),
                    )
                ]
            )
            self.print(
                f" - {'[DRY RUN]: ' if options['dry_run'] else ''}"
                f"Uploading style for {distribution.distribution_id} to {key}"
            )
            if not options["dry_run"]:
                self.do_upload(style.model_dump(exclude_none=True, by_alias=True), key)
            else:
                self.print(json.dumps(style.model_dump(exclude_none=True, by_alias=True)))
            nr_objs += 1
        return nr_objs

    # ##########################################################################
    def export_wms(self, *args: Any, **options: Any) -> int:  # noqa: ARG002
        # WMS Distributions can have an opacity different from 1.0 or a gutter > 0
        nr_objs = 0
        for distribution in ExternalWMSDistribution.objects.all():
            if not (distribution.opacity < Decimal("1.0") or distribution.gutter > 0):
                continue
            key = self.style_key(distribution)
            paintconfig = PaintConfig()
            if distribution.opacity < Decimal("1.0"):
                paintconfig.raster_opacity = float(distribution.opacity)
            if distribution.gutter > 0:
                paintconfig.raster_gutter = distribution.gutter
            style = MaplibreStyle(
                layers=[
                    MaplibreRasterLayer(
                        id=f"{distribution.distribution_id}",
                        source="wms.geo.admin.ch",
                        type="raster",
                        paint=paintconfig,
                    )
                ]
            )
            self.print(
                f" - {'[DRY RUN]: ' if options['dry_run'] else ''}"
                f"Uploading style for {distribution.distribution_id} to {key}"
            )
            if not options["dry_run"]:
                self.do_upload(style.model_dump(exclude_none=True, by_alias=True), key)
            else:
                self.print(json.dumps(style.model_dump(exclude_none=True, by_alias=True)))
            nr_objs += 1
        return nr_objs

    # ##########################################################################
    def export_geojson(self, *args: Any, **options: Any) -> int:  # noqa: ARG002
        # The GeoJSON styles are currently in files in this repository
        # this will likely change in the future. For now, we just upload them as-is
        # to s3.
        nr_objs = 0
        for distribution in ExternalGeoJSONDistribution.objects.all():
            if not distribution.style_url:
                continue
            style_file_name = distribution.style_url.rsplit("/", 1)[-1]
            key = f"{OAS_PREFIX}/styles/{style_file_name}"
            self.print(
                f" - {'[DRY RUN]: ' if options['dry_run'] else ''}"
                f"Uploading style for {distribution.distribution_id} to {key}"
            )
            if not options["dry_run"]:
                with open(f"./distribution/styles/{style_file_name}") as f:
                    style_obj = json.load(f)
                    self.do_upload(style_obj, key)

            nr_objs += 1
        return nr_objs

    # ##########################################################################
    def style_key(self, distribution: Distribution) -> str:
        """Build the default S3 key for a distribution's style file."""
        # Key format: api/oas/v0/{distribution_id}/{distribution_id}.style.json
        # FIX: We should use distribution identifiers without colons in the URL
        # once this has been changed, we can remove the replace() call
        return f"{OAS_PREFIX}/styles/{distribution.distribution_id}.style.json".replace(":", ".")

    # ##########################################################################
    def do_upload(self, snippet: dict[str, Any], key: str) -> None:
        """Helper function to upload a dict snippet to S3.

        Args:
            snippet: A dict structure representing an json object that should be uploaded to S3.
            key: The S3 object key to use for the uploaded object.
        """
        self.s3_client.put_object(
            Bucket=self.oastyles_s3_bucket,
            Key=key,
            Body=json.dumps(snippet, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        self.print(f"   ✔ Uploaded {key}")

    # ##########################################################################
    def do_clean(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success(
            f"Cleaning bucket: {self.oastyles_s3_bucket}. "
            "(delete files in batches of {options['batch_size']} files)..."
        )

        nr_objs = 0

        kwargs = {"Bucket": self.oastyles_s3_bucket, "MaxKeys": options["batch_size"]}
        result = self.s3_client.list_objects_v2(**kwargs)
        objs = result.get("Contents", [])
        while objs:
            nr_objs += len(objs)
            self.print(f"Found {len(objs)} more objects to delete in {self.oastyles_s3_bucket}...")
            keys = [{"Key": obj["Key"]} for obj in objs]
            self.print(
                f"{'[DRY RUN]: ' if options['dry_run'] else ''}"
                f"Deleting {len(keys)} objects from {self.oastyles_s3_bucket}..."
            )
            for key in keys:
                self.print(f" - {'[DRY RUN]:' if options['dry_run'] else ''} {key['Key']}")
            if not options["dry_run"]:
                self.s3_client.delete_objects(
                    Bucket=self.oastyles_s3_bucket, Delete={"Objects": keys}
                )
            if "NextContinuationToken" in result:
                result = self.s3_client.list_objects_v2(
                    ContinuationToken=result.get("NextContinuationToken"), **kwargs
                )
                objs = result.get("Contents", [])
            else:
                break
        self.print_success(f"Deleted total of {nr_objs} objects from {self.oastyles_s3_bucket}.")
