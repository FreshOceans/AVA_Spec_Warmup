(function () {
    function byId(id) {
        return document.getElementById(id);
    }

    function setHidden(element, hidden) {
        if (!element) {
            return;
        }
        element.hidden = hidden;
    }

    function updateExecutionMode() {
        var mode = byId("model_warmup_execution_mode");
        var workers = byId("model_warmup_parallel_workers");
        var field = byId("parallel-workers-field");
        if (!mode || !workers || !field) {
            return;
        }
        var isParallel = mode.value === "parallel";
        workers.disabled = !isParallel;
        field.dataset.disabled = isParallel ? "false" : "true";
        if (!isParallel) {
            workers.value = "1";
        }
    }

    function updateScheduleFields() {
        var cadence = byId("model_warmup_schedule_cadence");
        if (!cadence) {
            return;
        }
        var value = cadence.value;
        setHidden(byId("schedule-minute-field"), value !== "hourly");
        setHidden(byId("schedule-time-field"), value === "hourly");
        setHidden(byId("schedule-weekday-field"), value !== "weekly");
        setHidden(byId("schedule-month-day-field"), value !== "monthly");
    }

    function initializeDates() {
        var start = byId("model_warmup_schedule_start_date");
        var end = byId("model_warmup_schedule_end_date");
        if (!start || !end) {
            return;
        }
        var today = new Date();
        var future = new Date();
        future.setDate(today.getDate() + 30);
        var toDate = function (date) {
            return date.toISOString().slice(0, 10);
        };
        if (!start.value) {
            start.value = toDate(today);
        }
        if (!end.value) {
            end.value = toDate(future);
        }
    }

    function initializeTimezone() {
        var timezone = byId("model_warmup_schedule_timezone");
        if (!timezone || timezone.value !== "UTC") {
            return;
        }
        try {
            timezone.value = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
        } catch (error) {
            timezone.value = "UTC";
        }
    }

    function formatDuration(seconds) {
        if (seconds === null || seconds === undefined || !isFinite(seconds)) {
            return "calculating";
        }
        seconds = Math.max(0, Math.round(Number(seconds)));
        var minutes = Math.floor(seconds / 60);
        var remainingSeconds = seconds % 60;
        if (minutes <= 0) {
            return remainingSeconds + "s";
        }
        return minutes + "m " + String(remainingSeconds).padStart(2, "0") + "s";
    }

    function escapeHtml(value) {
        return String(value === null || value === undefined ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function renderDiagnostics(events) {
        var list = byId("live-diagnostics-list");
        if (!list) {
            return;
        }
        var recent = (events || []).slice(-25);
        if (!recent.length) {
            list.innerHTML = '<li class="empty">No diagnostics emitted for this page view yet.</li>';
            return;
        }
        list.innerHTML = recent.map(function (event) {
            return "<li>"
                + '<span class="diagnostic-time">' + escapeHtml(event.emitted_at || "") + "</span>"
                + '<span class="pill">' + escapeHtml(event.event_type || "event") + "</span>"
                + "<span>" + escapeHtml(event.message || "") + "</span>"
                + "</li>";
        }).join("");
    }

    function attemptStatus(attempt) {
        if (attempt.success) {
            return "success";
        }
        if (attempt.timed_out) {
            return "timeout";
        }
        if (attempt.skipped) {
            return "skipped";
        }
        return "failure";
    }

    function renderStageTimings(timings) {
        var entries = Object.entries(timings || {});
        if (!entries.length) {
            return "";
        }
        return "<details><summary>Stage timings</summary><ul>"
            + entries.map(function (entry) {
                return "<li><code>" + escapeHtml(entry[0]) + "</code>: "
                    + Number(entry[1] || 0).toFixed(3) + "ms</li>";
            }).join("")
            + "</ul></details>";
    }

    function messageRole(message) {
        if (!message || message.role === null || message.role === undefined) {
            return "message";
        }
        if (typeof message.role === "object" && message.role.value) {
            return String(message.role.value);
        }
        return String(message.role);
    }

    function renderConversationSnapshot(conversation) {
        var messages = conversation || [];
        if (!messages.length) {
            return '<section class="conversation-snapshot"><h3>Web Messenger Interaction Snapshot</h3>'
                + '<p class="empty">No Web Messenger transcript was captured for this attempt.</p></section>';
        }
        return '<section class="conversation-snapshot"><h3>Web Messenger Interaction Snapshot</h3><ol>'
            + messages.map(function (message) {
                var role = messageRole(message);
                return '<li class="conversation-message ' + escapeHtml(role) + '">'
                    + '<span class="conversation-meta"><strong>' + escapeHtml(role) + '</strong>'
                    + '<time>' + escapeHtml(message.timestamp || "-") + '</time></span>'
                    + '<p>' + escapeHtml(message.content || "") + '</p>'
                    + '</li>';
            }).join("")
            + '</ol></section>';
    }

    function renderAttempts(events) {
        var container = byId("live-attempts-list");
        if (!container) {
            return;
        }
        var attempts = [];
        (events || []).forEach(function (event) {
            if (event.event_type === "attempt_completed" && event.attempt_result) {
                attempts.push(event.attempt_result);
            }
        });
        if (!attempts.length) {
            container.innerHTML = '<p class="empty">No completed attempts yet.</p>';
            return;
        }
        container.innerHTML = attempts.map(function (attempt) {
            var status = attemptStatus(attempt);
            var rowClass = status === "success" ? "ok" : (status === "timeout" ? "warn" : "error");
            var duration = Number(attempt.duration_seconds || 0).toFixed(3);
            var messageCount = (attempt.conversation || []).length;
            var error = attempt.error
                ? '<p class="attempt-error">' + escapeHtml(attempt.error) + "</p>"
                : "";
            return '<details class="attempt-row ' + rowClass + '">'
                + "<summary><span><strong>Attempt " + escapeHtml(attempt.attempt_number || "") + "</strong></span> "
                + '<span class="pill">' + escapeHtml(status) + "</span>"
                + "<span>" + duration + "s</span></summary>"
                + "<p>" + escapeHtml(attempt.explanation || "") + "</p>"
                + error
                + "<dl><div><dt>Duration</dt><dd>" + duration + "s</dd></div>"
                + "<div><dt>Messages</dt><dd>" + messageCount + "</dd></div></dl>"
                + renderConversationSnapshot(attempt.conversation)
                + renderStageTimings(attempt.warmup_stage_durations_ms)
                + "</details>";
        }).join("");
    }

    function pollRunStatus() {
        var card = document.querySelector("[data-live-results='true']");
        if (!card) {
            return;
        }
        var statusEl = byId("live-status");
        var etaEl = byId("live-eta");
        var progressEl = byId("live-progress");
        fetch("/run/status", { cache: "no-store" })
            .then(function (response) { return response.json(); })
            .then(function (status) {
                var warmup = status.model_warmup_run || {};
                var live = status.live_progress || {};
                var progressEvents = status.progress || [];
                var planned = live.planned_attempts || warmup.planned_attempts || 0;
                var completed = live.completed_attempts || warmup.completed_attempts || 0;
                renderDiagnostics(progressEvents);
                renderAttempts(progressEvents);
                if (progressEl && planned) {
                    progressEl.max = planned;
                    progressEl.value = completed;
                    progressEl.setAttribute("aria-valuetext", completed + " of " + planned + " attempts completed");
                }
                if (statusEl) {
                    var latest = live.latest_message ? " Latest: " + live.latest_message : "";
                    statusEl.textContent = status.run_active
                        ? "Completed " + completed + " of " + planned + " attempts." + latest
                        : "Run complete. Refreshing results...";
                }
                if (etaEl) {
                    if (status.run_active) {
                        etaEl.textContent = "ETA: " + formatDuration(live.estimated_remaining_seconds)
                            + " | Elapsed: " + formatDuration(live.elapsed_seconds)
                            + " | Rate: " + Number(live.attempts_per_second || 0).toFixed(2) + " attempts/sec";
                    } else {
                        etaEl.textContent = "Run complete.";
                    }
                }
                if (!status.run_active) {
                    window.setTimeout(function () {
                        window.location.reload();
                    }, 800);
                    return;
                }
                window.setTimeout(pollRunStatus, 2000);
            })
            .catch(function () {
                window.setTimeout(pollRunStatus, 3000);
            });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var mode = byId("model_warmup_execution_mode");
        if (mode) {
            mode.addEventListener("change", updateExecutionMode);
            updateExecutionMode();
        }

        var cadence = byId("model_warmup_schedule_cadence");
        if (cadence) {
            cadence.addEventListener("change", updateScheduleFields);
            updateScheduleFields();
        }

        initializeTimezone();
        initializeDates();
        pollRunStatus();
    });
}());
