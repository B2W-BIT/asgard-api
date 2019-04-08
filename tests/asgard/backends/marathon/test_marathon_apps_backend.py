from aioresponses import aioresponses
from asynctest import TestCase
from freezegun import freeze_time

from asgard.backends.marathon.impl import MarathonAppsBackend
from asgard.backends.mesos.models.app import MesosApp
from asgard.conf import settings
from asgard.models.account import Account
from asgard.models.app import AppStats
from asgard.models.user import User
from itests.util import USER_WITH_MULTIPLE_ACCOUNTS_DICT, ACCOUNT_DEV_DICT
from tests.utils import build_mesos_cluster, add_agent_task_stats


class MarathonAppsBackendTest(TestCase):
    async def setUp(self):

        self.user = User(**USER_WITH_MULTIPLE_ACCOUNTS_DICT)
        self.account = Account(**ACCOUNT_DEV_DICT)
        self.apps_backend = MarathonAppsBackend()

    @freeze_time("2019-03-29")
    async def test_get_app_stats_has_some_data(self):
        with aioresponses() as rsps:
            agent_id = "ead07ffb-5a61-42c9-9386-21b680597e6c-S0"
            build_mesos_cluster(rsps, agent_id)
            add_agent_task_stats(
                rsps, agent_id, index_name="asgard-app-stats-2019-03-29-*"
            )
            stats = await self.apps_backend.get_app_stats(
                MesosApp(id="infra-asgard-api"), self.user, self.account
            )
            self.assertEqual(
                AppStats(cpu_pct="4.51", ram_pct="22.68", cpu_thr_pct="2.89"),
                stats,
            )

    @freeze_time("2019-03-29")
    async def test_get_app_stats_exception_on_search(self):
        """
        Returns AppStats with errors filled if any exception happend during ES query
        """
        with aioresponses() as rsps:
            agent_id = "ead07ffb-5a61-42c9-9386-21b680597e6c-S0"
            build_mesos_cluster(rsps, agent_id)

            index_name = "asgard-app-stats-2019-03-29-*"
            url = f"{settings.STATS_API_URL}/{index_name}/_search"
            rsps.get(url, exception=Exception("Connection error to ES"))

            stats = await self.apps_backend.get_app_stats(
                MesosApp(id="infra-asgard-api"), self.user, self.account
            )
            self.assertEqual(
                AppStats(
                    cpu_pct="0",
                    ram_pct="0",
                    cpu_thr_pct="0",
                    errors={"global": "Connection error to ES"},
                ),
                stats,
            )
