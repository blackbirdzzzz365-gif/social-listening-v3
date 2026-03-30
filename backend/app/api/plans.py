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
    SessionCreateRequest,
    SessionResponse,
)

router = APIRouter(prefix="/api", tags=["plans"])
SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"


def _load_skill(filename: str) -> str:
    template = (SKILLS_DIR / filename).read_text(encoding="utf-8")
    if filename in {"plan_generation.md", "plan_refinement.md"}:
        return f"{template}\n\n{render_action_registry_for_prompt()}"
    return template


async def _enrich_with_explanations(payload: dict, http_request: Request) -> dict:
    explanations = await http_request.app.state.planner_service.explain_steps(
        payload, _load_skill("step_explain.md")
    )
    for step in payload.get("steps", []):
        step["explain"] = explanations.get(step["step_id"], "")
    return payload


def _to_session_response(result) -> SessionResponse:
    return SessionResponse(
        context_id=result.context_id,
        topic=result.topic,
        status=result.status,
        clarifying_questions=result.clarifying_questions,
        keywords=result.keywords,
        retrieval_profile=result.retrieval_profile,
        clarification_history=result.clarification_history,
    )


@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest, http_request: Request) -> SessionResponse:
    try:
        result = await http_request.app.state.planner_service.analyze_topic(
            request.topic,
            _load_skill("keyword_analysis.md"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _to_session_response(result)


@router.get("/sessions/{context_id}", response_model=SessionResponse)
async def get_session(context_id: str, http_request: Request) -> SessionResponse:
    try:
        result = await http_request.app.state.planner_service.get_context_result(
            context_id,
            _load_skill("keyword_analysis.md"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_session_response(result)


@router.post("/sessions/{context_id}/clarifications", response_model=SessionResponse)
async def submit_clarifications(
    context_id: str,
    request: ClarificationAnswerRequest,
    http_request: Request,
) -> SessionResponse:
    try:
        result = await http_request.app.state.planner_service.submit_clarifications(
            context_id,
            request.answers,
            _load_skill("keyword_analysis.md"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_session_response(result)


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

    return _to_session_response(result)


@router.post("/plans", response_model=PlanResponse)
async def create_plan(request: PlanCreateRequest, http_request: Request) -> PlanResponse:
    try:
        payload = await http_request.app.state.planner_service.generate_plan(
            request.context_id,
            _load_skill("plan_generation.md"),
        )
        payload = await _enrich_with_explanations(payload, http_request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlanResponse(**payload)


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def refine_plan(plan_id: str, request: PlanRefineRequest, http_request: Request) -> PlanResponse:
    try:
        payload = await http_request.app.state.planner_service.refine_plan(
            plan_id,
            request.instruction,
            _load_skill("plan_refinement.md"),
        )
        payload = await _enrich_with_explanations(payload, http_request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlanResponse(**payload)


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str, http_request: Request) -> PlanResponse:
    try:
        payload = await http_request.app.state.planner_service.get_plan(plan_id)
        payload = await _enrich_with_explanations(payload, http_request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
