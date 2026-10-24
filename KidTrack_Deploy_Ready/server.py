import os, json, re
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

    base = os.environ.get('KIDTRACK_API_URL', 'https://api.openai.com/v1/chat/completions')
    model = os.environ.get('KIDTRACK_MODEL', 'gpt-4o-mini')

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
        with urlopen(req, timeout=22) as r:
            data = json.load(r)
        return data['choices'][0]['message']['content'], None

    except HTTPError as e:
        print('AI HTTP status:', e.code, flush=True)
        return None, 'Не удалось получить ответ AI. Проверьте настройки сервера.'

    except (URLError, KeyError, ValueError, TimeoutError) as e:
        print('AI request failed:', type(e).__name__, flush=True)
        return None, 'Не удалось получить ответ AI. Проверьте настройки сервера.'

def index(): return send_from_directory('static','index.html')

@app.get('/api/status')
def status(): return jsonify(ai_connected=bool(os.environ.get('KIDTRACK_API_KEY')))

@app.post('/api/chat')
def chat():
    body = request.get_json(silent=True) or {}
    prompt = body.get('message','')
    if not isinstance(prompt,str) or not 1 <= len(prompt.strip()) <= 800: return jsonify(error='Введите вопрос до 800 символов.'),400
    # No conversation storage; avoid sending profiles, coordinates or identifiers
    answer, err = ask_ai([{'role':'user','content':prompt}])
    return (jsonify(error=err),503) if err else jsonify(answer=answer,mode='ai')

@app.post('/api/plan')
def plan():
    d = request.get_json(silent=True) or {}
    try:
        start = str(d.get('start',''))
        end = str(d.get('end',''))
        datetime.strptime(start,'%H:%M'); datetime.strptime(end,'%H:%M')
        tasks = str(d.get('tasks',''))[:300]
        wake = str(d.get('wake',''))
        datetime.strptime(wake,'%H:%M')
    except (ValueError,TypeError): return jsonify(error='Проверьте время в расписании.'),400
    prompt = f'Составь примерный план учебного дня в формате простого списка со временем. Пробуждение {wake}; уроки {start}–{end}; другие занятия: {tasks or "не указаны"}. Учти обед, отдых, домашнюю работу, свободное время и вечерний отдых. Если расписание нелогично, укажи это. Не делай медицинских выводов.'
    answer,err = ask_ai([{'role':'user','content':prompt}])
    if err: return jsonify(error=err),503
    return jsonify(answer=answer,mode='ai')

if __name__ == '__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)
