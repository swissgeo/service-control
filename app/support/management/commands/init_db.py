from typing import Any

import environ
from psycopg import connect
from psycopg.sql import SQL
from psycopg.sql import Identifier
from psycopg.sql import Literal
from utils.command import CommandHandler
from utils.command import CustomBaseCommand

env = environ.Env()


class Handler(CommandHandler):
    """Create the postgres role and database from information from the environment. """

    def run(self) -> None:
        host = env.str('DB_HOST', default='').strip()
        port = env.str('DB_PORT', default='').strip()
        admin_name = env.str('DB_ADMIN_USER', default='').strip()
        admin_password = env.str('DB_ADMIN_PW', default='').strip()
        user_name = env.str('DB_USER', default='').strip()
        user_password = env.str('DB_PW', default='').strip()
        database_name = env.str('DB_NAME', default='').strip()

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
            f"host={host} "
            f"port={port} "
            f"user={admin_name} "
            f"password={admin_password} "
            "dbname=postgres"
        )

        with connect(connection_string, autocommit=True) as connection:
            with connection.cursor() as cursor:
                # create role
                result = cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s",
                                        (user_name,)).fetchone()
                if result is None:
                    cursor.execute(
                        SQL("CREATE ROLE {} WITH LOGIN ENCRYPTED PASSWORD {}").format(
                            Identifier(user_name),
                            Literal(user_password),
                        )
                    )
                    self.print_success("Created role '%s'", user_name)
                    connection.commit()

                # create database
                result = cursor.execute(
                    "SELECT 1 FROM pg_catalog.pg_database WHERE datname=%s", (database_name,)
                ).fetchone()
                if result is None:
                    cursor.execute(
                        SQL("CREATE DATABASE {} OWNER {}"
                           ).format(Identifier(database_name), Identifier(user_name))
                    )
                    self.print_success("Created database '%s'", database_name)
                    connection.commit()

            self.print('Done')


class Command(CustomBaseCommand):
    help = "Database management"

    def handle(self, *args: Any, **options: Any) -> None:
        Handler(self, options).run()
