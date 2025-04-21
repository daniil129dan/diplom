# Функции обработки данных
from collections import defaultdict

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
    return round(total_sales_cost / average_inventory, 2) if average_inventory != 0 else 0

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