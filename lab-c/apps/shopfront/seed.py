"""Create and seed the sqlite catalog used by the demo."""
import os
import sqlite3

PATH = os.environ.get("SHOP_DB", "/data/shop.db")

PRODUCTS = [
    ("Aurora Desk Lamp", 49.00, "home,lighting"),
    ("Nimbus Running Shoe", 120.00, "apparel,shoes"),
    ("Kettle Pro 1.7L", 35.50, "home,kitchen"),
    ("Trailhead Backpack", 89.90, "outdoor,bags"),
    ("Lumen E-Reader", 139.00, "electronics,reading"),
]


def main():
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    c = sqlite3.connect(PATH)
    c.execute("DROP TABLE IF EXISTS products")
    c.execute(
        "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL, tags TEXT)"
    )
    c.executemany(
        "INSERT INTO products (name, price, tags) VALUES (?, ?, ?)", PRODUCTS
    )
    c.commit()
    c.close()
    print(f"seeded {len(PRODUCTS)} products into {PATH}")


if __name__ == "__main__":
    main()
