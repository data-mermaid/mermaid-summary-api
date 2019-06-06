from django.core.management import call_command


def refresh_sites():
    call_command('refresh_view', 'vw_summary_site')
