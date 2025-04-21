# Функции для работы с OData
import requests
from config import Config

def get_data_from_odata(url, username=Config.USERNAME, password=Config.PASSWORD):
    """Получает данные из OData сервиса с учетом пагинации."""
    all_data = []
    next_link = url
    while next_link:
        try:
            response = requests.get(next_link, auth=(username, password))
            response.raise_for_status()
            data = response.json()
            all_data.extend(data.get('value', []))
            next_link = data.get('@odata.nextLink') or data.get('odata.nextLink')
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса OData: {e}")
            break
    return all_data