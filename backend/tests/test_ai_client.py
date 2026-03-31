from __future__ import annotations

import asyncio
import time
import unittest
from typing import Any

from app.infra.ai_client import AIClient, ProviderConfig, ProviderRateLimitError
from app.infrastructure.config import Settings


class RecordingAIClient(AIClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.calls: list[dict[str, Any]] = []
        self._responses: list[Any] = []

    def queue_response(self, value: Any) -> None:
        self._responses.append(value)

    async def _request_marketplace_text(
        self,
        *,
        provider_config: ProviderConfig,
        model: str,
        system_prompt: str,
        user_input: str,
        stream: bool,
        user_content: str | list[dict[str, Any]] | None,
    ) -> str:
        self.calls.append(
            {
                "slot": provider_config.slot,
                "provider_name": provider_config.provider_name,
                "api_key": provider_config.api_key,
                "base_url": provider_config.base_url,
                "timeout_sec": provider_config.timeout_sec,
                "model": model,
                "user_input": user_input,
                "user_content": user_content,
            }
        )
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return str(response)


def build_settings() -> Settings:
    return Settings(
        openai_compatible_api_key="default-key",
        openai_compatible_base_url="https://legacy.example/v1",
        openai_compatible_timeout_sec=11,
        phase8_judge_api_key="judge-key",
        phase8_judge_api_base_url="https://chiasegpu.vn/api/v1",
        phase8_judge_api_timeout_sec=25,
        phase8_judge_api_retry_count=2,
        phase8_ocr_api_key="ocr-key",
        phase8_ocr_api_base_url="https://chiasegpu.vn/api/v1",
        phase8_ocr_api_timeout_sec=40,
        phase8_ocr_api_retry_count=2,
        ai_rate_limit_cooldown_sec=1,
        anthropic_api_key="",
    )


class AIClientSlotRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_judge_slot_uses_phase8_judge_provider(self) -> None:
        client = RecordingAIClient(build_settings())
        client.queue_response('{"decision":"ACCEPTED","relevance_score":0.8,"confidence_score":0.9}')

        response = await client.call(
            model="gpt-4o",
            system_prompt="CONTENT_VALIDITY_JUDGE",
            user_input='{"hello":"world"}',
            provider_slot="judge",
        )

        self.assertEqual(response["_provider_meta"]["provider_used"], "chiasegpu-judge")
        self.assertEqual(response["_provider_meta"]["provider_slot"], "judge")
        self.assertEqual(client.calls[0]["api_key"], "judge-key")
        self.assertEqual(client.calls[0]["base_url"], "https://chiasegpu.vn/api/v1")

    async def test_ocr_slot_passes_multimodal_user_content(self) -> None:
        client = RecordingAIClient(build_settings())
        client.queue_response('{"image_summary":"ok","ocr_text":"scan","signals":["ocr"]}')
        content = [
            {"type": "text", "text": '{"foo":"bar"}'},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
        ]

        await client.call(
            model="gpt-4o-mini",
            system_prompt="IMAGE_UNDERSTANDING",
            user_input="fallback-text",
            provider_slot="ocr",
            user_content=content,
        )

        self.assertEqual(client.calls[0]["slot"], "ocr")
        self.assertEqual(client.calls[0]["api_key"], "ocr-key")
        self.assertEqual(client.calls[0]["timeout_sec"], 40)
        self.assertEqual(client.calls[0]["user_content"], content)

    async def test_rate_limit_retries_after_hold_window(self) -> None:
        client = RecordingAIClient(build_settings())
        client.queue_response(ProviderRateLimitError("rate-limited", retry_after_sec=0.02))
        client.queue_response('{"decision":"ACCEPTED","relevance_score":0.8,"confidence_score":0.9}')

        started = time.perf_counter()
        response = await client.call(
            model="gpt-4o-mini",
            system_prompt="CONTENT_VALIDITY_JUDGE",
            user_input='{"hello":"world"}',
            provider_slot="judge",
        )
        elapsed = time.perf_counter() - started

        self.assertEqual(response["_provider_meta"]["attempt_count"], 2)
        self.assertGreaterEqual(len(client.calls), 2)
        self.assertGreaterEqual(elapsed, 0.018)


if __name__ == "__main__":
    unittest.main()
