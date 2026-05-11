"""Local run history persistence for warm-up reports."""

from __future__ import annotations

import gzip
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import TestReport

_STORAGE_FULL_JSON = "full_json"
_STORAGE_GZIP_JSON = "gz_json"
_STORAGE_SUMMARY_ONLY = "summary_only"


class RunHistoryStore:
    """Persist completed warm-up reports and retrieve historical runs."""

    def __init__(
        self,
        history_dir: str,
        max_runs: int = 50,
        *,
        full_json_runs: int = 20,
        gzip_runs: int = 20,
    ):
        self.history_dir = Path(history_dir)
        self.runs_dir = self.history_dir / "runs"
        self.index_path = self.history_dir / "index.json"
        self.max_runs = max(1, int(max_runs))
        configured_full = max(0, int(full_json_runs))
        configured_gzip = max(0, int(gzip_runs))
        self.full_json_runs = min(self.max_runs, configured_full)
        self.gzip_runs = min(self.max_runs - self.full_json_runs, configured_gzip)

    def save_report(self, report: TestReport) -> dict:
        self._ensure_dirs()
        run_id = self._new_run_id()
        report_rel_path = f"runs/{run_id}.json"
        report_path = self.history_dir / report_rel_path
        self._atomic_write_json(report_path, report.model_dump(mode="json"))

        warmup = report.model_warmup_run
        entry = {
            "run_id": run_id,
            "suite_name": report.suite_name,
            "timestamp": report.timestamp.isoformat(),
            "report_file": report_rel_path,
            "storage_type": _STORAGE_FULL_JSON,
            "run_type": "model_warm_up",
            "overall_attempts": report.overall_attempts,
            "overall_successes": report.overall_successes,
            "overall_failures": report.overall_failures,
            "overall_timeouts": report.overall_timeouts,
            "overall_skipped": report.overall_skipped,
            "overall_success_rate": report.overall_success_rate,
            "duration_seconds": report.duration_seconds,
            "has_regressions": report.has_regressions,
            "model_warmup_run": (
                warmup.model_dump(mode="json", exclude={"deployment_id"})
                if warmup is not None
                else None
            ),
            "scenario_summaries": [
                {
                    "name": scenario.scenario_name,
                    "attempts": scenario.attempts,
                    "successes": scenario.successes,
                    "failures": scenario.failures,
                    "timeouts": scenario.timeouts,
                    "skipped": scenario.skipped,
                    "success_rate": scenario.success_rate,
                    "is_regression": scenario.is_regression,
                }
                for scenario in report.scenario_results
            ],
        }

        index = self._load_index()
        entries = [entry] + index["runs"]
        kept_entries = entries[: self.max_runs]
        pruned_entries = entries[self.max_runs :]
        for pruned in pruned_entries:
            self._delete_entry_file(pruned)

        compacted_entries = self._apply_compaction_windows(kept_entries)
        self._atomic_write_json(self.index_path, {"runs": compacted_entries})
        return compacted_entries[0]

    def list_entries(self, *, limit: Optional[int] = None) -> list[dict]:
        entries = self._load_index()["runs"]
        if limit is not None:
            entries = entries[: max(0, int(limit))]
        return entries

    def get_entry_by_run_id(self, run_id: str) -> Optional[dict]:
        target = str(run_id or "").strip()
        if not target:
            return None
        for entry in self.list_entries():
            if str(entry.get("run_id", "")).strip() == target:
                return entry
        return None

    def load_report_from_entry(self, entry: dict) -> Optional[TestReport]:
        storage_type = str(entry.get("storage_type") or _STORAGE_FULL_JSON)
        if storage_type == _STORAGE_SUMMARY_ONLY:
            return None
        rel_path = entry.get("report_file")
        if not isinstance(rel_path, str) or not rel_path.strip():
            return None
        report_path = self.history_dir / rel_path
        if not report_path.exists():
            return None
        try:
            if report_path.suffix == ".gz":
                with gzip.open(report_path, "rt", encoding="utf-8") as handle:
                    payload = json.load(handle)
            else:
                payload = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            return TestReport.model_validate(payload)
        except Exception:
            return None

    def _ensure_dirs(self) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict:
        if not self.index_path.exists():
            return {"runs": []}
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"runs": []}
        runs = payload.get("runs")
        if not isinstance(runs, list):
            return {"runs": []}
        return {"runs": [entry for entry in runs if isinstance(entry, dict)]}

    def _atomic_write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temp_path, path)

    def _apply_compaction_windows(self, entries: list[dict]) -> list[dict]:
        compacted = []
        for index, entry in enumerate(entries):
            desired_storage = self._desired_storage_for_index(index)
            compacted.append(self._coerce_entry_storage(dict(entry), desired_storage))
        return compacted

    def _desired_storage_for_index(self, index: int) -> str:
        if index < self.full_json_runs:
            return _STORAGE_FULL_JSON
        if index < self.full_json_runs + self.gzip_runs:
            return _STORAGE_GZIP_JSON
        return _STORAGE_SUMMARY_ONLY

    def _coerce_entry_storage(self, entry: dict, desired_storage: str) -> dict:
        report_file = entry.get("report_file")
        report_path = (
            self.history_dir / report_file
            if isinstance(report_file, str) and report_file.strip()
            else None
        )
        if desired_storage == _STORAGE_SUMMARY_ONLY:
            self._delete_entry_file(entry)
            entry["report_file"] = None
            entry["storage_type"] = _STORAGE_SUMMARY_ONLY
            return entry
        if report_path is None or not report_path.exists():
            entry["report_file"] = None
            entry["storage_type"] = _STORAGE_SUMMARY_ONLY
            return entry
        if desired_storage == _STORAGE_GZIP_JSON:
            if report_path.suffix != ".gz":
                gz_path = report_path.with_suffix(report_path.suffix + ".gz")
                self._gzip_file(report_path, gz_path)
                try:
                    report_path.unlink(missing_ok=True)
                except OSError:
                    pass
                entry["report_file"] = str(gz_path.relative_to(self.history_dir))
            entry["storage_type"] = _STORAGE_GZIP_JSON
            return entry
        if report_path.suffix == ".gz":
            json_path = report_path.with_suffix("")
            if not json_path.exists():
                self._gunzip_file(report_path, json_path)
            entry["report_file"] = str(json_path.relative_to(self.history_dir))
            try:
                report_path.unlink(missing_ok=True)
            except OSError:
                pass
        entry["storage_type"] = _STORAGE_FULL_JSON
        return entry

    def _delete_entry_file(self, entry: dict) -> None:
        rel_path = entry.get("report_file")
        if isinstance(rel_path, str) and rel_path.strip():
            try:
                (self.history_dir / rel_path).unlink(missing_ok=True)
            except OSError:
                pass

    def _gzip_file(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with src.open("rb") as in_handle, gzip.open(dst, "wb") as out_handle:
            out_handle.write(in_handle.read())

    def _gunzip_file(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(src, "rb") as in_handle, dst.open("wb") as out_handle:
            out_handle.write(in_handle.read())

    def _new_run_id(self) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"{timestamp}-{uuid.uuid4().hex[:8]}"
