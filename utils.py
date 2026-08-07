import logging
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from info import *
import asyncio
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from pyrogram import enums
from typing import Union
from Script import script
import pytz
import random
import re
import os
from datetime import datetime, date, time, timedelta
import string
from typing import List
from database.users_chats_db import db
from bs4 import BeautifulSoup
import requests
import aiohttp
from shortzy import Shortzy
import http.client
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(
    r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))"
)

# ============================================
# TMDB Configuration
# ============================================
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")  # Set your TMDB API key
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"
TMDB_SESSION = None

async def get_tmdb_session():
    """Get or create TMDB aiohttp session"""
    global TMDB_SESSION
    if TMDB_SESSION is None or TMDB_SESSION.closed:
        TMDB_SESSION = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Accept": "application/json"}
        )
    return TMDB_SESSION

async def close_tmdb_session():
    """Close TMDB session"""
    global TMDB_SESSION
    if TMDB_SESSION and not TMDB_SESSION.closed:
        await TMDB_SESSION.close()

# ============================================
# TMDB API Functions
# ============================================
async def tmdb_search(query, year=None):
    """Search for movies and TV shows on TMDB"""
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY not set!")
        return None
    
    session = await get_tmdb_session()
    results = []
    
    # Search Movies
    try:
        params = {
            "api_key": TMDB_API_KEY,
            "query": query,
            "include_adult": "false"
        }
        if year:
            params["year"] = year
            
        async with session.get(f"{TMDB_BASE_URL}/search/movie", params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data.get("results", []):
                    item["_type"] = "movie"
                    results.append(item)
    except Exception as e:
        logger.error(f"TMDB movie search error: {e}")
    
    # Search TV Shows
    try:
        params = {
            "api_key": TMDB_API_KEY,
            "query": query,
            "include_adult": "false"
        }
        if year:
            params["first_air_date_year"] = year
            
        async with session.get(f"{TMDB_BASE_URL}/search/tv", params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data.get("results", []):
                    item["_type"] = "tv"
                    results.append(item)
    except Exception as e:
        logger.error(f"TMDB TV search error: {e}")
    
    # Sort by popularity
    results.sort(key=lambda x: x.get("popularity", 0), reverse=True)
    return results

async def tmdb_get_details(media_id, media_type="movie"):
    """Get detailed info from TMDB including credits"""
    if not TMDB_API_KEY:
        return None
    
    session = await get_tmdb_session()
    
    try:
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits,external_ids"
        }
        url = f"{TMDB_BASE_URL}/{media_type}/{media_id}"
        
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        logger.error(f"TMDB details error: {e}")
    
    return None

async def tmdb_get_by_imdb_id(imdb_id):
    """Get TMDB ID from IMDB ID using find endpoint"""
    if not TMDB_API_KEY:
        return None
    
    session = await get_tmdb_session()
    
    try:
        params = {
            "api_key": TMDB_API_KEY,
            "external_source": "imdb_id"
        }
        url = f"{TMDB_BASE_URL}/find/{imdb_id}"
        
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("movie_results"):
                    return data["movie_results"][0]["id"], "movie"
                elif data.get("tv_results"):
                    return data["tv_results"][0]["id"], "tv"
    except Exception as e:
        logger.error(f"TMDB find by IMDB error: {e}")
    
    return None

# ============================================
# Main get_poster function (TMDB version)
# ============================================
async def get_poster(query, bulk=False, id=False, file=None):
    """
    Get movie/TV show info from TMDB
    Maintains same return format as IMDB version for compatibility
    """
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY not configured!")
        return None
    
    if not id:
        query = (query.strip()).lower()
        title = query
        year = None
        
        # Extract year from query
        year_match = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year_match:
            year = year_match[0]
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year_match = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year_match:
                year = year_match[0]
        
        # Detect if it's a TV show
        is_tv = bool(re.search(r'\b(s\d{1,2}|season\s*\d+|season\d+)\b', query, re.IGNORECASE))
        
        # Search TMDB
        search_results = await tmdb_search(title, year)
        
        if not search_results:
            return None
        
        # Filter results
        if year:
            filtered = [r for r in search_results if year in str(r.get("release_date", "") or r.get("first_air_date", ""))]
            if not filtered:
                filtered = search_results
        else:
            filtered = search_results
        
        # Prefer TV shows if query suggests series
        if is_tv:
            tv_results = [r for r in filtered if r.get("_type") == "tv"]
            if tv_results:
                filtered = tv_results
        
        if bulk:
            return filtered
        
        # Get the first result
        first_result = filtered[0]
        media_id = first_result["id"]
        media_type = first_result["_type"]
    else:
        # If ID is provided (could be TMDB or IMDB ID)
        if str(query).startswith("tt"):
            # It's an IMDB ID, convert to TMDB
            result = await tmdb_get_by_imdb_id(query)
            if not result:
                return None
            media_id, media_type = result
        else:
            # Assume it's a TMDB ID
            media_id = query
            # Default to movie, could be enhanced
            media_type = "movie"
    
    # Get detailed info
    details = await tmdb_get_details(media_id, media_type)
    
    if not details:
        return None
    
    # Extract credits
    credits = details.get("credits", {})
    cast_list = credits.get("cast", [])[:10]
    crew_list = credits.get("crew", [])
    
    # Extract specific crew roles
    directors = [c["name"] for c in crew_list if c.get("job") == "Director"]
    writers = [c["name"] for c in crew_list if c.get("job") in ["Writer", "Screenplay", "Story"]]
    producers = [c["name"] for c in crew_list if c.get("job") == "Producer"]
    composers = [c["name"] for c in crew_list if c.get("department") == "Music"]
    cinematographers = [c["name"] for c in crew_list if c.get("job") == "Director of Photography"]
    
    # Get release date
    release_date = details.get("release_date") or details.get("first_air_date") or "N/A"
    year = details.get("release_date", "")[:4] if details.get("release_date") else (details.get("first_air_date", "")[:4] if details.get("first_air_date") else "N/A")
    
    # Get poster URL
    poster_path = details.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None
    
    # Get plot
    plot = details.get("overview", "N/A")
    if plot and len(plot) > 800:
        plot = plot[:800] + "..."
    
    # Get IMDB ID if available
    external_ids = details.get("external_ids", {})
    imdb_id = external_ids.get("imdb_id", "")
    
    # Get genres
    genres = [g["name"] for g in details.get("genres", [])]
    
    # Get countries
    if media_type == "movie":
        countries = [c["name"] for c in details.get("production_countries", [])]
        runtime = details.get("runtime")
    else:
        countries = [c["name"] for c in details.get("origin_country", [])]
        runtime = details.get("episode_run_time", [None])[0]
    
    # Get languages
    if media_type == "movie":
        languages = [l["english_name"] for l in details.get("spoken_languages", [])]
    else:
        languages = [details.get("original_language", "").upper()]
    
    # Get seasons (for TV shows)
    seasons = details.get("number_of_seasons")
    
    # Get kind
    kind = "tv series" if media_type == "tv" else "movie"
    
    # Build return dict (same format as IMDB version)
    return {
        'title': details.get("title") or details.get("name", "N/A"),
        'votes': details.get("vote_count", "N/A"),
        "aka": details.get("original_title") or details.get("original_name", "N/A"),
        "seasons": seasons,
        "box_office": f"${details.get('revenue', 0):,}" if details.get("revenue") else "N/A",
        'localized_title': details.get("title") or details.get("name", "N/A"),
        'kind': kind,
        "imdb_id": imdb_id if imdb_id else f"tmdb:{media_id}",
        "cast": ', '.join([c["name"] for c in cast_list]) if cast_list else "N/A",
        "runtime": f"{runtime} min" if runtime else "N/A",
        "countries": ', '.join(countries) if countries else "N/A",
        "certificates": "N/A",  # TMDB free API doesn't provide this
        "languages": ', '.join(languages) if languages else "N/A",
        "director": ', '.join(directors) if directors else "N/A",
        "writer": ', '.join(writers) if writers else "N/A",
        "producer": ', '.join(producers) if producers else "N/A",
        "composer": ', '.join(composers) if composers else "N/A",
        "cinematographer": ', '.join(cinematographers) if cinematographers else "N/A",
        "music_team": ', '.join(composers) if composers else "N/A",
        "distributors": "N/A",  # Not available in free TMDB API
        'release_date': release_date,
        'year': year if year != "N/A" else "N/A",
        'genres': ', '.join(genres) if genres else "N/A",
        'poster': poster_url,
        'plot': plot,
        'rating': str(details.get("vote_average", "N/A")),
        'url': f"https://www.themoviedb.org/{media_type}/{media_id}" if not imdb_id else f"https://www.imdb.com/title/{imdb_id}"
    }


# ============================================
# Rest of utils.py remains the same
# ============================================

BANNED = {}
SMART_OPEN = '"'
SMART_CLOSE = '"'
START_CHAR = ('\'', '"', SMART_OPEN)


class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    SETTINGS = {}
    ME = None
    CURRENT = int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    B_LINK = None
    GETALL = {}
    SHORT = {}
    IMDB_CAP = {}
    VERIFICATIONS = {}


async def is_req_subscribed(bot, query, chnl):
    if await db.find_join_req(query.from_user.id, chnl):
        return True
    try:
        user = await bot.get_chat_member(chnl, query.from_user.id)
        if user.status != enums.ChatMemberStatus.BANNED:
            return True
    except UserNotParticipant:
        pass
    except Exception as e:
        print(e)
    return False


async def is_subscribed(bot, user_id, channel_id):
    try:
        user = await bot.get_chat_member(channel_id, user_id)
    except UserNotParticipant:
        pass
    except Exception as e:
        pass
    else:
        if user.status != enums.ChatMemberStatus.BANNED:
            return True
    return False


async def is_check_admin(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except:
        return False


async def users_broadcast(user_id, message, is_pin):
    try:
        m = await message.copy(chat_id=user_id)
        if is_pin:
            await m.pin(both_sides=True)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await users_broadcast(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        LOGGER.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        LOGGER.info(f"{user_id} -Blocked the bot.")
        await db.delete_user(user_id)
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        LOGGER.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"


async def groups_broadcast(chat_id, message, is_pin):
    try:
        m = await message.copy(chat_id=chat_id)
        if is_pin:
            try:
                await m.pin()
            except:
                pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await groups_broadcast(chat_id, message)
    except Exception as e:
        await db.delete_chat(chat_id)
        return "Error"


async def junk_group(chat_id, message):
    try:
        kk = await message.copy(chat_id=chat_id)
        await kk.delete(True)
        return True, "Succes", 'mm'
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await junk_group(chat_id, message)
    except Exception as e:
        await db.delete_chat(int(chat_id))
        LOGGER.info(f"{chat_id} - PeerIdInvalid")
        return False, "deleted", f'{e}\n\n'


async def clear_junk(user_id, message):
    try:
        key = await message.copy(chat_id=user_id)
        await key.delete(True)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await clear_junk(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        LOGGER.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        LOGGER.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        LOGGER.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"


async def get_status(bot_id):
    try:
        return await db.movie_update_status(bot_id) or False
    except Exception as e:
        logging.error(f"Error in get_movie_update_status: {e}")
        return False


async def search_gagala(text):
    usr_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/61.0.3163.100 Safari/537.36'
    }
    text = text.replace(" ", '+')
    url = f'https://www.google.com/search?q={text}'
    response = requests.get(url, headers=usr_agent)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    titles = soup.find_all('h3')
    return [title.getText() for title in titles]


async def get_shortlink(link, grp_id, is_second_shortener=False, is_third_shortener=False):
    settings = await get_settings(grp_id)
    if is_third_shortener:
        api, site = settings['api_three'], settings['shortner_three']
    else:
        if is_second_shortener:
            api, site = settings['api_two'], settings['shortner_two']
        else:
            api, site = settings['api'], settings['shortner']
    shortzy = Shortzy(api, site)
    try:
        link = await shortzy.convert(link)
    except Exception as e:
        link = await shortzy.get_quick_link(link)
    return link


async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS.update({group_id: settings})
    return settings


async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current.update({key: value})
    temp.SETTINGS.update({group_id: current})
    await db.update_settings(group_id, current)


def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


def silent_size(size):
    size = float(size)
    if size >= 1024 ** 3:
        return "%.2f GB" % (size / (1024 ** 3))
    else:
        return "%.2f MB" % (size / (1024 ** 2))


def extract_tag(file_name: str) -> str:
    file_name = file_name.lower()
    file_name = re.sub(r'[\._\-]+', ' ', file_name)

    patterns = [
        r'\b(?:s|season)\s*0*(\d{1,2})\s*(?:e|ep|episode)\s*0*(\d{1,2})\b',
        r'\b(\d{1,2})\s*(?:x|ep|episode)\s*0*(\d{1,2})\b',
        r'\bs0*(\d{1,2})(?:e|ep)0*(\d{1,2})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, file_name)
        if match:
            season = int(match.group(1))
            episode = int(match.group(2))
            return f"S{season:02d}E{episode:02d} •"

    season_match = re.search(r'\b(?:s|season)\s*0*(\d{1,2})\b', file_name)
    if season_match:
        season = int(season_match.group(1))
        return f"S{season:02d} •"

    episode_match = re.search(r'\b(?:ep|e|episode)\s*0*(\d{1,3})\b', file_name)
    if episode_match:
        episode = int(episode_match.group(1))
        return f"E{episode:02d} •"

    quality_match = re.search(r'\b(2160p|1080p|720p|540p|480p|360p|240p|4k)\b', file_name)
    if quality_match:
        return f"{quality_match.group(1)} •"

    return ""


def extract_request_content(message_text):
    match = re.search(r"<u>(.*?)</u>", message_text)
    if match:
        return match.group(1).strip()
    match = re.search(r"📝 ʀᴇǫᴜᴇꜱᴛ ?: ?(.*?)(?:\n|$)", message_text)
    if match:
        return match.group(1).strip()
    return message_text.strip()


def clean_filename(file_name):
    file_name = re.sub(r'http\S+', '', re.sub(r'@\w+|#\w+', '', file_name))
    file_name = re.sub(r"(_|\-|\.|\+)", " ", file_name)
    file_name = re.sub(r"[(){}\[\]:;\-!]", "", file_name)

    tag = extract_tag(file_name)
    if tag:
        file_name = file_name.replace(tag, "").strip()

    return file_name


def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj


def extract_user(message: Message) -> Union[int, str]:
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.id

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1 and
            message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):
            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)


def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    elif MAX_LIST_ELM:
        k = k[:int(MAX_LIST_ELM)]
        return ' '.join(f'{elem}, ' for elem in k)
    else:
        return ' '.join(f'{elem}, ' for elem in k)


def last_online(from_user):
    time = ""
    if from_user.is_bot:
        time += "🤖 Bot :("
    elif from_user.status == enums.UserStatus.RECENTLY:
        time += "Recently"
    elif from_user.status == enums.UserStatus.LAST_WEEK:
        time += "Within the last week"
    elif from_user.status == enums.UserStatus.LAST_MONTH:
        time += "Within the last month"
    elif from_user.status == enums.UserStatus.LONG_AGO:
        time += "A long time ago :("
    elif from_user.status == enums.UserStatus.ONLINE:
        time += "Currently Online"
    elif from_user.status == enums.UserStatus.OFFLINE:
        time += from_user.last_online_date.strftime("%a, %d %b %Y, %H:%M:%S")
    return time


def split_quotes(text: str) -> List:
    if not any(text.startswith(char) for char in START_CHAR):
        return text.split(None, 1)
    counter = 1
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1
        elif text[counter] == text[0] or (text[0] == SMART_OPEN and text[counter] == SMART_CLOSE):
            break
        counter += 1
    else:
        return text.split(None, 1)
    key = remove_escapes(text[1:counter].strip())
    rest = text[counter + 1:].strip()
    if not key:
        key = text[0] + text[0]
    return list(filter(None, [key, rest]))


def gfilterparser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None


def parser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None


def remove_escapes(text: str) -> str:
    res = ""
    is_escaped = False
    for counter in range(len(text)):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
    return res


async def log_error(client, error_message):
    try:
        await client.send_message(
            chat_id=LOG_CHANNEL,
            text=f"<b>⚠️ Error Log:</b>\n<code>{error_message}</code>"
        )
    except Exception as e:
        print(f"Failed to log error: {e}")


def get_time(seconds):
    periods = [(' ᴅᴀʏs', 86400), (' ʜᴏᴜʀ', 3600), (' ᴍɪɴᴜᴛᴇ', 60), (' sᴇᴄᴏɴᴅ', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result


def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'


def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f'{int(period_value)}{period_name}')
    return ' '.join(result)


async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:].lstrip()
        if value:
            value = int(value)
        return value, unit
    value, unit = extract_value_and_unit(time_string)
    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0


async def get_cap(settings, remaining_seconds, files, query, total_results, search, offset):
    if settings["imdb"]:
        IMDB_CAP = temp.IMDB_CAP.get(query.from_user.id)
        if IMDB_CAP:
            cap = IMDB_CAP
            for file_num, file in enumerate(files, start=offset+1):
                cap += f"\n\n<b>{file_num}. <a href='https://telegram.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'>{get_size(file.file_size)}| {clean_filename(file.file_name)}</a></b>"
        else:
            tmdb_data = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
            if tmdb_data:
                TEMPLATE = script.IMDB_TEMPLATE_TXT
                cap = TEMPLATE.format(
                    qurey=search,
                    title=tmdb_data['title'],
                    votes=tmdb_data['votes'],
                    aka=tmdb_data["aka"],
                    seasons=tmdb_data["seasons"],
                    box_office=tmdb_data['box_office'],
                    localized_title=tmdb_data['localized_title'],
                    kind=tmdb_data['kind'],
                    imdb_id=tmdb_data["imdb_id"],
                    cast=tmdb_data["cast"],
                    runtime=tmdb_data["runtime"],
                    countries=tmdb_data["countries"],
                    certificates=tmdb_data["certificates"],
                    languages=tmdb_data["languages"],
                    director=tmdb_data["director"],
                    writer=tmdb_data["writer"],
                    producer=tmdb_data["producer"],
                    composer=tmdb_data["composer"],
                    cinematographer=tmdb_data["cinematographer"],
                    music_team=tmdb_data["music_team"],
                    distributors=tmdb_data["distributors"],
                    release_date=tmdb_data['release_date'],
                    year=tmdb_data['year'],
                    genres=tmdb_data['genres'],
                    poster=tmdb_data['poster'],
                    plot=tmdb_data['plot'],
                    rating=tmdb_data['rating'],
                    url=tmdb_data['url'],
                    **locals()
                )
                for file_num, file in enumerate(files, start=offset+1):
                    cap += f"\n\n<b>{file_num}. <a href='https://telegram.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'>{get_size(file.file_size)}| {clean_filename(file.file_name)}</a></b>"
            else:
                cap = f"<b>📂 ʜᴇʀᴇ ɪ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ <code>{search}</code></b>\n\n"
                for file_num, file in enumerate(files, start=offset+1):
                    cap += f"<b>{file_num}. <a href='https://telegram.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'>{get_size(file.file_size)}| {clean_filename(file.file_name)}\n\n</a></b>"
    else:
        cap = f"<b>📂 ʜᴇʀᴇ ɪ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ <code>{search}</code></b>\n\n"
        for file_num, file in enumerate(files, start=offset+1):
            cap += f"<b>{file_num}. <a href='https://telegram.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'>{get_size(file.file_size)}| {clean_filename(file.file_name)}\n\n</a></b>"
    return cap


async def group_setting_buttons(grp_id):
    settings = await get_settings(grp_id)
    buttons = [[
        InlineKeyboardButton('ʀᴇꜱᴜʟᴛ ᴘᴀɢᴇ', callback_data=f'setgs#button#{settings.get("button")}#{grp_id}',),
        InlineKeyboardButton('ʙᴜᴛᴛᴏɴ' if settings.get("button") else 'ᴛᴇxᴛ', callback_data=f'setgs#button#{settings.get("button")}#{grp_id}',),
    ], [
        InlineKeyboardButton('ꜰɪʟᴇ ꜱᴇᴄᴜʀᴇ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',),
        InlineKeyboardButton('ᴇɴᴀʙʟᴇ' if settings["file_secure"] else 'ᴅɪꜱᴀʙʟᴇ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',),
    ], [
        InlineKeyboardButton('ᴛᴍᴅʙ ᴘᴏꜱᴛᴇʀ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',),
        InlineKeyboardButton('ᴇɴᴀʙʟᴇ' if settings["imdb"] else 'ᴅɪꜱᴀʙʟᴇ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',),
    ], [
        InlineKeyboardButton('ᴡᴇʟᴄᴏᴍᴇ ᴍꜱɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',),
        InlineKeyboardButton('ᴇɴᴀʙʟᴇ' if settings["welcome"] else 'ᴅɪꜱᴀʙʟᴇ', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',),
    ], [
        InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',),
        InlineKeyboardButton('ᴇɴᴀʙʟᴇ' if settings["auto_delete"] else 'ᴅɪꜱᴀʙʟᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',),
    ], [
        InlineKeyboardButton('ᴍᴀx ʙᴜᴛᴛᴏɴꜱ', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',),
        InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',),
    ], [
        InlineKeyboardButton('ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴍᴏᴅᴇ', callback_data=f'verification_setgs#{grp_id}',),
    ], [
        InlineKeyboardButton('ʟᴏɢ ᴄʜᴀɴɴᴇʟ', callback_data=f'log_setgs#{grp_id}',),
        InlineKeyboardButton('ꜱᴇᴛ ᴄᴀᴘᴛɪᴏɴ', callback_data=f'caption_setgs#{grp_id}',),
    ], [
        InlineKeyboardButton('⇋ ᴄʟᴏꜱᴇ ꜱᴇᴛᴛɪɴɢꜱ ᴍᴇɴᴜ ⇋', callback_data='close_data')
    ]]
    return buttons
