from django.conf import settings

from utils.ssm import Client


def add_extra_audience(aud: str) -> None:
    """Add client id to ssm parameter holding list of audiences for oauth2-proxy to read."""
    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    ssm_client = Client()
    param_value = ssm_client.get_parameter(param_name)
    param_value = aud if not param_value else param_value + "," + aud
    ssm_client.put_parameter(param_name, param_value)


def remove_extra_audience(aud: str) -> None:
    """Remove client id from ssm parameter holding list of audiences for oauth2-proxy to read."""
    param_name = settings.OAUTH2_PROXY_EXTRA_AUD_SSM_PARAM_NAME
    ssm_client = Client()
    param_value = ssm_client.get_parameter(param_name)
    list_value = param_value.split(",")
    while aud in list_value:
        list_value.remove(aud)
    new_value = ",".join(list_value)
    ssm_client.put_parameter(param_name, new_value)
