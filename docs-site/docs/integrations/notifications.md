---
title: Slack & Teams Notifications
---

# Slack & Teams Notifications

This integration is under active development. The notification endpoint is configured in `cherenkov.toml`.

## Configuration

```toml
[notifications]
slack_webhook = "${SLACK_WEBHOOK_URL}"
teams_webhook = "${TEAMS_WEBHOOK_URL}"

[notifications.triggers]
on_drift = true
on_gate_fail = true
on_release = true
```

Check back for the full integration guide, or [contribute on GitHub](https://github.com/moaidmoatasem/cherenkov-qa).
