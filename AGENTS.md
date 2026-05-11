# AGENTS.md

## Purpose

This repository is the standalone **AVA Spec Warm Up** application. It exists only to warm up a Genesys Cloud AVA/Web Messaging deployment and report transport metrics.

## Product Scope

- Single workflow: AVA Spec Warm Up.
- Fixed suite: `AVA Spec Warm Up Suite`.
- Fixed scenario: `No Help Needed Warm Up`.
- Fixed message: `no help needed`.
- No Judge LLM calls.
- No Ollama dependency.
- No suite builder, transcript import, analytics journey, intent validation, or journey validation features.

## Core Files

- `ava_warmup/runner.py`: async Web Messaging warm-up runner, request normalization, adaptive backpressure, and report assembly.
- `ava_warmup/scheduler.py`: persistent schedule store, cadence/date math, and scheduler daemon.
- `ava_warmup/web_messaging_client.py`: Genesys Cloud Web Messaging Guest API client.
- `ava_warmup/web_app.py`: Flask app factory, background run state, run/status/stop/schedule/results/export routes.
- `ava_warmup/schemas.py`: focused Pydantic schemas for config, attempts, reports, progress, diagnostics, and warm-up metadata.
- `ava_warmup/history.py`: local run history persistence.
- `templates/home.html`: warm-up form and schedule controls.
- `templates/results.html`: warm-up-only metrics, schedule, and history view.

## Behavioral Contracts

- Warm-up attempts must send exactly `no help needed` unless the product scope is explicitly changed.
- Successful attempts retain compact transport/stage timings and do not include judge diagnostics.
- `safe_adaptive` is the only performance profile.
- Pacing choices are `0.5`, `1.0`, `2.5`, `5.0`, and `7.5` seconds.
- Worker count is clamped to `1..5`; serial mode uses one worker.
- Schedule state is local-only in `model_warmup_schedule.json` under the history directory.
- Run history is local-only under `.ava_warmup_history/` by default.

## API Contracts

Keep these routes backward-compatible unless intentionally changing the standalone API:

- `POST /run/model_warm_up`
- `GET /run/status`
- `POST /run/stop`
- `POST /run/model_warm_up/schedule`
- `POST /run/model_warm_up/schedule/cancel`
- `POST /run/model_warm_up/schedule/disable`
- `GET /run/model_warm_up/schedule/status`
- `GET /results`
- `GET /results/history`
- `GET /results/export`

## Data and Privacy

- Do not commit `.ava_warmup_history/`, `.env`, or `config.yaml`.
- Do not commit customer deployment IDs, raw transcripts, conversation artifacts, or local schedules.
- History tests should isolate `AVA_WARMUP_HISTORY_DIR` or use temp directories.

## Validation

After edits, run:

```bash
python3 -m compileall ava_warmup tests
python3 -m pytest tests/test_runner.py tests/test_scheduler.py tests/test_web_app.py -q
python3 -m pytest -q
```

For UI changes, also start the app with `python3 -m ava_warmup` and verify Home, Results, schedule, run status, and history flows in a browser.
