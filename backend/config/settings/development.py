from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ✅ Allow both localhost variants during development
CORS_ALLOW_ALL_ORIGINS = True