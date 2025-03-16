import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request
from collections import defaultdict

# Настройки
base_url = "http://harts/hart/odata/standard.odata"
username = "hartman"
password = ""

app = Flask(__name__)

# Словарь с названиями месяцев
month_names = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь"
}

# --- Функции для работы с OData ---
def get_data_from_odata(url, username=username, password=password):
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

# --- Функции для обработки данных ---
def calculate_profit(sales, returns, expenses):
    """Вычисляет прибыль."""
    total_sales = sum(sale.get('СуммаДокумента', 0) for sale in sales)
    total_returns = sum(return_.get('СуммаДокумента', 0) for return_ in returns)
    total_expenses = sum(exp.get('СуммаДокумента', 0) for exp in expenses)
    return round(total_sales - total_returns - total_expenses, 2)

def calculate_inventory_turnover(sales, opening_balance, closing_balance):
    """Вычисляет оборачиваемость запасов."""
    total_sales_cost = sum(
        row.get('Себестоимость', row.get('Цена', 0)) * row.get('Количество', 0)
        for sale in sales
        for row in sale.get('Товары', [])
    )
    average_inventory = (opening_balance + closing_balance) / 2 if (opening_balance + closing_balance) > 0 else 0
    if average_inventory == 0:
        return 0
    return round(total_sales_cost / average_inventory, 2)

def get_top_products(sales, nomenclature_dict, n=10):
    """Получает топ N продаваемых товаров с названиями."""
    product_sales = defaultdict(int)
    for sale in sales:
        for row in sale.get('Товары', []):
            product_key = row.get('Номенклатура_Key')
            product_name = nomenclature_dict.get(product_key)
            if product_name:
                product_sales[product_name] += row.get('Количество', 0)
    
    sorted_products = sorted(product_sales.items(), key=lambda item: item[1], reverse=True)
    return [{'name': product[0], 'sales': round(product[1], 2)} for product in sorted_products[:n]]

def get_manager_performance(sales, returns, managers_dict):
    """Получает результаты менеджеров."""
    manager_sales = defaultdict(float)

    for sale in sales:
        manager_key = sale.get('Менеджер_Key')
        manager_name = managers_dict.get(manager_key)
        if manager_name:
            manager_sales[manager_name] += sale.get('СуммаДокумента', 0)

    for ret in returns:
        manager_key = ret.get('Менеджер_Key')
        manager_name = managers_dict.get(manager_key)
        if manager_name:
            manager_sales[manager_name] -= ret.get('СуммаДокумента', 0)

    return [{'name': manager, 'sales': round(sales, 2)} for manager, sales in manager_sales.items()]

# --- Flask маршруты ---
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    date_start = request.form.get('date_start', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    date_end = request.form.get('date_end', datetime.now().strftime('%Y-%m-%d'))
    
    manager_names = {
        "hartmann.base4@outlook.com": "Ольга Тутукова",
        "hartmann.base2@outlook.com": "Соколова Ирина"
    }

    # Фильтры по датам
    date_filter = f"Date ge datetime'{date_start}T00:00:00' and Date le datetime'{date_end}T23:59:59' and Posted eq true"

    # --- Запросы к OData ---
    sales = get_data_from_odata(f"{base_url}/Document_РеализацияТоваровУслуг?$format=json&$filter={date_filter}")
    returns = get_data_from_odata(f"{base_url}/Document_ВозвратТоваровОтКлиента?$format=json&$filter={date_filter}")
    expenses = get_data_from_odata(f"{base_url}/Document_СписаниеБезналичныхДенежныхСредств?$format=json&$filter={date_filter}")
    managers_data = get_data_from_odata(f"{base_url}/Catalog_Пользователи?$format=json&$select=Ref_Key,Description")
    nomenclature_data = get_data_from_odata(f"{base_url}/Catalog_Номенклатура?$format=json&$select=Ref_Key,Description")

    # Получение остатков через RecordSet
    opening_balance_data = get_data_from_odata(
        f"{base_url}/AccumulationRegister_ТоварыНаСкладах?$format=json&$select=RecordSet/Номенклатура_Key,RecordSet/ВНаличии,RecordSet/Period&$filter=RecordSet/any(a: a/Period le datetime'{date_start}T00:00:00')"
    )
    opening_balance = sum(item.get('RecordSet', [{}])[0].get('ВНаличии', 0) for item in opening_balance_data or [])

    closing_balance_data = get_data_from_odata(
        f"{base_url}/AccumulationRegister_ТоварыНаСкладах?$format=json&$select=RecordSet/Номенклатура_Key,RecordSet/ВНаличии,RecordSet/Period&$filter=RecordSet/any(a: a/Period le datetime'{date_end}T23:59:59')"
    )
    closing_balance = sum(item.get('RecordSet', [{}])[0].get('ВНаличии', 0) for item in closing_balance_data or [])

    managers_dict = {manager['Ref_Key']: manager_names.get(manager['Description'], manager['Description']) for manager in managers_data} if managers_data else {}
    nomenclature_dict = {item['Ref_Key']: item['Description'] for item in nomenclature_data} if nomenclature_data else {}

    # --- Подготовка данных для шаблона ---
    top_products = get_top_products(sales, nomenclature_dict)
    managers = get_manager_performance(sales, returns, managers_dict)

    total_income = round(sum(sale.get('СуммаДокумента', 0) for sale in sales), 2)
    total_expenses = round(sum(expense.get('СуммаДокумента', 0) for expense in expenses), 2)
    total_profit = calculate_profit(sales, returns, expenses)

    # Рассчитываем оборачиваемость, себестоимость и средний остаток для каждого месяца
    inventory_turnover_data = []
    inventory_turnover_labels = []
    sales_cost_data = []  # Себестоимость проданных товаров
    average_inventory_data = []  # Средний остаток запасов

    for i in range(6):
        start_date = (datetime.now() - timedelta(days=30 * (i + 1))).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=30 * i)).strftime('%Y-%m-%d')
        
        sales_month = get_data_from_odata(f"{base_url}/Document_РеализацияТоваровУслуг?$format=json&$filter=Date ge datetime'{start_date}T00:00:00' and Date le datetime'{end_date}T23:59:59' and Posted eq true")
        opening_balance_month = sum(item.get('RecordSet', [{}])[0].get('ВНаличии', 0) for item in get_data_from_odata(
            f"{base_url}/AccumulationRegister_ТоварыНаСкладах?$format=json&$select=RecordSet/Номенклатура_Key,RecordSet/ВНаличии,RecordSet/Period&$filter=RecordSet/any(a: a/Period le datetime'{start_date}T00:00:00')"
        ))
        closing_balance_month = sum(item.get('RecordSet', [{}])[0].get('ВНаличии', 0) for item in get_data_from_odata(
            f"{base_url}/AccumulationRegister_ТоварыНаСкладах?$format=json&$select=RecordSet/Номенклатура_Key,RecordSet/ВНаличии,RecordSet/Period&$filter=RecordSet/any(a: a/Period le datetime'{end_date}T23:59:59')"
        ))
        
        # Себестоимость проданных товаров
        total_sales_cost = sum(
            row.get('Себестоимость', row.get('Цена', 0)) * row.get('Количество', 0)
            for sale in sales_month
            for row in sale.get('Товары', [])
        )
        
        # Средний остаток запасов
        average_inventory = (opening_balance_month + closing_balance_month) / 2
        
        # Оборачиваемость запасов
        turnover = calculate_inventory_turnover(sales_month, opening_balance_month, closing_balance_month)
        
        inventory_turnover_data.append(turnover)
        sales_cost_data.append(total_sales_cost)
        average_inventory_data.append(average_inventory)

        # Добавляем название месяца
        month_number = (datetime.now() - timedelta(days=30 * i)).month
        inventory_turnover_labels.append(month_names.get(month_number, "Неизвестный месяц"))

    # Переворачиваем списки, чтобы данные шли от старых к новым
    inventory_turnover_data.reverse()
    inventory_turnover_labels.reverse()
    sales_cost_data.reverse()
    average_inventory_data.reverse()

    # Подготовка данных для графика
    sales_channels_labels = ['Розница', 'Опт', 'Интернет']
    sales_channels_data = [45, 25, 30]  # Пример данных для каналов сбыта
    
    # Рассчитываем среднее значение оборачиваемости
    average_turnover = sum(inventory_turnover_data) / len(inventory_turnover_data) if inventory_turnover_data else 0

    return render_template('dashboard.html',
                        date_start=date_start, date_end=date_end,
                        total_income=total_income, total_expenses=total_expenses, total_profit=total_profit,
                        top_products=top_products,
                        sales_channels_labels=sales_channels_labels, sales_channels_data=sales_channels_data,
                        inventory_turnover_labels=inventory_turnover_labels,
                        inventory_turnover_data=inventory_turnover_data,
                        sales_cost_data=sales_cost_data,  # Передаем себестоимость
                        average_inventory_data=average_inventory_data,  # Передаем средний остаток
                        average_turnover=average_turnover,  # Передаем среднее значение
                        managers=managers)

if __name__ == '__main__':
    app.run(debug=True, port=5000)