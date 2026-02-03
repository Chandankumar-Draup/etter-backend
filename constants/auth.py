import os

ENV = os.environ.get('ENV', 'qa')
URL_MAPPING = {
    "qa": "https://qa-platform.draup.technology",
    "prod": "https://platform.draup.com"
}

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')

TEMP_AUTH_TOKEN = os.environ.get('TEMP_AUTH_TOKEN')
DRAUP_API = URL_MAPPING.get(ENV)

DRAUP_LLM_USER = 'etter'
