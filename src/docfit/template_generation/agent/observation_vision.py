"""T4 视觉观察：MiniMax M3 读页图输出每页版式（Anthropic Messages 格式）。

M3 的视觉端点是 **Anthropic 兼容**（`/v1/messages` + `x-api-key`），不是 OpenAI 格式，
所以单独一个 responder，不复用 OpenAI 兼容 transport。逐页把渲染 PNG 发给 M3，
要一份每页版式 JSON（页眉/页脚/页码/是否独立页/单元线索）。

凭证从环境读取（``MINIMAX_API_KEY`` / ``MINIMAX_BASE_URL`` / ``MINIMAX_MODEL``），不写死。
单页失败/超时不拖垮整条：重试后降级为该页空观察。可选磁盘缓存（键含图 sha256）。
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx

from docfit.core.io import sha256_json

MINIMAX_DEFAULT_BASE_URL = "https://api.minimaxi.com/anthropic"
MINIMAX_DEFAULT_MODEL = "MiniMax-M3"
ANTHROPIC_VERSION = "2023-06-01"

PAGE_PROMPT = (
    "这是一份学位论文模板的第 {page_no} 页渲染图。只依据图里看到的，输出一个 JSON 对象："
    '{{"is_standalone_page": 该页是否只含一个逻辑单元(布尔),'
    '"unit_hint": "该页主要是什么单元(封面/版权/诚信声明/目录/摘要/正文/参考文献/致谢/附录/'
    '任务书/开题报告/开题论证记录表/答辩记录表/题目变更审批表/成绩评定表 等，不确定填 unknown)",'
    '"has_header": 有无页眉(布尔),"has_footer": 有无页脚(布尔),'
    '"page_number_visible": 能否看到页码(布尔),"page_number_text": "看到的页码文本，没有填空字符串",'
    '"visual_notes": "简要版式观察(居中/空行/字号/表格等)"}}。'
    "只输出 JSON，不要解释文字。看不清就把对应布尔设 false、字符串留空。"
)

_EMPTY_PAGE = {
    "is_standalone_page": None,
    "unit_hint": "unknown",
    "has_header": None,
    "has_footer": None,
    "page_number_visible": None,
    "page_number_text": "",
    "visual_notes": "",
}


class MinimaxVisionError(RuntimeError):
    pass


def post_anthropic_messages(
    *,
    base_url: str,
    api_key: str,
    model: str,
    content: Any,
    system: str | None = None,
    max_tokens: int,
    timeout: int = 90,
    temperature: float | None = None,
) -> str:
    """MiniMax(Anthropic Messages)统一调用 → 返回文本块拼接。content 可为字符串或多模态列表。"""

    body: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": content}],
    }
    if system:
        body["system"] = system
    if temperature is not None:
        body["temperature"] = temperature
    response = httpx.post(
        f"{base_url}/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json=body,
        timeout=timeout,
    )
    if response.status_code != 200:
        raise MinimaxVisionError(f"minimax {response.status_code}: {response.text[:200]}")
    data = response.json()
    return "".join(
        block.get("text", "")
        for block in data.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    )


def build_minimax_vision_config() -> tuple[str, str, str]:
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise MinimaxVisionError("MINIMAX_API_KEY is required for T4 vision observation")
    base_url = (os.environ.get("MINIMAX_BASE_URL") or MINIMAX_DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("MINIMAX_MODEL") or MINIMAX_DEFAULT_MODEL
    return api_key, base_url, model


class MinimaxVisionResponder:
    """逐页读图的 T4 视觉 responder。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int = 1200,
        timeout: int = 90,
        concurrency: int = 4,
        max_attempts: int = 3,
        retry_backoff: float = 4.0,
        cache_dir: Path | None = None,
        refresh: bool = False,
        record: list[dict[str, Any]] | None = None,
        progress: bool = True,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._concurrency = max(1, concurrency)
        self._max_attempts = max(1, max_attempts)
        self._retry_backoff = retry_backoff
        self._cache_dir = cache_dir
        self._refresh = refresh
        self._record = record
        self._progress = progress
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def observe_pages(self, page_images: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """并发逐页读图，返回按 page_no 排序的每页观察。"""

        pages = [p for p in page_images if isinstance(p, dict) and p.get("path")]
        if not pages:
            return []
        if self._concurrency > 1 and len(pages) > 1:
            with ThreadPoolExecutor(max_workers=self._concurrency) as pool:
                results = list(pool.map(self._observe_one, pages))
        else:
            results = [self._observe_one(p) for p in pages]
        return sorted(results, key=lambda r: r.get("page_no") or 0)

    def _observe_one(self, page: dict[str, Any]) -> dict[str, Any]:
        page_no = _as_int(page.get("page_no")) or 0
        path = Path(str(page.get("path")))
        started = time.monotonic()
        if not path.exists():
            return {**_EMPTY_PAGE, "page_no": page_no, "error": f"image missing: {path}"}
        prompt = PAGE_PROMPT.format(page_no=page_no)
        cache_key = sha256_json(
            {"prompt": prompt, "model": self._model, "image_sha256": page.get("sha256"), "page_no": page_no}
        )
        cached = self._cache_load(cache_key)
        if cached is not None:
            if self._progress:
                print(f"  [ cache] vision page {page_no}", file=sys.stderr, flush=True)
            return {**cached, "page_no": page_no}

        img_b64 = base64.b64encode(path.read_bytes()).decode()
        error: str | None = None
        payload = dict(_EMPTY_PAGE)
        for attempt in range(1, self._max_attempts + 1):
            try:
                content = self._call(prompt, img_b64)
                payload = _parse_json_object(content)
                error = None
                break
            except Exception as exc:  # 网络/超时/解析
                error = f"{type(exc).__name__}: {exc}"
                if attempt < self._max_attempts:
                    time.sleep(self._retry_backoff * attempt)

        observation = {**_EMPTY_PAGE, **payload, "page_no": page_no}
        if error:
            observation["error"] = error
        else:
            self._cache_store(cache_key, observation)
        if self._progress:
            flag = f" ERROR={error}" if error else f" unit={observation.get('unit_hint')}"
            print(
                f"  [{time.monotonic() - started:5.1f}s] vision page {page_no}{flag}",
                file=sys.stderr,
                flush=True,
            )
        if self._record is not None:
            self._record.append({"page_no": page_no, "payload": observation, "error": error})
        return observation

    def _call(self, prompt: str, img_b64: str) -> str:
        return post_anthropic_messages(
            base_url=self._base_url,
            api_key=self._api_key,
            model=self._model,
            content=[
                {"type": "text", "text": prompt},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
            ],
            max_tokens=self._max_tokens,
            timeout=self._timeout,
        )

    def _cache_path(self, cache_key: str) -> Path | None:
        return None if self._cache_dir is None else self._cache_dir / f"vision_{cache_key}.json"

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
        if path is not None:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class MinimaxTextResponder:
    """T2/T3 文本观察 responder（MiniMax M3, Anthropic 格式），与 Kimi 用相同 prompt。

    实现 ObservationResponder 协议（fetch_units/fetch_elements/fetch_layout）。T4 不走这里
    （T4 用视觉/确定性），fetch_layout 返回空。单次失败重试后降级为该阶段弃权。
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int = 8000,
        temperature: float = 0.6,
        timeout: int = 120,
        max_attempts: int = 3,
        retry_backoff: float = 4.0,
        cache_dir: Path | None = None,
        refresh: bool = False,
        record: list[dict[str, Any]] | None = None,
        progress: bool = True,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout
        self._max_attempts = max(1, max_attempts)
        self._retry_backoff = retry_backoff
        self._cache_dir = cache_dir
        self._refresh = refresh
        self._record = record
        self._progress = progress
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_units(self, *, evidence: dict[str, Any], n_samples: int) -> list[dict[str, Any]]:
        return [self._complete("t2", evidence, sample_index=i) for i in range(max(1, n_samples))]

    def fetch_elements(self, *, evidence: dict[str, Any], window: dict[str, Any]) -> dict[str, Any]:
        return self._complete("t3", evidence, label=str(window.get("window_id") or "t3"))

    def fetch_layout(self, *, evidence: dict[str, Any]) -> dict[str, Any]:
        del evidence
        return {"section_profiles": []}

    def _complete(
        self,
        stage: str,
        evidence: dict[str, Any],
        *,
        sample_index: int = 0,
        label: str | None = None,
    ) -> dict[str, Any]:
        # 延迟导入避免循环依赖（observation_prompts → evidence → ...）。
        from .observation_prompts import assemble_observation_messages

        system, user = assemble_observation_messages(stage, evidence)  # firewall asserted inside
        tag = f"{stage}:{label or sample_index}"
        started = time.monotonic()
        cache_key = sha256_json(
            {"system": system, "user": user, "model": self._model, "sample_index": sample_index}
        )
        cached = self._cache_load(cache_key)
        if cached is not None:
            if self._progress:
                print(f"  [ cache] {tag}", file=sys.stderr, flush=True)
            return cached

        empty: dict[str, Any] = {"items": []}
        error: str | None = None
        payload = empty
        for attempt in range(1, self._max_attempts + 1):
            try:
                content = post_anthropic_messages(
                    base_url=self._base_url,
                    api_key=self._api_key,
                    model=self._model,
                    content=user,
                    system=system,
                    max_tokens=self._max_tokens,
                    timeout=self._timeout,
                    temperature=self._temperature,
                )
                payload = _parse_json_object(content)
                error = None
                break
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                payload = empty
                if attempt < self._max_attempts:
                    time.sleep(self._retry_backoff * attempt)

        if error is None:
            self._cache_store(cache_key, payload)
        if self._progress:
            n = len(payload.get("items", []) or [])
            flag = f" ERROR={error}" if error else ""
            print(f"  [{time.monotonic() - started:5.1f}s] {tag:26s} raw={n}{flag}", file=sys.stderr, flush=True)
        if self._record is not None:
            self._record.append({"stage": stage, "label": label, "sample_index": sample_index, "payload": payload, "error": error})
        return payload

    def _cache_path(self, cache_key: str) -> Path | None:
        return None if self._cache_dir is None else self._cache_dir / f"text_{cache_key}.json"

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
        if path is not None:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if not text:
        raise MinimaxVisionError("empty vision response")
    # 容错：去掉可能的 ```json fence 或前后杂字，取第一个 { 到最后一个 }。
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    decoded = json.loads(text)
    if not isinstance(decoded, dict):
        raise MinimaxVisionError("vision response JSON is not an object")
    return decoded


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None
