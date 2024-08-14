from django.contrib.auth.hashers import check_password
from oauth2_provider.models import AccessToken, RefreshToken
from django.core.mail import send_mail
def check_client_secret(stored_secret, provided_secret):
    return check_password(provided_secret, stored_secret)

from django.conf import settings

def send_verification_email(to_email, subject, message):
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email],
        fail_silently=False,
    )