from typing import Any

from cognito.utils.client import Client
from user.models import User
from utils.command import CustomBaseCommand


class Command(CustomBaseCommand):
    """Import users from cognito to database."""

    help = "User management"

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        client = Client()
        none_imported = True
        pagination_token = None

        while True:
            user_respone = client.list_users(pagination_token=pagination_token)
            for u in user_respone["Users"]:
                if not User.objects.filter(username=u["Username"]).exists():
                    User.objects.create(username=u["Username"])
                    self.print(f"Imported user '{u['Username']}'")
                    none_imported = False
            pagination_token = user_respone.get("PaginationToken", None)
            if pagination_token is None:
                break

        if none_imported:
            self.print("no new users to import")
