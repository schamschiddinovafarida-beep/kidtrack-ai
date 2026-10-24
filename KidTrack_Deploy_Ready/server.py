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
