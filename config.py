import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_URL = os.getenv("BASE_URL")
    USERNAME = os.getenv("API_USERNAME")
    PASSWORD = os.getenv("PASSWORD")

    MANAGER_NAMES = {
        "hartmann.base4@outlook.com": "Ольга Тутукова",
        "hartmann.base2@outlook.com": "Соколова Ирина"
    }
