from django.test import override_settings
from django.urls import reverse

import pytest

from config.version import APP_VERSION
from tests.admin.test_dataset_admin import ADMIN_HEADERS


@pytest.mark.parametrize(
    ("app_env", "background"),
    [("local", "#B5CCD2"), ("dev", "#F3CB63"), ("int", "#E28054"), ("prod", "#D4311F")],
)
def test_admin_header_shows_environment_and_version(client, db, app_env, background):
    with override_settings(APP_ENV=app_env):
        response = client.get(reverse("admin:index"), **ADMIN_HEADERS)

    assert response.status_code == 200
    assert f"--header-bg: {background};" in response.text
    assert "#header {" in response.text
    assert f'<span class="app-env-badge">{app_env.upper()} · {APP_VERSION}</span>' in response.text


def test_admin_login_page_shows_environment(client, db):
    with override_settings(APP_ENV="prod"):
        response = client.get(reverse("admin:login"))

    assert response.status_code == 200
    assert "--header-bg: #D4311F;" in response.text
    assert f"PROD · {APP_VERSION}" in response.text


def test_admin_header_keeps_default_colors_for_unknown_environment(client, db):
    with override_settings(APP_ENV="foo"):
        response = client.get(reverse("admin:index"), **ADMIN_HEADERS)

    assert response.status_code == 200
    assert "--header-bg:" not in response.text
    assert f"FOO · {APP_VERSION}" in response.text
