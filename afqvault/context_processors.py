from django.conf import settings  # import the settings file


def ga_identifier(request):
    # Make Google Analytics ID available to all templates.
    return {'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID}
