#!/usr/bin/env python3
"""
Post checkpoint status to the dashboard API.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"


def load_config() -> dict:
    config = {"dashboard_url": "http://localhost:3000", "project_slug": ""}
    if CONFIG_FILE.exists():
        config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    if os.environ.get("DASHBOARD_URL"):
        config["dashboard_url"] = os.environ["DASHBOARD_URL"]
    if os.environ.get("PROJECT_SLUG"):
        config["project_slug"] = os.environ["PROJECT_SLUG"]
    return config


def build_payload(data: dict) -> dict:
    role = data.get("role", "implementer")
    normalized_issues = []
    for issue in data.get("issues", []):
        if isinstance(issue, str):
            normalized_issues.append({"severity": "warning", "description": issue})
        elif isinstance(issue, dict):
            normalized_issues.append(
                {
                    "severity": issue.get("severity", "warning") if issue.get("severity") in {"blocker", "warning"} else "warning",
                    "description": issue.get("description") or issue.get("message") or issue.get("type") or "",
                }
            )
    payload = {
        "role": role,
        "status": data.get("status", "READY" if role == "implementer" else "PASS"),
        "summary": data.get("summary", ""),
        "issues": normalized_issues,
    }
    if role == "implementer":
        payload["readyForNextTrigger"] = False
        payload["artifacts"] = data.get("artifacts", [])
        if data.get("notes"):
            payload["notes"] = data["notes"]
    else:
        payload["readyForNextTrigger"] = bool(data.get("ready_for_next_cp", data.get("status") in {"PASS", "PARTIAL"}))
        payload["checks"] = data.get("checks", [])
        if data.get("next_cp"):
            payload["nextCp"] = data["next_cp"]
            payload["nextActionMessage"] = f"Trigger {data['next_cp']} implementation."
    return payload


def post_status(result_file: str, dashboard_url: str, project_slug: str) -> bool:
    path = Path(result_file)
    if not path.exists():
        print(f"✗ File not found: {result_file}", file=sys.stderr)
        return False
    if not project_slug:
        print("✗ project_slug not configured", file=sys.stderr)
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    cp_code = data.get("cp", path.parent.name)
    payload = build_payload(data)
    url = f"{dashboard_url.rstrip('/')}/api/projects/{project_slug}/checkpoints/{cp_code}/status"
    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read())
        return bool(result.get("ok"))
    except urllib.error.URLError as exc:
        print(f"⚠ Dashboard unreachable ({exc.reason}) — bo qua, tiep tuc binh thuong")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Post checkpoint status to dashboard API")
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--dashboard-url", default="")
    parser.add_argument("--project-slug", default="")
    args = parser.parse_args()

    config = load_config()
    dashboard_url = args.dashboard_url or config["dashboard_url"]
    project_slug = args.project_slug or config["project_slug"]
    ok = post_status(args.result_file, dashboard_url, project_slug)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
