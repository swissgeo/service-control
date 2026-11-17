import re
import secrets
import string
import unicodedata

ALPHABET = string.ascii_lowercase + string.digits  # [a-z0-9]
UMLAUTS = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def nanoid(size: int) -> str:
    """Generate a NanoID-style random string from the given alphabet."""
    return "".join(secrets.choice(ALPHABET) for _ in range(size))


def normalize(value: str) -> str:
    """Convert a string into a lowercase, ASCII-only slug.

    Applies ``UMLAUTS`` replacements first (``ü`` -> ``ue``), then strips
    remaining accents via NFKD, and collapses everything outside ``[a-z0-9]``
    into single hyphens. Returns an empty string if nothing usable remains.
    """

    value = value.lower()
    for k, v in UMLAUTS.items():
        value = value.replace(k, v)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def dataset_sgid_from_dataset_id(dataset_id: str, data_source: str) -> str:
    """Creates the dataset sgid from a dataset ID.

    Removes the organization prefix, but appends organizations postfixes for
    - geodienste.ch broker datasets ("kgk")
    - geodienste.ch waldreservate dataset ("kgk")
    - geodienste.ch part datasets ("<canton>")

    Normalizes the rest of the name.
    """

    provider = None
    if data_source == "geodienste":
        if dataset_id.startswith("ch.geodienste-"):
            provider = dataset_id[len("ch.geodienste-") :].split(".")[0]  # noqa: PLC0207
        elif not dataset_id.startswith("ch.kgk") or "waldreservate" in dataset_id:
            provider = "kgk"

    parts = dataset_id.split(".")
    body = ".".join(parts[2:]) if len(parts) > 2 else dataset_id  # noqa: PLR2004
    body = normalize(body)
    return f"dat_{body}-{provider}" if provider else f"dat_{body}"


def distribution_sgid_from_dataset_sgid(dataset_sgid: str) -> str:
    """Creates the distribution sgid from a dataset sgid."""
    dataset_body = dataset_sgid.replace("dat_", "")
    return f"dst_{dataset_body}-{nanoid(5)}"


def organization_sgid_from_abbreviation(abbreviation_de: str, cantonal_org: bool = False) -> str:
    """Creates an organization sgid from a German organization abbreviation.

    Handle cantonal organizations specials, as the represent a Departement but currently use the
    abbreviations of the canton.
    """
    if cantonal_org:
        return f"org_geodienste-{normalize(abbreviation_de)}"
    return f"org_{normalize(abbreviation_de)}"
