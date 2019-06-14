import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENVIRONMENT = os.environ.get('ENV')
if ENVIRONMENT:
    ENVIRONMENT = ENVIRONMENT.lower()
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = ENVIRONMENT not in ('prod',)
if ENVIRONMENT in ('dev', 'prod',):
    ALLOWED_HOSTS = [host.strip() for host in os.environ['ALLOWED_HOSTS'].split(',')]
CORS_ORIGIN_ALLOW_ALL = True

INSTALLED_APPS = [
    # 'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'corsheaders',
    'rest_framework',
    'django_filters',
    'summary_api.apps.ApiConfig',
    'django_s3_storage',
    'drf_yasg',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR, os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME') or 'mermaid',
        'USER': os.environ.get('DB_USER') or 'postgres',
        'PASSWORD': os.environ.get('DB_PASSWORD') or 'postgres',
        'HOST': os.environ.get('DB_HOST') or 'localhost',
        'PORT': os.environ.get('DB_PORT') or '5432'
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
if ENVIRONMENT in ('dev', 'prod',):
    STATICFILES_STORAGE = "django_s3_storage.storage.StaticS3Storage"
    STATIC_BUCKET = "mermaid-summary-api-static"
    AWS_S3_BUCKET_NAME_STATIC = STATIC_BUCKET
    AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % STATIC_BUCKET
    STATIC_URL = "https://%s/" % AWS_S3_CUSTOM_DOMAIN


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'summary_api.resources.permissions.DefaultPermission',
        # 'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
}

SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_REQUIREMENTS': {},
    'SECURITY_DEFINITIONS': None
}
