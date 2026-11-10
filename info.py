import re
import os
from os import environ, getenv
from Script import script

id_pattern = re.compile(r'^.\d+$')

def is_enabled(value, default):
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default



def _required(name):
    """Return a required env var, or raise a clear error naming it.

    The old code did int(environ.get('API_ID', '')) which crashed with a
    bare ValueError: invalid literal for int() with base 10: '' - no clue
    which variable was missing. This names it.
    """
    value = environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name} (see example.env)")
    return value


def _int_env(name, default=None, required=False):
    """Parse an optional int env var; None when unset, never int('')."""
    raw = environ.get(name, "")
    if raw is None or str(raw).strip() == "":
        if required:
            raise ValueError(f"Missing required environment variable: {name} (see example.env)")
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        raise ValueError(f"Environment variable {name} must be an integer, got: {raw!r}")

SESSION = environ.get('SESSION', 'media_search')
API_ID = int(_required('API_ID'))
API_HASH = _required('API_HASH')
BOT_TOKEN = _required('BOT_TOKEN')

CACHE_TIME = int(environ.get('CACHE_TIME', 300))
USE_CAPTION_FILTER = bool(environ.get('USE_CAPTION_FILTER', True))
PICS = (environ.get('PICS', 'https://graph.org/file/cd932e8292208cf23526d.jpg https://graph.org/file/36f5f5a0e80ed808bb6d8.jpg https://graph.org/file/7b7d15ed77f1dcee3a4a5.jpg https://graph.org/file/89b8032cd09c973a24110.jpg https://graph.org/file/64b4f7e57b95e631f74ef.jpg https://graph.org/file/92fccf062388e8f22eda2.jpg https://te.legra.ph/file/6e5c54297d18da6b4d92b.jpg https://te.legra.ph/file/6ac3adf373702737d1e5f.jpg https://te.legra.ph/file/4777ff03f152d5229da1b.jpg https://te.legra.ph/file/da83aad83524ca220d6e6.jpg https://graph.org/-03-28-833 https://graph.org/file/94441bebd362d3e3b306a.jpg https://te.legra.ph/file/bad76d5f3ef81d105bcfd.jpg https://graph.org/file/caef8696d145dc667de58.jpg https://graph.org/file/b87fe278afc06741e2104.jpg https://graph.org/file/da176d9f8d3230a8e88c4.jpg')).split()
NOR_IMG = environ.get("NOR_IMG", "https://telegra.ph/file/0593a3103ba1b9a5855bf.jpg")
MELCOW_VID = environ.get("MELCOW_VID", "")
SPELL_IMG = environ.get("SPELL_IMG", "https://graph.org/file/a96c590ca726b2dbb9d96.jpg")
SUBSCRIPTION = (environ.get('SUBSCRIPTION', 'https://envs.sh/nwn.jpg'))
FSUB_IMG = (environ.get('FSUB_PICS', 'https://i.ibb.co/3Y8t1Cxz/x.jpg')).split() 

ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '').split()] 
CHANNELS = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('CHANNELS', '').split()]
LOG_CHANNEL = _int_env('LOG_CHANNEL', required=True)  
BIN_CHANNEL = _int_env('BIN_CHANNEL', required=True)  
MOVIE_UPDATE_CHANNEL = _int_env('MOVIE_UPDATE_CHANNEL')  # None = don't post movie updates  
PREMIUM_LOGS = _int_env('PREMIUM_LOGS', LOG_CHANNEL)  # falls back to LOG_CHANNEL 
auth_grp = environ.get('AUTH_GROUP')
AUTH_GROUPS = [int(ch) for ch in auth_grp.split()] if auth_grp else None
reqst_channel = environ.get('REQST_CHANNEL_ID', '') 
REQST_CHANNEL = int(reqst_channel) if reqst_channel and id_pattern.search(reqst_channel) else None
support_chat_id = environ.get('SUPPORT_CHAT_ID', '') 
SUPPORT_CHAT_ID = int(support_chat_id) if support_chat_id and id_pattern.search(support_chat_id) else None

DATABASE_URI = _required('DATABASE_URI')
DATABASE_NAME = environ.get('DATABASE_NAME', "")
COLLECTION_NAME = environ.get('COLLECTION_NAME', '')

# If MULTIPLE_DB Is True Then Fill DATABASE_URI2 Value Else You Will Get Error.
MULTIPLE_DB = is_enabled(os.environ.get('MULTIPLE_DB', "False"), False) # Type True For Turn On MULTIPLE DB FUNTION 
DATABASE_URI2 = environ.get('DATABASE_URI2', "")
DB_CHANGE_LIMIT = int(environ.get('DB_CHANGE_LIMIT', "432")) 

GRP_LNK = environ.get('GRP_LNK', '')
CHNL_LNK = environ.get('CHNL_LNK', '')
OWNER_LNK = environ.get('OWNER_LNK', '')
UPDATE_CHANNEL_LNK = environ.get('UPDATE_CHANNEL_LNK', '')

AUTH_CHANNEL = environ.get("AUTH_CHANNEL", "") # add multiple channels here, separated by single space
AUTH_CHANNEL = [int(ch) for ch in AUTH_CHANNEL.strip().split()] if AUTH_CHANNEL else []
AUTH_REQ_CHANNEL = environ.get('AUTH_REQ_CHANNEL', '') # add multiple channels here, separated by single space
AUTH_REQ_CHANNEL = [int(ch) for ch in AUTH_REQ_CHANNEL.strip().split()] if AUTH_REQ_CHANNEL else []
DELETE_CHANNELS = [int(dch) if id_pattern.search(dch) else dch for dch in environ.get('DELETE_CHANNELS', '').split()]

IS_VERIFY = is_enabled(environ.get('IS_VERIFY', 'False'), False)
LOG_VR_CHANNEL = _int_env('LOG_VR_CHANNEL', LOG_CHANNEL)  # falls back to LOG_CHANNEL
LOG_API_CHANNEL = _int_env('LOG_API_CHANNEL', LOG_CHANNEL)  # falls back to LOG_CHANNEL
VERIFY_IMG = environ.get("VERIFY_IMG", "https://telegra.ph/file/9ecc5d6e4df5b83424896.jpg")

TUTORIAL = environ.get("TUTORIAL", "")
TUTORIAL_2 = environ.get("TUTORIAL_2", "")
TUTORIAL_3 = environ.get("TUTORIAL_3", "")




TWO_VERIFY_GAP = int(environ.get('TWO_VERIFY_GAP', "1200"))
THREE_VERIFY_GAP = int(environ.get('THREE_VERIFY_GAP', "54000"))

MOVIE_UPDATE_NOTIFICATION = is_enabled(environ.get('MOVIE_UPDATE_NOTIFICATION', 'False'), False)
NO_RESULTS_MSG = is_enabled(environ.get('NO_RESULTS_MSG', 'True'), True)
MAX_B_TN = environ.get("MAX_B_TN", "10")
MAX_BTN = is_enabled((environ.get('MAX_BTN', "True")), True)
PORT = _int_env("PORT", 8080)
MSG_ALRT = environ.get('MSG_ALRT', 'Share & Support Us ♥️')
SUPPORT_CHAT = environ.get('SUPPORT_CHAT', '')
SUPPORT_LNK = environ.get('SUPPORT_LNK', OWNER_LNK)  # Support button URL; set this, don't hardcode it 
P_TTI_SHOW_OFF = is_enabled((environ.get('P_TTI_SHOW_OFF', "True")), False)
# ==========================================
# TMDB & IMDB Configuration
# ==========================================
TMDB_API_KEY = environ.get("TMDB_API_KEY", "")  # Get your key from https://www.themoviedb.org/
IMDB = is_enabled((environ.get('IMDB', "False")), False)
AUTO_FFILTER = is_enabled((environ.get('AUTO_FFILTER', "True")), True)
AUTO_DELETE = is_enabled((environ.get('AUTO_DELETE', "True")), True)
DELETE_TIME = int(environ.get("DELETE_TIME", "300"))  
LINK_MODE = is_enabled((environ.get('LINK_MODE', "True")), True)
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", f"{script.CAPTION}")
BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", CUSTOM_FILE_CAPTION)
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", f"{script.IMDB_TEMPLATE_TXT}")
LONG_IMDB_DESCRIPTION = is_enabled(environ.get("LONG_IMDB_DESCRIPTION", "False"), False)
SPELL_CHECK_REPLY = is_enabled(environ.get("SPELL_CHECK_REPLY", "True"), True)
MAX_LIST_ELM = environ.get("MAX_LIST_ELM", None)
INDEX_REQ_CHANNEL = int(environ.get('INDEX_REQ_CHANNEL', LOG_CHANNEL))
FILE_STORE_CHANNEL = [int(ch) for ch in (environ.get('FILE_STORE_CHANNEL', '')).split()]
MELCOW_NEW_USERS = is_enabled((environ.get('MELCOW_NEW_USERS', "False")), False)
PROTECT_CONTENT = is_enabled((environ.get('PROTECT_CONTENT', "False")), True)
PM_SEARCH = is_enabled(environ.get('PM_SEARCH', 'True'), True) 
EMOJI_MODE = is_enabled(environ.get('EMOJI_MODE', 'False'), False) 

LANGUAGES = ["malayalam", "", "tamil", "", "english", "", "hindi", "", "telugu", "", "kannada", "", "gujarati", "", "marathi", "", "punjabi", ""]
QUALITIES = ["240p", "", "360P", "", "480P", "", "540P", "", "720P", "", "1080P", "", "1440P", "", "2160P", ""]
SEASONS = ["s01" , "s02" , "s03" , "s04", "s05" , "s06" , "s07" , "s08" , "s09" , "s10"]


NO_PORT = is_enabled(environ.get('NO_PORT', 'False'), False)
HAS_SSL = is_enabled(getenv('HAS_SSL', 'False'), False)
APP_NAME = None
ON_HEROKU = 'DYNO' in environ
if ON_HEROKU:
    APP_NAME = environ.get('APP_NAME')
BIND_ADRESS = str(getenv('WEB_SERVER_BIND_ADDRESS', '0.0.0.0'))
# Public base URL for stream links and the keepalive ping. "" when not
# configured - never http://0.0.0.0/, which the old ping_loop hit.
if ON_HEROKU and APP_NAME:
    FQDN = APP_NAME + '.herokuapp.com'
else:
    FQDN = str(getenv('FQDN', '') or '')
if FQDN:
    URL = ("https://" if HAS_SSL or ON_HEROKU or NO_PORT else "http://") + FQDN + "/"
else:
    URL = ""

SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
WORKERS = int(environ.get('WORKERS', '4'))
SESSION_NAME = str(environ.get('SESSION_NAME', 'SilentXBotz'))
MULTI_CLIENT = False
name = str(environ.get('name', 'SilentX'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes


REACTIONS = ["🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏", "😛", "😈", "🎉", "⚡️", "🫡", "🤓", "😎", "🏆", "🔥", "🤭", "🌚", "🆒", "👻", "😁"]

STAR_PREMIUM_PLANS = {
    1: "7day",
    30: "15day",    
    60: "1month", 
    120: "2month",   
}

Bot_cmds = {
    "start": "ꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ",
    "trendlist": "ɢᴇᴛ ᴛᴏᴘ ꜱᴇᴀʀᴄʜ ʟɪꜱᴛ",
    "myplan" : "ᴄʜᴇᴄᴋ ᴘʀᴇᴍɪᴜᴍ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ",
    "plan" :"ᴄʜᴇᴄᴋ ᴘʀᴇᴍɪᴜᴍ ᴘʀɪᴄᴇ",
    "settings": "ᴄʜᴀɴɢᴇ sᴇᴛᴛɪɴɢs",
    "group_cmd": "ᴅᴇʟᴇᴛᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ꜰɪʟᴇ ꜰʀᴏᴍ ᴅʙ.",
    "admin_cmd": "ᴅᴇʟᴇᴛᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ꜰɪʟᴇ ꜰʀᴏᴍ ᴅʙ.",
    "details": "ꜱᴇᴇ ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ",
    "reset_group": "ʀᴇꜱᴇᴛ ɢʀᴏᴜᴘ ꜱᴇᴛᴛɪɴɢꜱ", 
    "stats": "ᴄʜᴇᴄᴋ ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ.",
    "delete": "ᴅᴇʟᴇᴛᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ꜰɪʟᴇ ꜰʀᴏᴍ ᴅʙ.",
    "movie_update": "ᴏɴ ᴏғғ ᴀᴄᴄᴏʀᴅɪɴɢ ʏᴏᴜʀ ɴᴇᴇᴅᴇᴅ...",
    "pm_search": "ᴘᴍ sᴇᴀʀᴄʜ ᴏɴ ᴏғғ ᴀᴄᴄᴏʀᴅɪɴɢ ʏᴏᴜʀ ɴᴇᴇᴅᴇᴅ...",
    "restart": "ʀᴇꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ."
}

#Don't Change Anything Here
if MULTIPLE_DB == False:
    DATABASE_URI = DATABASE_URI
    DATABASE_URI2 = DATABASE_URI
else:
    DATABASE_URI = DATABASE_URI
    DATABASE_URI2 = DATABASE_URI2
