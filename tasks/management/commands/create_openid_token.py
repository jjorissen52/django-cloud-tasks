from django.core.management import BaseCommand

from tasks.openid import create_token


class Command(BaseCommand):
    help = "Generates a Google OpenID JWT token. Useful for testing trade_portal.auth.GoogleOpenIDAuthentication"
    default_audience = 'http://localhost:8000/api/csv/test-auth/'
    audience_argname = 'audience'
    quiet_argname = 'quiet'

    def add_arguments(self, parser):
        parser.add_argument(f'--{Command.audience_argname}', help='URL for which validation with this token is valid.')
        parser.add_argument(f'--{Command.quiet_argname}', action='store_true',
                            help='Suppress all output from stdout except for the token.')

    def handle(self, *args, **options):
        audience = options.get(Command.audience_argname, None)
        quiet = options.get(Command.quiet_argname, False)

        return create_token(audience, quiet)
