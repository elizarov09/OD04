
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import re
import csv

# Установка веб-драйвера и настройка браузера
def setup_driver():
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        return driver
    except Exception as e:
        print(f"Ошибка при настройке драйвера: {e}")
        return None


# Функция для парсинга одной страницы
def parse_page(driver, url):
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('li', class_='grid-item')
    data = []

    for item in items:
        sku = item.find('span', class_='prod-sku').text.strip().replace('Арт. ', '')
        title = item.find('span', class_='category-item-title').text.strip()
        # Проверяем наличие новой цены, если нет, используем старую цену
        price_new = item.find('span', class_='prod-price-new')
        price = price_new.text.strip() if price_new else item.find('span', class_='category-item-price').text.strip()
        status = item.find('span', class_='category-item-status').text.strip()
        # Получаем ссылку на продукт
        link = item.find('a', class_='category-item')['href']
        if not link.startswith('http'):
            link = "https://abb-elektrika.ru" + link

        # Извлекаем модель и оставшуюся часть названия
        try:
            title_parts, model = title.rsplit(', ', 1)
        except ValueError:
            title_parts = title
            model = ''

        # Разбиваем оставшуюся часть названия на атрибуты
        parts = title_parts.split()
        naimenovanie = ' '.join(parts[:3])  # Автоматический выключатель ABB
        series = parts[3]  # Серия
        remaining_parts = ' '.join(parts[4:])  # Оставшиеся части строки после серии

        # Попробуем извлечь параметры с помощью регулярных выражений
        poles_match = re.search(r'(\d+P(\+N)?)', remaining_parts)
        current_match = re.search(r'(\d+)А', remaining_parts)
        curve_match = re.search(r'\((\w)\)', remaining_parts)
        breaking_capacity_match = re.search(r'(\d+(?:[.,]\d+)?)\s*кА', remaining_parts)

        if poles_match:
            poles = poles_match.group(1)
        else:
            poles = '0'

        if current_match:
            current = int(current_match.group(1))
        else:
            current = 0

        if curve_match:
            curve = curve_match.group(1)
        else:
            curve = ''

        if breaking_capacity_match:
            breaking_capacity_str = breaking_capacity_match.group(1).replace(',', '.')
            try:
                breaking_capacity = float(breaking_capacity_str)
            except ValueError:
                breaking_capacity = 0.0
        else:
            breaking_capacity = 0.0

        data.append([sku, title, price, status, link, naimenovanie, series, poles, current, curve, breaking_capacity, model])

    return data


# Основной код
url_template = "https://abb-elektrika.ru/modulnye-avtomaticheskie-vyklyuchateli?order=price&onpage=96&page={}"

# Спрашиваем пользователя, сколько страниц парсить
num_pages = input("Введите количество страниц для парсинга (или оставьте пустым для парсинга до конца): ")
if not num_pages:
    num_pages = float('inf')
else:
    num_pages = int(num_pages)

driver = setup_driver()

if driver is None:
    print("Не удалось настроить веб-драйвер. Завершение программы.")
else:
    all_data = []
    page = 1

    while page <= num_pages:
        url = url_template.format(page)
        data = parse_page(driver, url)

        if not data:
            break

        all_data.extend(data)
        page += 1

    # Создаем DataFrame
    df = pd.DataFrame(all_data,
                      columns=['Артикул', 'Описание', 'Стоимость', 'Статус', 'Ссылка', 'Наименование', 'Серия',
                               'Количество полюсов (P)', 'Номинальный ток (А)', 'Кривая срабатывания',
                               'Номинальная отключающая способность (кА)', 'Модель'])

    # Преобразуем столбцы в числовой формат
    df['Номинальный ток (А)'] = pd.to_numeric(df['Номинальный ток (А)'], errors='coerce')
    df['Номинальная отключающая способность (кА)'] = pd.to_numeric(df['Номинальная отключающая способность (кА)'],
                                                                   errors='coerce')

    # Заменяем None на 0 для числовых столбцов и на пустые строки для остальных столбцов
    df.fillna({
        'Номинальный ток (А)': 0,
        'Номинальная отключающая способность (кА)': 0.0,
        'Серия': '',
        'Кривая срабатывания': '',
        'Модель': ''
    }, inplace=True)

    # Преобразуем 'Номинальная отключающая способность (кА)' в float и удаляем неявные пробелы
    df['Номинальная отключающая способность (кА)'] = pd.to_numeric(df['Номинальная отключающая способность (кА)'].replace(',', '.', regex=True), errors='coerce')

    # Преобразуем целые числа для корректного отображения
    df['Номинальный ток (А)'] = df['Номинальный ток (А)'].astype(int)
    # Сохраняем в CSV, используя точку в качестве разделителя десятичных дробей
    df.to_excel('/Users/olegelizarov/Documents/GitHub/ABB-parsing/abb_data.xlsx', index=False)
    #df.to_csv('/Users/olegelizarov/Documents/GitHub/ABB-parsing/abb_data.csv',
              #index=False,
              #encoding='utf-8-sig',
              #quoting=csv.QUOTE_MINIMAL,
              #decimal='.')

    # Закрываем драйвер
    driver.quit()

    print("Парсинг завершен. Данные сохранены в файл abb_data.csv")
