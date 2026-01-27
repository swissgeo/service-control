from unittest.mock import patch

from django.conf import settings

from user.extra_audience import add_extra_audience, remove_extra_audience


@patch("user.extra_audience.Client")
def test_add_extra_audience(ssm_client):
    ssm_client.return_value.get_parameter.return_value = "first,second"
    add_extra_audience("new_value")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "first,second,new_value")


@patch("user.extra_audience.Client")
def test_add_extra_audience_empty(ssm_client):
    ssm_client.return_value.get_parameter.return_value = ""
    add_extra_audience("new_value")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "new_value")


@patch("user.extra_audience.Client")
def test_remove_extra_audience(ssm_client):
    ssm_client.return_value.get_parameter.return_value = "first,second"
    remove_extra_audience("second")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "first")


@patch("user.extra_audience.Client")
def test_remove_extra_audience_many(ssm_client):
    ssm_client.return_value.get_parameter.return_value = "first,second,third"
    remove_extra_audience("second")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "first,third")


@patch("user.extra_audience.Client")
def test_remove_extra_audience_last(ssm_client):
    ssm_client.return_value.get_parameter.return_value = "last"
    remove_extra_audience("last")

    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    assert ssm_client.return_value.get_parameter.call_count == 1
    ssm_client.return_value.put_parameter.assert_called_with(param_name, "")
