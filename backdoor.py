from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS
import hashlib
from datetime import datetime

# Используем curl_cffi вместо requests для обхода защиты
from curl_cffi import requests as curl_requests

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
    group_id = '111-14' 
    date_str = datetime.now().strftime("%d-%m-%Y")

    if not username or not password:
        return jsonify({"status": "error", "message": "Введите логин и пароль"}), 400

    grades_data = []
    average = 0.0
    
    try:
        hashed_pass = hashlib.sha1(password.encode('utf-8')).hexdigest()
        login_url = "https://journal.uc.osu.ru/region_pou_secured/region.ogi/login" 
        grades_url = "https://journal.uc.osu.ru/region_pou_secured/region.cgi/journal.och?page=18&marks=1"
        
        # ВАЖНО: impersonate="chrome" копирует отпечаток Chrome
        session = curl_requests.Session(impersonate="chrome")
        
        print("[*] Прогрев сессии (получение куки)...")
        session.get("https://journal.uc.osu.ru/", timeout=10)
        
        print(f"[*] Попытка входа для {username}...")
        
        # Логинимся
        login_resp = session.post(
            login_url, 
            data={"username": username, "userpass": hashed_pass, "enter": "Вход"}, 
            timeout=15
        )
        
        print(f"[*] Статус входа: {login_resp.status_code}")
        
        if login_resp.status_code == 200:
            print("[*] Вход успешен, скачиваем оценки...")
            grades_resp = session.get(grades_url, timeout=15)
            grades_resp.encoding = 'cp1251' 
            
            soup = BeautifulSoup(grades_resp.text, "html.parser")
            table_container = soup.find("div", class_="tableContainer")
            
            if table_container:
                print("[*] Таблица оценок найдена!")
                rows = table_container.find_all("tr")
                total_marks = []
                
                for row in rows:
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        subject = tds[0].get_text(strip=True)
                        marks_str = tds[1].get_text(strip=True)
                        
                        if subject == "Дисциплина" or not marks_str or subject == "":
                            continue
                            
                        marks = [int(m) for m in marks_str.split() if m.isdigit()]
                        if marks:
                            total_marks.extend(marks)
                            grades_data.append({"subject": subject, "date": "", "grade": marks_str})
                            
                if total_marks:
                    average = round(sum(total_marks) / len(total_marks), 2)
            else:
                print("[!] Таблица tableContainer НЕ найдена.")
        else:
            print(f"[!] Ошибка входа. Сервер вернул статус: {login_resp.status_code}")
            print(f"Ответ сервера: {login_resp.text[:200]}")
            
    except Exception as e:
        print(f"❌ Ошибка оценок: {e}")

    if not grades_data:
        grades_data = [{"subject": "Ошибка входа", "date": "Проверьте логи", "grade": "-"}]

    # РАСПИСАНИЕ (тоже через curl_cffi)
    schedule_data = []
    schedule_url = "https://www.uc.osu.ru/generate_data.php"
    payload_schedule = {"type": 1, "data": date_str, "id": group_id}

    try:
        sched_session = curl_requests.Session(impersonate="chrome")
        response = sched_session.post(schedule_url, data=payload_schedule, timeout=10)
        response.encoding = 'utf-8' 
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="tabdata")
        
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                row_text = [cell.get_text(separator=" | ", strip=True) for cell in cells]
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
