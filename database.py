import sqlite3, time
from product import Product


class DataBase:
    def __init__(self):

        self.db = sqlite3.connect('products.db')
        self.cursor = self.db.cursor()
        self.create_db()

# DATABASE CREATION ###################################################################################################

    def create_db(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY,
                last_checked TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                current_price REAL,
                in_stock INTEGER NOT NULL,
                comment TEXT,
                price_alert REAL DEFAULT NULL,
                alert_active TEXT DEFAULT '',
                stock_alert BOOLEAN DEFAULT FALSE
                );
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS timestamps(
            id INTEGER PRIMARY KEY,
            created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            price REAL,
            product_id REFERENCES products(id) ON DELETE CASCADE
            );
        ''')
        self.db.commit()

# ADDING, UPDATING, DELETING ##################################################################################

    def add_product(self, product):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO products (name, url, current_price, in_stock, comment)
                VALUES (?,?,?,?,?)''', (product.name, product.url, product.price, product.in_stock, product.stock_comment,))
            self.db.commit()
        except sqlite3.IntegrityError:
            print('invalid product.')
        else:
            self.update_one(product.name)

    def delete_item(self, name):
        self.cursor.execute('PRAGMA foreign_keys = ON')
        self.cursor.execute('DELETE FROM products WHERE name = ?', (name,))
        self.db.commit()

    def update_one(self, name):
        self.cursor.execute('SELECT * FROM products WHERE name = ?', (name,))
        selected = self.cursor.fetchone()
        selected_id = selected[0]
        selected_url = selected[3]
        product = Product(selected_url)
        self.cursor.execute('''
            UPDATE products SET current_price = ?, last_checked = CURRENT_TIMESTAMP 
            WHERE url = ?''', (product.price, selected_url,))
        self.cursor.execute('INSERT INTO timestamps (price, product_id) VALUES(?, ?)', (product.price, selected_id))
        self.db.commit()

    def update_all(self):
        self.cursor.execute('SELECT * FROM products')
        products_db = self.cursor.fetchall()
        for row in products_db:
            self.update_one(row[2])
            time.sleep(1)

    def update_price_timestamps(self, product):
        self.cursor.execute('SELECT id FROM products WHERE name = ?;', (product.name,))
        product_id = self.cursor.fetchone()[0]
        self.cursor.execute('INSERT INTO timestamps (price, product_id) VALUES (?,?);',
                            (product.price, product_id,))
        self.cursor.execute('''UPDATE products 
                                SET current_price = ?, comment = ?, last_checked = CURRENT_TIMESTAMP 
                                WHERE url = ?;''',
                            (product.price, product.stock_comment, product.url,))
        self.db.commit()

# GET PRODUCT INFORMATION #############################################################################################

    def get_product_list(self):
        self.cursor.execute('''SELECT alert_active, name, current_price, comment, last_checked, 
                            CASE WHEN typeof(price_alert) = ? THEN price_alert  ELSE '' END, 
                            CASE WHEN stock_alert IS TRUE THEN 'enabled' ELSE '' END,
                             url 
                             FROM products;''', ('real', ))
        return self.cursor.fetchall()

    def get_price_history(self, name):
        self.cursor.execute('''
            SELECT t.price, DATE(created_date) FROM
            products  LEFT OUTER JOIN timestamps t on products.id = t.product_id
            WHERE name=?
            GROUP BY DATE(created_date)
            ''', (name,))
        return self.cursor.fetchall()

# NOTIFIER ###########################################################################################################

    def get_products_to_notify(self):
        self.cursor.execute('''SELECT name FROM products 
                                        WHERE 
                                        (current_price < price_alert AND price_alert !='' AND alert_active != 'X')
                                         OR 
                                         (stock_alert = 1 AND in_stock = 1 AND alert_active != 'X')''')
        names_to_notify = self.cursor.fetchall()
        return names_to_notify

    def add_notify(self, name):
        self.cursor.execute('''
                    UPDATE products SET alert_active = 'X' WHERE name = ?;''', (name,))
        self.db.commit()

    def update_price_alert(self, selected_product, value):
        product_name = selected_product[1]
        if value is None:
            self.cursor.execute('''UPDATE products 
                                SET price_alert = NULL, alert_active = '' WHERE name = ?;''', ( product_name,))
            self.db.commit()
        else:
            self.cursor.execute('UPDATE products '
                                'SET price_alert = ? WHERE name = ?;', (value, product_name))
            self.db.commit()
            self.update_one(product_name)

    def update_stock_alert(self, selected_product, value):
        product_name = selected_product[1]
        self.cursor.execute('''UPDATE products SET stock_alert = ? WHERE name = ?''',
                            (1 if value else 0, product_name))
        self.db.commit()
