from flask import Blueprint, render_template
from db import get_db_connection

reports_bp = Blueprint('reports', __name__, template_folder='templates')

@reports_bp.route('/stats')
def stats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(id) as total_orders, IFNULL(SUM(final_amount), 0) as total_revenue 
        FROM Invoices
    """)
    overview = cursor.fetchone()

    cursor.execute("""
        SELECT DATE(created_at) as sale_date, SUM(final_amount) as daily_revenue
        FROM Invoices
        GROUP BY DATE(created_at)
        ORDER BY sale_date DESC
        LIMIT 7
    """)
    daily_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    daily_data.reverse()
    labels = [d['sale_date'].strftime('%d/%m') for d in daily_data] if daily_data else []
    revenues = [float(d['daily_revenue']) for d in daily_data] if daily_data else []

    return render_template('stats.html', overview=overview, labels=labels, revenues=revenues)

