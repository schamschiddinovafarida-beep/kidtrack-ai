import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024


@app.after_request
def secure_headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


SYSTEM = '''Ты KidTrack AI, дружелюбный помощник по организации учебы и отдыха школьников Кыргызстана. Отвечай на русском или кыргызском по языку запроса. Помогай составлять реалистичный план дня с перерывами, учебой, отдыхом и достаточным временем на сон. Не ставь диагнозов, не давай медицинских заключений. Не предлагай слежку, контроль или раскрытие местоположения ребенка. Не проси личные данные, имя, адрес, школу, координаты. Если данных не хватает, уточняй. Отвечай кратко, практично, без категоричных медицинских норм.'''


def ask_ai(messages):
    key = os.environ.get('KIDTRACK_API_KEY', '').strip()
    if not key:
        return None, 'AI не подключён: настройте KIDTRACK_API_KEY на сервере.'

    base = os.environ.get('KIDTRACK_API_URL', 'https://api.openai.com/v1/chat/completions').strip()
    model = os.environ.get('KIDTRACK_MODEL', 'gpt-4o-mini').strip()
    payload = json.dumps({
        'model': model,
        'messages': [{'role': 'system', 'content': SYSTEM}] + messages,
        'max_tokens': 650,
        'temperature': 0.5
    }, ensure_ascii=False).encode('utf-8')

    req = Request(
        base,
        data=payload,
        headers={
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/json'
        },
        method='POST'
    )

    try:
        with urlopen(req, timeout=60) as response:
            data = json.load(response)
        answer = data['choices'][0]['message']['content']
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError('Empty AI response')
        return answer, None
    except HTTPError as error:
        print('AI HTTP status:', error.code, flush=True)
        return None, 'Не удалось получить ответ AI. Проверьте настройки сервера.'
    except (URLError, KeyError, IndexError, TypeError, ValueError, TimeoutError) as error:
        print('AI request failed:', type(error).__name__, flush=True)
        return None, 'Не удалось получить ответ AI. Проверьте настройки сервера.'


@app.get('/')
def index():
    return send_from_directory('static', 'index.html')


@app.get('/api/status')
def status():
    return jsonify(ai_connected=bool(os.environ.get('KIDTRACK_API_KEY')))


@app.post('/api/chat')
def chat():
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify(error='Неверный формат запроса.'), 400
    prompt = body.get('message', '')
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 800:
        return jsonify(error='Введите вопрос до 800 символов.'), 400
    answer, error = ask_ai([{'role': 'user', 'content': prompt}])
    if error:
        return jsonify(error=error), 503
    return jsonify(answer=answer, mode='ai')


@app.post('/api/plan')
def plan():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(error='Неверный формат запроса.'), 400
    try:
        start = str(data.get('start', ''))
        end = str(data.get('end', ''))
        wake = str(data.get('wake', ''))
        datetime.strptime(start, '%H:%M')
        datetime.strptime(end, '%H:%M')
        datetime.strptime(wake, '%H:%M')
        tasks = str(data.get('tasks', ''))[:300]
    except (ValueError, TypeError):
        return jsonify(error='Проверьте время в расписании.'), 400

    prompt = (
        'Составь примерный план учебного дня в формате простого списка со временем. '
        f'Пробуждение {wake}; уроки {start}–{end}; '
        f'другие занятия: {tasks or "не указаны"}. '
        'Учти обед, отдых, домашнюю работу, свободное время и вечерний отдых. '
        'Если расписание нелогично, укажи это. Не делай медицинских выводов.'
    )
    answer, error = ask_ai([{'role': 'user', 'content': prompt}])
    if error:
        return jsonify(error=error), 503
    return jsonify(answer=answer, mode='ai')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
