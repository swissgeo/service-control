from io import StringIO
from unittest.mock import MagicMock

from django.core.management import call_command


def test_command_creates(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'localhost')
    monkeypatch.setenv('DB_PORT', '5432')
    monkeypatch.setenv('DB_ADMIN_USER', 'admin')
    monkeypatch.setenv('DB_ADMIN_PW', 'pazzword')
    monkeypatch.setenv('DB_USER', 'user')
    monkeypatch.setenv('DB_PW', 'password')
    monkeypatch.setenv('DB_NAME', 'database')

    cursor = MagicMock(name='cursor')
    cursor.execute.return_value.fetchone.return_value = None
    connection = MagicMock(name='connection')
    connection.cursor.return_value.__enter__.return_value = cursor
    connect = MagicMock(name='connect')
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr('support.management.commands.init_db.connect', connect)

    out = StringIO()
    call_command('init_db', verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Created role 'user'" in out
    assert "Created database 'database'" in out
    assert "Done" in out

    assert 'host=localhost port=5432 user=admin password=pazzword dbname=postgres' in str(
        connect.mock_calls
    )
    assert 'CREATE ROLE' in str(cursor.mock_calls)
    assert 'user' in str(cursor.mock_calls)
    assert 'password' in str(cursor.mock_calls)
    assert 'CREATE DATABASE' in str(cursor.mock_calls)
    assert 'database' in str(cursor.mock_calls)


def test_command_skips(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'localhost')
    monkeypatch.setenv('DB_PORT', '5432')
    monkeypatch.setenv('DB_ADMIN_USER', 'admin')
    monkeypatch.setenv('DB_ADMIN_PW', 'pazzword')
    monkeypatch.setenv('DB_USER', 'user')
    monkeypatch.setenv('DB_PW', 'password')
    monkeypatch.setenv('DB_NAME', 'database')

    cursor = MagicMock(name='cursor')
    cursor.execute.return_value.fetchone.return_value = (1,)
    connection = MagicMock(name='connection')
    connection.cursor.return_value.__enter__.return_value = cursor
    connect = MagicMock(name='connect')
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr('support.management.commands.init_db.connect', connect)

    out = StringIO()
    call_command('init_db', verbosity=2, stdout=out)
    out = out.getvalue()

    assert "Created" not in out
    assert "Done" in out

    assert 'host=localhost port=5432 user=admin password=pazzword dbname=postgres' in str(
        connect.mock_calls
    )
    assert 'CREATE ROLE' not in str(cursor.mock_calls)
    assert 'CREATE DATABASE' not in str(cursor.mock_calls)
