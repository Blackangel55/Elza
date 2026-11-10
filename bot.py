import logging
import logging.config
import time
import asyncio
from datetime import date, datetime
import pytz
from aiohttp import web
from pyrogram import idle, __version__
from pyrogram.raw.all import layer
from database.ia_filterdb import Media, Media2, backfill_added_on
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from plugins import web_server
from Lucia.Bot import SilentX
from Lucia.util.keepalive import ping_server
import pyrogram.utils

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.INFO)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

botStartTime = time.time()

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

async def SilentXBotz_start():
    print('Initalizing Your Bot!')
    await SilentX.start()
    bot_info = await SilentX.get_me()
    SilentX.username = bot_info.username
    if ON_HEROKU and URL:
        asyncio.create_task(ping_server())
    try:
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
    except Exception as e:
        logging.warning(f"Could not load banned users/chats, continuing with empty lists: {e}")
    try:
        await Media.ensure_indexes()
        if MULTIPLE_DB:
            await Media2.ensure_indexes()
            print("Multiple Database Mode On. Now Files Will Be Save In Second DB If First DB Is Full")
        else:
            print("Single DB Mode On ! Files Will Be Save In First Database")
    except Exception as e:
        logging.warning(f"Could not create DB indexes, continuing without them (search falls back to regex): {e}")
    # One-time backfill: files saved before added_on existed have no
    # timestamp, so they sort arbitrarily among themselves. Stamp them
    # in insertion order in the background; it never blocks startup,
    # and a failure only logs a warning inside the backfill itself.
    try:
        asyncio.create_task(backfill_added_on())
    except Exception as e:
        logging.warning(f"Could not start added_on backfill: {e}")
    me = await SilentX.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    SilentX.username = '@' + me.username
    logging.info(f"{me.first_name} with Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
    logging.info(script.LOGO)
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time_str = now.strftime("%H:%M:%S %p")
    try:
        await SilentX.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(temp.B_LINK, today, time_str))
    except Exception as e:
        logging.warning(f"Could not send restart notice to LOG_CHANNEL ({LOG_CHANNEL}): {e} - check the channel ID and that the bot is in the channel.")
    try:
        for admin in ADMINS:
            await SilentX.send_message(chat_id=admin, text=f"<b>๏[-ิ_•ิ]๏ {me.mention} Restarted ✅</code></b>")
    except Exception:
        pass
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()
    await idle()

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(SilentXBotz_start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')
