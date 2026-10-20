from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS
import hashlib
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login_and_fetch', methods=['POST'])
def login_and_fetch():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # ID группы по умолчанию (для расписания). Позже мы научимся выбирать её в приложении.
    group_id = '111-14' 
    
    # Получаем СЕГОДНЯШНЮЮ дату в формате ДД-ММ-ГГГГ (например, 20-10-2026)
    date_str = datetime.now().strftime("%d-%m-%Y")

    if not username or not password:
        return jsonify({"status": "error", "message": "Введите логин и пароль"}), 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.uc.osu.ru/"
    }

    # ==========================================
    # 1. ПОЛУЧЕНИЕ ОЦЕНОК (ВСЕХ ПРЕДМЕТОВ)
    # ==========================================
    grades_data = []
    average = 0.0
    
    try:
        hashed_pass = hashlib.sha1(password.encode('utf-8')).hexdigest()
        login_url = "https://journal.uc.osu.ru/region_pou_secured/region.cgi/login" 
        grades_url = "https://journal.uc.osu.ru/region_pou_secured/region.cgi/journal.och?page=18&marks=1"
        
        session = requests.Session()
        
        login_resp = session.post(login_url, data={"username": username, "userpass": hashed_pass, "enter": "Вход"}, headers=headers, timeout=10)
        
        if login_resp.status_code == 200:
            grades_resp = session.get(grades_url, headers=headers, timeout=10)
            grades_resp.encoding = 'cp1251' 
            
            soup = BeautifulSoup(grades_resp.text, "html.parser")
            table_container = soup.find("div", class_="tableContainer")
            
            if table_container:
                rows = table_container.find_all("tr")
                total_marks = []
                
                for row in rows:
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        subject = tds[0].get_text(strip=True)
                        marks_str = tds[1].get_text(strip=True)
                        
                        # Пропускаем заголовки и пустые строки
                        if subject == "Дисциплина" or not marks_str or subject == "":
                            continue
                            
                        # Собираем все цифры для среднего балла
                        marks = [int(m) for m in marks_str.split() if m.isdigit()]
                        if marks:
                            total_marks.extend(marks)
                            grades_data.append({
                                "subject": subject,
                                "date": "", # Дат в этой таблице нет
                                "grade": marks_str # Передаем как строку "5 4 5"
                            })
                            
                if total_marks:
                    average = round(sum(total_marks) / len(total_marks), 2)
    except Exception as e:
        print(f"Ошибка оценок: {e}")

    # Если логин не прошел, покажем ошибку
    if not grades_data:
        grades_data = [{"subject": "Ошибка входа или нет оценок", "date": "", "grade": "-"}]

    # ==========================================
    # 2. ПОЛУЧЕНИЕ РАСПИСАНИЯ (НА СЕГОДНЯ)
    # ==========================================
    schedule_data = []
    schedule_url = "https://www.uc.osu.ru/generate_data.php"
    payload_schedule = {"type": 1, "data": date_str, "id": group_id}

    try:
        response = requests.post(schedule_url, data=payload_schedule, headers=headers, timeout=5)
        response.encoding = 'utf-8' 
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="tabdata")
        
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                row_text = [cell.get_text(separator=" | ", strip=True) for cell in cells]
                # Пропускаем пустые строки
                if any(row_text):
                    schedule_data.append(row_text)
    except Exception as e:
        print(f"Ошибка расписания: {e}")
        schedule_data = [["1", "Сайт расписания недоступен", "", ""]]

    return jsonify({
        "status": "success",
        "grades": grades_data,
        "average": average,
        "schedule": schedule_data
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
