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
