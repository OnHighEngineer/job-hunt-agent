# Decision log

What was chosen, why, and what was rejected. A decision log is not a
changelog: it records the reasoning so future sessions do not relitigate.

## 2026-10-22 (day 1)

- **Stdlib-only core; optional deps load lazily.** Chosen so anyone can
  clone and run the full test suite with zero installs, and keys never
  pass through a third-party SDK's logging. Rejected: `openai`/`anthropic`
  SDKs as hard dependencies (install burden, version churn), PyYAML
  (config moved to JSON).
- **Config as JSON, not YAML.** Stdlib has no YAML parser and the core is
  dependency-free. Rejected: shipping a mini YAML parser (bug farm).
- **unittest, not pytest.** Runs anywhere with zero install; pytest still
  discovers the same tests if a contributor prefers it. Rejected: requiring
  pytest (extra install for no gain at this size).
- **Tests run fully offline on canned LLM replies.** No network, no key,
  no spend in CI or for contributors. Adapters are tested through
  `build_request`/`parse_response` with a fake transport.
- **Agent-Reach is an optional external dependency, never vendored.**
  It is MIT-licensed and actively maintained upstream; shelling out keeps
  upgrades free. Rejected: vendoring (goes stale), hard dependency
  (breaks the zero-install promise).
- **Deterministic rule gates before any paid LLM call.** Experience cap,
  freshness, blocklist and stipend floor cost nothing to check, so a
  posting that fails them never reaches the model. Rejected: LLM-first
  screening (pays to reject obvious mismatches).
- **LinkedIn is draft-and-approve, with no send function in code.**
  LinkedIn has no official API for connection requests and restricts
  accounts for automation. The queue has `draft`/`approve`/`done` and
  deliberately no `send`. Rejected: browser automation for sends
  (account-restriction risk).
- **Handoff instead of auto-apply on captcha/login/risky forms.** The
  agent sends the direct apply link plus the resume and stops. Rejected:
  captcha solving and credential filling (fragile, against site rules).
- **Gmail only through the official API.** Rejected: IMAP scraping or
  browser automation of the inbox.
- **SQLite tracker, CSV export.** Zero-install, inspectable, portable.
  Rejected: Google Sheets as the primary store (network dependency for
  every write); a Sheet exporter is a welcome contribution.
- **Daily send cap enforced in the pipeline, not the mail client.** The
  client stays dumb; policy lives in one place.
- **Default config ships the owner's hunt rules** (0-1 yr roles, 3-day
  freshness, stipend floor, blocklist). Users replace them with their own.
  No employer or proprietary names appear anywhere in the repo.

## 2026-10-22 (day 2)

- **Telegram is the first chat channel; the channel interface is
  pluggable.** Telegram bots are free and need only a token and a chat
  id. Rejected for v1: WhatsApp (Meta business API, approved templates,
  real setup burden), SMS (per-message cost through a provider),
  Instagram DMs (heavily restricted by Meta). New channels implement the
  two-method `Channel` interface (`send_alert`, `poll_decisions`).
- **Bot token and chat id come from the environment only.** Same rule as
  LLM keys: no secrets in the repo. Rejected: token in config.json
  (one slip and it is committed).
- **Decisions are plain-text replies: `approve <queue-id>`,
  `skip <company>`.** Approve drives the LinkedIn draft queue; skip
  flips the newest tracker row matching the company token. Rejected:
  inline buttons with callback state (more moving parts than v1 needs,
  and button callbacks die when the bot restarts), free-form replies
  (unparseable).
- **Polling with getUpdates and a persisted offset, no webhook.** The
  agent runs on a laptop with no public URL. The offset lives in
  `telegram_state.json` (gitignored) so restarts do not re-apply old
  decisions. Rejected: webhooks (needs a public endpoint).
- **The channel notifies and carries decisions; it never acts on its
  own.** Same rule as the LinkedIn queue: applying, emailing and
  messaging stay with the human. Rejected: letting a channel decision
  trigger an apply or send directly (defeats the approval model).
- **CI is GitHub Actions running the unittest suite on Python
  3.10-3.12.** Zero installs, mirrors the local command. Rejected:
  pytest in CI (the suite is stdlib unittest; nothing to install).
- **Main is protected: changes land through reviewed pull requests.**
  CODEOWNERS routes review to the owner; direct pushes are off. The
  owner is the only one who merges.
- **RSS company falls back to the job URL when the feed omits it.**
  Board URLs usually carry the company as the first path segment;
  otherwise the second-level domain is used. Rejected: leaving company
  empty (reply matching and channel `skip` need a company token to find
  the tracker row).
