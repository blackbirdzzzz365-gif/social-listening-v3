#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MONITOR_SCRIPT = REPO_ROOT / "scripts" / "monitor_production_run.py"


def request(method: str, url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "social-listening-v3-phase11-case-pack/1.0",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def answer_for_question(question: str, case: dict) -> str:
    normalized = question.lower()
    focus = case.get("focus") or case["topic"]
    timeframe = case.get("timeframe") or "Tap trung 6 thang gan nhat."
    audience = case.get("audience") or f"Tap trung vao feedback that lien quan den {focus} tai Viet Nam."
    comparison_policy = case.get("comparison_policy") or (
        f"Ghi nhan so sanh lien quan den {focus}, nhung uu tien feedback that ve {focus}."
    )
    vision_policy = case.get("vision_policy") or (
        f"Uu tien bai co hinh anh, screenshot, hoac bang chung truc quan lien quan den {focus}."
    )
    default_answer = case.get("default_answer") or audience

    if any(token in normalized for token in ("thoi gian", "thời gian", "6 thang", "6 tháng", "gan nhat")):
        return timeframe
    if any(token in normalized for token in ("so sanh", "so sánh", "doi thu", "đối thủ", "ngan hang khac", "thuong hieu khac")):
        return comparison_policy
    if any(token in normalized for token in ("khach hang", "khách hàng", "nguoi dung", "người dùng", "doi tuong", "đối tượng")):
        return audience
    if any(token in normalized for token in ("san pham", "sản phẩm", "thuong hieu", "thương hiệu", "brand")):
        return f"Tap trung vao {focus}."
    if any(token in normalized for token in ("hinh anh", "hình ảnh", "anh", "ảnh", "ocr", "image", "vision")):
        return vision_policy
    return default_answer


def ensure_keywords_ready(base_url: str, session: dict, case: dict) -> dict:
    current = session
    for _ in range(3):
        if current.get("status") == "keywords_ready":
            return current

        questions = current.get("clarifying_questions") or []
        if current.get("status") != "clarification_required" or not questions:
            raise RuntimeError(f"Unexpected session status: {current.get('status')}")

        answers = [answer_for_question(question, case) for question in questions]
        current = request(
            "POST",
            f"{base_url}/api/sessions/{current['context_id']}/clarifications",
            {"answers": answers},
        )

    raise RuntimeError("Keyword clarification did not converge to keywords_ready")


def resolve_defaults(case_pack: dict, cli_args: argparse.Namespace) -> dict:
    defaults = dict(case_pack.get("defaults") or {})
    if cli_args.base_url:
        defaults["base_url"] = cli_args.base_url
    if cli_args.ssh_target:
        defaults["ssh_target"] = cli_args.ssh_target
    if cli_args.container:
        defaults["container"] = cli_args.container
    if cli_args.interval_sec:
        defaults["interval_sec"] = cli_args.interval_sec
    if cli_args.report_root:
        defaults["report_root"] = cli_args.report_root
    return defaults


def selected_cases(case_pack: dict, only_cases: list[str]) -> list[dict]:
    cases = case_pack.get("cases") or []
    if not only_cases:
        return cases
    indexed = {case.get("id"): case for case in cases}
    missing = [case_id for case_id in only_cases if case_id not in indexed]
    if missing:
        raise SystemExit(f"Unknown case id(s): {', '.join(missing)}")
    return [indexed[case_id] for case_id in only_cases]


def limited_cases(cases: list[dict], limit: int | None) -> list[dict]:
    if not limit:
        return cases
    if limit < 1:
        raise SystemExit("--limit must be >= 1")
    return cases[:limit]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_live_case(case: dict, defaults: dict, dry_run: bool) -> dict:
    base_url = (case.get("base_url") or defaults["base_url"]).rstrip("/")
    ssh_target = case.get("ssh_target") or defaults["ssh_target"]
    container = case.get("container") or defaults["container"]
    interval_sec = int(case.get("interval_sec") or defaults.get("interval_sec") or 120)
    report_root = REPO_ROOT / (case.get("report_root") or defaults.get("report_root") or "reports/production")

    if dry_run:
        return {
            "case_id": case["id"],
            "mode": case["mode"],
            "topic": case["topic"],
            "base_url": base_url,
            "ssh_target": ssh_target,
            "container": container,
            "report_root": str(report_root),
            "dry_run": True,
        }

    browser_status = request("GET", f"{base_url}/api/browser/status")
    if browser_status.get("session_status") != "VALID":
        raise RuntimeError(
            f"Browser session is not valid for case {case['id']}. Current session_status={browser_status.get('session_status')}"
        )

    session = request("POST", f"{base_url}/api/sessions", {"topic": case["topic"]})
    session = ensure_keywords_ready(base_url, session, case)
    plan = request("POST", f"{base_url}/api/plans", {"context_id": session["context_id"]})

    approval_mode = case.get("approval_mode") or defaults.get("approval_mode") or "read-only"
    if approval_mode == "all":
        approved_steps = [step["step_id"] for step in plan.get("steps") or []]
    else:
        approved_steps = [step["step_id"] for step in plan.get("steps") or [] if step.get("read_or_write") == "READ"]

    grant = request(
        "POST",
        f"{base_url}/api/plans/{plan['plan_id']}/approve",
        {"step_ids": approved_steps},
    )
    run = request("POST", f"{base_url}/api/runs", {"plan_id": plan["plan_id"], "grant_id": grant["grant_id"]})

    run_id = run["run_id"]
    output_dir = report_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        output_dir / "case.json",
        {
            "case_id": case["id"],
            "pack_id": case.get("pack_id"),
            "topic": case["topic"],
            "phase": case.get("phase"),
            "expectation": case.get("expectation"),
            "success_signals": case.get("success_signals") or [],
            "started_at": utc_now(),
        },
    )
    write_json(
        output_dir / "bootstrap.json",
        {
            "case_id": case["id"],
            "topic": case["topic"],
            "session": session,
            "plan": plan,
            "grant": grant,
            "run": run,
        },
    )

    subprocess.run(
        [
            sys.executable,
            str(MONITOR_SCRIPT),
            run_id,
            "--ssh-target",
            ssh_target,
            "--container",
            container,
            "--interval-sec",
            str(interval_sec),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    return {
        "case_id": case["id"],
        "mode": case["mode"],
        "topic": case["topic"],
        "run_id": run_id,
        "output_dir": str(output_dir),
        "final_report": str(output_dir / "final_report.md"),
        "latest_analysis": str(output_dir / "latest_analysis.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and monitor a production case pack for social-listening-v3.")
    parser.add_argument("case_pack", help="Path to the case pack JSON file.")
    parser.add_argument("--case", action="append", default=[], help="Run only the specified case id. Repeatable.")
    parser.add_argument("--base-url")
    parser.add_argument("--ssh-target")
    parser.add_argument("--container")
    parser.add_argument("--report-root")
    parser.add_argument("--interval-sec", type=int)
    parser.add_argument("--limit", type=int, help="Run only the first N selected cases.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    case_pack_path = Path(args.case_pack).expanduser().resolve()
    case_pack = json.loads(case_pack_path.read_text(encoding="utf-8"))
    defaults = resolve_defaults(case_pack, args)

    cases = limited_cases(selected_cases(case_pack, args.case), args.limit)
    if not cases:
        raise SystemExit("No cases selected from case pack.")

    pack_id = case_pack.get("pack_id") or case_pack_path.stem
    run_index: dict[str, object] = {
        "pack_id": pack_id,
        "started_at": utc_now(),
        "case_pack": str(case_pack_path),
        "selected_case_ids": [case["id"] for case in cases],
        "cases": [],
    }

    for case in cases:
        if case.get("mode") != "live_api_flow":
            raise RuntimeError(f"Unsupported case mode: {case.get('mode')}")
        case = dict(case)
        case["pack_id"] = pack_id
        result = run_live_case(case, defaults, args.dry_run)
        run_index["cases"].append(result)
        time.sleep(2)

    run_index["finished_at"] = utc_now()
    if not args.dry_run:
        report_root = REPO_ROOT / (defaults.get("report_root") or "reports/production")
        index_path = report_root / "case-packs" / f"{pack_id}-latest.json"
        write_json(index_path, run_index)
    print(json.dumps(run_index, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
