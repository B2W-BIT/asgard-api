from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import List

from aiohttp import web
from asyncworker import RouteTypes

from asgard.api.resources.accounts import (
    AccountsResource,
    AccountResource,
    AccountUsersResource,
)
from asgard.app import app
from asgard.backends.accounts import AccountsBackend
from asgard.backends.users import UsersBackend
from asgard.http.auth import auth_required
from asgard.http.auth.jwt import jwt_encode
from asgard.models.user import User
from asgard.services.accounts import AccountsService
from asgard.services.users import UsersService


@app.route(
    ["/accounts/{account_id}/auth"], type=RouteTypes.HTTP, methods=["GET"]
)
@auth_required
async def change_account(request: web.Request):
    account_id: str = request.match_info["account_id"]
    user = await User.from_alchemy_obj(request["user"])
    permission_ok = False
    new_token = b""

    account = await AccountsService.get_account_by_id(
        int(account_id), AccountsBackend()
    )
    if account:
        permission_ok = await account.user_has_permission(user)

    if permission_ok and account:
        new_token = jwt_encode(user, account)
        return web.json_response(data={"jwt": new_token.decode("utf-8")})

    return web.json_response(status=HTTPStatus.FORBIDDEN)


@app.route(["/accounts"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
async def index(r: web.Request):
    accounts = await AccountsService.get_accounts(AccountsBackend())
    return web.json_response(AccountsResource(accounts=accounts).dict())


@app.route(["/accounts/{account_id}"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
async def account_by_id(request: web.Request):
    account_id: str = request.match_info["account_id"]
    account = await AccountsService.get_account_by_id(
        int(account_id), AccountsBackend()
    )
    status_code = HTTPStatus.OK if account else HTTPStatus.NOT_FOUND
    return web.json_response(
        AccountResource(account=account).dict(), status=status_code
    )


@app.route(
    ["/accounts/{account_id}/users"], type=RouteTypes.HTTP, methods=["GET"]
)
@auth_required
async def users_from_account(request: web.Request):
    account_id: str = request.match_info["account_id"]
    users: List[User] = []

    account = await AccountsService.get_account_by_id(
        int(account_id), AccountsBackend()
    )
    status_code = HTTPStatus.OK if account else HTTPStatus.NOT_FOUND
    if account:
        users = await AccountsService.get_users_from_account(
            account, AccountsBackend()
        )
    return web.json_response(
        AccountUsersResource(users=users).dict(), status=status_code
    )


@app.route(
    ["/accounts/{account_id}/users/{user_id}"],
    type=RouteTypes.HTTP,
    methods=["POST"],
)
@auth_required
async def add_user_to_account(request: web.Request):
    user_id: str = request.match_info["user_id"]
    account_id: str = request.match_info["account_id"]
    account = await AccountsService.get_account_by_id(
        int(account_id), AccountsBackend()
    )

    status_code = HTTPStatus.OK if account else HTTPStatus.NOT_FOUND
    user = await UsersService.get_user_by_id(int(user_id), UsersBackend())

    if account and user:
        await AccountsService.add_user_to_account(
            user, account, AccountsBackend()
        )

    return web.json_response(AccountUsersResource().dict(), status=status_code)


@app.route(
    ["/accounts/{account_id}/users/{user_id}"],
    type=RouteTypes.HTTP,
    methods=["DELETE"],
)
@auth_required
async def remove_user_from_account(request: web.Request):
    user_id: str = request.match_info["user_id"]
    account_id: str = request.match_info["account_id"]
    account = await AccountsService.get_account_by_id(
        int(account_id), AccountsBackend()
    )

    status_code = HTTPStatus.OK if account else HTTPStatus.NOT_FOUND
    user = await UsersService.get_user_by_id(int(user_id), UsersBackend())

    if account and user:
        await AccountsService.remove_user_from_account(
            user, account, AccountsBackend()
        )

    return web.json_response(AccountUsersResource().dict(), status=status_code)
