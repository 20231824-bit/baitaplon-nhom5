from db import get_db_connection

def get_products_list():
    """Lấy danh sách sản phẩm cho index.html và pos.html với stock trực tiếp từ DB"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, model_name, color, storage, sell_price, image_url, stock
        FROM Products
        ORDER BY id DESC
    """)
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return products

def get_brands():
    """Lấy danh sách brands cho form add/edit product"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Brands ORDER BY brand_name")
    brands = cursor.fetchall()
    cursor.close()
    conn.close()
    return brands

def get_product_by_id(product_id):
    """Lấy chi tiết 1 sản phẩm theo ID"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return product

