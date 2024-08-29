from flask import Flask, request, jsonify, send_file,  render_template
from datetime import datetime, timedelta
from collections import OrderedDict
from collections import defaultdict
import json
import os
import uuid

app = Flask(__name__)


responses = defaultdict(lambda: defaultdict(list))

def calculate_hours(date, start_time, end_time, lunch_start, lunch_end, dinner_start, dinner_end):
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    start = datetime.combine(date_obj, datetime.strptime(start_time, '%H:%M').time())
    end = datetime.combine(date_obj, datetime.strptime(end_time, '%H:%M').time())
    lunch_start = datetime.combine(date_obj, datetime.strptime(lunch_start, '%H:%M').time())
    lunch_end = datetime.combine(date_obj, datetime.strptime(lunch_end, '%H:%M').time())
    dinner_start = datetime.combine(date_obj, datetime.strptime(dinner_start, '%H:%M').time())
    dinner_end = datetime.combine(date_obj, datetime.strptime(dinner_end, '%H:%M').time())

    print("start", start, "end", end)

    if end < start:
        return {
            'morning_hours': 0,
            'evening_hours': 0,
            'lunch_duration': 0,
            'dinner_duration': 0
        }

    morning_hours = 0
    evening_hours = 0
    lunch_duration = 0
    dinner_duration = 0

    # 計算午休時間
    if lunch_start < end and lunch_end > start:
        lunch_start_within_work = max(lunch_start, start)
        lunch_end_within_work = min(lunch_end, end)
        lunch_duration = (lunch_end_within_work - lunch_start_within_work).total_seconds() / 3600

    # 計算晚餐時間
    if dinner_start < end and dinner_end > start:
        dinner_start_within_work = max(dinner_start, start)
        dinner_end_within_work = min(dinner_end, end)
        dinner_duration = (dinner_end_within_work - dinner_start_within_work).total_seconds() / 3600

    # 計算早班和晚班時間
    if start < dinner_start:
        morning_hours = (min(end, dinner_start) - start - timedelta(hours=lunch_duration)).total_seconds() / 3600
    if end > dinner_end:
        evening_hours = (end - max(start, dinner_end)).total_seconds() / 3600

    return {
        'morning_hours': max(morning_hours, 0),
        'evening_hours': max(evening_hours, 0),
        'lunch_duration': lunch_duration,
        'dinner_duration': dinner_duration
    }

def calculate_salary(morning_hours, evening_hours, morning_rate, evening_rate):
    morning_salary = morning_hours * morning_rate
    evening_salary = evening_hours * evening_rate
    return morning_salary + evening_salary

def load_data():
    # Load data from JSON file
    try:
        with open('static/data.json', 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
def initialize_responses():
    # Load initial data from static/data.json
    initial_data = load_data()
    global responses
    responses = defaultdict(lambda: defaultdict(list), initial_data)

# 假設 company_info.json 存儲公司資訊
with open('static/company_info.json', 'r') as f:
    company_info = json.load(f)


@app.route('/api/companies', methods=['GET'])
def get_companies():
    # 返回所有公司的名稱和對應的公司資訊
    return jsonify(company_info)

@app.route('/calculate_hours', methods=['POST'])
def get_hours():
    data = request.json
    company = data.get('company')
    date = data.get('date')
    start_time = data.get('start_datetime')
    end_time = data.get('end_datetime')

    print("start_time", start_time, "end_time", end_time)

    if not (company and date and start_time and end_time):
        return jsonify({'error': 'All required fields are not provided'}), 400

    # 從 company_info 中獲取公司資訊
    company_data = company_info.get(company)
    if not company_data:
        return jsonify({'error': 'Invalid company'}), 400

    lunch_start = company_data.get('lunch_start')
    lunch_end = company_data.get('lunch_end')
    dinner_start = company_data.get('dinner_start')
    dinner_end = company_data.get('dinner_end')
    morning_rate = company_data.get('morning_rate')
    evening_rate = company_data.get('evening_rate')

    try:
        result = calculate_hours(date, start_time, end_time, lunch_start, lunch_end, dinner_start, dinner_end)
        morning_hours = result['morning_hours']
        evening_hours = result['evening_hours']
        total_salary = calculate_salary(morning_hours, evening_hours, morning_rate, evening_rate)

        response = {
            'id': str(uuid.uuid4()),
            'morning_hours': morning_hours,
            'evening_hours': evening_hours,
            'lunch_duration': result['lunch_duration'],
            'dinner_duration': result['dinner_duration'],
            'total_salary': total_salary
        }

        # 假設 responses 是一個全域變數，這裡會更新對應公司的數據
        if company not in responses:
            responses[company] = {}
        if date not in responses[company]:
            responses[company][date] = []
        responses[company][date].append(response)
        print(dict(responses[company]))

        return jsonify({company: response})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
# @app.route('/calculate_hours', methods=['POST'])
# def get_hours():
#     data = request.json
#     company = data.get('company')
#     date = data.get('date')
#     start_time = data.get('start_datetime')
#     end_time = data.get('end_datetime')
#     lunch_start = data.get('lunch_start')
#     lunch_end = data.get('lunch_end')
#     dinner_start = data.get('dinner_start')
#     dinner_end = data.get('dinner_end')
#     morning_rate = data.get('morning_rate')
#     evening_rate = data.get('evening_rate')

#     if not (company and date and start_time and end_time and lunch_start and lunch_end and dinner_start and dinner_end and morning_rate and evening_rate):
#         return jsonify({'error': 'All required fields are not provided'}), 400

#     try:
#         result = calculate_hours(date, start_time, end_time, lunch_start, lunch_end, dinner_start, dinner_end)
#         morning_hours = result['morning_hours']
#         evening_hours = result['evening_hours']
#         total_salary = calculate_salary(morning_hours, evening_hours, morning_rate, evening_rate)

#         response = {
#             # 'date': date,
#             'id': str(uuid.uuid4()), 
#             'morning_hours': morning_hours,
#             'evening_hours': evening_hours,
#             'lunch_duration': result['lunch_duration'],
#             'dinner_duration': result['dinner_duration'],
#             'total_salary': total_salary
#         }

#         responses[company][date].append(response)

#         return jsonify({company: dict(responses[company])})
#     except ValueError as e:
#         return jsonify({'error': str(e)}), 400
@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(responses)

@app.route('/remove/<id>', methods=['DELETE'])
def remove_data(id):
    try:
        # 遍歷所有的公司和日期
        for company, dates in responses.items():
            for date, records in dates.items():
                # 找到該日期下對應的所有記錄
                for i, record in enumerate(records):
                    if record['id'] == id:
                        # 刪除該記錄
                        removed_data = records.pop(i)
                        return jsonify({'message': 'Data removed successfully', 'removed_data': removed_data})

        # 如果未找到對應的ID
        return jsonify({'error': 'ID not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@app.route('/save', methods=['POST'])
def save_data():
    try:
        filename = 'static/data.json'
        with open(filename, 'w') as f:
            json.dump(responses, f, indent=4)
        return jsonify({'message': 'Data saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export', methods=['GET'])
def export_data():
    try:
        filename = 'static/data.json'
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/', methods=['GET'])
def calendar():
    # data = load_data()
    return render_template('calendar.html', data=json.dumps(responses))

def calculate_totals():
    # Initialize weekly and monthly totals for both company-specific and overall totals
    weekly_totals = {f'week_{i}': {'total_salary': 0, 'total_hours': 0} for i in range(1, 6)}
    company_weekly_totals = {}
    monthly_totals = {'total_salary': 0, 'total_hours': 0}

    data = load_data()

    for company, records in data.items():
        # Initialize weekly totals for the company
        company_weekly_totals[company] = {f'week_{i}': {'total_salary': 0, 'total_hours': 0} for i in range(1, 6)}
        company_monthly_salary = 0
        company_monthly_hours = 0

        for date, entries in records.items():
            daily_salary = sum(entry['total_salary'] for entry in entries)
            daily_hours = sum(entry['morning_hours'] + entry['evening_hours'] for entry in entries)

            # Calculate monthly totals for the company
            company_monthly_salary += daily_salary
            company_monthly_hours += daily_hours

            # Calculate weekly totals for the company
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            week_number = (date_obj.day - 1) // 7 + 1  # Simplified week calculation
            week_key = f'week_{week_number}'

            if week_key in company_weekly_totals[company]:
                company_weekly_totals[company][week_key]['total_salary'] += daily_salary
                company_weekly_totals[company][week_key]['total_hours'] += daily_hours

        # Update the overall weekly totals
        for week_key, totals in company_weekly_totals[company].items():
            weekly_totals[week_key]['total_salary'] += totals['total_salary']
            weekly_totals[week_key]['total_hours'] += totals['total_hours']

        # Store company-specific totals
        company_weekly_totals[company]['monthly_totals'] = {
            'total_salary': company_monthly_salary,
            'total_hours': company_monthly_hours
        }

        # Update overall monthly totals
        monthly_totals['total_salary'] += company_monthly_salary
        monthly_totals['total_hours'] += company_monthly_hours

    return company_weekly_totals, weekly_totals, monthly_totals

@app.route('/api/company_weekly_totals', methods=['GET'])
def get_company_weekly_totals():
    company_weekly_totals, _, _ = calculate_totals()
    return jsonify(company_weekly_totals)

@app.route('/api/overall_weekly_totals', methods=['GET'])
def get_overall_weekly_totals():
    _, weekly_totals, _ = calculate_totals()
    return jsonify(weekly_totals)

@app.route('/api/monthly_totals', methods=['GET'])
def get_monthly_totals():
    _, _, monthly_totals = calculate_totals()
    return jsonify(monthly_totals)

@app.route('/api/get_res', methods=['GET'])
def get_res():
    return jsonify(responses)
    
if __name__ == '__main__':
    initialize_responses()
    app.run(debug=True)