from decimal import Decimal
from typing import Any, Dict, List

from aiohttp import web
from asyncworker import RouteTypes
from asyncworker.http.decorators import parse_path
from asyncworker.http.wrapper import RequestWrapper

from asgard.api.resources.agents import AgentsResource
from asgard.api.resources.apps import AppsResource
from asgard.app import app
from asgard.backends import mesos
from asgard.http.auth import auth_required
from asgard.math import round_up
from asgard.models.account import Account
from asgard.models.agent import Agent
from asgard.models.app import App
from asgard.models.user import User
from asgard.services import agents_service


def calculate_stats(agents):
    total_cpus = sum(
        [Decimal(agent.resources["cpus"]) for agent in agents]
    ) or Decimal("1")
    total_used_cpus = sum(
        [Decimal(agent.used_resources["cpus"]) for agent in agents]
    )

    total_ram = sum(
        [Decimal(agent.resources["mem"]) for agent in agents]
    ) or Decimal("1")
    total_used_ram = sum(
        [Decimal(agent.used_resources["mem"]) for agent in agents]
    )

    return {
        "cpu_pct": str(round_up(total_used_cpus / total_cpus * 100)),
        "ram_pct": str(round_up(total_used_ram / total_ram * 100)),
    }


@app.route(["/agents"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
async def agents_handler(user: User, account: Account):
    agents = await agents_service.get_agents(user, account, mesos)
    stats = calculate_stats(agents)
    return web.json_response(AgentsResource(agents=agents, stats=stats).dict())


def apply_attr_filter(
    filters_dict: Dict[str, Any], agents: List[Agent]
) -> List[Agent]:

    filtered_agents = []
    for agent in agents:
        all_filters = [
            agent.attr_has_value(attr_name, filters_dict[attr_name])
            for attr_name in filters_dict
        ]
        if all(all_filters):
            filtered_agents.append(agent)
    return filtered_agents


@app.route(["/agents/with-attrs"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
async def agents_with_attrs(
    wrapper: RequestWrapper, user: User, account: Account
):

    filters = wrapper.http_request.query.copy()
    filters.pop("account_id", None)

    agents = await agents_service.get_agents(user, account, backend=mesos)
    filtered_agents = apply_attr_filter(filters, agents)

    stats = calculate_stats(filtered_agents)
    return web.json_response(
        AgentsResource(agents=filtered_agents, stats=stats).dict()
    )


@app.route(["/agents/{agent_id}/apps"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
@parse_path
async def agent_apps(agent_id: str, user: User, account: Account):
    apps: List[App] = []

    agent = await agents_service.get_agent_by_id(agent_id, user, account, mesos)
    if agent:
        apps = agent.applications
    return web.json_response(AppsResource(apps=apps).dict())
