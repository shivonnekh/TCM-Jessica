"""HKO weather client + notable-condition detector.

All fetch functions are pure I/O wrappers — they return raw dicts and
fail closed (empty dict) on any error. ``detect_conditions`` is a pure
function; it does no I/O and is trivially testable.

HKO free API — no key needed:
  rhrread  : current temp, humidity, warnings
  warnsum  : active warning summary
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal

import httpx

logger = logging.getLogger("broadcaster.weather")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HKO_BASE = os.environ.get(
    "HKO_BASE_URL", "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
)
HKO_TIMEOUT = 10.0
HKO_OBSERVATORY = "Hong Kong Observatory"

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ConditionCode = Literal["heatwave", "cold_front", "rainstorm", "humidity_heat"]
Severity = Literal["mild", "moderate", "severe"]

# Priority order — highest to lowest
CONDITION_PRIORITY: list[ConditionCode] = [
    "rainstorm",
    "heatwave",
    "cold_front",
    "humidity_heat",
]

_SEVERITY_RANK: dict[Severity, int] = {"severe": 3, "moderate": 2, "mild": 1}


@dataclass(frozen=True)
class WeatherCondition:
    code: ConditionCode
    severity: Severity
    summary_zh: str       # 1-line HK Canto fact fed into composer
    temp_c: float | None = None
    humidity_pct: float | None = None


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------


async def fetch_current() -> dict:
    """Current observations (temp, humidity, warning messages)."""
    return await _get({"dataType": "rhrread", "lang": "en"}, "rhrread")


async def fetch_warnings() -> dict:
    """Active warning summary. Empty dict when no warnings."""
    return await _get({"dataType": "warnsum", "lang": "en"}, "warnsum")


async def _get(params: dict, label: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=HKO_TIMEOUT) as client:
            r = await client.get(HKO_BASE, params=params)
            r.raise_for_status()
            return r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("HKO %s fetch failed: %s", label, exc)
        return {}


# ---------------------------------------------------------------------------
# Extraction helpers (pure)
# ---------------------------------------------------------------------------


def _hko_temp(current: dict) -> float | None:
    """Extract Hong Kong Observatory temperature (°C). Falls back to average."""
    try:
        stations = current["temperature"]["data"]
        for entry in stations:
            if entry.get("place") == HKO_OBSERVATORY:
                return float(entry["value"])
        values = [e["value"] for e in stations if "value" in e]
        return round(sum(values) / len(values), 1) if values else None
    except Exception:  # noqa: BLE001
        return None


def _hko_humidity(current: dict) -> float | None:
    try:
        return float(current["humidity"]["data"][0]["value"])
    except Exception:  # noqa: BLE001
        return None


def _has_rainstorm(warnings: dict) -> tuple[bool, str]:
    """Returns (active, action_code). action_code: YELLOW | AMBER | RED."""
    if "WRAIN" not in warnings:
        return False, ""
    code = warnings["WRAIN"].get("actionCode", "AMBER")
    return True, code


# ---------------------------------------------------------------------------
# Detection (pure — no I/O, testable with fixture dicts)
# ---------------------------------------------------------------------------


def detect_conditions(current: dict, warnings: dict) -> list[WeatherCondition]:
    """Detect notable weather conditions. Returns list, priority-ordered."""
    if not current and not warnings:
        return []

    conditions: list[WeatherCondition] = []
    temp = _hko_temp(current)
    humidity = _hko_humidity(current)

    # ── Rainstorm (safety — highest priority) ─────────────────────────────
    rain_active, rain_code = _has_rainstorm(warnings)
    if rain_active:
        colour = {"RED": "紅色", "AMBER": "黃色", "YELLOW": "黃色"}.get(rain_code, "黃色")
        severity: Severity = (
            "severe" if rain_code == "RED"
            else "moderate" if rain_code == "AMBER"
            else "mild"
        )
        conditions.append(
            WeatherCondition(
                code="rainstorm",
                severity=severity,
                summary_zh=f"香港現正發出{colour}暴雨警告",
                temp_c=temp,
                humidity_pct=humidity,
            )
        )

    # ── Heatwave ──────────────────────────────────────────────────────────
    if temp is not None and temp >= 33:
        severity = (
            "severe" if temp >= 36
            else "moderate" if temp >= 34
            else "mild"
        )
        conditions.append(
            WeatherCondition(
                code="heatwave",
                severity=severity,
                summary_zh=f"今日氣溫高達 {int(temp)}°C，天氣非常炎熱",
                temp_c=temp,
                humidity_pct=humidity,
            )
        )

    # ── Cold front ────────────────────────────────────────────────────────
    if temp is not None and temp < 18:
        severity = (
            "severe" if temp < 12
            else "moderate" if temp < 15
            else "mild"
        )
        conditions.append(
            WeatherCondition(
                code="cold_front",
                severity=severity,
                summary_zh=f"今日氣溫只有 {int(temp)}°C，天氣明顯轉涼",
                temp_c=temp,
                humidity_pct=humidity,
            )
        )

    # ── Humidity + heat (暑濕) ────────────────────────────────────────────
    if (
        temp is not None
        and humidity is not None
        and temp >= 29
        and humidity >= 85
    ):
        conditions.append(
            WeatherCondition(
                code="humidity_heat",
                severity="moderate",
                summary_zh=f"今日又熱又濕，氣溫 {int(temp)}°C 濕度 {int(humidity)}%，典型香港暑濕天",
                temp_c=temp,
                humidity_pct=humidity,
            )
        )

    return conditions


def pick_best(conditions: list[WeatherCondition]) -> WeatherCondition | None:
    """Pick the single highest-priority, highest-severity condition."""
    for code in CONDITION_PRIORITY:
        matches = [c for c in conditions if c.code == code]
        if matches:
            return max(matches, key=lambda c: _SEVERITY_RANK.get(c.severity, 0))
    return None
