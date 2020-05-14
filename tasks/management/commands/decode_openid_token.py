import sys
import json

from django.core.management import BaseCommand

import google.auth.transport.requests
from google.oauth2 import id_token
from google.oauth2 import service_account


class Command(BaseCommand):
    help = "Verifies a Google OpenID JWT token. Useful for testing generated tokens."
    certs_url = 'https://www.googleapis.com/oauth2/v1/certs'
    token_argname = 'token'
    audience_argname = 'audience'
    quiet_argname = 'quiet'

    def add_arguments(self, parser):
        parser.add_argument(Command.token_argname, help='Google OpenID JWT Token.')
        parser.add_argument(f'--{Command.audience_argname}', help='URL for which validation with this token is valid.')
        parser.add_argument(f'--{Command.quiet_argname}', action='store_true',
                            help='Suppress all output from stdout except for the token.')

    def handle(self, *args, **options):
        token = options.get(Command.token_argname)
        audience = options.get(Command.audience_argname, None)
        quiet = options.get(Command.quiet_argname, False)

        request = google.auth.transport.requests.Request()
        result = id_token.verify_token(token, request, certs_url=Command.certs_url)
        sys.stdout.write(json.dumps(result, indent=2) + '\n')
        sys.stdout.flush()
        if audience is not None and audience != result['aud']:
            sys.stderr.write(f"Audience from token claim {result['aud']} did not match audience {audience}\n")
            sys.stderr.flush()
            exit(1)
        else:
            sys.stdout.flush()
