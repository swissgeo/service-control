from unittest.mock import MagicMock

from init_db import main


def test_init_db(monkeypatch):
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
    monkeypatch.setattr('init_db.connect', connect)

    main()

    assert 'host=localhost port=5432 user=admin password=pazzword dbname=postgres' in str(
        connect.mock_calls
    )
    assert 'CREATE ROLE' in str(cursor.mock_calls)
    assert 'user' in str(cursor.mock_calls)
    assert 'password' in str(cursor.mock_calls)
    assert 'CREATE DATABASE' in str(cursor.mock_calls)
    assert 'database' in str(cursor.mock_calls)


def test_init_db_skips_if_existing(monkeypatch):
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
    monkeypatch.setattr('init_db.connect', connect)

    main()

    assert 'host=localhost port=5432 user=admin password=pazzword dbname=postgres' in str(
        connect.mock_calls
    )
    assert 'CREATE ROLE' not in str(cursor.mock_calls)
    assert 'CREATE DATABASE' not in str(cursor.mock_calls)
