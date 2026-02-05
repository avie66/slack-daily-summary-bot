import asyncio
import logging
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from flexus_client_kit import ckit_client
from flexus_client_kit import ckit_cloudtool
from flexus_client_kit import ckit_bot_exec
from flexus_client_kit import ckit_shutdown
from flexus_client_kit import ckit_ask_model
from flexus_client_kit.integrations import fi_slack

from slack_daily_summary import slack_daily_summary_install

logger = logging.getLogger("slack_daily_summary")

BOT_NAME = "slack_daily_summary"
BOT_VERSION = "0.1.1"

GENERATE_SUMMARY_TOOL = ckit_cloudtool.CloudTool(
    strict=True,
    name="generate_daily_summary",
    description="Generate and post the daily Slack summary for the previous calendar day (IST timezone).",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
)

TOOLS = [
    GENERATE_SUMMARY_TOOL,
    fi_slack.SLACK_TOOL,
]


async def slack_daily_summary_main_loop(fclient: ckit_client.FlexusClient, rcx: ckit_bot_exec.RobotContext) -> None:
    setup = ckit_bot_exec.official_setup_mixing_procedure(
        slack_daily_summary_install.SLACK_DAILY_SUMMARY_SETUP_SCHEMA,
        rcx.persona.persona_setup,
    )

    SLACK_BOT_TOKEN = setup.get("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN = setup.get("SLACK_APP_TOKEN", "")
    target_channel = setup.get("target_channel", "bob-testing")

    slack_client = None
    bot_user_id = None

    if SLACK_BOT_TOKEN:
        try:
            slack_client = AsyncWebClient(token=SLACK_BOT_TOKEN)
            auth_response = await slack_client.auth_test()
            bot_user_id = auth_response["user_id"]
            logger.info(f"Bot authenticated as user_id: {bot_user_id}")
        except SlackApiError as e:
            logger.error(f"Failed to authenticate with Slack: {e}")
            slack_client = None
            bot_user_id = None
    else:
        logger.warning("SLACK_BOT_TOKEN not configured, bot will run but cannot generate summaries until configured")

    @rcx.on_updated_message
    async def updated_message_in_db(msg: ckit_ask_model.FThreadMessageOutput):
        pass

    @rcx.on_updated_thread
    async def updated_thread_in_db(th: ckit_ask_model.FThreadOutput):
        pass

    @rcx.on_tool_call(GENERATE_SUMMARY_TOOL.name)
    async def toolcall_generate_summary(toolcall: ckit_cloudtool.FCloudtoolCall, model_produced_args: Dict[str, Any]) -> str:
        if not slack_client or not bot_user_id:
            return "Configuration required: Please set SLACK_BOT_TOKEN in bot setup to enable summary generation. Go to bot settings to configure the token with required scopes: channels:read, channels:history, chat:write, reactions:read, users:read"

        logger.info("Generating daily summary")

        try:
            summary_text = await generate_summary(slack_client, bot_user_id, target_channel)
            if not summary_text:
                return "No activity detected for yesterday. Skipping summary post."

            return f"Summary generated and posted successfully:\n\n{summary_text}"
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}", exc_info=True)
            return f"Error generating summary: {type(e).__name__}: {e}"

    @rcx.on_tool_call(fi_slack.SLACK_TOOL.name)
    async def toolcall_slack(toolcall: ckit_cloudtool.FCloudtoolCall, model_produced_args: Dict[str, Any]) -> str:
        if not slack_client:
            return "Configuration required: Please set SLACK_BOT_TOKEN in bot setup to enable Slack integration"
        return "Slack tool is available but this bot primarily operates on a schedule. Use generate_daily_summary to test the summary generation."

    try:
        while not ckit_shutdown.shutdown_event.is_set():
            await rcx.unpark_collected_events(sleep_if_no_work=10.0)
    finally:
        logger.info(f"{rcx.persona.persona_id} exit")


async def generate_summary(slack_client: AsyncWebClient, bot_user_id: str, target_channel: str) -> Optional[str]:
    IST = timezone(timedelta(hours=5, minutes=30))

    now_ist = datetime.now(IST)
    yesterday_start = datetime.combine(now_ist.date() - timedelta(days=1), datetime.min.time(), tzinfo=IST)
    yesterday_end = datetime.combine(now_ist.date() - timedelta(days=1), datetime.max.time(), tzinfo=IST)

    oldest_ts = yesterday_start.timestamp()
    latest_ts = yesterday_end.timestamp()

    logger.info(f"Analyzing activity from {yesterday_start} to {yesterday_end} IST")

    channels = await fetch_all_channels(slack_client)
    logger.info(f"Found {len(channels)} public channels")

    all_messages = []
    user_ids = set()

    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]

        try:
            messages = await fetch_channel_history(slack_client, channel_id, oldest_ts, latest_ts)

            for msg in messages:
                if msg.get("user") == bot_user_id:
                    continue

                msg["channel_name"] = channel_name
                all_messages.append(msg)

                if msg.get("user"):
                    user_ids.add(msg["user"])

        except SlackApiError as e:
            logger.warning(f"Failed to fetch history for {channel_name}: {e}")
            continue

    if not all_messages:
        logger.info("No messages found for yesterday")
        return None

    logger.info(f"Found {len(all_messages)} messages from {len(user_ids)} unique users")

    top_thread = find_top_thread(all_messages)
    most_active_channels = find_most_active_channels(all_messages)
    most_helpful_user = await find_most_helpful_user(all_messages, slack_client)
    open_question = find_open_question(all_messages)

    total_messages = len(all_messages)
    active_members = len(user_ids)

    summary_parts = ["📊 Daily Slack Recap (Yesterday)\n"]

    if top_thread:
        thread_text = top_thread["text"][:60] + ("..." if len(top_thread["text"]) > 60 else "")
        summary_parts.append(f'🔥 Top thread: "{thread_text}" ({top_thread["reply_count"]} replies)')

    if most_active_channels:
        channel_name, count = most_active_channels[0]
        summary_parts.append(f"💬 Most active: #{channel_name} ({count} messages)")

    if most_helpful_user:
        username, reaction_count = most_helpful_user
        summary_parts.append(f"⭐ Shoutout: @{username} ({reaction_count} reactions)")

    if open_question:
        question_text = open_question[:80] + ("..." if len(open_question) > 80 else "")
        summary_parts.append(f'❓ Open question: "{question_text}"')

    summary_parts.append(f"📈 {total_messages} messages · {active_members} active members")

    summary_text = "\n".join(summary_parts)

    try:
        channel_id = await get_channel_id(slack_client, target_channel)
        await slack_client.chat_postMessage(
            channel=channel_id,
            text=summary_text,
        )
        logger.info(f"Posted summary to #{target_channel}")
    except SlackApiError as e:
        logger.error(f"Failed to post summary: {e}")
        raise

    return summary_text


async def fetch_all_channels(slack_client: AsyncWebClient) -> List[Dict]:
    channels = []
    cursor = None

    while True:
        try:
            response = await slack_client.conversations_list(
                types="public_channel",
                exclude_archived=True,
                limit=200,
                cursor=cursor,
            )
            channels.extend(response["channels"])

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        except SlackApiError as e:
            logger.error(f"Failed to list channels: {e}")
            break

    return channels


async def fetch_channel_history(slack_client: AsyncWebClient, channel_id: str, oldest: float, latest: float) -> List[Dict]:
    messages = []
    cursor = None

    while True:
        try:
            response = await slack_client.conversations_history(
                channel=channel_id,
                oldest=str(oldest),
                latest=str(latest),
                limit=1000,
                cursor=cursor,
            )
            messages.extend(response["messages"])

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        except SlackApiError:
            break

    return messages


def find_top_thread(messages: List[Dict]) -> Optional[Dict]:
    threads = {}

    for msg in messages:
        thread_ts = msg.get("thread_ts")
        if not thread_ts:
            continue

        reply_count = msg.get("reply_count", 0)
        if reply_count > 0:
            if thread_ts not in threads or reply_count > threads[thread_ts]["reply_count"]:
                threads[thread_ts] = {
                    "text": msg.get("text", ""),
                    "reply_count": reply_count,
                }

    if not threads:
        return None

    top = max(threads.values(), key=lambda x: x["reply_count"])
    return top


def find_most_active_channels(messages: List[Dict]) -> List[tuple]:
    channel_counts = defaultdict(int)

    for msg in messages:
        channel_name = msg.get("channel_name", "unknown")
        channel_counts[channel_name] += 1

    sorted_channels = sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_channels[:2]


async def find_most_helpful_user(messages: List[Dict], slack_client: AsyncWebClient) -> Optional[tuple]:
    user_reactions = defaultdict(int)

    for msg in messages:
        user_id = msg.get("user")
        if not user_id:
            continue

        reactions = msg.get("reactions", [])
        total_reactions = sum(r.get("count", 0) for r in reactions)
        user_reactions[user_id] += total_reactions

    if not user_reactions:
        return None

    top_user_id = max(user_reactions, key=user_reactions.get)
    top_count = user_reactions[top_user_id]

    if top_count == 0:
        return None

    try:
        user_info = await slack_client.users_info(user=top_user_id)
        username = user_info["user"]["name"]
    except SlackApiError:
        username = top_user_id

    return username, top_count


def find_open_question(messages: List[Dict]) -> Optional[str]:
    for msg in messages:
        text = msg.get("text", "")
        if "?" not in text:
            continue

        reply_count = msg.get("reply_count", 0)
        reactions = msg.get("reactions", [])

        if reply_count == 0 and len(reactions) == 0:
            return text

    return None


async def get_channel_id(slack_client: AsyncWebClient, channel_name: str) -> str:
    channel_name = channel_name.lstrip("#")

    cursor = None
    while True:
        response = await slack_client.conversations_list(
            types="public_channel",
            exclude_archived=True,
            limit=200,
            cursor=cursor,
        )

        for channel in response["channels"]:
            if channel["name"] == channel_name:
                return channel["id"]

        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    raise ValueError(f"Channel #{channel_name} not found")


def main():
    scenario_fn = ckit_bot_exec.parse_bot_args()
    fclient = ckit_client.FlexusClient(
        ckit_client.bot_service_name(BOT_NAME, BOT_VERSION),
        endpoint="/v1/jailed-bot",
    )

    asyncio.run(ckit_bot_exec.run_bots_in_this_group(
        fclient,
        marketable_name=BOT_NAME,
        marketable_version_str=BOT_VERSION,
        bot_main_loop=slack_daily_summary_main_loop,
        inprocess_tools=TOOLS,
        scenario_fn=scenario_fn,
        install_func=slack_daily_summary_install.install,
    ))


if __name__ == "__main__":
    main()
