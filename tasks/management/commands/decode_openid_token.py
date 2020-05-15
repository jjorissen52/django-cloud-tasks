import json

from django.core.management import BaseCommand

from tasks.openid import decode_token


class Command(BaseCommand):
    help = "Verifies a Google OpenID JWT token. Useful for testing generated tokens."
    certs_url = 'https://www.googleapis.com/oauth2/v1/certs'
    token_argname = 'token'
    audience_argname = 'audience'

    def add_arguments(self, parser):
        parser.add_argument(Command.token_argname, help='Google OpenID JWT Token.')
        parser.add_argument(f'--{Command.audience_argname}', help='URL for which validation with this token is valid.')

    def handle(self, *args, **options):
        token = options.get(Command.token_argname)
        audience = options.get(Command.audience_argname, None)

        return json.dumps(decode_token(token, audience), indent=2)
