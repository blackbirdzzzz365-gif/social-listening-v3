#!/usr/bin/env python3
"""
Checkpoint notification script.
Sends status to ntfy.sh after each CP implementation or validation.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"


def load_config() -> dict:
    config = {"ntfy_topic": "", "ntfy_base": "https://ntfy.sh"}
    if CONFIG_FILE.exists():
        config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    if os.environ.get("NTFY_TOPIC"):
        config["ntfy_topic"] = os.environ["NTFY_TOPIC"]
    if os.environ.get("NTFY_BASE"):
        config["ntfy_base"] = os.environ["NTFY_BASE"]
    return config


STATUS_EMOJI = {
    "READY": "✅",
    "BLOCKED": "🚫",
    "PASS": "✅",
    "FAIL": "❌",
    "PARTIAL": "⚠️",
}

STATUS_PRIORITY = {
    "READY": "default",
    "BLOCKED": "high",
    "PASS": "default",
    "FAIL": "high",
    "PARTIAL": "default",
}


def send_ntfy(topic: str, base_url: str, title: str, message: str, priority: str, tags: str) -> bool:
    url = f"{base_url.rstrip('/')}/{topic}"
    headers = {
        "Title": title.encode("utf-8"),
        "Priority": priority,
        "Content-Type": "text/plain; charset=utf-8",
    }
    if tags:
        headers["Tags"] = tags
    try:
        request = urllib.request.Request(
            url,
            data=message.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status == 200
    except urllib.error.URLError as exc:
        print(f"  ✗ Failed to send to ntfy.sh: {exc}", file=sys.stderr)
        return False


def notify(cp: str, role: str, status: str, summary: str, result_file: str, config: dict) -> None:
    if not config.get("ntfy_topic"):
        print(
            "\nERROR: ntfy_topic not configured.\n"
            "  Option 1: Set NTFY_TOPIC env var\n"
            "  Option 2: Edit checkpoints/config.json\n",
            file=sys.stderr,
        )
        sys.exit(1)

    emoji = STATUS_EMOJI.get(status, "ℹ️")
    role_label = "impl" if role == "implementer" else "validator"
    title = f"[SLv3] {cp} | {role_label} | {status} {emoji}"
    tags_map = {
        ("implementer", "READY"): "white_check_mark,computer",
        ("implementer", "BLOCKED"): "no_entry,computer",
        ("validator", "PASS"): "white_check_mark,test_tube",
        ("validator", "FAIL"): "x,test_tube",
        ("validator", "PARTIAL"): "warning,test_tube",
    }
    tags = tags_map.get((role, status), "information_source")
    message = "\n".join(
        [
            summary,
            "",
            f"CP:          {cp}",
            f"Role:        {role_label}",
            f"Status:      {status} {emoji}",
            f"Result file: {result_file}",
            f"Time:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Dashboard: https://ntfy.sh/{config['ntfy_topic']}",
        ]
    )
    ok = send_ntfy(
        topic=config["ntfy_topic"],
        base_url=config["ntfy_base"],
        title=title,
        message=message,
        priority=STATUS_PRIORITY.get(status, "default"),
        tags=tags,
    )
    if not ok:
        print("  ✗ Failed — check network or topic name", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send checkpoint notification to ntfy.sh")
    parser.add_argument("--cp", required=True)
    parser.add_argument("--role", required=True, choices=["implementer", "validator"])
    parser.add_argument("--status", required=True, choices=["READY", "BLOCKED", "PASS", "FAIL", "PARTIAL"])
    parser.add_argument("--summary", required=True)
    parser.add_argument("--result-file", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config()
    cp_dir = SCRIPT_DIR / args.cp
    if not cp_dir.exists():
        print(f"ERROR: CP directory not found: {cp_dir}", file=sys.stderr)
        sys.exit(1)

    result_file = args.result_file or str(cp_dir / ("result.json" if args.role == "implementer" else "validation.json"))
    if args.dry_run:
        print(f"[DRY RUN] {args.cp} {args.role} {args.status} -> {result_file}")
        return

    notify(
        cp=args.cp,
        role=args.role,
        status=args.status,
        summary=args.summary,
        result_file=result_file,
        config=config,
    )


if __name__ == "__main__":
    main()
