# Slack Daily Summary Bot

**One job. One message. Once a day.**

Automatically posts a daily summary of Slack workspace activity to keep teams informed without overwhelming them.

---

## What It Does

- **Analyzes** all public channel activity from the previous calendar day
- **Summarizes** key conversations, active channels, helpful members, and unanswered questions
- **Posts** a single formatted message to a designated channel at a specific time
- **Skips** posting if there was no activity (weekends, holidays)

---

## Behavior

### Schedule
- **When**: Daily at 3:30 PM IST
- **Posting frequency**: Every day (including weekends), but skips if no activity detected

### What Gets Analyzed
- **Scope**: All public channels in the SMC workspace
- **Time window**: Previous calendar day (midnight to midnight IST)
- **Exclusions**: Bot's own messages are not counted in statistics

### Message Format

Posts to `#bob-testing` with this structure:

```
📊 Daily Slack Recap (Yesterday)

🔥 Top thread: "<thread title or first message>" (<N> replies)
💬 Most active: #<channel-name> (<N> messages)
⭐ Shoutout: @<username> (<N> reactions on their messages)
❓ Open question: "<question text>"
📈 <total> messages · <count> active members
```

### Summary Components

1. **Top thread** - Thread with the most replies
2. **Most active channels** - Top 1-2 channels by message count
3. **Helpful humans** - Person who received the most reactions (all emoji types) on their messages
4. **Open questions** - Messages containing `?` that have:
   - No thread replies AND
   - No reactions
5. **Quick stats** - Total message count and number of unique active users

---

## Requirements

### Slack Permissions

Requires a Slack Bot with these scopes:
- `channels:history` - Read public channel messages
- `channels:read` - List available channels
- `chat:write` - Post summary messages
- `reactions:read` - Count reactions on messages
- `users:read` - Get user display names

### Environment

- **SLACK_BOT_TOKEN**: Bot User OAuth Token (xoxb-...)
- **SLACK_APP_TOKEN**: App-Level Token for Socket Mode (xapp-...) — if using Socket Mode

### Configuration

| Setting | Value |
|---------|-------|
| Target workspace | SMC |
| Post channel | `#bob-testing` |
| Post time | 3:30 PM IST (10:00 AM UTC) |
| Analysis window | Previous calendar day (IST timezone) |
| Channel scope | All public channels |
| Exclude bot messages | Yes |
| Post on zero activity | No (skip posting) |

---

## Implementation Notes

### Data Collection

- Use Slack `conversations.list` to get all public channels
- Use `conversations.history` with `oldest` and `latest` timestamps for the previous day
- Filter messages by timestamp to match IST midnight boundaries
- Track thread reply counts via `thread_ts` and `reply_count` fields
- Aggregate reactions per user from `reactions` arrays

### Timezone Handling

- Schedule must convert 3:30 PM IST to UTC for cron/scheduler
- Message timestamps from Slack API are Unix epochs (UTC) — convert to IST for day boundaries
- IST = UTC + 5:30

### Edge Cases

- **No activity**: Skip posting entirely
- **No threads with replies**: Omit "Top thread" line
- **No questions**: Omit "Open question" line
- **Multiple top items**: Pick first by timestamp or alphabetically
- **Deleted users**: Handle gracefully (show user ID or "Unknown User")

### Performance

- Fetch messages in parallel per channel (asyncio)
- Limit history fetch to 1000 messages per channel (Slack API default)
- Cache channel list to avoid repeated API calls

---

## Success Criteria

✅ Posts exactly once per day at 3:30 PM IST
✅ Accurately reflects previous day's activity (IST timezone)
✅ Message format is clean and readable
✅ Handles edge cases (no activity, no threads, etc.)
✅ Does not count bot's own messages in stats
✅ Runs reliably without manual intervention

---

## Example Output

```
📊 Daily Slack Recap (Yesterday)

🔥 Top thread: "How are you onboarding users?" (18 replies)
💬 Most active: #product (127 messages)
⭐ Shoutout: @aniket (7 reactions)
❓ Open question: "Any tool for webhook retries?"
📈 289 messages · 41 active members
```

---

## Technical Stack

- **Language**: Python 3.9+
- **Framework**: Flexus bot (flexus-client-kit)
- **Integrations**: `fi_slack.py` for Slack API
- **Scheduling**: `ckit_schedule.py` with daily cron
- **Time handling**: `pytz` or `zoneinfo` for IST timezone

---

## Future Enhancements (Out of Scope)

- Weekly rollup summaries
- Configurable summary components
- Multiple workspace support
- Sentiment analysis
- Trend detection (this week vs last week)