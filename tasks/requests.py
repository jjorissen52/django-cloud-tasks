"""
Some wrappers around the requests library. If we import these methods from this file,
we either get the defaults or the custom.
"""
from typing import Optional

from requests import *

from .openid import create_token


class Session(Session):
    """
    Wrapper around requests.Session that streamlines adding a Bearer token
    """

    def __init__(self, auth_token: Optional[str] = None, headers: Optional[dict] = None):
        super().__init__()
        if headers:
            if auth_token:
                auth_token = auth_token.split('Bearer')[-1].strip()
                headers['authorization'] = f'Bearer {auth_token}'
            self.headers.update(headers)


def create_openid_session(audience: Optional[str] = None) -> Session:
    """
    Create a Session with a Google OpenID using the given audience. Defaults to
    `tasks.open_id.DEFAULT_AUDIENCE`
    :param audience: audience (receiving url) of the token
    :return: tasks.requests.Session instance
    """
    token = create_token(audience=audience, quiet=True)
    return Session(auth_token=token)
