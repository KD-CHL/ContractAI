from __future__ import annotations

from types import SimpleNamespace

import pytest

from contract_guard.services.vision import OpenAIVisionOCR


class _FakeResponses:
    def __init__(self) -> None:
        self.request: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.request = kwargs
        return SimpleNamespace(output_text="第一条 服务内容")


@pytest.mark.asyncio
async def test_openai_vision_ocr_uses_image_input_without_leaking_binary() -> None:
    responses = _FakeResponses()
    client = SimpleNamespace(responses=responses)
    ocr = OpenAIVisionOCR(model="test-model", client=client)

    result = await ocr.extract_text(
        b"not-a-real-image", media_type="image/png", filename="contract.png"
    )

    assert result == "第一条 服务内容"
    assert responses.request is not None
    assert responses.request["model"] == "test-model"
    image_part = responses.request["input"][0]["content"][1]  # type: ignore[index]
    assert image_part["type"] == "input_image"
    assert str(image_part["image_url"]).startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_openai_vision_ocr_rejects_oversized_input_before_api_call() -> None:
    responses = _FakeResponses()
    ocr = OpenAIVisionOCR(client=SimpleNamespace(responses=responses), max_image_bytes=2)

    with pytest.raises(ValueError, match="OCR limit"):
        await ocr.extract_text(b"abc", media_type="image/png")

    assert responses.request is None


@pytest.mark.asyncio
async def test_openai_vision_ocr_rejects_unsupported_media_type() -> None:
    responses = _FakeResponses()
    ocr = OpenAIVisionOCR(client=SimpleNamespace(responses=responses))

    with pytest.raises(ValueError, match="supports PNG"):
        await ocr.extract_text(b"bitmap", media_type="image/bmp")

    assert responses.request is None
