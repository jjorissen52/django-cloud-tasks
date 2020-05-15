import google.auth.transport.requests
from google.oauth2 import id_token

from . conf import ROOT_URL

DEFAULT_AUDIENCE = f'{ROOT_URL}/api/csv/test-auth/'
CERTS_URL = 'https://www.googleapis.com/oauth2/v1/certs'


def create_token(audience=None, quiet=True) -> str:
    """
    Create Google OpenID token with the given audience

    :param audience: url endpoints for which this token can be successfully authenticated
    :param quiet: silence console output
    :return:
    """

    if audience is None:
        if not quiet:
            print(f'Audience unset. Defaulting to {DEFAULT_AUDIENCE}')
        audience = DEFAULT_AUDIENCE
    request = google.auth.transport.requests.Request()
    # https://github.com/googleapis/google-auth-library-python/blob/ca8d98ab2e5277e53ab8df78beb1e75cdf5321e3/google/oauth2/id_token.py#L168-L252
    return id_token.fetch_id_token(request, audience)


def decode_token(token, audience=None) -> dict:
    """
    Decide the given Google OpenID token into JSON representation. If an
    audience is given, the token is verified against the provided audience.
    Otherwise, verification is not attempted

    :param token:
    :param audience:
    :return:
    """
    request = google.auth.transport.requests.Request()
    # https://github.com/googleapis/google-auth-library-python/blob/ca8d98ab2e5277e53ab8df78beb1e75cdf5321e3/google/oauth2/id_token.py#L109-L127
    return id_token.verify_token(token, request, audience=audience, certs_url=CERTS_URL)
