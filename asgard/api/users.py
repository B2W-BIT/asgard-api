from http import HTTPStatus

from aiohttp import web
from aiohttp.web import json_response
from asyncworker import RouteTypes

from asgard.api.resources.users import (
    UserMeResource,
    UserListResource,
    UserResource,
    UserAccountsResource,
    ErrorResource,
    ErrorDetail,
)
from asgard.app import app
from asgard.backends.users import UsersBackend
from asgard.exceptions import DuplicateEntity
from asgard.http.auth import auth_required
from asgard.models.account import Account
from asgard.models.user import User
from asgard.services.users import UsersService


@app.route(["/users/me"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
async def whoami(request: web.Request):
    user = await User.from_alchemy_obj(request["user"])
    current_account = await Account.from_alchemy_obj(
        request["user"].current_account
    )

    alternate_accounts = await UsersService.get_alternate_accounts(
        user, current_account, UsersBackend()
    )

    resource_response = UserMeResource(
        user=user, current_account=current_account, accounts=alternate_accounts
    )

    return json_response(resource_response.dict())


@app.route(["/users"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
async def users_list(request: web.Request):
    users = await UsersService.get_users(UsersBackend())
    return web.json_response(UserListResource(users=users).dict())


@app.route(["/users/{user_id}"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
async def user_by_id(request: web.Request):

    user_id: str = request.match_info["user_id"]
    user = await UsersService.get_user_by_id(int(user_id), UsersBackend())
    status_code = HTTPStatus.OK if user else HTTPStatus.NOT_FOUND
    return web.json_response(UserResource(user=user).dict(), status=status_code)


@app.route(["/users/{user_id}/accounts"], type=RouteTypes.HTTP, methods=["GET"])
@auth_required
async def accounts_from_user(request: web.Request):
    user_id: str = request.match_info["user_id"]
    user = await UsersService.get_user_by_id(int(user_id), UsersBackend())

    status_code = HTTPStatus.OK if user else HTTPStatus.NOT_FOUND

    if user:
        accounts = await UsersService.get_accounts_from_user(
            user, UsersBackend()
        )
        return web.json_response(
            UserAccountsResource(accounts=accounts).dict(), status=status_code
        )
    return web.json_response(UserAccountsResource().dict(), status=status_code)


@app.route(["/users"], type=RouteTypes.HTTP, methods=["POST"])
@auth_required
async def create_user(request: web.Request):
    status_code = HTTPStatus.CREATED
    try:
        user = User(**await request.json())
    except ValueError:
        return web.json_response(
            UserResource().dict(), status=HTTPStatus.BAD_REQUEST
        )

    try:
        created_user = await UsersService.create_user(user, UsersBackend())
    except DuplicateEntity as de:
        return web.json_response(
            ErrorResource(errors=[ErrorDetail(msg=str(de))]).dict(),
            status=HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    return web.json_response(
        UserResource(user=created_user).dict(), status=status_code
    )


@app.route(["/users/{user_id}"], type=RouteTypes.HTTP, methods=["DELETE"])
@auth_required
async def delete_user(request: web.Request):
    user_id: str = request.match_info["user_id"]

    user = await UsersService.get_user_by_id(int(user_id), UsersBackend())
    status_code = HTTPStatus.OK if user else HTTPStatus.NOT_FOUND

    if user:
        await UsersService.delete_user(user, UsersBackend())
        return web.json_response(
            UserResource(user=user).dict(), status=status_code
        )

    return web.json_response(UserResource().dict(), status=status_code)
