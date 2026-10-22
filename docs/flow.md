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
        v               |              (alert goes out on the channel)
   tracker: MATCHED     no
        |               v
        |        outreach drafted for approval
        v
  replies (Gmail API) -> tracker: REPLIED
  approved mails -> send via Gmail API, daily cap enforced

channels (Telegram, ...):
  handoff + match alerts  -->  the user's chat
  `approve <queue-id>`    -->  LinkedIn queue: draft -> approved
  `skip <company>`        -->  tracker: matched -> skipped
```

Every posting ends up in the tracker exactly once, with the reason for
its status. Nothing leaves the machine without an approval step, and no
channel decision applies, emails, or messages anyone by itself.
