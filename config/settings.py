from typing import Final
from envparse import Env

# # Initialize Env and explicitly load the .env file
env = Env()
# env.read_envfile()

PROJECT_ID: Final[str] = env.str("PROJECT_ID")
DATASET_ID: Final[str] = env.str("DATASET_ID", default="VapiAiVoiceAgent")
APPOINTMENTS_TABLE_ID: Final[str] = env.str("APPOINTMENTS_TABLE_ID", default="appointments")
COMPLAINTS_TABLE_ID: Final[str] = env.str("COMPLAINTS_TABLE_ID", default="complaints")
TARGET_SERVICE_ACCOUNT: Final[str] = env.str("TARGET_SERVICE_ACCOUNT")
DELEGATED_USER: Final[str] = env.str("DELEGATED_USER")
VAPI_SERVER_SECRET: Final[str] = env.str("VAPI_SERVER_SECRET")