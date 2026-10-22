"""Command line: status, export, linkedin queue, doctor."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .config import ConfigError, load_config
from .outreach.linkedin_queue import LinkedInQueue
from .tracker import Tracker


def _load(args):
    return load_config(args.config)


def _cmd_status(args) -> int:
    cfg = _load(args)
    tracker = Tracker(cfg.tracker_path)
    counts = {}
    for row in tracker.all():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print(json.dumps(counts, indent=2) if counts else "tracker is empty")
    return 0


def _cmd_export(args) -> int:
    cfg = _load(args)
    tracker = Tracker(cfg.tracker_path)
    n = tracker.export_csv(args.out)
    print(f"exported {n} rows to {args.out}")
    return 0


def _cmd_linkedin(args) -> int:
    cfg = _load(args)
    queue = LinkedInQueue(cfg.linkedin_queue_path)
    if args.linkedin_cmd == "list":
        items = queue.list(status=args.status)
        if not items:
            print("queue is empty")
        for item in items:
            print(f"[{item['status']}] {item['id']} {item['person']}: {item['note']}")
        return 0
    if args.linkedin_cmd == "approve":
        ok = queue.approve(args.id)
        print("approved" if ok else "no such draft")
        return 0 if ok else 1
    if args.linkedin_cmd == "done":
        ok = queue.mark_done(args.id)
        print("marked done" if ok else "no such approved draft")
        return 0 if ok else 1
    return 2


def _cmd_doctor(args) -> int:
    from .config import get_api_key
    from .reach.agent_reach import AgentReachSource
    cfg = _load(args)
    ok = True
    try:
        get_api_key(cfg.provider)
        print(f"LLM key ({cfg.provider}): set")
    except ConfigError as exc:
        print(f"LLM key ({cfg.provider}): MISSING - {exc}")
        ok = False
    if AgentReachSource.available():
        print("agent-reach CLI: found")
    else:
        print("agent-reach CLI: not installed (optional)")
    if os.path.exists(cfg.resume_path):
        print("resume file: found")
    else:
        print(f"resume file: MISSING ({cfg.resume_path})")
        ok = False
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="jobhunter")
    parser.add_argument("--config", default=None, help="path to config JSON")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    exp = sub.add_parser("export")
    exp.add_argument("--out", default="tracker.csv")
    sub.add_parser("doctor")
    li = sub.add_parser("linkedin")
    li_sub = li.add_subparsers(dest="linkedin_cmd", required=True)
    li_sub.add_parser("list").add_argument("--status", default=None)
    li_sub.add_parser("approve").add_argument("id")
    li_sub.add_parser("done").add_argument("id")
    args = parser.parse_args(argv)
    if args.cmd == "status":
        return _cmd_status(args)
    if args.cmd == "export":
        return _cmd_export(args)
    if args.cmd == "doctor":
        return _cmd_doctor(args)
    if args.cmd == "linkedin":
        return _cmd_linkedin(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
