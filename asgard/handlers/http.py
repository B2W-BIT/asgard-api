from asyncworker import RouteTypes
from asgard.app import app
from aiohttp import web


@app.route(["/"], methods=["GET"], type=RouteTypes.HTTP)
async def handle(r):
    return web.json_response({"OK": True})
