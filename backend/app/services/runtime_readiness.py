from __future__ import annotations

from typing import Any

from app.services.health_monitor import BrowserRuntimeState


def build_runtime_readiness_payload(state: BrowserRuntimeState) -> dict[str, Any]:
    summary = _build_summary(state)
    next_steps = _build_next_steps(state)
    return {
        "runnable": state.runnable,
        "session_status": state.session_status,
        "health_status": state.health_status,
        "action_required": state.action_required,
        "block_reason": state.block_reason,
        "last_checked": state.last_checked,
        "summary": summary,
        "next_steps": next_steps,
    }


def build_runtime_block_message(state: BrowserRuntimeState, *, stage: str) -> str:
    payload = build_runtime_readiness_payload(state)
    stage_label = _stage_label(stage)
    guidance = payload["next_steps"][0] if payload["next_steps"] else "Restore browser runtime and retry."
    return f"{payload['summary']} {guidance} Blocked before {stage_label}."


def _build_summary(state: BrowserRuntimeState) -> str:
    if state.runnable:
        return "Browser runtime is ready. Research kickoff can continue."
    if state.session_status == "NOT_SETUP":
        return "Browser runtime is not ready. Facebook session has not been connected yet."
    if state.session_status == "EXPIRED":
        return "Browser runtime is not ready. Facebook session has expired."
    if state.health_status == "BLOCKED":
        return "Browser runtime is not ready. The account is currently blocked or cooling down."
    if state.health_status == "CAUTION":
        return "Browser runtime is not ready. Account health requires operator attention first."
    return "Browser runtime is not ready. Research cannot start yet."


def _build_next_steps(state: BrowserRuntimeState) -> list[str]:
    if state.runnable:
        return ["Proceed with topic analysis or plan generation."]
    if state.action_required == "CONNECT_FACEBOOK":
        return [
            "Open Browser Setup and connect the Facebook session first.",
            "Wait until browser status shows session_status=VALID and runnable=true.",
        ]
    if state.action_required == "REAUTH_REQUIRED":
        return [
            "Open Browser Setup and log back into Facebook on the production browser profile.",
            "Retry research only after browser status returns session_status=VALID and runnable=true.",
        ]
    if state.action_required == "WAIT_COOLDOWN":
        return [
            "Wait for cooldown to expire before retrying the browser runtime.",
            "Re-check browser status after cooldown_until.",
        ]
    return ["Resolve browser runtime issues, then retry the research flow."]


def _stage_label(stage: str) -> str:
    labels = {
        "topic_analysis": "topic analysis",
        "clarification_submit": "clarification submission",
        "plan_generation": "plan generation",
        "plan_refinement": "plan refinement",
    }
    return labels.get(stage, stage.replace("_", " "))
