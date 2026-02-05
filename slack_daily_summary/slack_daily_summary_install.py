import asyncio
import base64
import json
from pathlib import Path

from flexus_client_kit import ckit_client, ckit_bot_install
from flexus_client_kit import ckit_cloudtool

from slack_daily_summary import slack_daily_summary_prompts


BOT_DESCRIPTION = """
## Slack Daily Summary - Automated Activity Digest

A focused bot that posts a single daily summary of your Slack workspace activity. No noise, no spam—just one clean message per day.

**What It Does:**
- **Analyzes** all public channel activity from the previous calendar day
- **Summarizes** top threads, active channels, helpful members, and unanswered questions
- **Posts** a formatted summary to your designated channel at 3:30 PM IST
- **Skips** posting when there's no activity

**Key Features:**
- **Fully automated**: Runs on schedule, no manual intervention needed
- **Smart filtering**: Excludes bot messages from statistics
- **Timezone aware**: Properly handles IST (UTC+5:30) for day boundaries
- **Clean format**: Consistent, easy-to-read summary structure
- **Efficient**: Analyzes all public channels in parallel

**Perfect For:**
- Teams who want to stay informed without constant notifications
- Managers tracking workspace engagement
- Remote teams staying connected across timezones
- Identifying unanswered questions that need attention

**Requirements:**
- Slack Bot Token (xoxb-...) with `channels:read`, `channels:history`, `chat:write`, `reactions:read`, `users:read` scopes
- Posts to a designated channel (default: #bob-testing)

Keep your team in the loop with minimal effort—one summary, once a day.
"""


SLACK_DAILY_SUMMARY_SETUP_SCHEMA = [
    {
        "bs_name": "SLACK_BOT_TOKEN",
        "bs_type": "string_long",
        "bs_default": "",
        "bs_group": "Slack",
        "bs_importance": 0,
        "bs_description": "Bot User OAuth Token from Slack app settings (starts with xoxb-). Required scopes: channels:read, channels:history, chat:write, reactions:read, users:read",
    },
    {
        "bs_name": "SLACK_APP_TOKEN",
        "bs_type": "string_long",
        "bs_default": "",
        "bs_group": "Slack",
        "bs_importance": 1,
        "bs_description": "App-Level Token for Socket Mode (starts with xapp-). Optional for this bot as it only posts messages on schedule.",
    },
    {
        "bs_name": "target_channel",
        "bs_type": "string_short",
        "bs_default": "bob-testing",
        "bs_group": "Configuration",
        "bs_importance": 0,
        "bs_description": "Channel name (without #) where daily summaries will be posted",
    },
]


async def install(
    client: ckit_client.FlexusClient,
    ws_id: str,
    bot_name: str,
    bot_version: str,
    tools: list[ckit_cloudtool.CloudTool],
):
    bot_internal_tools = json.dumps([t.openai_style_tool() for t in tools])

    pic_big_path = Path(__file__).with_name("slack_daily_summary-1024x1536.webp")
    pic_small_path = Path(__file__).with_name("slack_daily_summary-256x256.webp")

    if pic_big_path.exists():
        pic_big = base64.b64encode(open(pic_big_path, "rb").read()).decode("ascii")
    else:
        pic_big = ""

    if pic_small_path.exists():
        pic_small = base64.b64encode(open(pic_small_path, "rb").read()).decode("ascii")
    else:
        pic_small = ""

    await ckit_bot_install.marketplace_upsert_dev_bot(
        client,
        ws_id=ws_id,
        marketable_name=bot_name,
        marketable_version=bot_version,
        marketable_accent_color="#4A154B",
        marketable_title1="Slack Daily Summary",
        marketable_title2="Automated daily activity digest for your Slack workspace",
        marketable_author="Flexus",
        marketable_occupation="Workspace Analytics",
        marketable_description=BOT_DESCRIPTION,
        marketable_typical_group="Productivity / Communication",
        marketable_github_repo="https://github.com/smallcloudai/slack-daily-summary",
        marketable_run_this=f"python -m {bot_name}.{bot_name}_bot",
        marketable_setup_default=SLACK_DAILY_SUMMARY_SETUP_SCHEMA,
        marketable_featured_actions=[
            {"feat_question": "Generate today's summary", "feat_expert": "default", "feat_depends_on_setup": ["SLACK_BOT_TOKEN"]},
            {"feat_question": "Show bot status", "feat_expert": "default", "feat_depends_on_setup": []},
        ],
        marketable_intro_message="Hi! I'm the Slack Daily Summary bot. I'll automatically post a daily digest of your workspace activity to your designated channel at 3:30 PM IST. Make sure to configure your SLACK_BOT_TOKEN in the setup!",
        marketable_preferred_model_default="grok-4-1-fast-non-reasoning",
        marketable_daily_budget_default=10_000,
        marketable_default_inbox_default=1_000,
        marketable_experts=[
            ("default", ckit_bot_install.FMarketplaceExpertInput(
                fexp_system_prompt=slack_daily_summary_prompts.slack_daily_summary_prompt,
                fexp_python_kernel="",
                fexp_block_tools="",
                fexp_allow_tools="",
                fexp_app_capture_tools=bot_internal_tools,
                fexp_description="Main expert that generates and posts daily Slack summaries on schedule.",
            )),
        ],
        marketable_tags=["Slack", "Analytics", "Automation", "Productivity"],
        marketable_picture_big_b64=pic_big,
        marketable_picture_small_b64=pic_small,
        marketable_schedule=[
            {
                "sched_type": "SCHED_NEW_CHAT",
                "sched_when": "WEEKDAYS:MO:TU:WE:TH:FR:SA:SU/15:30",
                "sched_first_question": "Generate and post the daily summary for yesterday's Slack activity.",
                "sched_fexp_name": "default",
            },
        ],
        marketable_forms=ckit_bot_install.load_form_bundles(__file__),
    )


if __name__ == "__main__":
    from slack_daily_summary import slack_daily_summary_bot
    args = ckit_bot_install.bot_install_argparse()
    client = ckit_client.FlexusClient("slack_daily_summary_install")
    asyncio.run(install(
        client,
        ws_id=args.ws,
        bot_name=slack_daily_summary_bot.BOT_NAME,
        bot_version=slack_daily_summary_bot.BOT_VERSION,
        tools=slack_daily_summary_bot.TOOLS,
    ))
