from aiohttp import web
from asyncworker import RouteTypes

from asgard.app import app


@app.route(["/"], methods=["GET"], type=RouteTypes.HTTP)
async def handle():
    return web.json_response({"OK": True})
