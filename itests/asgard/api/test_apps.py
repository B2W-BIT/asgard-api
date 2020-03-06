from datetime import datetime, timezone
from http import HTTPStatus

from aioresponses import aioresponses
from asyncworker.testing import HttpClientContext

from asgard.api.apps import app
from asgard.conf import settings
from asgard.models.app import AppStats
from itests.util import (
    BaseTestCase,
    ACCOUNT_DEV_ID,
    USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY,
)
from tests.utils import build_mesos_cluster, get_fixture


class AppStatsTest(BaseTestCase):
    async def setUp(self):
        await super(AppStatsTest, self).setUp()
        self.client = await self.aiohttp_client(app)
        self.utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.INDEX_NAME = (
            f"asgard-app-stats-{self.utc_now.strftime('%Y-%m-%d-%H')}"
        )

    async def tearDown(self):
        await super(AppStatsTest, self).tearDown()
        await self.esclient.indices.delete(
            index=self.INDEX_NAME,
            ignore=[HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND],
        )

    async def test_apps_stats_empty_stats_for_existing_app(self):
        async with HttpClientContext(app) as client:
            local_address = (
                f"http://{client._server.host}:{client._server.port}"
            )
            with aioresponses(
                passthrough=[local_address, settings.STATS_API_URL]
            ) as rsps:
                agent_id = "ead07ffb-5a61-42c9-9386-21b680597e6c-S0"

                build_mesos_cluster(rsps, agent_id)  # namespace=asgard-infra

                app_stats_datapoints = get_fixture(
                    f"agents/{agent_id}/app_stats.json"
                )

                await self._load_app_stats_into_storage(
                    self.INDEX_NAME, self.utc_now, app_stats_datapoints
                )
                resp = await client.get(
                    f"/apps/infra/asgard/api/stats?account_id={ACCOUNT_DEV_ID}",
                    headers={
                        "Authorization": f"Token {USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY}"
                    },
                )
                self.assertEqual(HTTPStatus.OK, resp.status)
                data = await resp.json()
                self.assertEqual(
                    AppStats(
                        cpu_pct="0.25", ram_pct="15.05", cpu_thr_pct="1.00"
                    ).dict(),
                    data["stats"],
                )

    async def test_apps_stats_with_avg_1_min(self):
        async with HttpClientContext(app) as client:
            local_address = (
                f"http://{client._server.host}:{client._server.port}"
            )
            with aioresponses(
                passthrough=[local_address, settings.STATS_API_URL]
            ) as rsps:
                agent_id = "ead07ffb-5a61-42c9-9386-21b680597e6c-S0"

                build_mesos_cluster(rsps, agent_id)  # namespace=asgard-infra

                app_stats_datapoints = get_fixture(
                    f"agents/{agent_id}/app_stats.json"
                )

                await self._load_app_stats_into_storage(
                    self.INDEX_NAME, self.utc_now, app_stats_datapoints
                )
                resp = await client.get(
                    f"/apps/infra/asgard/api/stats/avg-1min?account_id={ACCOUNT_DEV_ID}",
                    headers={
                        "Authorization": f"Token {USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY}"
                    },
                )
                self.assertEqual(HTTPStatus.OK, resp.status)
                data = await resp.json()
                self.assertEqual(
                    AppStats(
                        cpu_pct="0.25", ram_pct="15.05", cpu_thr_pct="1.00"
                    ).dict(),
                    data["stats"],
                )

    async def test_apps_stats_app_not_found(self):
        async with HttpClientContext(app) as client:
            local_address = (
                f"http://{client._server.host}:{client._server.port}"
            )
            with aioresponses(
                passthrough=[local_address, settings.STATS_API_URL]
            ) as rsps:
                agent_id = "ead07ffb-5a61-42c9-9386-21b680597e6c-S0"
                build_mesos_cluster(rsps, agent_id)  # namespace=asgard-infra

                app_stats_datapoints = get_fixture(
                    f"agents/{agent_id}/app_stats.json"
                )

                resp = await client.get(
                    f"/apps/asgard/api/not-exist/stats?account_id={ACCOUNT_DEV_ID}",
                    headers={
                        "Authorization": f"Token {USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY}"
                    },
                )
                self.assertEqual(HTTPStatus.OK, resp.status)
                data = await resp.json()
                self.assertEqual(
                    AppStats(cpu_pct="0", ram_pct="0", cpu_thr_pct="0").dict(),
                    data["stats"],
                )

    async def test_apps_stats_check_uri_regex(self):
        async with HttpClientContext(app) as client:
            local_address = (
                f"http://{client._server.host}:{client._server.port}"
            )
            with aioresponses(
                passthrough=[local_address, settings.STATS_API_URL]
            ) as rsps:
                agent_id = "ead07ffb-5a61-42c9-9386-21b680597e6c-S0"
                build_mesos_cluster(rsps, agent_id)  # namespace=asgard-infra

                resp = await client.get(
                    f"/apps/asgard/pgsql-9.4/stats?account_id={ACCOUNT_DEV_ID}",
                    headers={
                        "Authorization": f"Token {USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY}"
                    },
                )
                self.assertEqual(HTTPStatus.OK, resp.status)

                resp = await client.get(
                    f"/apps/asgard/pgsql-9..4/stats?account_id={ACCOUNT_DEV_ID}",
                    headers={
                        "Authorization": f"Token {USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY}"
                    },
                )
                self.assertEqual(HTTPStatus.OK, resp.status)
