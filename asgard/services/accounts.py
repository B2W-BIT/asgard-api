from asgard.backends.accounts import AccountsBackend
from asgard.models.account import Account


class AccountsService:
    @staticmethod
    async def get_account_by_id(
        account_id: int, backend: AccountsBackend
    ) -> Account:
        return await backend.get_account_by_id(account_id)
