from flask import Flask, render_template, request, make_response 
import re

app = Flask(__name__)

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Страница с формой
@app.route('/form', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        pass
    return render_template('form.html')

# Страница с заголовками запроса
@app.route('/headers')
def headers():
    return render_template('headers.html')

# Страница с параметрами URL
@app.route('/args')
def args():
    # Искусственный вывод URL
    current_url = request.url

    return render_template('args.html', current_url=current_url)

# Страница с куки
@app.route('/cookie')
def cookie():
    resp = make_response(render_template('cookie.html'))
    if 'user' in request.cookies:
        resp.delete_cookie('user')
    else:
        resp.set_cookie('user','NoName')
    return resp

@app.context_processor
def inject_footer():
    return dict(footer_text='Жирнов Глеб Альбертович, 221-353')

@app.route('/phone_check', methods=['GET', 'POST'])
def phone_check():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number', '')
        
        # Удаление лишних символов
        phone_digits = re.sub(r'[\s()+.-]', '', phone_number)
        
        # Проверка длины номера
        if not (10 <= len(phone_digits) <= 11):
            error_message = "Недопустимый ввод. Неверное количество цифр."
            return render_template('phone_form.html', error_message=error_message, phone_number=phone_number, is_invalid=True)
        
        # Преобразование номера к формату 8-***-***-**-**
        formatted_phone_number = '8-' + phone_digits[-10:-7] + '-' + phone_digits[-7:-4] + '-' + phone_digits[-4:-2] + '-' + phone_digits[-2:]
        
        return render_template('phone_form.html', formatted_phone_number=formatted_phone_number)
    
    return render_template('phone_form.html')


if __name__ == '__main__':
    app.run(debug=True)
