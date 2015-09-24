from __future__ import absolute_import, unicode_literals

from .production import *

ROOT_URLCONF = 'opencanada.urls_admin'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

IS_PRODUCTION = False
