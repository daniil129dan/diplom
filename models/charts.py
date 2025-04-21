from datetime import datetime, timedelta
from utils.odata_client import get_data_from_odata
from utils.data_processing import calculate_inventory_turnover
from utils.constants import MONTH_NAMES
from config import Config

def prepare_inventory_turnover_data(date_start, date_end):
    """Подготавливает данные для графика оборачиваемости запасов."""
    inventory_turnover_data = []
    inventory_turnover_labels = []
    sales_cost_data = []
    average_inventory_data = []

    for i in range(6):
        start_date = (datetime.now() - timedelta(days=30 * (i + 1))).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=30 * i)).strftime('%Y-%m-%d')
        
        sales_month = get_data_from_odata(
            f"{Config.BASE_URL}/Document_РеализацияТоваровУслуг?$format=json&$filter="
            f"Date ge datetime'{start_date}T00:00:00' and Date le datetime'{end_date}T23:59:59' and Posted eq true"
        )
        
        opening_balance_month = sum(
            item.get('RecordSet', [{}])[0].get('ВНаличии', 0) 
            for item in get_data_from_odata(
                f"{Config.BASE_URL}/AccumulationRegister_ТоварыНаСкладах?$format=json&$select="
                f"RecordSet/Номенклатура_Key,RecordSet/ВНаличии,RecordSet/Period&$filter="
                f"RecordSet/any(a: a/Period le datetime'{start_date}T00:00:00')"
            )
        )
        
        closing_balance_month = sum(
            item.get('RecordSet', [{}])[0].get('ВНаличии', 0) 
            for item in get_data_from_odata(
                f"{Config.BASE_URL}/AccumulationRegister_ТоварыНаСкладах?$format=json&$select="
                f"RecordSet/Номенклатура_Key,RecordSet/ВНаличии,RecordSet/Period&$filter="
                f"RecordSet/any(a: a/Period le datetime'{end_date}T23:59:59')"
            )
        )
        
        total_sales_cost = sum(
            row.get('Себестоимость', row.get('Цена', 0)) * row.get('Количество', 0)
            for sale in sales_month
            for row in sale.get('Товары', [])
        )
        
        average_inventory = (opening_balance_month + closing_balance_month) / 2
        turnover = calculate_inventory_turnover(sales_month, opening_balance_month, closing_balance_month)
        
        inventory_turnover_data.append(turnover)
        sales_cost_data.append(total_sales_cost)
        average_inventory_data.append(average_inventory)

        month_number = (datetime.now() - timedelta(days=30 * i)).month
        inventory_turnover_labels.append(MONTH_NAMES.get(month_number, "Неизвестный месяц"))

    # Переворачиваем списки
    inventory_turnover_data.reverse()
    inventory_turnover_labels.reverse()
    sales_cost_data.reverse()
    average_inventory_data.reverse()

    return {
        'labels': inventory_turnover_labels,
        'turnover_data': inventory_turnover_data,
        'sales_cost_data': sales_cost_data,
        'average_inventory_data': average_inventory_data,
        'average_turnover': sum(inventory_turnover_data) / len(inventory_turnover_data) if inventory_turnover_data else 0
    }