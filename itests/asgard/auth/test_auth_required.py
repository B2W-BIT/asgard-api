import jwt
from aiohttp import web
from asynctest import skip
from asyncworker import App
from asyncworker.options import RouteTypes

from asgard.http.auth import auth_required
from asgard.http.auth.jwt import jwt_encode
from asgard.models.account import Account
from asgard.models.user import User
from itests.util import (
    BaseTestCase,
    USER_WITH_MULTIPLE_ACCOUNTS_DICT,
    USER_WITH_MULTIPLE_ACCOUNTS_EMAIL,
    USER_WITH_MULTIPLE_ACCOUNTS_ID,
    ACCOUNT_INFRA_DICT,
)


class AuthRequiredTest(BaseTestCase):
    async def setUp(self):
        await super(AuthRequiredTest, self).setUp()
        self.app = App()

        @self.app.route(["/"], methods=["GET"], type=RouteTypes.HTTP)
        @auth_required
        async def handler(auth_user: User, account: Account):
            data = {
                "user": {"id": auth_user.id, "email": auth_user.email},
                "current_account": {
                    "id": account.id,
                    "namespace": account.namespace,
                    "name": account.name,
                },
            }
            return web.json_response(data)

        self.client = await self.aiohttp_client(self.app)

    async def tearDown(self):
        await super(AuthRequiredTest, self).tearDown()

    async def test_auth_token_populate_request_user_if_key_is_valid(self):
        """
        Populates request.user if authentication is successful
        """

        resp = await self.client.get(
            "/",
            headers={"Authorization": "Token 69ed620926be4067a36402c3f7e9ddf0"},
        )
        data = await resp.json()
        self.assertEqual(200, resp.status)
        self.assertEqual(
            {
                "id": USER_WITH_MULTIPLE_ACCOUNTS_ID,
                "email": USER_WITH_MULTIPLE_ACCOUNTS_EMAIL,
            },
            data["user"],
        )

    async def test_auth_auth_fails_if_token_type_is_invalid(self):

        resp = await self.client.get(
            "/", headers={"Authorization": "Invalid-Type invalidToken"}
        )
        data = await resp.json()
        self.assertEqual(401, resp.status)
        self.assertEqual({"msg": "Authorization token is invalid"}, data)

    async def test_auth_auth_fails_if_header_is_not_present(self):

        resp = await self.client.get("/")
        data = await resp.json()
        self.assertEqual(401, resp.status)
        self.assertEqual({"msg": "Authorization token is invalid"}, data)

    async def test_auth_auth_failts_if_key_not_found(self):

        resp = await self.client.get(
            "/", headers={"Authorization": "Token token-not-found"}
        )
        data = await resp.json()
        self.assertEqual(401, resp.status)
        self.assertEqual({"msg": "Authorization token is invalid"}, data)

    async def test_auth_auth_fails_if_user_has_no_associated_account(self):
        resp = await self.client.get(
            "/",
            headers={"Authorization": "Token 7b4184bfe7d2349eb56bcfb9dc246cf8"},
        )
        data = await resp.json()
        self.assertEqual(401, resp.status)
        self.assertEqual({"msg": "No associated account"}, data)

    async def test_auth_auth_fails_if_desired_account_does_not_exist(self):
        resp = await self.client.get(
            "/",
            params={"account_id": 42},
            headers={"Authorization": "Token 69ed620926be4067a36402c3f7e9ddf0"},
        )
        data = await resp.json()
        self.assertEqual(401, resp.status)
        self.assertEqual({"msg": "Account does not exist"}, data)

    async def test_auth_populate_default_account_if_request_account_is_empty(
        self
    ):
        resp = await self.client.get(
            "/",
            headers={"Authorization": "Token 69ed620926be4067a36402c3f7e9ddf0"},
        )
        data = await resp.json()
        self.assertEqual(200, resp.status)
        self.assertEqual(
            {
                "user": {
                    "id": USER_WITH_MULTIPLE_ACCOUNTS_ID,
                    "email": USER_WITH_MULTIPLE_ACCOUNTS_EMAIL,
                },
                "current_account": {
                    "name": "Dev Team",
                    "id": 10,
                    "namespace": "dev",
                },
            },
            data,
        )

    async def test_auth_auth_fails_if_user_is_not_associated_to_desired_account(
        self
    ):
        """
        Qualquer request com `?account_id` que o usuário nao esteja vinculado, retorna 401
        """
        resp = await self.client.get(
            "/",
            params={"account_id": 12},  # Other Account
            headers={"Authorization": "Token 69ed620926be4067a36402c3f7e9ddf0"},
        )
        data = await resp.json()
        self.assertEqual(401, resp.status)
        self.assertEqual(
            {"msg": "Permission Denied to access this account"}, data
        )

    @skip("Ainda nao temos usuarios validos/ativos/invalidos")
    def test_auth_auth_failts_if_token_is_valid_but_user_is_invalid(self):
        """
        User could be inactive or does not exist
        """
        self.fail()

    @skip("Ainda nao temos usuarios validos/ativos/invalidos")
    def test_jwt_auth_failts_if_token_is_valid_but_user_is_invalid(self):
        """
        User could be inactive or does not exist
        """
        self.fail()

    async def test_jwt_token_populate_request_user_if_key_is_valid(self):
        """
        Populates request.user if authentication is successful
        """

        user = User(**USER_WITH_MULTIPLE_ACCOUNTS_DICT)
        account = Account(**ACCOUNT_INFRA_DICT)
        jwt_token = jwt_encode(user, account)
        auth_header = {
            "Authorization": "JWT {}".format(jwt_token.decode("utf-8"))
        }

        resp = await self.client.get("/", headers=auth_header)
        data = await resp.json()
        self.assertEqual(200, resp.status)
        self.assertEqual(
            {
                "id": USER_WITH_MULTIPLE_ACCOUNTS_ID,
                "email": USER_WITH_MULTIPLE_ACCOUNTS_EMAIL,
            },
            data["user"],
        )

    async def test_jwt_auth_fails_if_jwt_token_is_invalid(self):

        jwt_token = jwt.encode({"email": "user@host.com.br"}, key="wrong key")
        auth_header = {
            "Authorization": "JWT {}".format(jwt_token.decode("utf-8"))
        }

        resp = await self.client.get("/", headers=auth_header)
        data = await resp.json()
        self.assertEqual(401, resp.status)
        self.assertEqual({"msg": "Authorization token is invalid"}, data)
