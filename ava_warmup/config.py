"""Configuration loading for the standalone warm-up app."""

from __future__ import annotations

import os
from typing import Any

from .schemas import AppConfig


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def load_app_config() -> AppConfig:
    """Load warm-up configuration from environment variables."""

    return AppConfig(
        gc_region=os.getenv("AVA_WARMUP_REGION") or os.getenv("GC_REGION"),
        gc_deployment_id=(
            os.getenv("AVA_WARMUP_DEPLOYMENT_ID") or os.getenv("GC_DEPLOYMENT_ID")
        ),
        response_timeout=_env_int("AVA_WARMUP_RESPONSE_TIMEOUT", 90),
        success_threshold=_env_float("AVA_WARMUP_SUCCESS_THRESHOLD", 0.8),
        performance_diagnostics_enabled=_env_bool(
            "AVA_WARMUP_PERFORMANCE_DIAGNOSTICS_ENABLED",
            True,
        ),
        debug_capture_frames=_env_bool("AVA_WARMUP_DEBUG_CAPTURE_FRAMES", False),
        debug_capture_frame_limit=_env_int("AVA_WARMUP_DEBUG_FRAME_LIMIT", 8),
        history_dir=(
            os.getenv("AVA_WARMUP_HISTORY_DIR")
            or os.getenv("GC_TESTER_HISTORY_DIR")
            or ".ava_warmup_history"
        ),
        history_max_runs=_env_int("AVA_WARMUP_HISTORY_MAX_RUNS", 50),
        history_full_json_runs=_env_int("AVA_WARMUP_HISTORY_FULL_JSON_RUNS", 20),
        history_gzip_runs=_env_int("AVA_WARMUP_HISTORY_GZIP_RUNS", 20),
    )


def merge_config(config: AppConfig, overrides: dict[str, Any]) -> AppConfig:
    """Return a copy of config with non-None overrides applied."""

    clean = {key: value for key, value in overrides.items() if value is not None}
    return config.model_copy(update=clean)
