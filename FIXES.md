# Elza (Lucia Filter Bot) — critical bug fixes

Original: `Elza-main.zip` (Lucia Filter Bot v4.2, fork of NBBotz/DreamXBotz
Auto_Filter_Bot). All changes below are in this folder; nothing else was
changed. Verified with `python3 -m py_compile` on every `.py` file and a
smoke test of `info.py` (see "Verified" at the bottom).

## 1. Double plugin loading — `bot.py`
Pyrogram already loads `plugins/` once via `plugins={"root": "plugins"}` in
`Lucia/Bot/__init__.py`. `bot.py` then re-imported every plugin file with
`importlib` after `SilentX.start()`, registering every handler a second
time (duplicate replies, double file indexing). The manual import loop,
`glob`, `importlib`, `sys`/`Path` imports are removed. Plugins load once.

## 2. `info.py` crashed on missing config — `info.py`
`int(environ.get('API_ID', ''))` / `int(environ.get('LOG_CHANNEL', ''))`
crashed with a bare `ValueError: invalid literal for int() with base 10: ''`.
Now `_required()` / `_int_env()` raise `Missing required environment
variable: API_ID` (etc.) naming the variable. Required: `API_ID`,
`API_HASH`, `BOT_TOKEN`, `DATABASE_URI`, `LOG_CHANNEL`, `BIN_CHANNEL`.

## 3. Dead `IS_VERIFY` toggle — `info.py`
Was `is_enabled('IS_VERIFY', False)` — the literal string, so the env var
was never read and verification could never be turned on. Now reads
`environ.get('IS_VERIFY', 'False')`. Same class of bug fixed for the
`bool(environ.get(...))` toggles (`PM_SEARCH`, `EMOJI_MODE`, `PAID_STREAM`,
`STREAM_MODE`, `NO_PORT`, `MOVIE_UPDATE_NOTIFICATION`, `NO_RESULTS_MSG`),
where `bool("False")` is `True` — they now use `is_enabled()`.

## 4. Duplicate `stream_handler` — `plugins/route.py`
Two handlers had the same name, so the second silently overwrote the
first. Renamed: `/watch/{path}` → `watch_handler`, `/{path}` → 
`download_handler`. Root route now returns "Elza Filter Bot".

## 5. Premium-expiry polling hammered MongoDB — `plugins/__init__.py`, `database/users_chats_db.py`
`check_expired_premium` looped with `sleep(1)` — two Mongo queries every
second, forever. It now polls every 60s. That alone would have broken
reminders, because `get_expiring_soon()` only matched users expiring in a
60-second window around now+10min. It now matches anyone expiring between
now and now+10min (the per-user reminder flag still prevents duplicates),
so a 60s poll cannot miss a reminder.

## 6. Previous owner's IDs and links — `info.py`, `plugins/pm_filter.py`, `Script.py`, templates
Hardcoded `-1001583883335` (BIN / movie-update / premium-log / verify-log
channels), `t.me/AM_FILMS`, `t.me/GUARDIANff`, `t.me/am_films` and
`@AMSearch1bot` are gone from code and user-visible text. Log channels now
fall back to `LOG_CHANNEL` when unset; `BIN_CHANNEL` / `LOG_CHANNEL` are
required; links are env vars (`SUPPORT_LNK`, `OWNER_LNK`, `CHNL_LNK`,
`GRP_LNK`, `UPDATE_CHANNEL_LNK`, `SUPPORT_CHAT`, `TUTORIAL*`). `MOVIE_UPDATE_CHANNEL`
unset = no update posts (guard in `plugins/channel.py`). Set your own
values in `example.env` before running — Support/owner buttons use
`SUPPORT_LNK` / `OWNER_LNK` and will have an empty URL until you set them.

## 7. Ping loop + FQDN/URL — `bot.py`, `info.py`, `Lucia/util/keepalive.py`
The threading `ping_loop` hit `URL` every 120s, and with no `FQDN` set
`URL` was `http://0.0.0.0/`. Removed. `FQDN`/`URL` is now one clean block
(no duplicated `ON_HEROKU` block): `URL` is `""` when no `FQDN` is set,
and `keepalive.ping_server()` skips when `URL` is empty. `PORT` is now
parsed as an int (aiohttp `TCPSite` needs an int).

## 8. Event-loop startup — `bot.py`
`asyncio.get_event_loop()` + `loop.run_until_complete()` replaced with
`asyncio.run()`, and `SilentX.loop.create_task(...)` replaced with
`asyncio.create_task(...)`. Same dead-loop pinning that crashed the
Spotify bot on Koyeb. Also fixed `time = now.strftime(...)` shadowing
the `time` module (renamed `time_str`).

## 9. Housekeeping
- `requirements.txt`: dropped `opencv-python-headless`, `speedtest`,
  `ffmpeg-python` — nothing in the codebase imports them.
- `docker-compose.yml`: was broken YAML (bad indentation, stray
  `HEROKU_API_KEY`, missing vars). Rewritten with `${VAR}` env vars.
- Added `example.env` (see above). No secrets are in this repo.

## Not fixed (out of scope)
- No tests exist in the original project; none were added.
- Stream-page CSS/JS are still loaded from the previous owner's Vercel
  URL (`developer-six-dusky.vercel.app/.../SilentXBotz.css|js`) — the
  files work, but they are not yours. Self-host them if that matters.
- `workers=150` in `Lucia/Bot/__init__.py` is very high; lower it if the
  host is small.

## Verified
- `python3 -m py_compile` passes on all `.py` files.
- `info.py` with dummy env (`API_ID=123`, `API_HASH=x`, `BOT_TOKEN=x`,
  `DATABASE_URI=mongodb://x`, `LOG_CHANNEL=-1001`, `BIN_CHANNEL=-1002`):
  imports cleanly, `IS_VERIFY` now follows the env var, `URL` is `""`
  with no `FQDN`, `PORT` is `int 8080`.
- `info.py` with `API_ID` unset: raises
  `ValueError: Missing required environment variable: API_ID`.
- No `AM_FILMS` / `GUARDIANff` / `1001583883335` / `1001826416677`
  remains in any `.py` / `.html` file.
- `bot.py` contains no `importlib` / `glob` plugin loading; `route.py`
  contains `watch_handler` and `download_handler`, no `stream_handler`.

## 10. Removed PAID_STREAM, shortener, STREAM_MODE (2026-11-10, user request)

- **PAID_STREAM gone:** the `streamfile` callback in `plugins/pm_filter.py`
  (which gated streaming behind premium) is removed entirely, and the
  `PAID_STREAM` flag is gone from `info.py`. Premium itself (`/plan`,
  `/myplan`) is untouched.
- **STREAM_MODE gone:** the three `if STREAM_MODE:` branches in
  `plugins/commands.py` that added a "Generate Streaming Link" button are
  removed. Files are now always sent directly in Telegram with just the
  Update Channel button. The `STREAM_MODE` flag is gone from `info.py`.
  Note: the aiohttp web server in `bot.py` still runs (it is the Koyeb
  health endpoint), but no button or handler generates stream links any
  more.
- **Shortener gone:** verification links in `plugins/commands.py` are now
  direct `telegram.me/...?start=...` links — no `get_shortlink()`, no
  `Shortzy`, no `shortzy` dependency in `requirements.txt`. Removed:
  `SHORTENER_API/WEBSITE` (x3) from `info.py` and `example.env`, the
  shortener keys from group settings defaults (`database/users_chats_db.py`)
  and `/reset_group`, the shortener sections from `/details`, the
  Shortner button + `changeshortner` / `set_verify` handlers from the
  settings panel in `plugins/pm_filter.py`, and the `/set_shortner*`
  lines from `Script.py` help text. The 2nd/3rd *verification* itself is
  kept (direct links, tutorial, timing) — only the shortening is gone;
  its helpers were renamed `use_second_shortener` → `use_second_verify`
  (same for third) to match what they actually do.
- Verified: `py_compile` passes on all files; no `PAID_STREAM`,
  `STREAM_MODE`, `SHORTENER`, `shortner`, `Shortzy`, `get_shortlink`,
  `streamfile` or `Generate Streaming` remains in any `.py` file.

## 11. Rebased onto branch 2026 (2026-11-10, before pushing)

The fixes above were first made on the older `Elza-main.zip` snapshot.
Branch `2026` on GitHub turned out to be newer: it has TMDB integration
(`tmdb_search` in `utils.py` and in the spell-check in `plugins/pm_filter.py`)
and Malayalam forward-file messages in `plugins/commands.py`, none of which
were in the zip. All fixes (sections 1–10) were re-applied onto the branch
`2026` code, and that rebased version is what was pushed. Preserved from
branch 2026, verified by diff: the TMDB code, the TMDB API key as committed
on that branch (still hardcoded in `info.py` and `utils.py` — rotate it and
move it to an env var), and both Malayalam messages. The pushed copy lives
in `~/workspace/elza-2026/` and `Elza-fixed.zip` was rebuilt from it.

## 12. Streaming + premium plans removed (2026-11-10)

On Sreehari's request ("streaming and premium plans also not needed").

Streaming — gone: the `/watch` and `/download` routes and the
`media_streamer` in `plugins/route.py`, `Lucia/util/custom_dl.py`
(ByteStreamer), `Lucia/util/render_template.py`, the `dl.html`/`req.html`
templates, `Lucia/Bot/clients.py` (multi-client serving) and the
`multi_clients`/`work_loads` dicts. `plugins/route.py` is now only a
health endpoint (`/`, `/health`, `/healthz` returning `{"status": "ok"}`),
so the web server in `bot.py` stays for Koyeb Web health checks only.
`Lucia/util/file_properties.py` was kept but trimmed: `get_file_ids`
(streaming-only) is gone, `get_name`/`get_hash`/`get_media_file_size`
stay — `plugins/pm_filter.py` imports them, and deleting the file would
have broken the plugin at import time. `BIN_CHANNEL` stays: it is still
used for the no-results log message in `pm_filter.py`.

Premium — gone: `plugins/Premium.py` (`/plan`, `/myplan`, `/add_premium`,
`/remove_premium`, `/get_premium`, `/premium_users`, Stars purchase),
`plugins/license.py` (`/redeem`, `/add_redeem`, `/clearcodes`,
`/allcodes`), the free trial, the `buy`/`star`/`upi`/`premium`/
`give_trial` callbacks in `plugins/pm_filter.py`, the
`check_expired_premium` loop in `plugins/__init__.py` + `bot.py`, the
premium methods in `database/users_chats_db.py` (`has_premium_access`,
`get_expired`, `get_expiring_soon`, `remove_premium_access`,
`check_trial_status`, `give_free_trial`, `all_premium_users`, plus the
`codes` collection), `STAR_PREMIUM_PLANS` / `PREMIUM_LOGS` /
`SUBSCRIPTION` / `MULTI_CLIENT` in `info.py`, the premium texts and
`/stats` premium count in `Script.py` / `plugins/p_ttishow.py`, and the
premium lines in `README.md` / `example.env`. Verification now applies
to everyone: the `if not await db.has_premium_access(user_id):` wrapper
in `plugins/commands.py` was removed (the verification block itself is
unchanged). The refer system stays, but its reward was premium, so at
100 points the referrer no longer gets a 1-month premium grant — points
just reset to 0 — and the three texts that promised premium (self-refer
message, refer link text, 100-point DM) no longer mention it. Note:
refer points now have no reward attached; remove the refer system too
if it is not wanted. Verified: py_compile clean, zero references to
premium/streaming in any `.py` file, TMDB and Malayalam intact.

## 13. Search speed (2026-11-10)

Searches were slow because every search scanned the whole files
collection: the DB query is an unanchored regex, which no index can
serve (the text index on `file_name` existed but was never used), and
`count_documents` scanned it a second time — up to 3 query variants
meant up to 6 full scans per search. On top of that the poster fetch
(2-3 sequential TMDB calls) blocked the results, and a misspelled query
waited 2s for nothing before re-searching.

- `database/ia_filterdb.py`: `get_search_results` now tries a MongoDB
  `$text` search first, which is served from the existing text index and
  ranked by relevance (`textScore`). The old regex variants only run if
  `$text` finds nothing (or the text index is missing), so caption-only
  matches and odd queries still work, just slower. One behaviour change:
  results are now ranked by relevance instead of newest-first.
- `utils.py`: `tmdb_search` runs the movie and TV searches concurrently
  instead of one after the other; `get_poster` results are cached for 1
  hour (max 500 entries) since the same titles get searched repeatedly.
- `plugins/pm_filter.py`: the poster fetch now starts before the DB
  search and runs in parallel with it (the year then comes from the
  query only, not the first result's file name); it is cancelled when a
  search finds nothing, and a failed poster fetch shows results without
  the poster instead of failing the search. The 2s sleep after an AI
  spelling suggestion is gone — the suggestion stays visible while the
  re-search runs and is removed once results are back.
- Not verified against a live database here: the `$text` path falls back
  to the old regex search on any error, so a missing text index cannot
  break searching. If searches are still slow after this, the next thing
  to check is the MongoDB Atlas tier/region and the collection size.

## 14. /start not replying (2026-11-10)

The deployed bot was running and healthy on Koyeb, but /start got no
reply. Two code causes found and fixed:

- One of the 15 welcome-photo URLs in `PICS` (`info.py`) was not a
  file URL at all (`https://graph.org/-03-28-833`), so whenever
  `random.choice` picked it, `reply_photo` raised and /start died with
  no reply. The bad URL is removed.
- `plugins/commands.py`: /start now falls back to sending the same
  welcome text without the photo if `reply_photo` fails, so a dead
  image link can never silence /start again.
- `bot.py`: startup no longer dies if loading the banned list, creating
  the DB indexes, or sending the restart notice to LOG_CHANNEL fails —
  each now logs a warning and startup continues. Before this, any of
  those three failing killed the bot before `idle()`, so it never came
  online at all.

Note: the first thing to check when /start is silent is that the
message is going to the right bot — the running bot is @AMSearch2bot
(see its Koyeb log line "started on AMSearch2bot") — in a private chat,
not a group (in a group /start only flashes a sticker for 5 seconds).

## 15. Patched zip applied (2026-11-10, user upload)

Sreehari uploaded `Elza-2026-patched.zip` — the branch 2026 code plus
his own patches — and asked for it to be pushed. Applied as-is (4 files):

- `Lucia/Bot/__init__.py`: `workers=150` → `workers=16` (the section 9
  note above suggested lowering it on a small host).
- `plugins/commands.py`: the two LOG_CHANNEL sends in /start are now
  wrapped in try/except — a failed log send prints an error instead of
  killing /start.
- `plugins/extra.py`: a debug handler (`group=-1`) that prints every
  incoming message (chat, user, text). Same job as the temporary
  `plugins/debug_updates.py` from the /start investigation, which stays
  on the branch — remove one of them once the silence is diagnosed.
- `plugins/pm_filter.py`: `tracemalloc.start()` added;
  `update_top_messages` wrapped in try/except;
  `settings['auto_ffilter']` / `settings['imdb']` /
  `settings['spell_check']` changed to safe `.get()` (a missing key used
  to raise KeyError and kill the filter); the no-results log now also
  requires `BIN_CHANNEL` to be set.
- `example.env` was NOT pushed: the zip's version (empty COLLECTION_NAME)
  is already identical to the branch — his earlier web edit had emptied
  it there. Note: an empty COLLECTION_NAME in the live env vars would
  stop the bot starting; it must be set in Koyeb.
- The zip's 31 `__pycache__` files were not pushed (bytecode junk).
- Verified: py_compile passes on all four files (one pre-existing
  SyntaxWarning for an invalid escape in pm_filter.py, unchanged).
