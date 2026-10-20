from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://college-app-38q6.onrender.com/"}})
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login_and_fetch', methods=['POST'])
def login_and_fetch():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    group_id = data.get('group_id', '111-14') # ID группы по умолчанию
    date_str = "21-10-2026" # В реальном приложении дату лучше брать сегодняшнюю

    if not username or not password:
        return jsonify({"status": "error", "message": "Введите логин и пароль"}), 400

    # ==========================================
    # 1. ПОЛУЧЕНИЕ РАСПИСАНИЯ (РЕАЛЬНЫЙ ЗАПРОС)
    # ==========================================
    schedule_data = []
    schedule_url = "https://www.uc.osu.ru/generate_data.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.uc.osu.ru/"
    }
    payload_schedule = {"type": 1, "data": date_str, "id": group_id}

    try:
        # Пытаемся скачать реальное расписание
        response = requests.post(schedule_url, data=payload_schedule, headers=headers, timeout=5)
        response.encoding = 'utf-8' # В прошлый раз мы поняли, что тут utf-8
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="tabdata")
        
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                row_text = [cell.get_text(separator=" | ", strip=True) for cell in cells]
                if row_text:
                    schedule_data.append(row_text)
    except Exception as e:
        print(f"Сайт колледжа недоступен: {e}")
        # Если сайт упал, возвращаем фейковое расписание, чтобы интерфейс не был пустым
        schedule_data = [
            ["1", "Математика", "Иванов И.И.", "301"],
            ["2", "Физика", "Петров П.П.", "205"],
            ["3", "История", "Сидоров С.С.", "Актовый зал"]
        ]

    # ==========================================
    # 2. ПОЛУЧЕНИЕ ОЦЕНОК (ПОКА ФЕЙКОВОЕ)
    # ==========================================
    # Когда сайт разблокирует логин, мы вставим сюда реальный запрос из прошлых шагов.
    # А пока используем тестовые данные для демонстрации.
    grades_data = [
        {"subject": "Математика", "date": "19.10.2026", "grade": 5},
        {"subject": "Русский язык", "date": "20.10.2026", "grade": 4},
        {"subject": "Информатика", "date": "21.10.2026", "grade": 5},
        {"subject": "История", "date": "22.10.2026", "grade": 4}
    ]

    # Считаем средний балл
    if grades_data:
        total = sum(item['grade'] for item in grades_data)
        average = round(total / len(grades_data), 2)
    else:
        average = 0.0

    # Отдаем всё в браузер
    return jsonify({
        "status": "success",
        "grades": grades_data,
        "average": average,
        "schedule": schedule_data
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
