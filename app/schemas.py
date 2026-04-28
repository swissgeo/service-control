from typing import TYPE_CHECKING, Any, TypedDict

from ninja import Schema

if TYPE_CHECKING:
    from django.http import HttpRequest


SUPPORTED_LANGS = ("de", "en", "fr", "it", "rm")


class TranslationsSchema(Schema):
    de: str
    fr: str
    en: str
    it: str | None = None
    rm: str | None = None


def build_translations(obj: Any, field_prefix: str) -> dict[str, str]:
    return {lang: getattr(obj, f"{field_prefix}_{lang}") for lang in SUPPORTED_LANGS}


class ResolverContext(TypedDict):
    request: HttpRequest
