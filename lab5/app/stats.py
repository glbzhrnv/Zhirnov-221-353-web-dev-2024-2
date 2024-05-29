from math import ceil
from flask import Blueprint, request, url_for, render_template, send_file, flash, redirect
from flask_login import login_required, current_user
from auth import check_permission
from mysql_db import MySQL
import io
import datetime

stats_bp = Blueprint('stats', __name__, url_prefix='/stats')
mysql = MySQL(stats_bp)

PER_PAGE = 5

@stats_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * PER_PAGE
    cursor = mysql.connection().cursor(named_tuple=True)
    
    if current_user.is_admin():
        cursor.execute('''
            SELECT stats.id, stats.path, stats.created_at, 
                   users.id as user_id, users.first_name, users.middle_name, users.last_name
            FROM stats
            LEFT JOIN users ON stats.user_id = users.id
            ORDER BY stats.created_at DESC
            LIMIT %s OFFSET %s
        ''', (PER_PAGE, offset))
    else:
        cursor.execute('''
            SELECT stats.id, stats.path, stats.created_at, 
                   users.id as user_id, users.first_name, users.middle_name, users.last_name
            FROM stats
            LEFT JOIN users ON stats.user_id = users.id
            WHERE stats.user_id = %s
            ORDER BY stats.created_at DESC
            LIMIT %s OFFSET %s
        ''', (current_user.id, PER_PAGE, offset))
    
    stats = cursor.fetchall()

    cursor.execute('SELECT COUNT(*) as count FROM stats')
    total_stats = cursor.fetchone().count
    last_page = ceil(total_stats / PER_PAGE)

    return render_template('stats/index.html', stats=stats, page=page, last_page=last_page, per_page=PER_PAGE)

@stats_bp.route('/export_csv')
@login_required
def export_csv():
    cursor = mysql.connection().cursor(named_tuple=True)
    
    if current_user.is_admin():
        cursor.execute('''
            SELECT stats.path, stats.created_at, 
                   users.id as user_id, users.first_name, users.middle_name, users.last_name
            FROM stats
            LEFT JOIN users ON stats.user_id = users.id
            ORDER BY stats.created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT stats.path, stats.created_at, 
                   users.id as user_id, users.first_name, users.middle_name, users.last_name
            FROM stats
            LEFT JOIN users ON stats.user_id = users.id
            WHERE stats.user_id = %s
            ORDER BY stats.created_at DESC
        ''', (current_user.id,))
        
    stats = cursor.fetchall()

    csv_data = "User,Page,Date\n"
    for stat in stats:
        if stat.user_id:
            user_name = f"{stat.first_name} {stat.middle_name} {stat.last_name}"
        else:
            user_name = "Неаутентифицированный пользователь"
        created_at = stat.created_at.strftime('%d.%m.%Y %H:%M:%S')
        csv_data += f"{user_name},{stat.path},{created_at}\n"

    f = io.BytesIO()
    f.write(csv_data.encode('utf-8'))
    f.seek(0)
    return send_file(f, as_attachment=True, download_name='stats.csv')

@stats_bp.route('/export_csv_by_routes')
@login_required
def export_csv_by_routes():
    cursor = mysql.connection().cursor(named_tuple=True)
    
    if current_user.is_admin():
        cursor.execute('''
            SELECT path, COUNT(*) as count 
            FROM stats 
            GROUP BY path 
            ORDER BY count DESC
        ''')
    else:
        cursor.execute('''
            SELECT path, COUNT(*) as count 
            FROM stats 
            WHERE user_id = %s
            GROUP BY path 
            ORDER BY count DESC
        ''', (current_user.id,))
        
    stats = cursor.fetchall()

    csv_data = "Page,Number of visits\n"
    for stat in stats:
        csv_data += f"{stat.path},{stat.count}\n"

    f = io.BytesIO()
    f.write(csv_data.encode('utf-8'))
    f.seek(0)
    return send_file(f, as_attachment=True, download_name='stats_by_routes.csv')

@stats_bp.route('/export_csv_by_users')
@login_required
def export_csv_by_users():
    if not current_user.is_admin():
        flash('Недостаточно прав доступа', 'danger')
        return redirect(url_for('index'))
    
    cursor = mysql.connection().cursor(named_tuple=True)
    cursor.execute('''
        SELECT users.id as user_id, CONCAT(users.first_name, ' ', users.middle_name, ' ', users.last_name) as full_name, COUNT(*) as count
        FROM stats
        LEFT JOIN users ON stats.user_id = users.id
        GROUP BY users.id, full_name 
        ORDER BY count DESC
    ''')
        
    stats = cursor.fetchall()

    csv_data = "User,Number of visits\n"
    for stat in stats:
        user_name = stat.full_name if stat.user_id else "Неаутентифицированный пользователь"
        csv_data += f"{user_name},{stat.count}\n"

    f = io.BytesIO()
    f.write(csv_data.encode('utf-8'))
    f.seek(0)
    return send_file(f, as_attachment=True, download_name='stats_by_users.csv')

@stats_bp.route('/by_routes')
@login_required
def by_routes():
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * PER_PAGE
    cursor = mysql.connection().cursor(named_tuple=True)
    
    if current_user.is_admin():
        cursor.execute('''
            SELECT path, COUNT(*) as count 
            FROM stats 
            GROUP BY path
        ''')
    else:
        cursor.execute('''
            SELECT path, COUNT(*) as count 
            FROM stats 
            WHERE user_id = %s
            GROUP BY path
        ''', (current_user.id,))
    
    stats = cursor.fetchall()

    total_stats = len(stats)
    last_page = ceil(total_stats / PER_PAGE)

    if page == 1:
        offset = 0
    else:
        offset = max(0, (page - 1) * PER_PAGE)
        
    if current_user.is_admin():
        cursor.execute('''
            SELECT path, COUNT(*) as count 
            FROM stats 
            GROUP BY path
            LIMIT %s OFFSET %s
        ''', (PER_PAGE, offset))
    else:
        cursor.execute('''
            SELECT path, COUNT(*) as count 
            FROM stats 
            WHERE user_id = %s
            GROUP BY path
            LIMIT %s OFFSET %s
        ''', (current_user.id, PER_PAGE, offset))
    
    stats = cursor.fetchall()

    return render_template('stats/by_routes.html', stats=stats, page=page, last_page=last_page, per_page=PER_PAGE)

@stats_bp.route('/by_users')
@login_required
def by_users():
    if not current_user.is_admin():
        flash('Недостаточно прав доступа', 'danger')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * PER_PAGE
    cursor = mysql.connection().cursor(named_tuple=True)
    
    cursor.execute('''
        SELECT users.id as user_id, CONCAT(users.first_name, ' ', users.middle_name, ' ', users.last_name) as full_name, COUNT(*) as count
        FROM stats
        LEFT JOIN users ON stats.user_id = users.id
        GROUP BY users.id, full_name 
    ''')
    
    stats = cursor.fetchall()

    total_stats = len(stats)
    last_page = ceil(total_stats / PER_PAGE)

    if page == 1:
        offset = 0
    else:
        offset = max(0, (page - 1) * PER_PAGE)

    cursor.execute('''
        SELECT users.id as user_id, CONCAT(users.first_name, ' ', users.middle_name, ' ', users.last_name) as full_name, COUNT(*) as count
        FROM stats
        LEFT JOIN users ON stats.user_id = users.id
        GROUP BY users.id, full_name 
        LIMIT %s OFFSET %s
    ''', (PER_PAGE, offset))
    
    stats = cursor.fetchall()

    return render_template('stats/by_users.html', stats=stats, page=page, last_page=last_page, per_page=PER_PAGE)

