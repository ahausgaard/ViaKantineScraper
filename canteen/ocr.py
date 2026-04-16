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

