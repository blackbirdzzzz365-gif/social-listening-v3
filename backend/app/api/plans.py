from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.domain.action_registry import render_action_registry_for_prompt
from app.schemas.plans import (
    ApprovalGrantResponse,
    ApprovalRequest,
    ClarificationAnswerRequest,
    KeywordUpdateRequest,
    PlanCreateRequest,
    PlanRefineRequest,
    PlanResponse,
    RuntimeReadinessSummary,
    SessionCreateRequest,
    SessionResponse,
)
from app.services.planner import PlannerProviderUnavailableError
from app.services.runtime_readiness import (
    build_runtime_block_message,
    build_runtime_readiness_payload,
)

router = APIRouter(prefix="/api", tags=["plans"])
SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"


def _load_skill(filename: str) -> str:
    template = (SKILLS_DIR / filename).read_text(encoding="utf-8")
    if filename in {"plan_generation.md", "plan_refinement.md"}:
        return f"{template}\n\n{render_action_registry_for_prompt()}"
    return template


async def _enrich_with_explanations(payload: dict, http_request: Request) -> dict:
    try:
        explanations = await http_request.app.state.planner_service.explain_steps(
            payload, _load_skill("step_explain.md")
        )
    except PlannerProviderUnavailableError:
        payload.setdefault("warnings", []).append(
            "Step explanations are temporarily unavailable due to planner provider instability."
        )
        return payload

    for step in payload.get("steps", []):
        step["explain"] = explanations.get(step["step_id"], "")
    return payload


def _runtime_readiness(http_request: Request) -> RuntimeReadinessSummary | None:
    health_monitor = getattr(http_request.app.state, "health_monitor", None)
    if health_monitor is None:
        return None
    state = health_monitor.get_browser_runtime_state()
    return RuntimeReadinessSummary(**build_runtime_readiness_payload(state))


def _require_runtime_ready(http_request: Request, *, stage: str) -> RuntimeReadinessSummary | None:
    health_monitor = getattr(http_request.app.state, "health_monitor", None)
    if health_monitor is None:
        return None
    state = health_monitor.get_browser_runtime_state()
    if not state.runnable:
        raise HTTPException(status_code=409, detail=build_runtime_block_message(state, stage=stage))
    return RuntimeReadinessSummary(**build_runtime_readiness_payload(state))


def _to_session_response(result, runtime_readiness: RuntimeReadinessSummary | None = None) -> SessionResponse:
    return SessionResponse(
        context_id=result.context_id,
        topic=result.topic,
        status=result.status,
        clarifying_questions=result.clarifying_questions,
        keywords=result.keywords,
        retrieval_profile=result.retrieval_profile,
        validity_spec=result.validity_spec,
        clarification_history=result.clarification_history,
        planning_meta=result.planning_meta,
        runtime_readiness=runtime_readiness,
    )


@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest, http_request: Request) -> SessionResponse:
    runtime_readiness = _require_runtime_ready(http_request, stage="topic_analysis")
    try:
        result = await http_request.app.state.planner_service.analyze_topic(
            request.topic,
            _load_skill("keyword_analysis.md"),
        )
    except PlannerProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_session_response(result, runtime_readiness=runtime_readiness)


@router.get("/sessions/{context_id}", response_model=SessionResponse)
async def get_session(context_id: str, http_request: Request) -> SessionResponse:
    try:
        result = await http_request.app.state.planner_service.get_context_result(
            context_id,
            _load_skill("keyword_analysis.md"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PlannerProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _to_session_response(result, runtime_readiness=_runtime_readiness(http_request))


@router.post("/sessions/{context_id}/clarifications", response_model=SessionResponse)
async def submit_clarifications(
    context_id: str,
    request: ClarificationAnswerRequest,
    http_request: Request,
) -> SessionResponse:
    runtime_readiness = _require_runtime_ready(http_request, stage="clarification_submit")
    try:
        result = await http_request.app.state.planner_service.submit_clarifications(
            context_id,
            request.answers,
            _load_skill("keyword_analysis.md"),
        )
    except PlannerProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_session_response(result, runtime_readiness=runtime_readiness)


@router.patch("/sessions/{context_id}/keywords", response_model=SessionResponse)
async def update_keywords(
    context_id: str,
    request: KeywordUpdateRequest,
    http_request: Request,
) -> SessionResponse:
    try:
        result = await http_request.app.state.planner_service.update_keywords(
            context_id,
            request.keywords.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _to_session_response(result, runtime_readiness=_runtime_readiness(http_request))


@router.post("/plans", response_model=PlanResponse)
async def create_plan(request: PlanCreateRequest, http_request: Request) -> PlanResponse:
    runtime_readiness = _require_runtime_ready(http_request, stage="plan_generation")
    try:
        payload = await http_request.app.state.planner_service.generate_plan(
            request.context_id,
            _load_skill("plan_generation.md"),
        )
        payload = await _enrich_with_explanations(payload, http_request)
    except PlannerProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload["runtime_readiness"] = None if runtime_readiness is None else runtime_readiness.model_dump()
    return PlanResponse(**payload)


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def refine_plan(plan_id: str, request: PlanRefineRequest, http_request: Request) -> PlanResponse:
    runtime_readiness = _require_runtime_ready(http_request, stage="plan_refinement")
    try:
        payload = await http_request.app.state.planner_service.refine_plan(
            plan_id,
            request.instruction,
            _load_skill("plan_refinement.md"),
        )
        payload = await _enrich_with_explanations(payload, http_request)
    except PlannerProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload["runtime_readiness"] = None if runtime_readiness is None else runtime_readiness.model_dump()
    return PlanResponse(**payload)


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str, http_request: Request) -> PlanResponse:
    try:
        payload = await http_request.app.state.planner_service.get_plan(plan_id)
        payload = await _enrich_with_explanations(payload, http_request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    runtime_readiness = _runtime_readiness(http_request)
    payload["runtime_readiness"] = None if runtime_readiness is None else runtime_readiness.model_dump()
    return PlanResponse(**payload)


@router.post("/plans/{plan_id}/approve", response_model=ApprovalGrantResponse)
async def approve_plan(
    plan_id: str,
    request: ApprovalRequest,
    http_request: Request,
) -> ApprovalGrantResponse:
    try:
        grant = await http_request.app.state.approval_service.issue_grant(plan_id, request.step_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ApprovalGrantResponse(
        grant_id=grant.grant_id,
        approved_step_ids=json.loads(grant.approved_step_ids),
        plan_version=grant.plan_version,
        approver_id=grant.approver_id,
        approved_at=grant.approved_at,
    )
