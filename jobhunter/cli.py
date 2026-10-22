"""Command line: scan, replies, status, export, linkedin, channel, doctor."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .channels.ops import apply_decision, channel_notifier
from .config import ConfigError, load_config
from .outreach.linkedin_queue import LinkedInQueue
from .pipeline import Pipeline
from .tracker import Tracker


def build_provider(cfg):
    """LLM provider from config. Separate so tests can patch it."""
    from .llm.providers import get_provider
    return get_provider(cfg.provider, cfg.resolved_model())


def build_mail(cfg):
    """Mail client from config. Separate so tests can patch it."""
    from .outreach.gmail_client import GmailAPIClient
    return GmailAPIClient()


def build_channel(cfg):
    """Telegram channel from the environment. Separate so tests can patch it."""
    from .channels.telegram import TelegramChannel
    return TelegramChannel(state_path=cfg.channel_state_path)


def _build_sources(cfg):
    from .reach.agent_reach import AgentReachSource
    from .reach.rss import RSSSource
    sources = [RSSSource(feed) for feed in cfg.rss_feeds]
    for query in cfg.agent_reach_queries:
        if AgentReachSource.available():
            sources.append(AgentReachSource(query=query))
        else:
            print("agent-reach CLI not installed; skipping its queries")
    return sources


def _load(args):
    return load_config(args.config)


def _cmd_scan(args) -> int:
    cfg = _load(args)
    sources = _build_sources(cfg)
    if not sources:
        print("no sources configured: add rss_feeds or agent_reach_queries "
              "to your config.json")
        return 2
    provider = build_provider(cfg)
    tracker = Tracker(cfg.tracker_path)
    try:
        notifier = channel_notifier(build_channel(cfg))
    except RuntimeError:
        notifier = lambda entry: print(entry.get("message", entry))
    pipe = Pipeline(cfg, provider, tracker, notifier=notifier)
    summary = pipe.scan(sources)
    print(json.dumps(summary, indent=2))
    return 0


def _cmd_replies(args) -> int:
    cfg = _load(args)
    tracker = Tracker(cfg.tracker_path)
    pipe = Pipeline(cfg, provider=None, tracker=tracker, mail=build_mail(cfg))
    updated = pipe.process_replies()
    for url in updated:
        print(f"replied: {url}")
    if not updated:
        print("no new replies matched to tracker rows")
    return 0


def _cmd_channel(args) -> int:
    cfg = _load(args)
    channel = build_channel(cfg)
    if args.channel_cmd == "poll":
        queue = LinkedInQueue(cfg.linkedin_queue_path)
        tracker = Tracker(cfg.tracker_path)
        decisions = channel.poll_decisions()
        if not decisions:
            print("no pending decisions")
            return 0
        for decision in decisions:
            print(apply_decision(decision, queue=queue, tracker=tracker))
        return 0
    return 2


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
    if os.environ.get("JOBHUNTER_TELEGRAM_BOT_TOKEN", "").strip():
        print("telegram bot token: set")
    else:
        print("telegram bot token: not set (optional)")
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
    sub.add_parser("scan")
    sub.add_parser("replies")
    exp = sub.add_parser("export")
    exp.add_argument("--out", default="tracker.csv")
    sub.add_parser("doctor")
    li = sub.add_parser("linkedin")
    li_sub = li.add_subparsers(dest="linkedin_cmd", required=True)
    li_sub.add_parser("list").add_argument("--status", default=None)
    li_sub.add_parser("approve").add_argument("id")
    li_sub.add_parser("done").add_argument("id")
    ch = sub.add_parser("channel")
    ch_sub = ch.add_subparsers(dest="channel_cmd", required=True)
    ch_sub.add_parser("poll")
    args = parser.parse_args(argv)
    if args.cmd == "status":
        return _cmd_status(args)
    if args.cmd == "scan":
        return _cmd_scan(args)
    if args.cmd == "replies":
        return _cmd_replies(args)
    if args.cmd == "export":
        return _cmd_export(args)
    if args.cmd == "doctor":
        return _cmd_doctor(args)
    if args.cmd == "linkedin":
        return _cmd_linkedin(args)
    if args.cmd == "channel":
        return _cmd_channel(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
