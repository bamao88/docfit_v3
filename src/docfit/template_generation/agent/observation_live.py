"""Module 1 live responder：用真实 OpenAI 兼容模型（Kimi）产出三阶段观察。

每阶段一次 ``response_format=json_object`` 完成调用——不挂 tools，绕开 tools 与
json_object 冲突（历史 blocker B3）。送进模型的只有 clean evidence + rubric +
允许标签集；evidence 已在 build_*_evidence / build_observation_prompt 两道防火墙过。

凭证从环境读取（``KIMI_API_KEY`` 等），绝不写死。本模块只产出**真实模型**结果；
原始响应可选记录到 ``record`` 供事后审计 / 复跑，但那是回归护栏，不是产品口径。
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from docfit.core.io import sha256_json

from .api_config import (
    LiveProviderConfig,
    LiveProviderConfigError,
    LiveProviderUsageLimitState,
    is_provider_usage_limit_error,
    resolve_live_provider_config,
)
from .observation_prompts import (
    ObservationPromptTemplates,
    assemble_observation_messages,
)
from .observation_multimodal import attachment_refs, openai_user_content


class LiveObservationError(RuntimeError):
    pass


def strip_think(content: str) -> str:
    return re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL | re.I).strip()


def build_openai_chat_client(
    provider_config: LiveProviderConfig,
    *,
    timeout: int = 300,
) -> tuple[Any, str]:
    """从统一 provider config 构造 OpenAI chat-compatible client。"""

    if provider_config.endpoint_family != "openai_chat":
        raise LiveObservationError(
            f"{provider_config.provider} does not expose an OpenAI chat endpoint"
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise LiveObservationError("openai package is required for live observation") from exc

    client = OpenAI(
        api_key=provider_config.api_key,
        base_url=provider_config.base_url,
        timeout=timeout,
        default_headers=dict(provider_config.default_headers),
    )
    return client, provider_config.model


def build_kimi_client(*, timeout: int = 300) -> tuple[Any, str]:
    """Compatibility helper: build the default Kimi text client from env."""

    try:
        provider_config = resolve_live_provider_config(
            role="text",
            provider="kimi",
        )
    except LiveProviderConfigError as exc:
        raise LiveObservationError(str(exc)) from exc
    return build_openai_chat_client(provider_config, timeout=timeout)


class LiveResponder:
    """真实模型驱动的三阶段 responder。"""

    supports_action_refinement = True

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        temperature: float = 0.4,
        max_tokens: int = 8000,
        max_tokens_cap: int = 32000,
        thinking: bool = False,
        record: list[dict[str, Any]] | None = None,
        progress: bool = True,
        max_attempts: int = 3,
        retry_backoff: float = 5.0,
        cache_dir: Path | None = None,
        refresh: bool = False,
        prompt_templates: ObservationPromptTemplates | None = None,
        record_metadata: dict[str, Any] | None = None,
        usage_limit_state: LiveProviderUsageLimitState | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._thinking = thinking
        # Kimi 端点的耦合约束：thinking 关 → 只允许 temperature=0.6；thinking 开（默认，
        # 不传 thinking 参数）→ temperature 自由。关 thinking 时强制 0.6。
        self._temperature = temperature if thinking else 0.6
        self._extra_body: dict[str, Any] = {} if thinking else {"thinking": {"type": "disabled"}}
        self._max_tokens = max_tokens
        self._max_tokens_cap = max(max_tokens, max_tokens_cap)
        self._record = record
        self._progress = progress
        self._max_attempts = max(1, max_attempts)
        self._retry_backoff = retry_backoff
        self._cache_dir = cache_dir
        self._refresh = refresh
        self._prompt_templates = prompt_templates
        self._record_metadata = dict(record_metadata or {})
        self._usage_limit_state = usage_limit_state or LiveProviderUsageLimitState()
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_units(self, *, evidence: dict[str, Any], n_samples: int) -> list[dict[str, Any]]:
        # 自一致性：温度>0 下重复采样 N 次，交给上层投票。
        return [self._complete("t2", evidence, sample_index=i) for i in range(max(1, n_samples))]

    def fetch_t3_decision(
        self,
        *,
        evidence: dict[str, Any],
        node: dict[str, Any],
        unit_id: str,
    ) -> dict[str, Any]:
        del unit_id
        return self._complete(
            "t3_hierarchy",
            evidence,
            label=str(node.get("ref") or "t3_hierarchy"),
        )

    def fetch_layout(self, *, evidence: dict[str, Any]) -> dict[str, Any]:
        return self._complete("t4", evidence)

    def _complete(
        self,
        stage: str,
        evidence: dict[str, Any],
        *,
        sample_index: int = 0,
        label: str | None = None,
    ) -> dict[str, Any]:
        system, user = assemble_observation_messages(
            stage,
            evidence,
            prompt_templates=self._prompt_templates,
        )
        user_content = openai_user_content(user, evidence)
        tag = f"{stage}:{label or sample_index}"
        started = time.monotonic()

        # 缓存键覆盖一切影响输出的东西：prompt 文本 + 模型 + 温度 + 采样序号。
        # 改了 prompt（rubric/contract）键就变 → 自动失效；没改就命中、跳过真实调用。
        cache_key = sha256_json(
            {
                "system": system,
                "user": user,
                "model": self._model,
                "temperature": self._temperature,
                "thinking": self._thinking,
                "max_tokens": self._max_tokens,
                "max_tokens_cap": self._max_tokens_cap,
                "sample_index": sample_index,
                "visual_refs": attachment_refs(evidence),
            }
        )
        cached = self._cache_load(cache_key)
        if cached is not None:
            payload = cached
            if self._progress:
                n = len(payload.get("units", payload.get("items", payload.get("section_profiles", []))) or [])
                print(f"  [ cache] {tag:28s} raw={n}", file=sys.stderr, flush=True)
            if self._record is not None:
                self._record.append(
                    {
                        "stage": stage,
                        "label": label,
                        "sample_index": sample_index,
                        "from_cache": True,
                        "provider": "kimi",
                        "model": self._model,
                        "payload": payload,
                        "error": None,
                        **self._record_metadata,
                    }
                )
            return payload

        # 单次调用的网络/超时/限流/截断都不该拖垮整条流水线：重试若干次，
        # 仍失败就降级为该阶段弃权（空 payload）——物化闸门会把它落成
        # schema-valid 的全 unknown 产物。失败信息进 record。
        content = ""
        finish_reason: str | None = None
        error: str | None = None
        attempt_tokens = self._max_tokens
        skipped_due_usage_limit = self._usage_limit_state.is_exhausted("kimi")
        if skipped_due_usage_limit:
            error = "kimi usage limit already exhausted"
        else:
            for attempt in range(1, self._max_attempts + 1):
                try:
                    completion = self._client.chat.completions.create(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_content},
                        ],
                        temperature=self._temperature,
                        max_tokens=attempt_tokens,
                        response_format={"type": "json_object"},
                        extra_body=self._extra_body,
                    )
                    choice = completion.choices[0]
                    finish_reason = choice.finish_reason
                    content = strip_think(choice.message.content or "")
                    error = None
                    # 截断（大表单 JSON 超出预算）→ 加倍预算重试，挽回被砍掉的元素。
                    if finish_reason == "length" and attempt < self._max_attempts:
                        attempt_tokens = min(attempt_tokens * 2, self._max_tokens_cap)
                        error = (
                            "truncated (finish=length); escalating max_tokens "
                            f"to {attempt_tokens}"
                        )
                        continue
                    break
                except Exception as exc:  # APITimeout/Connection/RateLimit/APIError 等
                    error = f"{type(exc).__name__}: {exc}"
                    if is_provider_usage_limit_error(exc):
                        self._usage_limit_state.mark_exhausted("kimi")
                        break
                    if attempt < self._max_attempts:
                        time.sleep(self._retry_backoff * attempt)

        if error is not None:
            payload: dict[str, Any] = (
                {"units": []}
                if stage == "t2"
                else ({} if stage == "t3_hierarchy" else {"section_profiles": []})
            )
        else:
            try:
                payload = _parse_json_object(content, stage=stage)
            except LiveObservationError as exc:
                error = str(exc)
                payload = (
                    {"units": []}
                    if stage == "t2"
                    else ({} if stage == "t3_hierarchy" else {"section_profiles": []})
                )
        if finish_reason == "length" and not content.strip():
            error = error or "model hit max_tokens before emitting content (reasoning budget exhausted)"
        if error is not None:
            payload["_observation_error"] = error
        # 只缓存成功结果；失败/降级不写缓存，下次还会真打。
        if error is None:
            self._cache_store(cache_key, payload)
        if self._progress:
            n = len(payload.get("units", payload.get("items", payload.get("section_profiles", []))) or [])
            flag = f" ERROR={error}" if error else ""
            print(
                f"  [{time.monotonic() - started:5.1f}s] {tag:28s} finish={finish_reason} raw={n}{flag}",
                file=sys.stderr,
                flush=True,
            )
        if self._record is not None:
            self._record.append(
                {
                    "stage": stage,
                    "label": label,
                    "sample_index": sample_index,
                    "provider": "kimi",
                    "model": self._model,
                    "finish_reason": finish_reason,
                    "raw_content": content,
                    "payload": payload,
                    "error": error,
                    "skipped_due_usage_limit": skipped_due_usage_limit,
                    **self._record_metadata,
                }
            )
        return payload

    def _cache_path(self, cache_key: str) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / f"{cache_key}.json"

    def _cache_load(self, cache_key: str) -> dict[str, Any] | None:
        if self._refresh:
            return None
        path = self._cache_path(cache_key)
        if path is None or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _cache_store(self, cache_key: str, payload: dict[str, Any]) -> None:
        path = self._cache_path(cache_key)
        if path is None:
            return
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_json_object(content: str, *, stage: str) -> dict[str, Any]:
    if not content.strip():
        # 空响应 → 该阶段弃权（物化闸门会把它落成 schema-valid 的全 unknown 产物）。
        if stage == "t2":
            return {"units": []}
        if stage == "t3_hierarchy":
            return {}
        return {"section_profiles": []}
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LiveObservationError(
            f"{stage} live response was not valid JSON after <think> cleanup: {content[:200]}"
        ) from exc
    if not isinstance(decoded, dict):
        raise LiveObservationError(f"{stage} live response JSON must be an object")
    return decoded
