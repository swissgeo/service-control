"""
Database initialization script for PostgreSQL.

This script creates the role and database used by Django using the database admin credentials.
Uses autocommit mode because PostgreSQL does not allow CREATE DATABASE to run inside a transaction
block.
"""

from logging import getLogger
from logging.config import dictConfig
from os import environ

from psycopg import connect
from psycopg.sql import SQL
from psycopg.sql import Identifier
from psycopg.sql import Literal

from django.conf import settings

dictConfig(settings.LOGGING)
logger = getLogger(__name__)


def main() -> None:
    host = environ.get('DB_HOST')
    port = environ.get('DB_PORT')
    admin_name = environ.get('DB_ADMIN_USER')
    admin_password = environ.get('DB_ADMIN_PW')
    user_name = environ.get('DB_USER')
    user_password = environ.get('DB_PW')
    database_name = environ.get('DB_NAME')

    if not user_name:
        raise ValueError("no DB_USER provided")
    if not user_password:
        raise ValueError("no DB_NAME provided")
    if not database_name:
        raise ValueError("no DB_NAME provided")

    if not all((host, port, admin_name, admin_password, user_name, user_password, database_name)):
        raise ValueError('Some of the environment variables are undefined')

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
            connection.commit()
            logger.info("Created role '%s'", user_name)

            # create database
            result = cursor.execute(
                "SELECT 1 FROM pg_catalog.pg_database WHERE datname=%s", (database_name,)
            ).fetchone()
            if result is None:
                cursor.execute(
                    SQL("CREATE DATABASE {} OWNER {}"
                       ).format(Identifier(database_name), Identifier(user_name))
                )
            connection.commit()
            logger.info("Created database '%s'", database_name)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:  # pylint: disable=broad-exception-caught
        dictConfig(settings.LOGGING)
        logger = getLogger(__name__)
        logger.exception(e)
