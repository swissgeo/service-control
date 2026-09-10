from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PaintConfig(BaseModel):
    raster_gutter: int | None = Field(default=None, ge=0, le=1000)
    raster_opacity: float | None = Field(default=1.0, ge=0.0, le=1.0)

    # We forbid to add extra fields since we want to have control over the fields
    model_config = ConfigDict(extra="forbid")


class MaplibreStyle(BaseModel):
    layers: list[MaplibreLayer] = []


class MaplibreLayer(BaseModel):
    id: str
    source: str
    type: str | None = None
    paint: PaintConfig = PaintConfig()


class MaplibreRasterLayer(MaplibreLayer):
    type: Literal["raster"]
