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
- **Integrations**: Slack Web API via `slack-sdk`
- **Scheduling**: `ckit_schedule.py` with daily WEEKDAYS schedule
- **Time handling**: `datetime` with `timezone` for IST (UTC+5:30)

## Implementation Status

✅ **Completed**

The bot is fully implemented with the following structure:

- `slack_daily_summary_bot.py` - Main bot logic with summary generation
- `slack_daily_summary_prompts.py` - System prompts for the bot
- `slack_daily_summary_install.py` - Marketplace registration and schedule configuration
- `slack_daily_summary-1024x1536.webp` - Large marketplace image
- `slack_daily_summary-256x256.webp` - Bot avatar
- `setup.py` - Package installation configuration

### Key Implementation Details

**Schedule**: Configured as `WEEKDAYS:MO:TU:WE:TH:FR:SA:SU/15:30` (daily at 3:30 PM in workspace timezone)

**Bot Token Only**: This bot uses `SLACK_BOT_TOKEN` with the Slack Web API directly. It doesn't need Socket Mode (`SLACK_APP_TOKEN`) since it only posts messages on schedule and doesn't listen for events.

**Required Slack Scopes**:
- `channels:read` - List available channels
- `channels:history` - Read message history
- `chat:write` - Post summary messages
- `reactions:read` - Count reactions on messages
- `users:read` - Get user display names

**IST Timezone Handling**:
- Schedule uses workspace timezone (IST)
- Summary analysis uses IST for day boundaries (midnight to midnight)
- Slack API timestamps are Unix epochs (UTC) converted to IST for filtering

**Statistics Collection**:
- Fetches all public channels in parallel
- Filters messages by timestamp to match previous IST day
- Excludes bot's own messages from all statistics
- Calculates: top thread, most active channels, most helpful user, open questions
- Skips posting if no activity detected

**Error Handling**:
- Gracefully handles missing channels, API errors
- Logs warnings for channels that can't be accessed
- Returns error messages for tool calls that fail

---

## Future Enhancements (Out of Scope)

- Weekly rollup summaries
- Configurable summary components
- Multiple workspace support
- Sentiment analysis
- Trend detection (this week vs last week)