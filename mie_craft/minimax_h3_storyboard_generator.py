"""MiniMax H3 role-event storyboard asset generator.

The public node emits a validated portable asset, its JSON, a readable
preview and the shot count. V3 compiles events without another LLM call.
"""
from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Optional

from mie_llm.utils import mie_log

from mie_prompt.storyboard_prompts import DEFAULT_LANGUAGE, DEFAULT_OUTPUT_FORMAT, DEFAULT_STYLE, LANGUAGES, MAX_SHOTS, OUTPUT_FORMATS, STYLES, STYLE_CODES, SYSTEM_STORYBOARD_PROMPT, PARSE_RETRY_CORRECTION, build_user_text, extract_json_array, normalize_shots, parse_output_format, parse_style, render_storyboard_markdown, shots_to_json_string
from mie_prompt.h3_prompts import CATEGORIES


MY_CATEGORY = "\U0001F411 MieNodes/\U0001F411 Prompt Generator"

# Token budget: sized for reasoning models that burn the budget on the
# think chain before the visible answer (see the LTX-2.5 sibling note).
_DEFAULT_MAX_TOKENS = 8192
_MIN_MAX_TOKENS = 64
_MAX_MAX_TOKENS = 32768

# Creative board layout: 0.8 matches the creative siblings (LTX-2.5).
_DEFAULT_TEMPERATURE = 0.8

# One LLM call at 120 s covers the typical response window with headroom.
_DEFAULT_TIMEOUT = 120

_MIN_SHOT_COUNT = 1
_MAX_SHOT_COUNT_WIDGET = 20  # Phase-1 widget cap; normalize_shots caps at MAX_SHOTS

# Strip a leading <think>...</think> block that reasoning models may emit
# before the JSON array.
_THINK_BLOCK_RE = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)

# One retry on unparseable replies, then fail the node (no partial boards).
_PARSE_RETRIES = 1


def postprocess_reply(raw_text: str) -> str:
    """Strip a leading ``<think>...</think>`` block and outer whitespace."""
    if not raw_text:
        return ""
    text = raw_text.strip()
    text = _THINK_BLOCK_RE.sub("", text, count=1).strip()
    return text


def _default_concept() -> str:
    return (
        "A short, visually striking cinematic moment with one clear "
        "protagonist, a simple emotional arc, and a satisfying final image."
    )


class H3StoryboardEnhancer:
    """Storyboard planner that talks to the project's LLMServiceConnector.

    Mirrors ``LTX25PromptEnhancer`` / ``H3PromptEnhancer`` (shared logging
    + timeout-override pattern) so all LLM nodes behave alike.
    """

    def __init__(
        self,
        llm_service_connector: Any,
        *,
        temperature: float = _DEFAULT_TEMPERATURE,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        timeout: Optional[int] = None,
    ):
        self.llm = llm_service_connector
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        # Saved/restored around invoke() so a shared connector keeps its
        # own timeout for other nodes.
        self._timeout_override = int(timeout) if timeout else None

    def _invoke(
        self,
        messages: list[dict],
        *,
        temperature: float,
        seed: Optional[int],
        stage: str,
    ) -> str:
        prev_timeout = getattr(self.llm, "timeout", None)
        try:
            if self._timeout_override is not None:
                self.llm.timeout = self._timeout_override
            t0 = time.perf_counter()
            out = self.llm.invoke(
                messages,
                seed=seed,
                temperature=temperature,
                max_tokens=self.max_tokens,
            )
            elapsed = time.perf_counter() - t0
            model_name = getattr(self.llm, "model", "?")
            if not out:
                mie_log(
                    f"H3SB {stage}: model={model_name} returned empty after {elapsed:.2f}s"
                )
                return ""
            mie_log(
                f"H3SB {stage}: model={model_name} ok in {elapsed:.2f}s response_chars={len(out)}"
            )
            return out.strip()
        finally:
            if prev_timeout is not None:
                self.llm.timeout = prev_timeout

    @staticmethod
    def _build_messages(system_prompt: str, user_text: str) -> list[dict]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]

    def _call_storyboard(
        self, messages: list[dict], *, seed: Optional[int]
    ) -> list[Any]:
        """One storyboard call with a corrective retry.

        The retry appends an explicit "reply with ONLY the JSON array"
        user turn instead of replaying the identical messages — a model
        that answered in prose the first time needs the correction, not
        a repeat. Raises ``RuntimeError`` (with the reply head for
        diagnosis) when every attempt fails; a partial board must never
        reach the outputs.
        """
        last_error: Optional[Exception] = None
        last_head = "<no reply>"
        for attempt in range(1 + _PARSE_RETRIES):
            attempt_messages = messages
            if attempt > 0:
                attempt_messages = messages + [
                    {"role": "user", "content": PARSE_RETRY_CORRECTION}
                ]
            raw = postprocess_reply(
                self._invoke(
                    attempt_messages,
                    temperature=self.temperature,
                    seed=seed,
                    stage=f"plan[attempt {attempt + 1}]",
                )
            )
            if not raw:
                last_error = ValueError("empty storyboard reply")
                last_head = "<empty reply>"
                continue
            last_head = raw[:200]
            try:
                return extract_json_array(raw)
            except ValueError as exc:
                last_error = exc
                mie_log(
                    f"H3SB: parse failed ({exc}); retry head={last_head!r}"
                )
        raise RuntimeError(
            f"storyboard reply unparseable after {1 + _PARSE_RETRIES} attempts: "
            f"{last_error}; last reply head: {last_head!r}"
        )

    def __call__(
        self,
        concept: str,
        shot_count: int,
        *,
        style: str = DEFAULT_STYLE,
        genre: str = "",
        language: str = DEFAULT_LANGUAGE,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        seed: Optional[int] = None,
    ) -> dict:
        """Run the storyboard pipeline.

        Returns ``{"storyboard_text", "shots_json", "shot_count"}``.
        """
        style_code = parse_style(style)
        if style_code not in STYLE_CODES:
            mie_log(
                f"H3SB: unknown style {style!r} (parsed {style_code!r}); "
                f"falling back to {DEFAULT_STYLE}"
            )
            style_code = DEFAULT_STYLE
        fmt_code = parse_output_format(output_format)
        if fmt_code not in ("table", "detailed", "minimal"):
            fmt_code = DEFAULT_OUTPUT_FORMAT
        count = max(_MIN_SHOT_COUNT, min(int(shot_count or 1), MAX_SHOTS))

        idea = (concept or "").strip() or _default_concept()
        if not (concept or "").strip():
            mie_log(f"H3SB: empty concept; using default idea: {idea[:80]!r}")

        user_text = build_user_text(idea, count, style_code, genre, language)
        messages = self._build_messages(SYSTEM_STORYBOARD_PROMPT, user_text)

        raw_shots = self._call_storyboard(messages, seed=seed)
        shots, warnings = normalize_shots(raw_shots, count)

        storyboard_text = render_storyboard_markdown(shots, fmt_code, warnings)
        return {
            "storyboard_text": storyboard_text,
            "shots_json": shots_to_json_string(shots),
            "shot_count": len(shots),
        }


# --------------------------------------------------------------------------- #
# ComfyUI node
# --------------------------------------------------------------------------- #
from mie_craft.script.generator import AssetStoryboardEnhancer, preview_asset
