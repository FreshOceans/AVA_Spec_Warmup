# AVA Spec Warm Up

Standalone Flask application for warming up an AVA/Web Messaging deployment. It opens Genesys Cloud Web Messaging conversations, sends the fixed message `no help needed`, records transport timing metrics, and exits without calling a Judge LLM or Ollama.

## Features

- Manual AVA Spec Warm Up runs with configurable deployment, region, attempts, execution mode, workers, and pacing.
- Safe adaptive performance profile that reduces worker/pacing pressure when timeout or error pressure rises.
- Persistent hourly, daily, weekly, or monthly schedule stored under the local history directory.
- Warm-up-only results view with attempts/sec, success/timeout/failure counts, duration percentiles, per-stage Web Messaging percentiles, adaptive adjustments, schedule state, and local run history.
- Minimal automation API for run, status, stop, schedule, history, and JSON/CSV metrics export.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Start the web app:

```bash
python3 -m ava_warmup
```

Open `http://localhost:5000`.

## Configuration

The form can supply deployment and region at run time. Environment variables can set defaults:

| Variable | Purpose | Default |
| --- | --- | --- |
| `AVA_WARMUP_DEPLOYMENT_ID` | Default Web Messaging deployment ID | unset |
| `AVA_WARMUP_REGION` | Default Genesys Cloud region | unset |
| `AVA_WARMUP_RESPONSE_TIMEOUT` | Per-stage Web Messaging timeout in seconds | `90` |
| `AVA_WARMUP_SUCCESS_THRESHOLD` | Regression threshold for completion rate | `0.8` |
| `AVA_WARMUP_HISTORY_DIR` | Local run/schedule history directory | `.ava_warmup_history` |
| `GC_TESTER_HISTORY_DIR` | Compatibility fallback for history directory | unset |
| `AVA_WARMUP_PERFORMANCE_DIAGNOSTICS_ENABLED` | Include compact performance diagnostics | `true` |

Schedule state is stored in `model_warmup_schedule.json` inside the history directory. Run reports are stored under `runs/` with an `index.json` history file.

## HTTP API

- `POST /run/model_warm_up`: start a run. Accepts form data or JSON fields such as `deployment_id`, `region`, `attempt_count`, `execution_mode`, `worker_count`, and `pacing_seconds`.
- `GET /run/status`: return active run state, trigger source, warm-up metadata, stop state, and recent progress.
- `POST /run/stop`: request that the active run stop.
- `POST /run/model_warm_up/schedule`: save and enable the persistent schedule.
- `POST /run/model_warm_up/schedule/cancel`: cancel the schedule.
- `GET /run/model_warm_up/schedule/status`: return persisted schedule status.
- `GET /results`: render the warm-up metrics dashboard.
- `GET /results/history`: return local warm-up run history.
- `GET /results/export?format=json`: export the latest or selected warm-up report as JSON.
- `GET /results/export?format=csv`: export a compact metrics CSV.

## Testing

```bash
python3 -m compileall ava_warmup tests
python3 -m pytest tests/test_runner.py tests/test_scheduler.py tests/test_web_app.py -q
python3 -m pytest -q
```

The tests use fake Web Messaging clients and temp history directories; they do not connect to Genesys Cloud.
