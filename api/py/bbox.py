from __future__ import annotations

import os

from fastapi import HTTPException

# ~55 km at Brisbane latitudes — map UI unloads pins below zoom ~12.8 anyway.
MAX_BBOX_SPAN_DEG = float(os.environ.get("MAX_BBOX_SPAN_DEG", "0.5"))


def validate_bbox(
    west: float | None,
    south: float | None,
    east: float | None,
    north: float | None,
    *,
    max_span_deg: float | None = None,
) -> tuple[float, float, float, float]:
    span = MAX_BBOX_SPAN_DEG if max_span_deg is None else max_span_deg
    if any(v is None for v in (west, south, east, north)):
        raise HTTPException(
            status_code=400,
            detail="west, south, east, and north are required",
        )
    assert west is not None and south is not None and east is not None and north is not None
    if not (west < east and south < north):
        raise HTTPException(status_code=400, detail="invalid bbox order")
    if (east - west) > span or (north - south) > span:
        raise HTTPException(status_code=400, detail="bbox too large")
    return west, south, east, north
