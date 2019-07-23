import asyncio
from http import HTTPStatus

from asgard.api import jobs
from asgard.api.resources.jobs import ScheduledJobResource
from asgard.app import app
from asgard.backends.chronos.models.converters import (
    ChronosScheduledJobConverter,
)
from asgard.clients.chronos.models.job import ChronosJob
from asgard.conf import settings
from asgard.http.client import http_client
from asgard.models.account import Account
from asgard.models.user import User
from itests.util import (
    BaseTestCase,
    USER_WITH_MULTIPLE_ACCOUNTS_DICT,
    ACCOUNT_DEV_DICT,
    USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY,
)
from tests.utils import with_json_fixture


class JobsEndpointTestCase(BaseTestCase):
    async def setUp(self):
        await super(JobsEndpointTestCase, self).setUp()
        self.client = await self.aiohttp_client(app)
        self.user = User(**USER_WITH_MULTIPLE_ACCOUNTS_DICT)
        self.account = Account(**ACCOUNT_DEV_DICT)

    async def tearDown(self):
        await super(JobsEndpointTestCase, self).tearDown()

    async def test_jobs_get_by_id_auth_required(self):
        resp = await self.client.get("/jobs/job-does-not-exist")
        self.assertEqual(HTTPStatus.UNAUTHORIZED, resp.status)

    @with_json_fixture("scheduled-jobs/chronos/infra-purge-logs-job.json")
    async def test_jobs_get_by_id_job_exist(self, chronos_job_fixture):

        chronos_job_fixture["name"] = f"{self.account.namespace}-my-job"
        async with http_client as client:
            await client.post(
                f"{settings.SCHEDULED_JOBS_SERVICE_ADDRESS}/v1/scheduler/iso8601",
                json=chronos_job_fixture,
            )

        # Para dar tempo do chronos registra e responder no request log abaixo
        await asyncio.sleep(1)
        asgard_job = ChronosScheduledJobConverter.to_asgard_model(
            ChronosJob(**chronos_job_fixture)
        )
        # A busca deve ser feita sempre *sem* o namespace
        asgard_job.remove_namespace(self.account)
        resp = await self.client.get(
            f"/jobs/{asgard_job.id}",
            headers={
                "Authorization": f"Token {USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY}"
            },
        )
        self.assertEqual(HTTPStatus.OK, resp.status)
        resp_data = await resp.json()
        self.assertEqual(ScheduledJobResource(job=asgard_job).dict(), resp_data)

    async def test_jobs_get_by_by_id_jobs_does_not_exist(self):
        resp = await self.client.get(
            "/jobs/job-does-not-exist",
            headers={
                "Authorization": f"Token {USER_WITH_MULTIPLE_ACCOUNTS_AUTH_KEY}"
            },
        )
        self.assertEqual(HTTPStatus.NOT_FOUND, resp.status)
        resp_data = await resp.json()
        self.assertEqual(ScheduledJobResource().dict(), resp_data)
