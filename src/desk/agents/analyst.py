"""AGENT 3: ANALYST — Grok JSON scoring or rule-based fallback."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from desk.config import DeskSettings
from desk.models import AnalystResult, FilterContext, ScannedPair


class AnalystAgent:
    def __init__(self, settings: DeskSettings) -> None:
        self.settings = settings
        self._client: OpenAI | None = None
        if settings.grok_available:
            self._client = OpenAI(
                api_key=settings.xai_api_key,
                base_url=settings.xai_base_url,
            )

    def score(
        self,
        pair: ScannedPair,
        filter_details: dict[str, Any],
        ctx: FilterContext | None = None,
    ) -> AnalystResult:
        if self._client:
            return self._grok_score(pair, filter_details)
        return self._rule_based_score(pair, filter_details)

    def _grok_score(
        self, pair: ScannedPair, filter_details: dict[str, Any]
    ) -> AnalystResult:
        metrics = {
            "symbol": pair.symbol,
            "mint": pair.mint,
            "price_usd": pair.price_usd,
            "liquidity_usd": pair.liquidity_usd,
            "volume_h1": pair.volume_h1,
            "buys_h1": pair.buys_h1,
            "sells_h1": pair.sells_h1,
            "filter": filter_details,
        }
        prompt = (
            "Analyze this Solana memecoin candidate for organic momentum vs rug risk. "
            "Return ONLY valid JSON: "
            '{"score": <float 0-1>, "rationale": "<short string>"}. '
            f"Metrics: {json.dumps(metrics)}"
        )
        try:
            completion = self._client.chat.completions.create(  # type: ignore[union-attr]
                model="grok-2-1212",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a quantitative crypto risk analyst. "
                            "Output strict JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            text = (completion.choices[0].message.content or "").strip()
            parsed = self._parse_json_score(text)
            return AnalystResult(
                score=parsed["score"],
                rationale=parsed.get("rationale", ""),
                source="grok",
                breakdown={"raw": text},
            )
        except Exception as exc:
            rb = self._rule_based_score(pair, filter_details)
            rb.rationale = f"Grok error ({exc}); {rb.rationale}"
            rb.breakdown["grok_error"] = str(exc)
            return rb

    def _parse_json_score(self, text: str) -> dict[str, Any]:
        try:
            data = json.loads(text)
            score = float(data.get("score", 0))
            return {"score": max(0.0, min(1.0, score)), "rationale": data.get("rationale", "")}
        except json.JSONDecodeError:
            m = re.search(r"(\d+\.?\d*)", text)
            score = float(m.group(1)) if m else 0.0
            if score > 1:
                score = score / 100.0
            return {"score": max(0.0, min(1.0, score)), "rationale": text[:200]}

    def _rule_based_score(
        self, pair: ScannedPair, filter_details: dict[str, Any]
    ) -> AnalystResult:
        score = 0.35
        rationale_parts = ["RULE_BASED_ANALYST (XAI_API_KEY missing)"]

        vol_liq = filter_details.get("vol_to_liq")
        if vol_liq is None and pair.liquidity_usd > 0:
            vol_liq = pair.volume_h1 / pair.liquidity_usd
        if vol_liq and vol_liq >= 0.3:
            score += 0.15
            rationale_parts.append("healthy vol/liq")

        bs = filter_details.get("buy_sell_ratio")
        if bs is None and pair.sells_h1 > 0:
            bs = pair.buys_h1 / pair.sells_h1
        if bs and 1.2 <= bs <= 2.5:
            score += 0.15
            rationale_parts.append("balanced flow")

        if pair.liquidity_usd >= 25_000:
            score += 0.1
            rationale_parts.append("depth ok")

        ext = filter_details.get("price_above_low_pct")
        if ext is not None and ext < 0.2:
            score += 0.15
            rationale_parts.append("not extended from low")

        if pair.buys_h1 >= 40:
            score += 0.1

        score = max(0.0, min(1.0, score))
        return AnalystResult(
            score=score,
            rationale="; ".join(rationale_parts),
            source="rule_based",
            breakdown=filter_details,
        )