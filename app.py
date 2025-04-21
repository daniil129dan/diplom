from dotenv import load_dotenv
import os

# Загружаем переменные окружения из .env
load_dotenv()

from flask import Flask, render_template, request
from datetime import datetime, timedelta
from config import Config
from utils.odata_client import get_data_from_odata
from utils.data_processing import (
    calculate_profit, 
    get_top_products, 
    get_manager_performance
)
from models.charts import prepare_inventory_turnover_data

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    date_start = request.form.get('date_start', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    date_end = request.form.get('date_end', datetime.now().strftime('%Y-%m-%d'))
    
    # Фильтры по датам
    date_filter = f"Date ge datetime'{date_start}T00:00:00' and Date le datetime'{date_end}T23:59:59' and Posted eq true"

    # --- Запросы к OData ---
    sales = get_data_from_odata(f"{Config.BASE_URL}/Document_РеализацияТоваровУслуг?$format=json&$filter={date_filter}")
    returns = get_data_from_odata(f"{Config.BASE_URL}/Document_ВозвратТоваровОтКлиента?$format=json&$filter={date_filter}")
    expenses = get_data_from_odata(f"{Config.BASE_URL}/Document_СписаниеБезналичныхДенежныхСредств?$format=json&$filter={date_filter}")
    managers_data = get_data_from_odata(f"{Config.BASE_URL}/Catalog_Пользователи?$format=json&$select=Ref_Key,Description")
    nomenclature_data = get_data_from_odata(f"{Config.BASE_URL}/Catalog_Номенклатура?$format=json&$select=Ref_Key,Description")

    # Получение остатков
    opening_balance_data = get_data_from_odata(
        f"{Config.BASE_URL}/AccumulationRegister_ТоварыНаСкладах?$format=json&$select=RecordSet/Номенклатура_Key,RecordSet/ВНаличии,RecordSet/Period&$filter=RecordSet/any(a: a/Period le datetime'{date_start}T00:00:00')"
    )
    opening_balance = sum(item.get('RecordSet', [{}])[0].get('ВНаличии', 0) for item in opening_balance_data or [])

    closing_balance_data = get_data_from_odata(
        f"{Config.BASE_URL}/AccumulationRegister_ТоварыНаСкладах?$format=json&$select=RecordSet/Номенклатура_Key,RecordSet/ВНаличии,RecordSet/Period&$filter=RecordSet/any(a: a/Period le datetime'{date_end}T23:59:59')"
    )
    closing_balance = sum(item.get('RecordSet', [{}])[0].get('ВНаличии', 0) for item in closing_balance_data or [])

    managers_dict = {
        manager['Ref_Key']: Config.MANAGER_NAMES.get(manager['Description'], manager['Description']) 
        for manager in managers_data
    } if managers_data else {}
    
    nomenclature_dict = {
        item['Ref_Key']: item['Description'] 
        for item in nomenclature_data
    } if nomenclature_data else {}

    # Подготовка данных
    top_products = get_top_products(sales, nomenclature_dict)
    managers = get_manager_performance(sales, returns, managers_dict)
    total_income = round(sum(sale.get('СуммаДокумента', 0) for sale in sales), 2)
    total_expenses = round(sum(expense.get('СуммаДокумента', 0) for expense in expenses), 2)
    total_profit = calculate_profit(sales, returns, expenses)
    
    # Данные для графиков
    inventory_data = prepare_inventory_turnover_data(date_start, date_end)
    sales_channels_labels = ['Розница', 'Опт', 'Интернет']
    sales_channels_data = [45, 25, 30]  # Пример данных

    return render_template('dashboard.html',
                        date_start=date_start, date_end=date_end,
                        total_income=total_income, total_expenses=total_expenses, total_profit=total_profit,
                        top_products=top_products,
                        sales_channels_labels=sales_channels_labels, sales_channels_data=sales_channels_data,
                        inventory_turnover_labels=inventory_data['labels'],
                        inventory_turnover_data=inventory_data['turnover_data'],
                        sales_cost_data=inventory_data['sales_cost_data'],
                        average_inventory_data=inventory_data['average_inventory_data'],
                        average_turnover=inventory_data['average_turnover'],
                        managers=managers)

if __name__ == '__main__':
    app.run(debug=True, port=5000)