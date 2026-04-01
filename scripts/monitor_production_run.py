#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path


TERMINAL_STATUSES = {"DONE", "FAILED", "CANCELLED", "ERROR"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def run_local(cmd: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )


def remote_python(ssh_target: str, container: str, code: str) -> str:
    result = run_local(["ssh", ssh_target, "docker", "exec", "-i", container, "python", "-"], input_text=code)
    return result.stdout


def remote_docker_logs(ssh_target: str, container: str, since_iso: str) -> str:
    result = run_local(["ssh", ssh_target, "docker", "logs", "--since", since_iso, container])
    return result.stdout + result.stderr


def fetch_snapshot(ssh_target: str, container: str, run_id: str) -> dict:
    code = f"""
import json
import sqlite3

run_id = {run_id!r}
conn = sqlite3.connect("/data/app.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

out = {{}}

cur.execute("SELECT * FROM plan_runs WHERE run_id = ?", (run_id,))
run_row = cur.fetchone()
out["run"] = dict(run_row) if run_row else None

if not run_row:
    print(json.dumps(out, ensure_ascii=False))
    raise SystemExit(0)

plan_id = run_row["plan_id"]

cur.execute(
    "SELECT * FROM step_runs WHERE run_id = ? ORDER BY COALESCE(started_at, '9999-12-31T23:59:59'), step_run_id",
    (run_id,),
)
out["step_runs"] = [dict(row) for row in cur.fetchall()]

cur.execute(
    "SELECT step_id, step_order, action_type, read_or_write, target, estimated_count, estimated_duration_sec, risk_level, dependency_step_ids "
    "FROM plan_steps WHERE plan_id = ? ORDER BY step_order, step_id",
    (plan_id,),
)
out["plan_steps"] = [dict(row) for row in cur.fetchall()]

cur.execute("SELECT context_id FROM plans WHERE plan_id = ?", (plan_id,))
context_row = cur.fetchone()
context_id = context_row["context_id"] if context_row else None
out["context_id"] = context_id

cur.execute("SELECT * FROM plans WHERE plan_id = ?", (plan_id,))
plan_row = cur.fetchone()
out["plan"] = dict(plan_row) if plan_row else None

if context_id:
    cur.execute("SELECT * FROM product_contexts WHERE context_id = ?", (context_id,))
    row = cur.fetchone()
    out["context"] = dict(row) if row else None
else:
    out["context"] = None

    # Phase 7 operational summaries.
summary_queries = {{
    "crawled_by_status": (
        "SELECT record_type, COALESCE(pre_ai_status, 'NULL') AS pre_ai_status, COUNT(*) AS count "
        "FROM crawled_posts WHERE run_id = ? GROUP BY record_type, pre_ai_status "
        "ORDER BY record_type, pre_ai_status"
    ),
    "crawled_by_step": (
        "SELECT step_run_id, record_type, COALESCE(pre_ai_status, 'NULL') AS pre_ai_status, COUNT(*) AS count "
        "FROM crawled_posts WHERE run_id = ? GROUP BY step_run_id, record_type, pre_ai_status "
        "ORDER BY step_run_id, record_type, pre_ai_status"
    ),
    "crawled_by_query_family": (
        "SELECT COALESCE(query_family, 'NULL') AS query_family, COALESCE(pre_ai_status, 'NULL') AS pre_ai_status, COUNT(*) AS count "
        "FROM crawled_posts WHERE run_id = ? GROUP BY query_family, pre_ai_status ORDER BY query_family, pre_ai_status"
    ),
    "crawled_by_batch_decision": (
        "SELECT COALESCE(batch_decision, 'NULL') AS batch_decision, COUNT(*) AS count "
        "FROM crawled_posts WHERE run_id = ? GROUP BY batch_decision ORDER BY batch_decision"
    ),
    "labels_by_status": (
        "SELECT COALESCE(label_status, 'NULL') AS label_status, COUNT(*) AS count "
        "FROM crawled_posts WHERE run_id = ? GROUP BY label_status ORDER BY label_status"
    ),
    "providers": (
        "SELECT COALESCE(provider_used, 'NULL') AS provider_used, fallback_used, COUNT(*) AS count "
        "FROM crawled_posts WHERE run_id = ? GROUP BY provider_used, fallback_used ORDER BY provider_used, fallback_used"
    ),
    "judge_outcomes": (
        "SELECT COALESCE(judge_decision, COALESCE(pre_ai_status, 'NULL')) AS decision, "
        "judge_used_image_understanding AS used_image_understanding, COUNT(*) AS count "
        "FROM crawled_posts WHERE run_id = ? "
        "GROUP BY decision, used_image_understanding ORDER BY decision, used_image_understanding"
    ),
    "label_jobs": (
        "SELECT label_job_id, status, records_total, records_labeled, records_failed, records_fallback, created_at, ended_at "
        "FROM label_jobs WHERE run_id = ? ORDER BY created_at DESC"
    ),
    "theme_results": (
        "SELECT COUNT(*) AS theme_count FROM theme_results WHERE run_id = ?"
    ),
    "record_timing": (
        "SELECT MIN(crawled_at) AS first_record_at, "
        "MIN(CASE WHEN COALESCE(judge_decision, pre_ai_status) = 'ACCEPTED' THEN crawled_at END) AS first_accepted_at, "
        "MAX(crawled_at) AS last_record_at "
        "FROM crawled_posts WHERE run_id = ?"
    ),
    "top_records": (
        "SELECT post_id, record_type, pre_ai_status, pre_ai_score, judge_decision, judge_confidence_score, "
        "judge_used_image_understanding, query_family, source_type, batch_decision, source_url, parent_post_id "
        "FROM crawled_posts WHERE run_id = ? "
        "ORDER BY CASE COALESCE(judge_decision, pre_ai_status, 'NULL') "
        "WHEN 'ACCEPTED' THEN 0 WHEN 'UNCERTAIN' THEN 1 ELSE 2 END, COALESCE(pre_ai_score, -1) DESC, post_id LIMIT 25"
    ),
}}

out["summaries"] = {{}}
for key, query in summary_queries.items():
    cur.execute(query, (run_id,))
    out["summaries"][key] = [dict(row) for row in cur.fetchall()]

print(json.dumps(out, ensure_ascii=False))
"""
    return json.loads(remote_python(ssh_target, container, code))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def safe_json_loads(value: str | None) -> dict | list | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def summarize_run(snapshot: dict) -> dict:
    run = snapshot.get("run") or {}
    step_runs = snapshot.get("step_runs") or []
    context = snapshot.get("context") or {}
    summaries = (snapshot.get("summaries") or {})
    top_records = summaries.get("top_records") or []

    phase_flags = {
        "retrieval_profile_present": bool(context.get("retrieval_profile_json")),
        "pre_ai_status_present": any((row.get("pre_ai_status") or "NULL") != "NULL" for row in summaries.get("crawled_by_status", [])),
        "batch_decision_present": any((row.get("batch_decision") or "NULL") != "NULL" for row in summaries.get("crawled_by_batch_decision", [])),
        "comment_step_zero_after_no_accepts": False,
        "answer_status_present": bool(run.get("answer_status")),
        "reformulation_observed": False,
        "reason_cluster_observed": False,
        "image_fallback_observed": False,
        "planner_meta_present": bool(context.get("planning_meta_json")) or bool((snapshot.get("plan") or {}).get("generation_meta_json")),
        "timeout_salvage_observed": False,
    }

    accepted_total = 0
    uncertain_total = 0
    rejected_total = 0
    for row in summaries.get("crawled_by_status", []):
        status = row.get("pre_ai_status")
        count = int(row.get("count") or 0)
        if status == "ACCEPTED":
            accepted_total += count
        elif status == "UNCERTAIN":
            uncertain_total += count
        elif status == "REJECTED":
            rejected_total += count

    by_action = {}
    for plan_step in snapshot.get("plan_steps") or []:
        by_action[plan_step["step_id"]] = plan_step["action_type"]

    accepted_by_step_run: dict[str, int] = {}
    for row in summaries.get("crawled_by_step", []):
        if row.get("pre_ai_status") == "ACCEPTED":
            accepted_by_step_run[row.get("step_run_id") or ""] = accepted_by_step_run.get(row.get("step_run_id") or "", 0) + int(row.get("count") or 0)

    completed_steps = []
    running_steps = []
    pending_steps = []
    failed_steps = []
    timeout_salvage_steps = []
    for step in step_runs:
        checkpoint = safe_json_loads(step.get("checkpoint") or step.get("checkpoint_json"))
        salvage = checkpoint.get("salvage") if isinstance(checkpoint, dict) else None
        summary = {
            "step_id": step["step_id"],
            "action_type": by_action.get(step["step_id"]),
            "status": step["status"],
            "started_at": step.get("started_at"),
            "ended_at": step.get("ended_at"),
            "actual_count": step.get("actual_count"),
            "accepted_count": accepted_by_step_run.get(step["step_run_id"], 0),
            "error_message": step.get("error_message"),
            "heartbeat_at": checkpoint.get("heartbeat_at") if isinstance(checkpoint, dict) else None,
            "progress": checkpoint.get("progress") if isinstance(checkpoint, dict) else None,
            "salvage": salvage if isinstance(salvage, dict) else None,
        }
        if step["status"] == "DONE":
            completed_steps.append(summary)
        elif step["status"] == "RUNNING":
            running_steps.append(summary)
        elif step["status"] == "PENDING":
            pending_steps.append(summary)
        elif step["status"] == "FAILED":
            failed_steps.append(summary)
            if isinstance(salvage, dict) and salvage.get("available"):
                timeout_salvage_steps.append(
                    {
                        "step_id": step["step_id"],
                        "action_type": by_action.get(step["step_id"]),
                        "collected_count": salvage.get("collected_count"),
                        "persisted_count": salvage.get("persisted_count"),
                        "lost_before_persist_count": salvage.get("lost_before_persist_count"),
                        "image_candidate_count": salvage.get("image_candidate_count"),
                        "sample_candidates": salvage.get("sample_candidates") or [],
                    }
                )
                phase_flags["timeout_salvage_observed"] = True

    for step in step_runs:
        if by_action.get(step["step_id"]) != "CRAWL_COMMENTS":
            continue
        if step.get("actual_count") == 0 and accepted_total == 0:
            phase_flags["comment_step_zero_after_no_accepts"] = True

    checkpoint_batch_summaries = []
    query_attempts = []
    for step in step_runs:
        checkpoint = safe_json_loads(step.get("checkpoint") or step.get("checkpoint_json"))
        if not isinstance(checkpoint, dict):
            continue
        for batch in checkpoint.get("batch_summaries") or []:
            checkpoint_batch_summaries.append(batch)
        for query_attempt in checkpoint.get("query_attempts") or []:
            query_attempts.append(query_attempt)

    decision_counter = Counter(
        batch.get("batch_decision") or batch.get("decision")
        for batch in checkpoint_batch_summaries
        if batch.get("batch_decision") or batch.get("decision")
    )
    reformulated_queries = [
        reformulated_query
        for attempt in query_attempts
        for reformulated_query in (attempt.get("reformulated_queries") or [])
        if reformulated_query
    ]
    reason_clusters = Counter(
        attempt.get("reason_cluster")
        for attempt in query_attempts
        if attempt.get("reason_cluster")
    )
    phase_flags["reformulation_observed"] = bool(reformulated_queries or any(attempt.get("used_reformulation") for attempt in query_attempts))
    phase_flags["reason_cluster_observed"] = bool(reason_clusters)

    judge_outcomes = summaries.get("judge_outcomes") or []
    image_fallback_total = 0
    accepted_with_image = 0
    for row in judge_outcomes:
        count = int(row.get("count") or 0)
        if int(row.get("used_image_understanding") or 0) == 1:
            image_fallback_total += count
            if row.get("decision") == "ACCEPTED":
                accepted_with_image += count
    phase_flags["image_fallback_observed"] = image_fallback_total > 0

    label_jobs = summaries.get("label_jobs") or []
    latest_label_job = label_jobs[0] if label_jobs else None
    theme_summary = summaries.get("theme_results") or []
    theme_count = int((theme_summary[0] or {}).get("theme_count") or 0) if theme_summary else 0
    record_timing = (summaries.get("record_timing") or [{}])[0] or {}
    run_started_at = parse_ts(run.get("started_at"))
    first_record_at = parse_ts(record_timing.get("first_record_at"))
    first_accepted_at = parse_ts(record_timing.get("first_accepted_at"))
    time_to_first_record_sec = (
        round((first_record_at - run_started_at).total_seconds(), 1)
        if run_started_at and first_record_at
        else None
    )
    time_to_first_accepted_sec = (
        round((first_accepted_at - run_started_at).total_seconds(), 1)
        if run_started_at and first_accepted_at
        else None
    )

    concerns: list[str] = []
    context_planning_meta = safe_json_loads(context.get("planning_meta_json")) if context else None
    plan_generation_meta = safe_json_loads((snapshot.get("plan") or {}).get("generation_meta_json"))
    if accepted_total == 0:
        concerns.append("No ACCEPTED records so far; retrieval is spending budget mostly on REJECTED/UNCERTAIN candidates.")
    if uncertain_total > 0 and accepted_total == 0:
        concerns.append("UNCERTAIN records are present without any ACCEPTED records, which suggests thresholds or query quality may still be too weak for strict mode.")
    if decision_counter.get("continue", 0) > 0 and accepted_total == 0:
        concerns.append("Batch health continued at least one weak query path despite zero accepted records; query abandonment may still be too slow.")
    if running_steps:
        for step in running_steps:
            concerns.append(
                f"Step {step['step_id']} ({step['action_type']}) is still RUNNING, so the end-to-end AI/theme stages have not been proven yet."
            )
    for step in failed_steps:
        if step.get("error_message"):
            concerns.append(
                f"Step {step['step_id']} is marked FAILED with error `{step['error_message']}`."
            )
    if run.get("failure_class"):
        concerns.append(f"Run failure class is `{run.get('failure_class')}`, which indicates an infra/runtime category rather than a generic step failure.")
    if run.get("status") == "CANCELLING":
        concerns.append("Run is still in CANCELLING state, so the stop request has not converged to a true terminal halt yet.")
    if accepted_total > 0 and run.get("answer_status") not in {"ANSWER_READY", "NO_ANSWER_CONTENT"}:
        concerns.append(
            "Accepted records exist but answer closeout did not finish in a final answer state yet."
        )
    if accepted_total > 0 and theme_count == 0:
        concerns.append(
            "Accepted records were found but theme synthesis still produced zero persisted themes."
        )
    if accepted_total == 0 and not phase_flags["reformulation_observed"]:
        concerns.append(
            "Zero accepted records were observed without any reformulated query path, so reason-aware reformulation is not yet helping this run."
        )
    if image_fallback_total == 0:
        concerns.append(
            "No record triggered image understanding in this run, so the vision fallback path is still unproven for this production scenario."
        )
    if not phase_flags["planner_meta_present"]:
        concerns.append("Planner/provider attempt metadata is missing from production artifacts, so planner resilience is not yet auditable end to end.")
    if run.get("failure_class") == "STEP_STUCK_TIMEOUT" and not phase_flags["timeout_salvage_observed"]:
        concerns.append("The run hit STEP_STUCK_TIMEOUT without salvage metadata, so collected-but-unpersisted evidence is still opaque.")
    for step in completed_steps:
        if step.get("action_type") == "SEARCH_IN_GROUP" and step.get("accepted_count") == 0 and int(step.get("actual_count") or 0) > 0:
            concerns.append(
                f"Step {step['step_id']} SEARCH_IN_GROUP scanned records but yielded zero ACCEPTED posts, so this path may still be over-prioritized."
            )

    failure_mode = None
    if failed_steps:
        if any(step.get("error_message") == "run has no crawled posts" for step in failed_steps) and accepted_total == 0:
            failure_mode = (
                "post_run_labeling_failed_on_zero_eligible_records"
            )
            concerns.append(
                "The run failed after retrieval because auto-labeling still started in strict mode even though zero eligible ACCEPTED records were available."
            )

    recommendations = [
        "Keep browser-backed runs behind a single-flight lease and alert explicitly on browser admission wait time so production safety regressions are visible early.",
        "Promote answer delivery to a first-class success criterion by tracking accepted-to-theme and accepted-to-answer conversion on every production run.",
        "Re-rank weak SEARCH_IN_GROUP paths behind proven trust, fraud, fee, and complaint postures when early search batches already show better yield elsewhere.",
        "Use dominant reject reason clusters to force reformulation instead of only stopping weak paths, then audit whether the rewritten query changed yield.",
        "Continue capturing image-fallback usage metrics, but validate them on dedicated image-bearing contexts before claiming the capability is production-proven.",
        "Persist richer run-level audit events so production analysis does not depend only on checkpoint blobs and container logs.",
    ]

    next_phase_options = [
        "Goal-aware execution: stop the whole plan once the run has enough high-confidence evidence to answer the user question, not only once the step list is exhausted.",
        "Source quality memory: maintain per-group and per-query quality scores across runs for smarter exploration budgets.",
        "Operator rescue mode: let an operator expand into category, symptom, or competitor terms when strict mode finds zero evidence after the first strong paths.",
        "Vision validation track: run recurring image-bearing case packs for before-after, screenshot, fee table, and scam-proof scenarios.",
        "Run observability layer: show admission queueing, answer closeout state, reformulation attempts, and image-trigger counts directly in the monitor UI.",
    ]

    return {
        "run_status": run.get("status"),
        "completion_reason": run.get("completion_reason"),
        "failure_class": run.get("failure_class"),
        "answer_status": run.get("answer_status"),
        "total_records": run.get("total_records"),
        "time_to_first_record_sec": time_to_first_record_sec,
        "time_to_first_accepted_sec": time_to_first_accepted_sec,
        "accepted_total": accepted_total,
        "uncertain_total": uncertain_total,
        "rejected_total": rejected_total,
        "theme_count": theme_count,
        "image_fallback_total": image_fallback_total,
        "accepted_with_image": accepted_with_image,
        "latest_label_job": latest_label_job,
        "phase_flags": phase_flags,
        "planner_analysis_meta": context_planning_meta,
        "plan_generation_meta": plan_generation_meta,
        "completed_steps": completed_steps,
        "running_steps": running_steps,
        "pending_steps": pending_steps,
        "failed_steps": failed_steps,
        "timeout_salvage_steps": timeout_salvage_steps,
        "failure_mode": failure_mode,
        "batch_decisions": dict(decision_counter),
        "reason_clusters": dict(reason_clusters),
        "reformulated_queries": reformulated_queries[:20],
        "query_attempts": query_attempts[:20],
        "top_records": top_records[:10],
        "concerns": concerns,
        "recommendations": recommendations,
        "next_phase_options": next_phase_options,
    }


def render_report(snapshot: dict, analysis: dict, output_dir: Path) -> None:
    report_path = output_dir / "final_report.md"
    run = snapshot.get("run") or {}
    context = snapshot.get("context") or {}
    lines = [
        f"# Production Analysis For {run.get('run_id', 'unknown-run')}",
        "",
        "## Request Context",
        f"- Topic: {context.get('topic', 'N/A')}",
        f"- Run status: {analysis.get('run_status')}",
        f"- Completion reason: {analysis.get('completion_reason')}",
        f"- Failure class: {analysis.get('failure_class')}",
        f"- Answer status: {analysis.get('answer_status')}",
        f"- Started at: {run.get('started_at')}",
        f"- Ended at: {run.get('ended_at')}",
        f"- Total records persisted: {analysis.get('total_records')}",
        f"- Time to first record (sec): {analysis.get('time_to_first_record_sec')}",
        f"- Time to first accepted (sec): {analysis.get('time_to_first_accepted_sec')}",
        "",
        "## End-to-End Timeline",
    ]
    for item in analysis.get("completed_steps", []):
        lines.append(
            f"- DONE `{item['step_id']}` `{item['action_type']}` from {item.get('started_at')} to {item.get('ended_at')} "
            f"with actual_count={item.get('actual_count')} accepted_count={item.get('accepted_count')}"
        )
    for item in analysis.get("running_steps", []):
        lines.append(
            f"- RUNNING `{item['step_id']}` `{item['action_type']}` since {item.get('started_at')}"
        )
        if item.get("heartbeat_at"):
            lines.append(f"  heartbeat=`{item.get('heartbeat_at')}` progress=`{json.dumps(item.get('progress') or {}, ensure_ascii=False)}`")
    for item in analysis.get("failed_steps", []):
        lines.append(
            f"- FAILED `{item['step_id']}` `{item['action_type']}` from {item.get('started_at')} to {item.get('ended_at')} "
            f"with actual_count={item.get('actual_count')} error=`{item.get('error_message')}`"
        )
        if item.get("salvage"):
            lines.append(f"  salvage=`{json.dumps(item.get('salvage') or {}, ensure_ascii=False)}`")
    for item in analysis.get("pending_steps", []):
        lines.append(f"- PENDING `{item['step_id']}` `{item['action_type']}`")

    flags = analysis.get("phase_flags") or {}
    lines.extend(
        [
            "",
            "## Phase Alignment",
            f"- Retrieval profile present: `{flags.get('retrieval_profile_present')}`",
            f"- Deterministic pre-AI statuses present: `{flags.get('pre_ai_status_present')}`",
            f"- Batch-level decisions present: `{flags.get('batch_decision_present')}`",
            f"- Selective comment expansion observed: `{flags.get('comment_step_zero_after_no_accepts')}`",
            f"- Reason-aware reformulation observed: `{flags.get('reformulation_observed')}`",
            f"- Reason clusters observed: `{flags.get('reason_cluster_observed')}`",
            f"- Image fallback observed: `{flags.get('image_fallback_observed')}`",
            f"- Planner metadata present: `{flags.get('planner_meta_present')}`",
            f"- Timeout salvage observed: `{flags.get('timeout_salvage_observed')}`",
            f"- Answer status present: `{flags.get('answer_status_present')}`",
            f"- ACCEPTED / UNCERTAIN / REJECTED: `{analysis.get('accepted_total')}` / `{analysis.get('uncertain_total')}` / `{analysis.get('rejected_total')}`",
            f"- Theme count: `{analysis.get('theme_count')}`",
            f"- Image fallback count / accepted with image: `{analysis.get('image_fallback_total')}` / `{analysis.get('accepted_with_image')}`",
            "",
            "## Initial Verdict",
        ]
    )

    if flags.get("retrieval_profile_present") and flags.get("pre_ai_status_present") and flags.get("batch_decision_present"):
        lines.append("- Current phase runtime signals are visible in production artifacts: retrieval profile, deterministic gating, and batch health are present.")
    else:
        lines.append("- Current phase logic is not fully observable from production artifacts yet.")

    if analysis.get("accepted_total", 0) == 0:
        lines.append("- The current run has not produced any ACCEPTED records yet, so business-value output is still weak even though gating is running.")
    if analysis.get("completion_reason") == "NO_ELIGIBLE_RECORDS":
        lines.append("- The run ended gracefully with zero eligible records after pre-AI gating, which matches the intended strict-mode behavior.")
    if analysis.get("failure_mode") == "post_run_labeling_failed_on_zero_eligible_records":
        lines.append("- The final FAILED state is misleading: the retrieval pipeline completed, but post-run auto-labeling treated zero eligible records as an exception instead of a graceful no-op.")
    if analysis.get("answer_status") == "ANSWER_READY":
        lines.append("- The run reached an answer-ready terminal state, which means Phase 9 answer closeout worked end-to-end.")
    elif analysis.get("accepted_total", 0) > 0 and analysis.get("theme_count", 0) == 0:
        lines.append("- The run found accepted evidence, but answer delivery is still incomplete because no themes were persisted.")
    if analysis.get("running_steps"):
        lines.append("- The run is still in progress, so this report is interim until final completion.")

    planner_analysis_meta = analysis.get("planner_analysis_meta") or {}
    plan_generation_meta = analysis.get("plan_generation_meta") or {}
    if planner_analysis_meta or plan_generation_meta:
        lines.extend(["", "## Planner Resilience"])
        if planner_analysis_meta:
            lines.append(f"- Context planning meta: `{json.dumps(planner_analysis_meta, ensure_ascii=False)}`")
        if plan_generation_meta:
            lines.append(f"- Plan generation meta: `{json.dumps(plan_generation_meta, ensure_ascii=False)}`")

    if analysis.get("timeout_salvage_steps"):
        lines.extend(["", "## Timeout Salvage"])
        for salvage in analysis.get("timeout_salvage_steps", []):
            lines.append(
                f"- `{salvage['step_id']}` `{salvage['action_type']}` collected=`{salvage.get('collected_count')}` "
                f"persisted=`{salvage.get('persisted_count')}` lost_before_persist=`{salvage.get('lost_before_persist_count')}` "
                f"image_candidates=`{salvage.get('image_candidate_count')}`"
            )
            for sample in salvage.get("sample_candidates") or []:
                lines.append(f"  sample=`{json.dumps(sample, ensure_ascii=False)}`")

    lines.extend(["", "## Efficiency Concerns"])
    for concern in analysis.get("concerns", []):
        lines.append(f"- {concern}")

    if analysis.get("reason_clusters") or analysis.get("reformulated_queries"):
        lines.extend(["", "## Reformulation Signals"])
        if analysis.get("reason_clusters"):
            lines.append(f"- Reason clusters: `{json.dumps(analysis.get('reason_clusters') or {}, ensure_ascii=False)}`")
        for query in analysis.get("reformulated_queries") or []:
            lines.append(f"- Reformulated query: `{query}`")

    lines.extend(["", "## Recommended Fixes"])
    for recommendation in analysis.get("recommendations", []):
        lines.append(f"- {recommendation}")

    lines.extend(["", "## Next Phase Exploration"])
    for option in analysis.get("next_phase_options", []):
        lines.append(f"- {option}")

    lines.extend(["", "## Top Records Snapshot"])
    for record in analysis.get("top_records", []):
        lines.append(
            f"- `{record.get('post_id')}` status=`{record.get('judge_decision') or record.get('pre_ai_status')}` "
            f"score=`{record.get('pre_ai_score')}` confidence=`{record.get('judge_confidence_score')}` "
            f"query_family=`{record.get('query_family')}` source_type=`{record.get('source_type')}` "
            f"image_used=`{record.get('judge_used_image_understanding')}`"
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_status(snapshot: dict, analysis: dict, output_dir: Path) -> None:
    status_path = output_dir / "status.md"
    run = snapshot.get("run") or {}
    lines = [
        f"# Live Status For {run.get('run_id', 'unknown-run')}",
        "",
        f"- Last updated (UTC): {utc_now().isoformat()}",
        f"- Run status: `{analysis.get('run_status')}`",
        f"- Completion reason: `{analysis.get('completion_reason')}`",
        f"- Failure class: `{analysis.get('failure_class')}`",
        f"- Answer status: `{analysis.get('answer_status')}`",
        f"- Total records: `{analysis.get('total_records')}`",
        f"- ACCEPTED / UNCERTAIN / REJECTED: `{analysis.get('accepted_total')}` / `{analysis.get('uncertain_total')}` / `{analysis.get('rejected_total')}`",
        f"- Batch decisions: `{json.dumps(analysis.get('batch_decisions') or {}, ensure_ascii=False)}`",
        f"- Theme count: `{analysis.get('theme_count')}`",
        f"- Image fallback count: `{analysis.get('image_fallback_total')}`",
        f"- Planner metadata present: `{(analysis.get('phase_flags') or {}).get('planner_meta_present')}`",
        f"- Timeout salvage observed: `{(analysis.get('phase_flags') or {}).get('timeout_salvage_observed')}`",
        "",
        "## Running Steps",
    ]
    running_steps = analysis.get("running_steps") or []
    if running_steps:
        for step in running_steps:
            lines.append(f"- `{step['step_id']}` `{step['action_type']}` since {step.get('started_at')}")
    else:
        lines.append("- None")
    salvage_steps = analysis.get("timeout_salvage_steps") or []
    if salvage_steps:
        lines.extend(["", "## Timeout Salvage"])
        for step in salvage_steps:
            lines.append(
                f"- `{step['step_id']}` `{step['action_type']}` collected=`{step.get('collected_count')}` "
                f"persisted=`{step.get('persisted_count')}` lost_before_persist=`{step.get('lost_before_persist_count')}`"
            )
    status_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor a production run on the ChiaseGPU VM.")
    parser.add_argument("run_id")
    parser.add_argument("--ssh-target", default="chiasegpu-vm")
    parser.add_argument("--container", default="social-listening-v3")
    parser.add_argument("--interval-sec", type=int, default=300)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-polls", type=int, default=0)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    snapshots_dir = output_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    state_path = output_dir / "state.json"
    full_log_path = output_dir / "full.log"
    monitor_log_path = output_dir / "monitor.log"
    latest_snapshot_path = output_dir / "latest_snapshot.json"
    latest_analysis_path = output_dir / "latest_analysis.json"

    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))

    poll_count = 0
    while True:
        poll_started_at = utc_now()
        try:
            snapshot = fetch_snapshot(args.ssh_target, args.container, args.run_id)
            if not snapshot.get("run"):
                raise RuntimeError(f"Run {args.run_id} was not found on production.")

            run_started = datetime.fromisoformat(snapshot["run"]["started_at"])
            if run_started.tzinfo is None:
                run_started = run_started.replace(tzinfo=UTC)

            since_iso = state.get("last_log_since") or (run_started - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
            log_chunk = remote_docker_logs(args.ssh_target, args.container, since_iso)
            if log_chunk:
                append_text(full_log_path, f"\n\n===== poll {poll_started_at.isoformat()} =====\n")
                append_text(full_log_path, log_chunk)

            analysis = summarize_run(snapshot)

            snapshot_name = poll_started_at.strftime("%Y%m%dT%H%M%SZ")
            write_json(snapshots_dir / f"{snapshot_name}.json", snapshot)
            write_json(latest_snapshot_path, snapshot)
            write_json(latest_analysis_path, analysis)
            update_status(snapshot, analysis, output_dir)
            render_report(snapshot, analysis, output_dir)

            state = {
                "run_id": args.run_id,
                "last_polled_at": poll_started_at.isoformat(),
                "last_log_since": poll_started_at.isoformat().replace("+00:00", "Z"),
                "run_status": analysis.get("run_status"),
            }
            write_json(state_path, state)
            poll_count += 1

            append_text(
                monitor_log_path,
                f"[{poll_started_at.isoformat()}] status={analysis.get('run_status')} "
                f"records={analysis.get('total_records')} accepted={analysis.get('accepted_total')} "
                f"uncertain={analysis.get('uncertain_total')} rejected={analysis.get('rejected_total')}\n",
            )

            if (analysis.get("run_status") or "").upper() in TERMINAL_STATUSES:
                append_text(monitor_log_path, f"[{utc_now().isoformat()}] terminal status reached, monitor exiting\n")
                return 0
            if args.max_polls and poll_count >= args.max_polls:
                append_text(monitor_log_path, f"[{utc_now().isoformat()}] max polls reached, monitor exiting\n")
                return 0
        except Exception as exc:  # noqa: BLE001
            append_text(monitor_log_path, f"[{poll_started_at.isoformat()}] ERROR {exc}\n")

        time.sleep(max(30, args.interval_sec))


if __name__ == "__main__":
    sys.exit(main())
