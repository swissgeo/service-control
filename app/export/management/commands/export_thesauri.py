from json import dumps
from typing import Any

import environ
from boto3 import Session
from botocore.client import Config

from django.conf import settings
from django.core.management.base import CommandParser

from export.export_models import LANGS, Thesaurus
from thesaurus.models import ECH0166_THESAURUS_ID
from thesaurus.models import Thesaurus as ThesaurusModel
from thesaurus.utils import thesaurus_to_skos_jsonld
from utils.command import CustomBaseCommand

env = environ.Env()

# The prefix of the S3 key, e.g. api/oas/v0/styles
KEY_PREFIX = settings.THESAURI_PATH_PREFIX.strip("/")


class Command(CustomBaseCommand):
    """Export thesauri to static s3 bucket."""

    help = "static thesauri management"

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
            choices=["dev", "int", "prod", "local"],
            default="dev",
            help="Specify the target environment",
        )

        clean = sub.add_parser("clean", help="Delete static files from S3 buckets")
        clean.add_argument(
            "--batch-size", type=int, default=1000, help="Number of files to delete per batch"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Main entry point of command."""
        profile = options.get("profile")
        if profile and profile != "default":
            self.session = Session(profile_name=profile)  # pylint: disable=attribute-defined-outside-init
        else:
            self.session = Session()  # pylint: disable=attribute-defined-outside-init

        # S3 client configuration
        client_access_kwargs = {
            "region_name": "eu-central-1",
            "config": Config(signature_version="s3v4"),
        }
        if options["target_env"] == "local":
            client_access_kwargs["region_name"] = env.str("AWS_DEFAULT_REGION")
            client_access_kwargs["endpoint_url"] = "http://localhost:5000"
        self.s3_client = self.session.client("s3", **client_access_kwargs)  # ty: ignore[no-matching-overload]

        # derive bucket name from target environment
        self.bucket = f"static-thesauri-{options['target_env']}-swissgeo"

        # Show parsed arguments (useful for debugging)
        if options.get("verbosity", 0) >= 2:  # noqa: PLR2004
            self.print(f"Debug: parsed args = {dumps(options, default=str)}")

        if options["command"] == "clean":
            self.do_clean(*args, **options)
        else:
            self.do_export(*args, **options)

    # ##########################################################################
    def do_export(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        self.print_success(f"Exporting thesauri to {self.bucket}...")

        nr_objs = 0
        for thesaurus in ThesaurusModel.objects.filter(thesaurus_id=ECH0166_THESAURUS_ID).all():
            # Simple JSON
            for lang in LANGS:
                key = f"{KEY_PREFIX}/{thesaurus.thesaurus_id}.{lang}.json"
                dump = Thesaurus.from_thesaurus(thesaurus, lang=lang).model_dump(
                    exclude_none=True, by_alias=True
                )
                self.print(
                    f" - {'[DRY RUN]: ' if options['dry_run'] else ''}"
                    f"Uploading {thesaurus} to {key}"
                )
                if not options["dry_run"]:
                    self.do_upload(dumps(dump, ensure_ascii=False), key)
                else:
                    self.print(dumps(dump, ensure_ascii=False, indent=2))
                nr_objs += 1

            # SKOS JSON-LD
            key = f"{KEY_PREFIX}/{thesaurus.thesaurus_id}.json"
            content = thesaurus_to_skos_jsonld(thesaurus=thesaurus)
            self.print(
                f" - {'[DRY RUN]: ' if options['dry_run'] else ''}Uploading {thesaurus} to {key}"
            )
            if not options["dry_run"]:
                self.do_upload(content, key)
            else:
                self.print(content)
            nr_objs += 1

        self.print_success(f"Exported {nr_objs} objects to {self.bucket}.")

    # ##########################################################################
    def do_upload(self, content: str, key: str) -> None:
        """Helper function to upload a dict snippet to S3.

        Args:
            snippet: A dict structure representing an json object that should be uploaded to S3.
            key: The S3 object key to use for the uploaded object.
        """
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="application/json",
        )
        self.print(f"   ✔ Uploaded {key}")

    # ##########################################################################
    def do_clean(self, *args: Any, **options: Any) -> None:  # noqa: ARG002

        self.print_success(
            f"Cleaning bucket: {self.bucket}. "
            "(delete files in batches of {options['batch_size']} files)..."
        )

        nr_objs = 0

        kwargs = {"Bucket": self.bucket, "MaxKeys": options["batch_size"]}
        result = self.s3_client.list_objects_v2(**kwargs)
        objs = result.get("Contents", [])
        while objs:
            nr_objs += len(objs)
            self.print(f"Found {len(objs)} more objects to delete in {self.bucket}...")
            keys = [{"Key": obj["Key"]} for obj in objs]
            self.print(
                f"{'[DRY RUN]: ' if options['dry_run'] else ''}"
                f"Deleting {len(keys)} objects from {self.bucket}..."
            )
            for key in keys:
                self.print(f" - {'[DRY RUN]:' if options['dry_run'] else ''} {key['Key']}")
            if not options["dry_run"]:
                self.s3_client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys})
            if "NextContinuationToken" in result:
                result = self.s3_client.list_objects_v2(
                    ContinuationToken=result.get("NextContinuationToken"), **kwargs
                )
                objs = result.get("Contents", [])
            else:
                break
        self.print_success(f"Deleted total of {nr_objs} objects from {self.bucket}.")
