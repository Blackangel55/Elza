# Temporary debug plugin — proves whether Telegram delivers updates at all.
# It only LOGS incoming messages; it never replies and never blocks them.
# Group -1 runs before every other handler. Remove this file once the
# /start silence is diagnosed.
import logging

from pyrogram import Client, filters

log = logging.getLogger(__name__)

# Fires the moment this module is imported by Pyrogram's load_plugins().
# If this line never appears in the Koyeb logs, the plugins never loaded
# there at all (silent — the [LOAD] lines go through the pyrogram logger,
# which bot.py + Lucia/Bot/__init__.py accidentally disable with their
# double logging.config.fileConfig() call).
log.error("[DEBUG-PLUGIN-LOADED] debug_updates module imported")


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
