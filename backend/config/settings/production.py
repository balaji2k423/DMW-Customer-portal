from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'https://dmw-customer-portal-3.onrender.com'
).split(',')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')