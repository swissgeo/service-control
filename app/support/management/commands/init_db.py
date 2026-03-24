from typing import TYPE_CHECKING, Any

import environ
from psycopg import connect
from psycopg.sql import SQL, Identifier, Literal

from utils.command import CustomBaseCommand

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

env = environ.Env()


class Command(CustomBaseCommand):
    """Create the postgres role and database from information from the environment."""

    help = "Database management"

    def add_arguments(self, parser: CommandParser) -> None:
        # Call the base class method to get default arguments defined in the base class
        # (mainly 'logger')
        super().add_arguments(parser)

        parser.add_argument(
            "--recreate-db",
            action="store_true",
            help="Drop the database and recreate it (THIS REMOVES ALL DATA)",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002, C901
        host = env.str("DB_HOST", default="").strip()
        port = env.str("DB_PORT", default="").strip()
        admin_name = env.str("DB_ADMIN_USER", default="").strip()
        admin_password = env.str("DB_ADMIN_PW", default="").strip()
        user_name = env.str("DB_USER", default="").strip()
        user_password = env.str("DB_PW", default="").strip()
        database_name = env.str("DB_NAME", default="").strip()

        if not host:
            self.print_error("no DB_HOST provided")
        if not port:
            self.print_error("no DB_PORT provided")
        if not admin_name:
            self.print_error("no DB_ADMIN_USER provided")
        if not admin_password:
            self.print_error("no DB_ADMIN_PW provided")
        if not user_name:
            self.print_error("no DB_USER provided")
        if not user_password:
            self.print_error("no DB_PW provided")
        if not database_name:
            self.print_error("no DB_NAME provided")

        connection_string = (
            f"host={host} port={port} user={admin_name} password={admin_password} dbname=postgres"
        )

        with connect(connection_string, autocommit=True) as connection:
            with connection.cursor() as cursor:
                # create role
                result = cursor.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=%s", (user_name,)
                ).fetchone()
                if result is None:
                    cursor.execute(
                        SQL("CREATE ROLE {} WITH LOGIN ENCRYPTED PASSWORD {}").format(
                            Identifier(user_name),
                            Literal(user_password),
                        ),
                    )
                    self.print_success("Created role '%s'", user_name)
                    connection.commit()

                if options.get("recreate_db", False):
                    # drop database
                    cursor.execute(
                        SQL("DROP DATABASE IF EXISTS {}").format(Identifier(database_name)),
                    )
                    self.print_success("Dropped database '%s'", database_name)
                    connection.commit()

                # create database
                result = cursor.execute(
                    "SELECT 1 FROM pg_catalog.pg_database WHERE datname=%s",
                    (database_name,),
                ).fetchone()
                if result is None:
                    cursor.execute(
                        SQL(
                            "CREATE DATABASE {} OWNER {}",
                        ).format(Identifier(database_name), Identifier(user_name)),
                    )
                    self.print_success("Created database '%s'", database_name)
                    connection.commit()

            self.print("Done")
