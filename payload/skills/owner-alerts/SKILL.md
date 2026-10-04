---
name: owner-alerts
description: Set up and send optional owner-approved iMessage blocker or input alerts for a Codex project without reading Messages history or storing the destination in Git.
---

# Owner alerts

At new-project setup, ask once whether the owner wants iMessage alerts for actionable blockers or needed input and, if yes, which phone number is approved. Record the answer and exact receiver only in owner-private, per-project configuration outside Git; do not place it in a repo, global instructions, task memory or shared agent brief. If declined, unanswered or not configured, stay in chat. Re-ask only if the owner changes the preference.

Send only within that opt-in scope, for a meaningful new blocker or a specific decision the owner must make. Keep one short message with project name, concise blocker and one requested action. Deduplicate unchanged blockers; do not send routine progress, passwords, tokens, logs, customer data, session codes or private transcripts. Do not expand the approved recipient list by looking up contacts or chats.

If the owner separately installs and authorizes the standard [imsg](https://github.com/openclaw/imsg) CLI on macOS, use its ordinary `imsg send --to` text operation to the exact approved number. This skill installs nothing and never calls `chats`, `history`, `watch`, JSON-RPC, an injected helper, or a permission bypass. Sending may be unavailable because Messages.app, account or macOS Automation permission is not ready; report that failure in chat and do not silently retry through another channel. Claim an alert was sent only after the actual send operation succeeds; do not claim phone delivery or reading without independent confirmation. No daemon, scheduled monitor or automatic background alert loop is included.
