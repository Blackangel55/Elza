# Temporary debug plugin — proves whether Telegram delivers updates at all.
# It only LOGS incoming messages; it never replies and never blocks them.
# Group -1 runs before every other handler. Remove this file once the
# /start silence is diagnosed.
import logging

from pyrogram import Client, filters

log = logging.getLogger(__name__)


@Client.on_message(filters.incoming, group=-1)
async def debug_update(client, message):
    try:
        user = message.from_user.id if message.from_user else None
        log.error(
            "[DEBUG-UPDATE] chat=%s user=%s text=%r",
            message.chat.id,
            user,
            message.text,
        )
    except Exception:
        # Never let the debug logger break real handling.
        pass
