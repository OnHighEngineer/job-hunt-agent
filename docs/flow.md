# Flow

```
sources (RSS, career pages, Agent-Reach)
        |
        v
  rule gates  --------fail-------> tracker: SKIPPED (reason logged)
  (free, no LLM)        |
        | pass          v
        v          LLM fit score
        |               |
        |        below threshold -> tracker: SKIPPED (score + reason)
        v               |
  matched               v
        |        needs_human? --yes--> HANDOFF: link + resume to the user
        v               |
   tracker: MATCHED     no
        |               v
        |        outreach drafted for approval
        v
  replies (Gmail API) -> tracker: REPLIED
  approved mails -> send via Gmail API, daily cap enforced
```

Every posting ends up in the tracker exactly once, with the reason for
its status. Nothing leaves the machine without an approval step.
