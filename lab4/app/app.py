from flask import Flask, render_template, redirect, url_for, request, make_response, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from mysql_db import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

login_manager = LoginManager()

app = Flask(__name__)

app.config.from_pyfile('config.py')

mysql = MySQL(app)

login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Доступ к данной странице есть только у авторизованных пользователей'
login_manager.login_message_category = 'warning'


class User(UserMixin):
    def __init__(self, user_id, login):
        self.id = user_id
        self.login = login


@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection().cursor(named_tuple=True)
    cursor.execute('SELECT * FROM users WHERE id=%s', (user_id,))
    user = cursor.fetchone()
    if user:
        return User(user_id=user.id, login=user.login)
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/users/')
@login_required
def users():
    cursor = mysql.connection().cursor()
    cursor.execute('SELECT id, login, first_name, last_name FROM users')
    users = cursor.fetchall()
    return render_template('users/index.html', users=users)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        login = request.form.get('login')
        password = request.form.get('password')
        remember = request.form.get('remember')
        if login and password:
            cursor = mysql.connection().cursor(named_tuple=True)
            cursor.execute('SELECT * FROM users WHERE login=%s', (login,))
            user = cursor.fetchone()
            if user and check_password_hash(user.password_hash, password):
                login_user(User(user_id=user.id, login=user.login), remember=remember)
                flash('Вы успешно прошли аутентификацию', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
        flash('Неверные логин или пароль', 'danger')
    return render_template('login.html')


@app.route('/users/register', methods=['GET', 'POST'])
# @login_required
def register():
    if request.method == "POST":
        login = request.form.get('loginInput')
        password = request.form.get('passwordInput')
        first_name = request.form.get('firstNameInput')
        last_name = request.form.get('lastNameInput')
        middle_name = request.form.get('middleNameInput')

        if len(login) < 6:
            flash('Логин должен содержать минимум 6 символов', 'danger')
            return redirect(request.url)
        
        # Проверка длины пароля
        if len(password) < 8:
            flash('Пароль должен содержать минимум 8 символов', 'danger')
            return redirect(request.url)
        
        if len(password) > 128:
            flash('Пароль должен содержать не больше 128 символов', 'danger')
            return redirect(request.url)

        # Проверка наличия заглавной, строчной буквы и цифры в пароле
        has_upper = any(char.isupper() for char in password)
        has_lower = any(char.islower() for char in password)
        has_digit = any(char.isdigit() for char in password)
        if not (has_upper and has_lower and has_digit):
            flash('Пароль должен содержать как минимум одну заглавную и одну строчную букву, и одну цифру', 'danger')
            return redirect(request.url)

        # Проверка наличия недопустимых символов в пароле
        invalid_chars = set(password) - set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        if invalid_chars:
            flash('Пароль содержит недопустимые символы: {}'.format(', '.join(invalid_chars)), 'danger')
            return redirect(request.url)
        
        if not all([login, password, first_name, last_name]):
            flash('Все поля должны быть заполнены', 'danger')
            return redirect(request.url)
        password_hash = generate_password_hash(password)
        cursor = mysql.connection().cursor(named_tuple=True)
        query = """INSERT INTO users 
                   (login, password_hash, first_name, last_name, middle_name)
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (login, password_hash, first_name, last_name, middle_name))
        mysql.connection().commit()
        cursor.close()
        flash('Успешная регистрация', 'success')
        # return redirect(url_for('users'))
        cursor = mysql.connection().cursor(named_tuple=True)
        cursor.execute('SELECT * FROM users WHERE login=%s', (login,))
        user = cursor.fetchone()
        login_user(User(user_id=user.id, login=user.login), remember=False)
        flash('Вы успешно прошли аутентификацию', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))
    return render_template('users/register.html')


@app.route('/users/<int:user_id>')
@login_required
def view_user(user_id):
    cursor = mysql.connection().cursor(named_tuple=True)
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    if user:
        return render_template('users/view.html', user=user)
    else:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('index'))


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if request.method == 'POST':
        login = request.form.get('login')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        try:
            with mysql.connection().cursor(named_tuple=True) as cursor:
                cursor.execute('UPDATE users SET login = %s, first_name = %s, last_name = %s WHERE id = %s',
                               (login, first_name, last_name, user_id,))
                mysql.connection().commit()
                flash('Сведения о пользователе успешно сохранены', 'success')
                return redirect(url_for('view_user', user_id=user_id))
        except Exception as e:
            mysql.connection().rollback()
            flash('Ошибка', 'danger')
            return render_template('users/edit.html')
    else:
        cursor = mysql.connection().cursor(named_tuple=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        if user:
            return render_template('users/edit.html', user=user)
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('index'))


@app.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    cursor = mysql.connection().cursor(named_tuple=True)
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    mysql.connection().commit()
    flash('Пользователь успешно удалён', 'success')
    return redirect(url_for('users'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/users/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Проверка наличия значений в полях
        if not all([old_password, new_password, confirm_password]):
            flash('Все поля должны быть заполнены', 'danger')
            return redirect(request.url)

        # Проверка совпадения нового и подтвержденного паролей
        if new_password != confirm_password:
            flash('Новые пароли не совпадают', 'danger')
            return redirect(request.url)

        # Проверка длины нового пароля
        if len(new_password) < 8:
            flash('Новый пароль должен содержать минимум 8 символов', 'danger')
            return redirect(request.url)
        
        if len(new_password) > 128:
            flash('Новый пароль должен содержать не больше 128 символов', 'danger')
            return redirect(request.url)

        # Проверка наличия заглавной, строчной буквы и цифры в новом пароле
        has_upper = any(char.isupper() for char in new_password)
        has_lower = any(char.islower() for char in new_password)
        has_digit = any(char.isdigit() for char in new_password)
        if not (has_upper and has_lower and has_digit):
            flash('Новый пароль должен содержать как минимум одну заглавную и одну строчную букву, и одну цифру', 'danger')
            return redirect(request.url)

        # Проверка наличия недопустимых символов в новом пароле
        invalid_chars = set(new_password) - set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        if invalid_chars:
            flash('Новый пароль содержит недопустимые символы: {}'.format(', '.join(invalid_chars)), 'danger')
            return redirect(request.url)

        # Если все проверки пройдены, обновляем пароль в базе данных
        cursor = mysql.connection().cursor(named_tuple=True)
        cursor.execute('SELECT password_hash FROM users WHERE id = %s', (current_user.id,))
        user = cursor.fetchone()

        if not user or not check_password_hash(user.password_hash, old_password):
            flash('Неверный старый пароль', 'danger')
            return redirect(request.url)

        new_password_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (new_password_hash, current_user.id))
        mysql.connection().commit()

        flash('Пароль успешно изменён', 'success')
        return redirect(url_for('index'))

    return render_template('/users/change_password.html')

@app.context_processor
def inject_footer():
    return dict(footer_text='Жирнов Глеб Альбертович, 221-353')

if __name__ == '__main__':
    app.run(debug=True)
