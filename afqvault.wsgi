import os
import sys
sys.path.append('/var/www/AFQVault')
sys.path.append('/var/www/afqvault')
os.environ['DJANGO_SETTINGS_MODULE'] = 'afqvault.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
