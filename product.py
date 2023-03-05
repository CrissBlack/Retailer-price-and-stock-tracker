import requests
from bs4 import BeautifulSoup

HEADERS = {
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64)'
                       'AppleWebKit/537.36 (KHTML, like Gecko)'
                       'Chrome/44.0.2403.157 Safari/537.36'),
        'Accept-Language': 'en-US, en;q=0.5'
    }


class Product:
    def __init__(self, url):
        self.url = url
        self.soup = self.get_soup()
        self.name = self.get_name()
        self.stock_comment = self.get_stock_comment()
        self.in_stock = 0 if self.stock_comment == 'Stoc epuizat' else 1
        self.price = self.get_price() if self.in_stock else None

    def get_soup(self):
        html = requests.get(self.url, headers=HEADERS)
        return BeautifulSoup(html.text, features='lxml')

    def check_stock(self):
        return False if self.soup.find_all(class_='label-out_of_stock') else True

    def get_stock_comment(self):
        return self.soup.select_one('p[class="stock-and-genius"]').text.strip()

    def get_price(self):
        price_string = self.soup.select_one('.product-new-price').text.strip()
        price_float = float(price_string.rstrip(" Lei").replace(".", "").replace(",", "."))
        return price_float

    def get_name(self):
        name = self.soup.select_one('h1[class="page-title"]').text.strip()
        return name


