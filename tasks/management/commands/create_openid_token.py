from django.core.management import BaseCommand

import google.auth.transport.requests
from google.oauth2 import id_token
from google.oauth2 import service_account


class Command(BaseCommand):
    help = "Generates a Google OpenID JWT token. Useful for testing trade_portal.auth.GoogleOpenIDAuthentication"
    default_audience = 'http://localhost:8000/api/csv/test-auth/'
    keyfile_argname = 'service_account_keyfile'
    audience_argname = 'audience'
    quiet_argname = 'quiet'

    def add_arguments(self, parser):
        parser.add_argument(Command.keyfile_argname, help='Location of keyfile on disk.')
        parser.add_argument(f'--{Command.audience_argname}', help='URL for which validation with this token is valid.')
        parser.add_argument(f'--{Command.quiet_argname}', action='store_true',
                            help='Suppress all output from stdout except for the token.')

    def handle(self, *args, **options):
        service_account_file = options.get(Command.keyfile_argname)
        audience = options.get(Command.audience_argname, None)
        quiet = options.get(Command.quiet_argname, False)

        if audience is None:
            if not quiet:
                print(f'Audience unset. Defaulting to {Command.default_audience}')
            audience = Command.default_audience
        creds = service_account.IDTokenCredentials.from_service_account_file(
            service_account_file,
            target_audience=audience)
        request = google.auth.transport.requests.Request()
        creds.refresh(request)
        return creds.token
