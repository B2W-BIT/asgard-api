from collections import defaultdict
from typing import Callable, Dict

import jwt
import sqlalchemy
from aiohttp import web
from asyncworker.http.wrapper import RequestWrapper
from asyncworker.routes import call_http_handler
from sqlalchemy.orm.exc import NoResultFound

from asgard import db
from asgard.models.account import AccountDB, Account
from asgard.models.user import UserDB, User
from asgard.models.user_has_account import UserHasAccount
from hollowman.conf import SECRET_KEY
from hollowman.log import logger

unhandled_auth_error = {"msg": "Authorization failed. Unexpected error"}
invalid_token_response_body = {"msg": "Authorization token is invalid"}
permission_denied_on_account_response_body = {
    "msg": "Permission Denied to access this account"
}
no_associated_account_response_error = {"msg": "No associated account"}
account_does_not_exist_response_error = {"msg": "Account does not exist"}


def make_response(json_data, status_code):
    return web.json_response(json_data, status=status_code)


class TokenTypes(object):
    USER_TOKEN = "Token"
    JWT = "JWT"


async def _get_account_by_id(account_id):
    if account_id:
        async with db.AsgardDBSession() as s:
            try:
                return (
                    await s.query(AccountDB)
                    .filter(AccountDB.id == account_id)
                    .one()
                )
            except NoResultFound:
                return None


def _build_base_query(session: db.session.AsgardDBConnection):
    _join = UserDB.__table__.join(
        UserHasAccount, UserDB.id == UserHasAccount.c.user_id, isouter=True
    ).join(
        AccountDB.__table__,
        AccountDB.id == UserHasAccount.c.account_id,
        isouter=True,
    )
    session.query(UserDB, AccountDB.id.label("account_id")).join(_join)


async def _build_user_instance(
    session: db.session.AsgardDBConnection,
    query_additional_criteria: sqlalchemy.sql.elements.BinaryExpression,
    auth_failed_log_data: dict,
):
    _build_base_query(session)
    rows = await session.filter(query_additional_criteria).all()
    if not rows:
        logger.warning(auth_failed_log_data)
        return None
    account_ids = [row.account_id for row in rows if row.account_id]
    user = UserDB(
        id=rows[0].id, tx_name=rows[0].tx_name, tx_email=rows[0].tx_email
    )
    user.account_ids = account_ids
    return user


async def check_auth_token(token):
    async with db.AsgardDBSession() as session:
        return await _build_user_instance(
            session,
            UserDB.tx_authkey == token,
            {
                "event": "auth-failed",
                "token-type": "apikey",
                "error": "Key not found",
                "token": token,
            },
        )


async def check_jwt_token(jwt_token):
    try:
        payload = jwt.decode(jwt_token, key=SECRET_KEY)
    except Exception as e:
        logger.warning(
            {
                "event": "invalid-token",
                "token-type": "jwt",
                "error": str(e),
                "token": jwt_token,
            }
        )
        return None
    async with db.AsgardDBSession() as session:
        return await _build_user_instance(
            session,
            UserDB.tx_email == payload["user"]["email"],
            {
                "event": "auth-failed",
                "token-type": "JWT",
                "error": "user not found",
                "email": payload["user"]["email"],
            },
        )


def _extract_account_id_from_jwt(jwt_token):
    try:
        return jwt.decode(jwt_token, key=SECRET_KEY)["current_account"]["id"]
    except Exception:
        return None


async def not_authenticated(_):
    return None


AUTH_TYPES: Dict[str, Callable] = defaultdict(lambda: not_authenticated)
AUTH_TYPES[TokenTypes.USER_TOKEN] = check_auth_token
AUTH_TYPES[TokenTypes.JWT] = check_jwt_token


def auth_required(fn):
    async def wrapper(wrapper: RequestWrapper, *args, **kwargs):
        try:
            user = None
            auth_header = wrapper.http_request.headers.get(
                "Authorization", "invalid-type invalid-token"
            )
            token_type, token = auth_header.strip().split(" ")

            user = await AUTH_TYPES[token_type](token)

            if not user:
                return make_response(invalid_token_response_body, 401)

            if not user.account_ids:
                return make_response(no_associated_account_response_error, 401)

            request_account_id = wrapper.http_request.query.get(
                "account_id"
            ) or _extract_account_id_from_jwt(token)
            request_account_on_db = await _get_account_by_id(
                request_account_id or user.account_ids[0]
            )
            if request_account_id and not request_account_on_db:
                return make_response(account_does_not_exist_response_error, 401)

            if (
                request_account_on_db.id
                and request_account_on_db.id not in user.account_ids
            ):
                return make_response(
                    permission_denied_on_account_response_body, 401
                )

            wrapper.types_registry.set(await User.from_alchemy_obj(user))
            wrapper.types_registry.set(
                await Account.from_alchemy_obj(request_account_on_db)
            )

        except Exception as e:
            logger.exception({"exc": e, "event": "auth-unhandled-error"})
            return make_response(unhandled_auth_error, 401)

        user.current_account = request_account_on_db
        wrapper.http_request.user = user
        return await call_http_handler(wrapper.http_request, fn)

    return wrapper
