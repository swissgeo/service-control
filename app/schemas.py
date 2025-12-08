from typing import Optional

from ninja import Schema


class TranslationsSchema(Schema):
    de: str
    fr: str
    en: str
    it: Optional[str] = None
    rm: Optional[str] = None
