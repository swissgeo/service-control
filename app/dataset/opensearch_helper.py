"""Shared OpenSearch connection helpers for the management commands.

The commands that talk to OpenSearch (`oar_opensearch_export`, `oar_opensearch_indexes`) all
need the same connection options and the same authenticated client, so both live here rather
than in any one command module.
"""

import logging
import os
import time
from typing import Any

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from django.core.management.base import CommandError, CommandParser

from utils.command import CustomBaseCommand

LOGGER = logging.getLogger(__name__)


def add_connection_arguments(parser: CommandParser) -> None:
    """Add the OpenSearch connection flags consumed by `build_client`."""
    parser.add_argument(
        "--opensearch-url",
        type=str,
        default=os.environ.get("OPENSEARCH_URL", "http://localhost:9200"),
        help="OpenSearch endpoint URL (default: $OPENSEARCH_URL or http://localhost:9200)",
    )
    parser.add_argument(
        "--aws-auth",
        dest="aws_auth",
        action="store_true",
        default=None,
        help="Force AWS SigV4 authentication (default: enabled automatically for https URLs)",
    )
    parser.add_argument(
        "--no-aws-auth",
        dest="aws_auth",
        action="store_false",
        help="Disable AWS SigV4 authentication",
    )


def wait_for_credentials() -> None:  # pragma: no cover
    """Wait for AWS credentials to become available.

    IMDS credential fetches can fail transiently on startup due to network errors.
    """
    retries = 3
    delay = 2.0
    for attempt in range(1, retries + 1):
        creds = boto3.Session().get_credentials()
        if creds is not None and creds.get_frozen_credentials().access_key:
            return
        if attempt == retries:
            raise RuntimeError(f"AWS credentials unavailable after {retries} attempts")
        LOGGER.warning(
            "AWS credentials not ready (attempt %d/%d), retrying in %.1fs",
            attempt,
            retries,
            delay,
        )
        time.sleep(delay)


def build_client(command: CustomBaseCommand, options: dict) -> Any:  # pragma: no cover
    """Build and ping an OpenSearch client, optionally using AWS SigV4 auth.

    `command` is only used to report the connection on success.
    """
    url = options["opensearch_url"]
    aws_auth = options["aws_auth"]
    use_aws = aws_auth if aws_auth is not None else url.startswith("https")

    if use_aws:
        wait_for_credentials()  # ensures credentials are available below
        region = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
        credentials = boto3.Session().get_credentials().get_frozen_credentials()  # ty:ignore[unresolved-attribute]
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            "es",
            session_token=credentials.token,
        )
        client = OpenSearch(
            url,
            http_auth=auth,
            use_ssl=url.startswith("https"),
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )
    else:
        client = OpenSearch(url, verify_certs=False)

    if not client.ping():
        raise CommandError(f"Cannot connect to OpenSearch at {url}")
    command.print_success(f"Connected to OpenSearch at {url}")
    return client
