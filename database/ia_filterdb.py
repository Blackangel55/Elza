import logging
from struct import pack
import re
import base64
import asyncio
from typing import Dict, List, Tuple, Optional
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from pymongo import UpdateOne
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import *
from utils import get_settings, save_group_settings
from collections import defaultdict
from logging_helper import LOGGER
from datetime import datetime, timedelta
from functools import lru_cache

# Cache configuration
_db_stats_cache_primary = {
    "timestamp": None,
    "primary_size": 0
}
_db_stats_cache_secondary = {
    "timestamp": None,
    "primary_size": 0
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

processed_movies = set()

MONGODB_SIZE_LIMIT = (512 * 1024 * 1024) - (80 * 1024 * 1024) 

# Optimized MongoDB connections with connection pooling
client = AsyncIOMotorClient(
    DATABASE_URI,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=45000,
    connectTimeoutMS=10000,
    serverSelectionTimeoutMS=10000
)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

client2 = AsyncIOMotorClient(
    DATABASE_URI2,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=45000,
    connectTimeoutMS=10000,
    serverSelectionTimeoutMS=10000
)
db2 = client2[DATABASE_NAME]
instance2 = Instance.from_db(db2)

# Pre-compiled regex patterns for file name cleaning
SPECIAL_CHARS_LIST = [
    '@', '-', '.', '#', '+', '$', '%', '^', '*', '(', ')', 
    '~', '`', ',', ';', ':', "'", '"', '!', '?', '/', '<', 
    '>', '[', ']', '{', '}', '=', '|', '\\'
]

SPECIAL_CHARS_PATTERN = re.compile('[' + ''.join(re.escape(c) for c in SPECIAL_CHARS_LIST) + ']+')

KEYWORDS_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(keyword) for keyword in ['_', 'MoviiWrld', 'Smile_Upload', 'XDMovies', '4kHdHub', 'HDHub4u']) + r')\b',
    flags=re.IGNORECASE
)
SPACES_PATTERN = re.compile(r'\s+')

# Search result cache
class SearchCache:
    def __init__(self, ttl_minutes=5, max_size=1000):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Tuple]:
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.utcnow() - timestamp < self.ttl:
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Tuple):
        if len(self.cache) >= self.max_size:
            oldest_keys = sorted(
                self.cache.keys(), 
                key=lambda k: self.cache[k][1]
            )[:int(self.max_size * 0.1)]
            for k in oldest_keys:
                del self.cache[k]
        
        self.cache[key] = (value, datetime.utcnow())
    
    def clear(self):
        self.cache.clear()

search_cache = SearchCache(ttl_minutes=5, max_size=1000)

@lru_cache(maxsize=1000)
def get_compiled_regex(query: str):
    """Cache compiled regex patterns to avoid recompilation"""
    query = query.strip()
    
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*')
    
    try:
        return re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception as e:
        logger.error(f"Regex compilation error for '{query}': {e}")
        return None

@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    added_on = fields.DateTimeField(allow_none=True)
    
    class Meta:
        indexes = (
            '$file_name',
            [('file_name', 1), ('file_type', 1)],
            [('caption', 1)],
            [('file_type', 1)],
        )
        collection_name = COLLECTION_NAME

@instance2.register
class Media2(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    added_on = fields.DateTimeField(allow_none=True)
    
    class Meta:
        indexes = (
            '$file_name',
            [('file_name', 1), ('file_type', 1)],
            [('caption', 1)],
            [('file_type', 1)],
        )
        collection_name = COLLECTION_NAME

async def check_db_size(db, cache):
    try:
        now = datetime.utcnow()
        cache_stale = cache["timestamp"] is None or \
                      (now - cache["timestamp"] > timedelta(minutes=10))
        if not cache_stale:
            return cache["primary_size"]
        dbstats = await db.command("dbStats")
        db_size = dbstats['dataSize']
        db_size_mb = db_size / (1024 * 1024) 
        cache["primary_size"] = db_size_mb
        cache["timestamp"] = now
        return db_size_mb
    except Exception as e:
        LOGGER.error(f"Error Checking Database Size: {e}")
        return 0

async def save_file(media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    
    file_name = SPECIAL_CHARS_PATTERN.sub(" ", str(media.file_name))
    file_name = KEYWORDS_PATTERN.sub(" ", file_name)
    file_name = SPACES_PATTERN.sub(" ", file_name).strip()

    primary_db_size = await check_db_size(db, _db_stats_cache_primary)
    use_secondary = False
    saveMedia = Media

    if MULTIPLE_DB and primary_db_size >= DB_CHANGE_LIMIT:
        LOGGER.info("Primary Database Is Low On Space. Switching To Secondary DB.")
        saveMedia = Media2
        use_secondary = True
            
    try:
        file = saveMedia(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
            added_on=datetime.utcnow(),
        )
        await file.commit()
    except DuplicateKeyError:
        LOGGER.error(f'{file_name} Is Already Saved In {"Secondary" if use_secondary else "Primary"} Database')
        return False, 0
    except ValidationError as e:
        LOGGER.error(f'Validation Error While Saving File: {e}')
        return False, 2
    else:
        LOGGER.info(f'{file_name} Saved Successfully In {"Secondary" if use_secondary else "Primary"} Database')
        return True, 1

async def backfill_added_on(batch_size=500):
    targets = [(db, "primary")]
    if MULTIPLE_DB:
        targets.append((db2, "secondary"))
    for target_db, label in targets:
        collection = target_db[COLLECTION_NAME]
        try:
            missing = await collection.count_documents({"added_on": None})
        except Exception as e:
            LOGGER.warning(f"added_on backfill ({label}): count failed: {e}")
            continue
        if not missing:
            continue
        LOGGER.info(f"added_on backfill ({label}): stamping {missing} files...")
        try:
            # Newest missing row ends up ~now; older rows go back one
            # second each, so the timestamps keep the true insertion order.
            base = datetime.utcnow() - timedelta(seconds=missing)
            stamped = 0
            while True:
                ids = [doc["_id"] async for doc in
                       collection.find({"added_on": None}, {"_id": 1}).sort("$natural", 1).limit(batch_size)]
                if not ids:
                    break
                ops = [UpdateOne({"_id": file_id}, {"$set": {"added_on": base + timedelta(seconds=stamped + i)}})
                       for i, file_id in enumerate(ids)]
                await collection.bulk_write(ops)
                stamped += len(ids)
            LOGGER.info(f"added_on backfill ({label}): stamped {stamped} files.")
        except Exception as e:
            LOGGER.warning(f"added_on backfill ({label}) failed: {e}")

def _text_search_terms(query: str):
    terms = re.sub(r'[^A-Za-z0-9 ]+', ' ', query or '')
    terms = re.sub(r'\s+', ' ', terms).strip()
    return terms or None


# Words that carry no meaning on their own in a title: filenames often
# drop them ("Odyssey 2026" for "The Odyssey 2026"), so they must never
# be required for a file to match.
_TITLE_STOP_WORDS = {"the", "a", "an", "and", "or", "of", "to", "in", "is", "for", "on", "with", "by", "at", "from", "as"}
_YEAR_RE = re.compile(r'(19|20)\d\d')


def _split_terms(query: str):
    """Split a query into title words (no stop words, no year) and years."""
    words = re.sub(r'[^A-Za-z0-9 ]+', ' ', query or '').split()
    years = [w for w in words if _YEAR_RE.fullmatch(w)]
    titles = [w for w in words
              if len(w) >= 2
              and w.lower() not in _TITLE_STOP_WORDS
              and not _YEAR_RE.fullmatch(w)]
    return titles, years


def _merge_newest(*lists, limit):
    """Merge result lists from both databases, newest file first."""
    merged = [f for lst in lists for f in lst]
    merged.sort(key=lambda f: getattr(f, 'added_on', None) or datetime.min, reverse=True)
    return merged[:limit]


async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    if chat_id is not None:
        settings = await get_settings(int(chat_id))
        try:
            max_results = 10 if settings.get('max_btn') else int(MAX_B_TN)
        except KeyError:
            await save_group_settings(int(chat_id), 'max_btn', False)
            settings = await get_settings(int(chat_id))
            max_results = 10 if settings.get('max_btn') else int(MAX_B_TN)

    cache_key = f"{chat_id}:{query}:{file_type}:{max_results}:{offset}"
    cached_result = search_cache.get(cache_key)
    if cached_result:
        return cached_result

    if max_results % 2 != 0:
        logger.info(f"Since max_results Is An Odd Number ({max_results}), Bot Will Use {max_results + 1} As max_results To Make It Even.")
        max_results += 1

    projection = {
        'file_id': 1,
        'file_ref': 1,
        'file_name': 1,
        'file_size': 1,
        'file_type': 1,
        'caption': 1,
        'mime_type': 1,
        'added_on': 1
    }

    search_queries = []
    original_query = query.strip()
    
    search_queries.append(original_query)
    
    query_with_spaces = SPECIAL_CHARS_PATTERN.sub(' ', original_query)
    query_with_spaces = SPACES_PATTERN.sub(' ', query_with_spaces).strip()
    if query_with_spaces != original_query:
        search_queries.append(query_with_spaces)
    
    query_no_special = original_query
    for char in SPECIAL_CHARS_LIST:
        query_no_special = query_no_special.replace(char, '')
    query_no_special = SPACES_PATTERN.sub(' ', query_no_special).strip()
    if query_no_special and query_no_special not in search_queries:
        search_queries.append(query_no_special)
    text_terms = _text_search_terms(original_query)
    if text_terms:
        titles, years = _split_terms(original_query)
        sort_spec = [('added_on', -1)]   # newest first, always
        attempts = []

        def _with_type(f):
            if file_type:
                f['file_type'] = file_type
            return f

        if titles:
            # $text uses the index to find candidates by title words only.
            # Every title word AND the year must then appear in the file name.
            title_text = ' '.join(titles)
            title_res = [{'file_name': re.compile(re.escape(t), re.IGNORECASE)} for t in titles]
            year_res = [{'file_name': re.compile(r'(?<!\d)' + y + r'(?!\d)')} for y in years]
            attempts.append(_with_type({'$text': {'$search': title_text}, '$and': title_res + year_res}))
            if years:
                # No file with that year: show the title of any year, newest first.
                attempts.append(_with_type({'$text': {'$search': title_text}, '$and': title_res}))
        else:
            # Only a year or only stop words: plain text search, newest first.
            attempts.append(_with_type({'$text': {'$search': text_terms}}))

        for text_filter in attempts:
            try:
                if MULTIPLE_DB:
                    c1, c2, f1, f2 = await asyncio.gather(
                        Media.count_documents(text_filter),
                        Media2.count_documents(text_filter),
                        Media.find(text_filter, projection).sort(sort_spec).skip(offset).limit(max_results).to_list(length=max_results),
                        Media2.find(text_filter, projection).sort(sort_spec).skip(offset).limit(max_results).to_list(length=max_results)
                    )
                    total_results = c1 + c2
                    files = _merge_newest(f1, f2, limit=max_results)
                else:
                    total_results = await Media.count_documents(text_filter)
                    files = await Media.find(text_filter, projection).sort(sort_spec).skip(offset).limit(max_results).to_list(length=max_results)
                if files:
                    logger.info(f"✅ Found {len(files)} results with $text search: '{text_terms}'")
                    next_offset = offset + len(files)
                    if next_offset >= total_results:
                        next_offset = ''
                    result = (files, next_offset, total_results)
                    search_cache.set(cache_key, result)
                    return result
            except Exception as e:
                logger.warning(f"$text search failed ({e}) - trying next")
        logger.info(f"❌ No $text results for: '{text_terms}' - falling back to regex")

    files = []
    total_results = 0
    next_offset = ''
    
    for idx, search_query in enumerate(search_queries, 1):
        if not search_query:
            continue
            
        logger.info(f"🔍 Search attempt {idx}/{len(search_queries)}: '{search_query}'")
        
        regex = get_compiled_regex(search_query)
        if not regex:
            logger.warning(f"Failed to compile regex for: '{search_query}'")
            continue

        if USE_CAPTION_FILTER:
            filter_query = {'$or': [{'file_name': regex}, {'caption': regex}]}
        else:
            filter_query = {'file_name': regex}
        
        if file_type:
            filter_query['file_type'] = file_type

        if MULTIPLE_DB:
            total_results_task1 = Media.count_documents(filter_query)
            total_results_task2 = Media2.count_documents(filter_query)
            
            cursor1 = Media.find(filter_query, projection).sort('$natural', -1).skip(offset).limit(max_results)
            cursor2 = Media2.find(filter_query, projection).sort('$natural', -1).skip(offset).limit(max_results)
            
            results = await asyncio.gather(
                total_results_task1,
                total_results_task2,
                cursor1.to_list(length=max_results),
                cursor2.to_list(length=max_results)
            )
            
            total_results = results[0] + results[1]
            files1 = results[2]
            files2 = results[3]
            
            files = (files1 + files2)[:max_results]
        else:
            total_results = await Media.count_documents(filter_query)
            cursor1 = Media.find(filter_query, projection).sort('$natural', -1).skip(offset).limit(max_results)
            files = await cursor1.to_list(length=max_results)
        
        if files:
            logger.info(f"✅ Found {len(files)} results with query: '{search_query}' (attempt {idx})")
            break
        else:
            logger.info(f"❌ No results for: '{search_query}'")
    
    next_offset = offset + len(files)
    if next_offset >= total_results:
        next_offset = ''
    
    result = (files, next_offset, total_results)
    
    if files:
        search_cache.set(cache_key, result)
    
    return result

async def get_bad_files(query, file_type=None):
    regex = get_compiled_regex(query)
    if not regex:
        return [], 0
    
    if USE_CAPTION_FILTER:
        filter_query = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter_query = {'file_name': regex}
    
    if file_type:
        filter_query['file_type'] = file_type
    
    if MULTIPLE_DB:
        count_task1 = Media.count_documents(filter_query)
        count_task2 = Media2.count_documents(filter_query)
        counts = await asyncio.gather(count_task1, count_task2)
        count1, count2 = counts[0], counts[1]
        
        cursor1 = Media.find(filter_query).sort('$natural', -1)
        cursor2 = Media2.find(filter_query).sort('$natural', -1)
        
        files_results = await asyncio.gather(
            cursor1.to_list(length=count1),
            cursor2.to_list(length=count2)
        )
        
        files = files_results[0] + files_results[1]
    else:
        count = await Media.count_documents(filter_query)
        cursor1 = Media.find(filter_query).sort('$natural', -1)
        files = await cursor1.to_list(length=count)
    
    total_results = len(files)
    return files, total_results

async def get_file_details(query):
    filter_query = {'file_id': query}
    
    if MULTIPLE_DB:
        cursor1 = Media.find(filter_query)
        cursor2 = Media2.find(filter_query)
        
        results = await asyncio.gather(
            cursor1.to_list(length=1),
            cursor2.to_list(length=1)
        )
        
        filedetails = results[0] if results[0] else results[1]
    else:
        cursor = Media.find(filter_query)
        filedetails = await cursor.to_list(length=1)
    
    return filedetails

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref

async def siletxbotz_fetch_media(limit: int) -> List[dict]:
    try:
        projection = {'file_name': 1, 'caption': 1}
        
        if MULTIPLE_DB:
            db_size = await check_db_size(db, _db_stats_cache_primary)
            if db_size > DB_CHANGE_LIMIT:
                cursor = Media2.find({}, projection).sort("$natural", -1).limit(limit)
                files = await cursor.to_list(length=limit)
                return files
        
        cursor = Media.find({}, projection).sort("$natural", -1).limit(limit)
        files = await cursor.to_list(length=limit)
        return files
    except Exception as e:
        LOGGER.error(f"Error in siletxbotz_fetch_media: {e}")
        return []

async def silentxbotz_clean_title(filename: str, is_series: bool = False) -> str:
    try:
        year_match = re.search(r"^(.*?(\d{4}|\(\d{4}\)))", filename, re.IGNORECASE)
        if year_match:
            title = year_match.group(1).replace('(', '').replace(')', '') 
            return re.sub(r"[._\-\[\]@()]+", " ", title).strip().title()
        
        if is_series:
            season_match = re.search(r"(.*?)(?:S(\d{1,2})|Season\s*(\d+)|Season(\d+))(?:\s*Combined)?", filename, re.IGNORECASE)
            if season_match:
                title = season_match.group(1).strip()
                season = season_match.group(2) or season_match.group(3) or season_match.group(4)
                title = re.sub(r"[._\-\[\]@()]+", " ", title).strip().title()
                return f"{title} S{int(season):02}"
        
        return re.sub(r"[._\-\[\]@()]+", " ", filename).strip().title()
    except Exception as e:
        logger.error(f"Error in truncate_title: {e}")
        return filename

async def siletxbotz_get_movies(limit: int = 20) -> List[str]:
    try:
        cursor = await siletxbotz_fetch_media(limit * 2)
        results = set()
        pattern = r"(?:s\d{1,2}|season\s*\d+|season\d+)(?:\s*combined)?(?:e\d{1,2}|episode\s*\d+)?\b"
        
        for file in cursor:
            file_name = getattr(file, "file_name", "")
            caption = getattr(file, "caption", "")
            
            if not (re.search(pattern, file_name, re.IGNORECASE) or re.search(pattern, caption, re.IGNORECASE)):
                title = await silentxbotz_clean_title(file_name)
                results.add(title)
            
            if len(results) >= limit:
                break
        
        return sorted(list(results))[:limit]
    except Exception as e:
        logger.error(f"Error in siletxbotz_get_movies: {e}")
        return []

async def siletxbotz_get_series(limit: int = 30) -> Dict[str, List[int]]:
    try:
        cursor = await siletxbotz_fetch_media(limit * 5)
        grouped = defaultdict(list)
        pattern = r"(.*?)(?:S(\d{1,2})|Season\s*(\d+)|Season(\d+))(?:\s*Combined)?(?:E(\d{1,2})|Episode\s*(\d+))?\b"
        
        for file in cursor:
            file_name = getattr(file, "file_name", "")
            caption = getattr(file, "caption", "")
            
            match = None
            if file_name:
                match = re.search(pattern, file_name, re.IGNORECASE)
            if not match and caption:
                match = re.search(pattern, caption, re.IGNORECASE)
            
            if match:
                title = await silentxbotz_clean_title(match.group(1), is_series=True)
                season = int(match.group(2) or match.group(3) or match.group(4))
                grouped[title].append(season)
        
        return {title: sorted(set(seasons))[:10] for title, seasons in grouped.items() if seasons}
    except Exception as e:
        logger.error(f"Error in siletxbotz_get_series: {e}")
        return []

def clear_search_cache():
    """Clear the search cache - useful after bulk updates"""
    search_cache.clear()
    get_compiled_regex.cache_clear()
    logger.info("Search cache cleared successfully")
