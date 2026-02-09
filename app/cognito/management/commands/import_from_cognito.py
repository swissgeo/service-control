from typing import Any

from cognito.utils.client import Client
from user.models import User
from utils.command import CustomBaseCommand


class Command(CustomBaseCommand):
    """Import users from cognito to database."""

    help = "User management"

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        client = Client()
        user_response = client.list_users(pagination_token=None)
        none_imported = True
        for u in user_response["Users"]:
            db_user = User.objects.filter(username=u["Username"]).first()
            if db_user is None:
                self.print(f"Imported user '{u['Username']}'")
                # Create the user
                User.objects.create(username=u["Username"])
                none_imported = False

        pagination_token = user_response.get("PaginationToken", None)
        while pagination_token is not None:
            user_response = client.list_users(pagination_token=pagination_token)
            for u in user_response["Users"]:
                db_user = User.objects.filter(username=u["Username"]).first()
                if db_user is None:
                    self.print(f"Imported user '{u['Username']}'")
                    # Create the user
                    User.objects.create(username=u["Username"])
            pagination_token = user_response.get("PaginationToken", None)

        if none_imported:
            self.print("no new users to import")
