import os
import subprocess
import time
from functools import wraps
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import re
import csv

# Установим зависимости из requirements.txt
def install_requirements():
    subprocess.check_call([os.sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

install_requirements()

# Декоратор для измерения времени выполнения функции
def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        wrapper.execution_time = end_time - start_time
        print(f"Function {func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper

# Установка веб-драйвера и настройка браузера
@measure_time
def setup_driver():
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        return driver
    except Exception as e:
        print(f"Ошибка при настройке драйвера: {e}")
        return None

# Функция для парсинга одной страницы
@measure_time
def parse_page(driver, url):
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('li', class_='grid-item')
    data = []

    for item in items:
        sku = item.find('span', class_='prod-sku').text.strip().replace('Арт. ', '')
        title = item.find('span', class_='category-item-title').text.strip()
        price_new = item.find('span', class_='prod-price-new')
        price = price_new.text.strip() if price_new else item.find('span', class_='category-item-price').text.strip()
        status = item.find('span', class_='category-item-status').text.strip()
        link = item.find('a', class_='category-item')['href']
        if not link.startswith('http'):
            link = "https://abb-elektrika.ru" + link

        try:
            title_parts, model = title.rsplit(', ', 1)
        except ValueError:
            title_parts = title
            model = ''

        parts = title_parts.split()
        naimenovanie = ' '.join(parts[:3])
        series = parts[3]
        remaining_parts = ' '.join(parts[4:])

        poles_match = re.search(r'(\d+P(\+N)?)', remaining_parts)
        current_match = re.search(r'(\d+)А', remaining_parts)
        curve_match = re.search(r'\((\w)\)', remaining_parts)
        breaking_capacity_match = re.search(r'(\d+(?:[.,]\d+)?)\s*кА', remaining_parts)

        poles = poles_match.group(1) if poles_match else '0'
        current = int(current_match.group(1)) if current_match else 0
        curve = curve_match.group(1) if curve_match else ''
        breaking_capacity_str = breaking_capacity_match.group(1).replace(',', '.') if breaking_capacity_match else '0.0'
        breaking_capacity = float(breaking_capacity_str) if breaking_capacity_str else 0.0

        data.append([sku, title, price, status, link, naimenovanie, series, poles, current, curve, breaking_capacity, model])

    return data

# Основной код
url_template = "https://abb-elektrika.ru/modulnye-avtomaticheskie-vyklyuchateli?order=price&onpage=96&page={}"

num_pages = input("Введите количество страниц для парсинга (или оставьте пустым для парсинга до конца): ")
num_pages = float('inf') if not num_pages else int(num_pages)

driver = setup_driver()

if driver is None:
    print("Не удалось настроить веб-драйвер. Завершение программы.")
else:
    all_data = []
    page = 1
    parse_times = []

    while page <= num_pages:
        url = url_template.format(page)
        data = parse_page(driver, url)
        parse_times.append(parse_page.execution_time)

        if not data:
            break

        all_data.extend(data)
        page += 1

    @measure_time
    def process_data(data):
        df = pd.DataFrame(data, columns=['Артикул', 'Описание', 'Стоимость', 'Статус', 'Ссылка', 'Наименование', 'Серия', 'Количество полюсов (P)', 'Номинальный ток (А)', 'Кривая срабатывания', 'Номинальная отключающая способность (кА)', 'Модель'])
        df['Номинальный ток (А)'] = pd.to_numeric(df['Номинальный ток (А)'], errors='coerce')
        df['Номинальная отключающая способность (кА)'] = pd.to_numeric(df['Номинальная отключающая способность (кА)'], errors='coerce')
        df.fillna({'Номинальный ток (А)': 0, 'Номинальная отключающая способность (кА)': 0.0, 'Серия': '', 'Кривая срабатывания': '', 'Модель': ''}, inplace=True)
        df['Номинальная отключающая способность (кА)'] = pd.to_numeric(df['Номинальная отключающая способность (кА)'].replace(',', '.', regex=True), errors='coerce')
        df['Номинальный ток (А)'] = df['Номинальный ток (А)'].astype(int)
        df.to_excel('abb_data.xlsx', index=False)
        print("Парсинг завершен. Данные сохранены в файл abb_data.xlsx")

    process_data(all_data)
    driver.quit()

    # Анализ параметров
    def analyze_code():
        total_pages_parsed = page - 1
        total_items_parsed = len(all_data)

        # Временная сложность
        time_complexity = f"O(m * n) где m = {total_pages_parsed}, n = {total_items_parsed / total_pages_parsed if total_pages_parsed else 0}"

        # Пространственная сложность
        space_complexity = f"O(m * n) где m = {total_pages_parsed}, n = {total_items_parsed / total_pages_parsed if total_pages_parsed else 0}"

        # Наихудший случай
        worst_case = f"Время: O(m * n), Память: O(m * n)"

        # Средний случай
        average_case = f"Время: O(m * n), Память: O(m * n)"

        # Лучший случай
        best_case = "Время: O(1), если сразу после первой страницы нет данных для парсинга. Память: O(1)"

        # Читаемость и поддерживаемость
        readability = "Код структурирован, использование декораторов и комментариев улучшает читаемость. Можно улучшить, добавив более подробные комментарии."

        # Скалируемость
        scalability = "Алгоритм хорошо масштабируется, но производительность зависит от возможностей системы и эффективности библиотек."

        print("\nАнализ кода по параметрам:")
        print(f"1. Временная сложность: {time_complexity}")
        print(f"2. Пространственная сложность: {space_complexity}")
        print(f"3. Наихудший случай: {worst_case}")
        print(f"4. Средний случай: {average_case}")
        print(f"5. Лучший случай: {best_case}")
        print(f"6. Читаемость и поддерживаемость: {readability}")
        print(f"7. Скалируемость: {scalability}")

    analyze_code()
