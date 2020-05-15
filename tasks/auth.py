import re
import time
import logging
import google.auth
import google.auth.transport.requests

from types import SimpleNamespace

from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from google.oauth2 import id_token

User = get_user_model()
logger = logging.getLogger(__name__)

uri_pattern = r'^https?:\/\/(.*)$'
uri_regex = re.compile(uri_pattern)


def remove_protocol(uri):
    match = uri_regex.match(uri)
    if not match:
        return None
    else:
        return match.group(1)


class GoogleOpenIDAuthentication(BaseAuthentication):
    """
    This authentication class requires a bearer token with the standard claims
    (https://developers.google.com/identity/protocols/oauth2/openid-connect#obtainuserinfo)
    and an audience of the current URL.

    It checks that the token was signed with a valid certificate, that the token
    has not expired, that the audience matches the current URL, and that a Django User account for
    the indicated service account exists. Once those checks pass, the user corresponding to the
    indicated service account is returned.
    """
    certs_url = 'https://www.googleapis.com/oauth2/v1/certs'

    def authenticate(self, request):
        print(__name__)
        now = time.time()
        try:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                bearer_token = auth_header[7:]
            else:
                msg = _(f'Authorization header malformed. Expected Bearer: <token>; got {auth_header}')
                logging.info(msg)
                raise exceptions.AuthenticationFailed(msg)
        except KeyError:
            msg = _('Invalid Authorization header. No credentials provided.')
            logging.info(msg)
            raise exceptions.AuthenticationFailed(msg)

        # verify our token
        auth_request = google.auth.transport.requests.Request()
        try:
            token = id_token.verify_token(bearer_token, auth_request, certs_url=GoogleOpenIDAuthentication.certs_url)
        except ValueError as e:
            error_message = getattr(e, 'message', str(e))
            msg = _(f'Authentication failed. Could not verify token; err = {error_message}.')
            logging.error(msg)
            raise exceptions.AuthenticationFailed(msg)
        # ensure that it has the desired claims
        if not all([key in token for key in ['aud', 'iss', 'email', 'email_verified', 'iat', 'exp', 'sub']]):
            msg = _('Authentication failed. Token did not contain all required claims.')
            logging.info(msg)
            raise exceptions.AuthenticationFailed(msg)
        token = SimpleNamespace(**token)
        logging.debug(f'Access attempted with token: {token}')
        # the audience indicated in the token should be the visited URL
        token_audience, required_audience = remove_protocol(token.aud), remove_protocol(request.build_absolute_uri())
        if token_audience != required_audience:
            msg = _(f'Authentication failed. Audience {token.aud} did not match auth endpoint {required_audience}.')
            logging.info(msg)
            raise exceptions.AuthenticationFailed(msg)
        if not token.iat < now < token.exp:
            msg = _(f'Authentication failed. Token outside of valid window. '
                    f'Issued {token.iat}, Expires: {token.exo}, Now: {now}')
            logging.info(msg)
            raise exceptions.AuthenticationFailed(msg)
        try:
            user = User.objects.get(email__iexact=token.email)
        except User.DoesNotExist:
            msg = _(f'Authentication failed. No user with email {token.email}')
            logging.info(msg)
            raise exceptions.AuthenticationFailed(msg)

        return user, None
