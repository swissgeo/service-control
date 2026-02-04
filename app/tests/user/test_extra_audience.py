from unittest.mock import patch

from django.conf import settings

import pytest

from user.extra_audience import add_extra_audience, remove_extra_audience
from utils.testing import AsyncMagicMock


@pytest.mark.asyncio
@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
async def test_add_extra_audience(ssm_client):
    ssm_client.return_value.get_parameter.return_value = "first,second"
    await add_extra_audience("new_value")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "first,second,new_value")


@pytest.mark.asyncio
@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
async def test_add_extra_audience_empty(ssm_client):
    ssm_client.return_value.get_parameter.return_value = ""
    await add_extra_audience("new_value")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "new_value")


@pytest.mark.asyncio
@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
async def test_remove_extra_audience(ssm_client):
    ssm_client.return_value.get_parameter.return_value = "first,second"
    await remove_extra_audience("second")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "first")


@pytest.mark.asyncio
@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
async def test_remove_extra_audience_many(ssm_client):
    ssm_client.return_value.get_parameter.return_value = "first,second,third"
    await remove_extra_audience("second")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "first,third")


@pytest.mark.asyncio
@patch("user.extra_audience.Client", new_callable=AsyncMagicMock)
async def test_remove_extra_audience_last(ssm_client):
    ssm_client.return_value.get_parameter.return_value = "last"
    await remove_extra_audience("last")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "")
