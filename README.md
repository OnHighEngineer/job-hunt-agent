# job-hunt-agent

An open source agent that hunts jobs the way a careful person would:
it finds postings, checks each one against your resume with an LLM you
choose, logs every decision in a tracker, drafts outreach for your
approval, and hands you a link the moment a human step comes up.

Bring your own LLM key. Your keys stay on your machine. Nothing here
auto-applies through captchas or sends LinkedIn messages behind your back.

## What it does

1. **Finds jobs** through pluggable sources: RSS feeds, company career
   pages, and [Agent-Reach](https://github.com/Panniantong/Agent-Reach)
   (web search, clean page reads, public LinkedIn pages) when installed.
2. **Gates cheaply first** - deterministic rules (experience cap, posting
   freshness, blocklist, internship stipend floor) skip bad postings
   before a single paid model call.
3. **Scores fit with your LLM** - OpenAI, Gemini, Grok, or Claude. One
   interface, four adapters, score plus one-line reason.
4. **Tracks everything** in a local SQLite tracker: matched, skipped
   (with why), applied, handoff, replied, interview, rejected. Export to
   CSV anytime.
5. **Reads Gmail replies** through the official Gmail API and flips
   tracker rows when a recruiter answers.
6. **Sends approved cold email** through the Gmail API with a daily cap -
   only what you approved.
7. **Drafts LinkedIn connect notes** into a local queue. You approve,
   you send. There is deliberately no auto-send.
8. **Hands off** with the direct apply link and your tailored resume when
   a captcha, login, or risky form appears.

## What it never does

- No auto-applying through captchas, logins, or bot checks.
- No LinkedIn connection requests or DMs sent without your approval.
- No untruthful answers on any form, no invented resume lines.
- No keys in the repo, commits, or logs. Keys live in your environment.
- No spending past your monthly cap.
- No logged-in scraping in v1.

## Quickstart

No dependencies beyond Python 3.10+ for the core and the tests.

```bash
git clone https://github.com/OnHighEngineer/job-hunt-agent.git
cd job-hunt-agent
cp config.example.json config.json   # edit your rules
python3 -m unittest discover -s tests # 69 tests, all offline
```

Set your LLM key (any one provider):

```bash
export OPENAI_API_KEY=...      # or
export GEMINI_API_KEY=...      # or
export XAI_API_KEY=...         # Grok, or
export ANTHROPIC_API_KEY=...   # Claude
```

Pick the provider in `config.json` (`"provider": "openai" | "gemini" | "grok" | "claude"`).
`python3 -m jobhunter.cli doctor` checks your setup.

## Configuration

All rules live in `config.json` (see `config.example.json`):

| Key | Meaning |
| --- | --- |
| `roles` | Titles to target |
| `max_experience_years` | Skip roles requiring more |
| `locations` | Location preference order |
| `salary_min_lpa` / `salary_max_lpa` | Expected range, India |
| `internship_stipend_floor` | Internships below this monthly stipend are skipped |
| `max_posting_age_days` | Skip older postings |
| `blocklist` | Companies never to touch |
| `fit_threshold` | Minimum LLM score (0-100) to proceed |
| `daily_send_cap` | Max outreach emails per day |
| `provider` / `model` | Which LLM, which model |
| `monthly_spend_cap_usd` | Hard stop for LLM spend |

## Tracker

One row per job: date, source, direct link, company, role, fit score and
reason, status, next step and owner. Statuses update themselves when
replies arrive. `python3 -m jobhunter.cli status` for a summary,
`export` for CSV you can open in any spreadsheet.

## Gmail setup

Reading replies and sending approved mail uses the official Gmail API.
Create an OAuth token (Google Cloud console, Gmail API enabled) and export
it as `JOBHUNTER_GMAIL_TOKEN`. The token stays in your environment.

## Agent-Reach as the reach layer

Install [Agent-Reach](https://github.com/Panniantong/Agent-Reach) (MIT)
and `jobhunter` can use it for web search and clean JD page reads. It is
an optional dependency: RSS and static sources work without it. Its
logged-in LinkedIn features stay unused here - same account-restriction
risk as any automation.

## Contributing

Issues and PRs welcome. Good first contributions:

- New job sources (a board you use, a career-page adapter)
- New LLM adapters (implement `complete(prompt) -> str`)
- Tracker exporters (Google Sheets, Notion)
- Better reply-to-tracker matching

Please keep the "never does" list intact - it is the point of the project.

## License

MIT. Use it, fork it, make it yours.
