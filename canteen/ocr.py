from __future__ import annotations

from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

from canteen import config


def _make_client() -> ImageAnalysisClient:
    return ImageAnalysisClient(
        endpoint=config.get("VISION_ENDPOINT"),
        credential=AzureKeyCredential(config.get("VISION_KEY")),
    )


def extract_text(image_url: str) -> str:
    """Run OCR on an image URL and return the extracted text in lowercase."""
    client = _make_client()
    result = client.analyze_from_url(
        image_url=image_url,
        visual_features=[VisualFeatures.READ],
    )

    lines: list[str] = []
    if result.read is not None and result.read.blocks:
        for line in result.read.blocks[0].lines:
            lines.append(line.text)

    return " ".join(lines).lower()


def extract_lines_with_coords(image_url: str) -> list[dict]:
    """Run OCR on an image URL and return each line with its bounding-box centre.

    Returns a list of dicts:
        {"text": str, "x": float, "y": float}
    where x/y are the centre pixel coordinates of the line's bounding polygon.
    Original casing is preserved.
    """
    client = _make_client()
    result = client.analyze_from_url(
        image_url=image_url,
        visual_features=[VisualFeatures.READ],
    )

    lines: list[dict] = []
    if result.read is None or not result.read.blocks:
        return lines

    for block in result.read.blocks:
        for line in block.lines:
            polygon = line.bounding_polygon  # list of {x, y} points
            if not polygon:
                continue
            xs = [pt["x"] for pt in polygon]
            ys = [pt["y"] for pt in polygon]
            cx = (min(xs) + max(xs)) / 2
            cy = (min(ys) + max(ys)) / 2
            lines.append({"text": line.text, "x": cx, "y": cy})

    return lines
