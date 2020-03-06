from aiohttp import web
from asyncworker import RouteTypes
from asyncworker.http.decorators import parse_path

from asgard.api.resources.apps import AppStatsResource
from asgard.app import app
from asgard.backends import mesos
from asgard.backends.base import Interval
from asgard.http.auth import auth_required
from asgard.models.account import Account
from asgard.models.user import User
from asgard.services.apps import AppsService


async def get_app_stats(
    app_id: str, user: User, account: Account, interval: Interval
):
    stats = await AppsService.get_app_stats(
        app_id, interval, user, account, mesos
    )

    return web.json_response(AppStatsResource(stats=stats).dict())


@app.route(
    ["/apps/{app_id:[.a-z0-9/-]+}/stats"], type=RouteTypes.HTTP, methods=["GET"]
)
@auth_required
@parse_path
async def app_stats(app_id: str, user: User, account: Account):
    return await get_app_stats(app_id, user, account, Interval.ONE_HOUR)


@app.route(
    ["/apps/{app_id:[.a-z0-9/-]+}/stats/avg-1min"],
    type=RouteTypes.HTTP,
    methods=["GET"],
)
@auth_required
@parse_path
async def app_stats_avg_1min(app_id: str, user: User, account: Account):
    return await get_app_stats(app_id, user, account, Interval.ONE_MINUTE)
