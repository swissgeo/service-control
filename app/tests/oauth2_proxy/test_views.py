from django.urls import reverse


def test_admin_login(client):
    response = client.get(reverse('oauth2_proxy_admin_login'))

    assert response.status_code == 302
    assert response.url == 'http://testserver/oauth2-proxy/start?rd=http%3A//testserver/admin/'


def test_admin_logout(settings, client):
    settings.OAUTH2_PROXY_COGNITO_URL = 'https://cognito'
    settings.OAUTH2_PROXY_COGNITO_APP_CLIENT_ID = 'client_id'
    settings.OAUTH2_PROXY_EIAM_URL = 'https://eiam'

    response = client.get(reverse('oauth2_proxy_admin_logout'))

    assert response.status_code == 302
    assert response.url == (
        'http://testserver/oauth2-proxy/sign_out?rd='
        'https%3A%2F%2Fcognito%2Flogout%3Fclient_id%3Dclient_id%26logout_uri%3D'
        'https%253A%252F%252Feiam%252Flogout%253Flogout_uri%253D'
        'http%25253A%25252F%25252Ftestserver%25252F'
    )
