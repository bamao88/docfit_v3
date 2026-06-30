"""Module 1 live responder：用真实 OpenAI 兼容模型（Kimi）产出三阶段观察。

每阶段一次 ``response_format=json_object`` 完成调用——不挂 tools，绕开 tools 与
json_object 冲突（历史 blocker B3）。送进模型的只有 clean evidence + rubric +
允许标签集；evidence 已在 build_*_evidence / build_observation_prompt 两道防火墙过。

凭证从环境读取（``KIMI_API_KEY`` 等），绝不写死。本模块只产出**真实模型**结果；
原始响应可选记录到 ``record`` 供事后审计 / 复跑，但那是回归护栏，不是产品口径。
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from docfit.core.io import sha256_json

from .observation_prompts import (
    ALLOWED_LABELS,
    OUTPUT_CONTRACT,
    build_observation_prompt,
)
from .transport import strip_think

KIMI_DEFAULT_BASE_URL = "https://api.kimi.com/coding/v1"
KIMI_DEFAULT_MODEL = "kimi-for-coding"
KIMI_DEFAULT_HEADERS = {
    "User-Agent": "claude-cli/2.0.0 (external, darwin)",
    "X-Client-Type": "claude-code",
}


class LiveObservationError(RuntimeError):
    pass


def build_kimi_client(*, timeout: int = 300) -> tuple[Any, str]:
    """从环境构造 Kimi OpenAI 兼容 client，返回 (client, model)。"""

    api_key = os.environ.get("KIMI_API_KEY")
    if not api_key:
        raise LiveObservationError("KIMI_API_KEY is required for live observation")
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise LiveObservationError("openai package is required for live observation") from exc

    base_url = os.environ.get("KIMI_BASE_URL") or KIMI_DEFAULT_BASE_URL
    model = os.environ.get("KIMI_MODEL") or KIMI_DEFAULT_MODEL
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        default_headers=KIMI_DEFAULT_HEADERS,
    )
    return client, model


class LiveResponder:
    """真实模型驱动的三阶段 responder。"""

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        temperature: float = 0.4,
        max_tokens: int = 8000,
        max_tokens_cap: int = 32000,
        record: list[dict[str, Any]] | None = None,
        progress: bool = True,
        max_attempts: int = 3,
        retry_backoff: float = 5.0,
        cache_dir: Path | None = None,
        refresh: bool = False,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._max_tokens_cap = max(max_tokens, max_tokens_cap)
        self._record = record
        self._progress = progress
        self._max_attempts = max(1, max_attempts)
        self._retry_backoff = retry_backoff
        self._cache_dir = cache_dir
        self._refresh = refresh
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_units(self, *, evidence: dict[str, Any], n_samples: int) -> list[dict[str, Any]]:
        # 自一致性：温度>0 下重复采样 N 次，交给上层投票。
        return [self._complete("t2", evidence, sample_index=i) for i in range(max(1, n_samples))]

    def fetch_elements(self, *, evidence: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]:
        return self._complete("t3", evidence, label=str(window.get("window_id") or "t3"))

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
        prompt = build_observation_prompt(stage=stage, evidence_view=evidence)  # firewall asserted
        system = (
            "你是 DocFit 模板结构观察器。只依据给定的 Word 事实独立判断，"
            "看不到也不要假设任何代码已有结论。\n"
            f"任务：{prompt['rubric']}\n"
            f"允许标签集：{json.dumps(ALLOWED_LABELS, ensure_ascii=False)}\n"
            f"输出契约：{OUTPUT_CONTRACT[stage]}\n"
            "弃权是合法输出：没有证据支撑就少认领、留 unknown。"
        )
        user = json.dumps(prompt["evidence"], ensure_ascii=False)
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
                "sample_index": sample_index,
            }
        )
        cached = self._cache_load(cache_key)
        if cached is not None:
            payload = cached
            if self._progress:
                n = len(payload.get("items", payload.get("section_profiles", [])) or [])
                print(f"  [ cache] {tag:28s} raw={n}", file=sys.stderr, flush=True)
            if self._record is not None:
                self._record.append(
                    {"stage": stage, "label": label, "sample_index": sample_index,
                     "from_cache": True, "payload": payload, "error": None}
                )
            return payload

        # 单次调用的网络/超时/限流/截断都不该拖垮整条流水线：重试若干次，
        # 仍失败就降级为该阶段弃权（空 payload）——物化闸门会把它落成
        # schema-valid 的全 unknown 产物。失败信息进 record。
        content = ""
        finish_reason: str | None = None
        error: str | None = None
        attempt_tokens = self._max_tokens
        for attempt in range(1, self._max_attempts + 1):
            try:
                completion = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=self._temperature,
                    max_tokens=attempt_tokens,
                    response_format={"type": "json_object"},
                )
                choice = completion.choices[0]
                finish_reason = choice.finish_reason
                content = strip_think(choice.message.content or "")
                error = None
                # 截断（大表单 JSON 超出预算）→ 加倍预算重试，挽回被砍掉的元素。
                if finish_reason == "length" and attempt < self._max_attempts:
                    attempt_tokens = min(attempt_tokens * 2, self._max_tokens_cap)
                    error = f"truncated (finish=length); escalating max_tokens to {attempt_tokens}"
                    continue
                break
            except Exception as exc:  # APITimeout/Connection/RateLimit/APIError 等
                error = f"{type(exc).__name__}: {exc}"
                if attempt < self._max_attempts:
                    time.sleep(self._retry_backoff * attempt)

        if error is not None:
            payload: dict[str, Any] = {"items": []} if stage in {"t2", "t3"} else {"section_profiles": []}
        else:
            try:
                payload = _parse_json_object(content, stage=stage)
            except LiveObservationError as exc:
                error = str(exc)
                payload = {"items": []} if stage in {"t2", "t3"} else {"section_profiles": []}
        if finish_reason == "length" and not content.strip():
            error = error or "model hit max_tokens before emitting content (reasoning budget exhausted)"
        # 只缓存成功结果；失败/降级不写缓存，下次还会真打。
        if error is None:
            self._cache_store(cache_key, payload)
        if self._progress:
            n = len(payload.get("items", payload.get("section_profiles", [])) or [])
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
                    "finish_reason": finish_reason,
                    "raw_content": content,
                    "payload": payload,
                    "error": error,
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
        return {"items": []} if stage in {"t2", "t3"} else {"section_profiles": []}
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LiveObservationError(
            f"{stage} live response was not valid JSON after <think> cleanup: {content[:200]}"
        ) from exc
    if not isinstance(decoded, dict):
        raise LiveObservationError(f"{stage} live response JSON must be an object")
    return decoded
