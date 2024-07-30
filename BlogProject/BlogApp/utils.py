from django.contrib.auth.hashers import check_password
from oauth2_provider.models import AccessToken, RefreshToken
def check_client_secret(stored_secret, provided_secret):
    return check_password(provided_secret, stored_secret)