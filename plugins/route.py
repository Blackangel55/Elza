from aiohttp import web

# Streaming is removed: no /watch or /download routes, no file serving.
# The web server stays only as a health endpoint (e.g. Koyeb Web health
# checks), which is why bot.py still starts it on $PORT.

routes = web.RouteTableDef()


@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "ok", "bot": "Elza Filter Bot"})


@routes.get("/health", allow_head=True)
async def health_handler(request):
    return web.json_response({"status": "ok"})


@routes.get("/healthz", allow_head=True)
async def healthz_handler(request):
    return web.json_response({"status": "ok"})
