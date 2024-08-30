from flask import Flask, request, jsonify, send_file,  render_template, redirect, url_for, abort
from datetime import datetime, timedelta
from collections import OrderedDict
from collections import defaultdict
import json
import os
import uuid

app = Flask(__name__)


responses = defaultdict(lambda: defaultdict(list))
company_info_path = 'static/company_info.json'
company_info ={}
# 假設 company_info.json 存儲公司資訊
def load_company_info():
    if os.path.exists(company_info_path):
        with open(company_info_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {}

def save_company_info(company_info):
    with open(company_info_path, 'w', encoding='utf-8') as f:
        json.dump(company_info, f, ensure_ascii=False, indent=4)


def calculate_hours(date, start_time, end_time, lunch_start=None, lunch_end=None, dinner_start=None, dinner_end=None, evening_shift_start=None, has_evening_shift=False, deduct_lunch_time=False, deduct_dinner_time=False):
    # Convert date and times to datetime objects
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    start = datetime.combine(date_obj, datetime.strptime(start_time, '%H:%M').time())
    end = datetime.combine(date_obj, datetime.strptime(end_time, '%H:%M').time())
    
    # Initialize durations
    morning_hours = 0
    evening_hours = 0
    lunch_duration = 0
    dinner_duration = 0

    # Check for invalid cases
    if end < start:
        return {
            'morning_hours': 0,
            'evening_hours': 0,
            'lunch_duration': 0,
            'dinner_duration': 0
        }

    # Handle optional lunch times
    if lunch_start and lunch_end and deduct_lunch_time:
        lunch_start = datetime.combine(date_obj, datetime.strptime(lunch_start, '%H:%M').time())
        lunch_end = datetime.combine(date_obj, datetime.strptime(lunch_end, '%H:%M').time())
        if lunch_start < end and lunch_end > start:
            lunch_start_within_work = max(lunch_start, start)
            lunch_end_within_work = min(lunch_end, end)
            if lunch_end_within_work > lunch_start_within_work:
                lunch_duration = (lunch_end_within_work - lunch_start_within_work).total_seconds() / 3600

    # Handle optional dinner times
    if dinner_start and dinner_end and deduct_dinner_time:
        dinner_start = datetime.combine(date_obj, datetime.strptime(dinner_start, '%H:%M').time())
        dinner_end = datetime.combine(date_obj, datetime.strptime(dinner_end, '%H:%M').time())
        if dinner_start < end and dinner_end > start:
            dinner_start_within_work = max(dinner_start, start)
            dinner_end_within_work = min(dinner_end, end)
            if dinner_end_within_work > dinner_start_within_work:
                dinner_duration = (dinner_end_within_work - dinner_start_within_work).total_seconds() / 3600

    # Calculate morning and evening hours
    if evening_shift_start:
        evening_shift_start = datetime.combine(date_obj, datetime.strptime(evening_shift_start, '%H:%M').time())
        if start < evening_shift_start:
            # Calculate morning hours up to the evening shift start
            morning_end = min(end, evening_shift_start)
            morning_hours = (morning_end - start - timedelta(hours=lunch_duration)).total_seconds() / 3600

        if has_evening_shift and end > evening_shift_start:
            # Calculate evening hours from the evening shift start
            evening_start = max(start, evening_shift_start)
            evening_hours = (end - evening_start - timedelta(hours=dinner_duration)).total_seconds() / 3600
    else:
        # If no evening shift is defined, calculate the full duration as morning hours
        morning_hours = (end - start - timedelta(hours=lunch_duration)).total_seconds() / 3600

    return {
        'morning_hours': max(morning_hours, 0),
        'evening_hours': max(evening_hours, 0),
        'lunch_duration': lunch_duration,
        'dinner_duration': dinner_duration
    }

def calculate_salary(morning_hours, evening_hours, morning_rate, evening_rate):
    morning_hours = float(morning_hours)
    evening_hours = float(evening_hours)
    morning_rate = float(morning_rate)
    evening_rate = float(evening_rate)

    morning_salary = morning_hours * morning_rate
    evening_salary = evening_hours * evening_rate
    return morning_salary + evening_salary
    # return morning_salary + evening_salary


def load_data():
    # Load data from JSON file
    try:
        with open('static/data.json', 'r', encoding='utf-8') as f:
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




@app.route('/api/companies', methods=['GET'])
def get_companies():
    # 返回所有公司的名稱和對應的公司資訊
    return jsonify(load_company_info())


@app.route('/calculate_hours', methods=['POST'])
def get_hours():
    data = request.json
    company = data.get('company')
    date = data.get('date')
    start_time = data.get('start_datetime')
    end_time = data.get('end_datetime')
    company_info = load_company_info()

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

    evening_shift_start = company_data.get('evening_shift_start')
    has_evening_shift = company_data.get('has_evening_shift')
    deduct_lunch_time = company_data.get('deduct_lunch_time')
    deduct_dinner_time = company_data.get('deduct_dinner_time')
    # evening_rate = company_data.get('evening_rate')

    try:
        # date, start_time, end_time, lunch_start, lunch_end, dinner_start, dinner_end, evening_shift_start, has_evening_shift, deduct_lunch_time, deduct_dinner_time
        result = calculate_hours(
            date, start_time, end_time, lunch_start, lunch_end, dinner_start, dinner_end, evening_shift_start, has_evening_shift, deduct_lunch_time, deduct_dinner_time)
        morning_hours = result['morning_hours']
        evening_hours = result['evening_hours']
        total_salary = calculate_salary(
            morning_hours, evening_hours, morning_rate, evening_rate)

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


@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(responses)


@app.route('/reset_res', methods=['GET'])
def reset_res_data():
    # Perform any necessary data reset operations here
    global responses
    responses = {}  # Return an empty object to indicate success
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
        with open(filename, 'w', encoding='utf-8') as f:
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


@app.route('/import', methods=['POST'])
def import_data():
    global responses
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        try:
            data = json.load(file)
            responses = data  # Update the global responses with imported data
            return jsonify({'message': 'Data imported successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/', methods=['GET'])
def calendar():
    # data = load_data()
    return render_template('calendar.html', data=json.dumps(responses))


def calculate_totals(selected_month):
    # Initialize weekly and monthly totals for both company-specific and overall totals
    weekly_totals = {f'{i}': {'total_salary': 0, 'total_hours': 0}
                     for i in range(1, 6)}
    company_weekly_totals = {}
    monthly_totals = {'total_salary': 0, 'total_hours': 0}

    data = responses

    for company, records in data.items():
        # Initialize weekly totals for the company
        company_weekly_totals[company] = {
            f'{i}': {'total_salary': 0, 'total_hours': 0} for i in range(1, 6)}
        company_monthly_salary = 0
        company_monthly_hours = 0

        for date, entries in records.items():
            date_obj = datetime.strptime(date, '%Y-%m-%d')

            # Check if the date belongs to the selected month
            if date_obj.strftime('%Y-%m') == selected_month:
                daily_salary = sum(entry['total_salary'] for entry in entries)
                daily_hours = sum(
                    entry['morning_hours'] + entry['evening_hours'] for entry in entries)

                # Calculate monthly totals for the company
                company_monthly_salary += daily_salary
                company_monthly_hours += daily_hours

                # Calculate weekly totals for the company
                week_number = (date_obj.day - 1) // 7 + \
                    1  # Simplified week calculation
                week_key = f'{week_number}'

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
    selected_month = request.args.get('month')  # 從查詢參數獲取月份
    company_weekly_totals, _, _ = calculate_totals(selected_month)
    return jsonify(company_weekly_totals)


@app.route('/api/overall_weekly_totals', methods=['GET'])
def get_overall_weekly_totals():
    selected_month = request.args.get('month')  # 從查詢參數獲取月份
    _, weekly_totals, _ = calculate_totals(selected_month)
    return jsonify(weekly_totals)


@app.route('/api/monthly_totals', methods=['GET'])
def get_monthly_totals():
    selected_month = request.args.get('month')  # 從查詢參數獲取月份
    _, _, monthly_totals = calculate_totals(selected_month)
    return jsonify(monthly_totals)


@app.route('/api/get_res', methods=['GET'])
def get_res():
    return jsonify(responses)


@app.route('/company_list')
def company_list():
    company_info = load_company_info()
    return render_template('company_list.html', company_info=company_info)

@app.route('/company_add', methods=['GET', 'POST'])
def company_add():
    company_info = load_company_info()
    
    if request.method == 'POST':
        if 'add_company' in request.form:
            new_company_name = request.form.get('name')
            if new_company_name not in company_info:
                company_data = {
                    'lunch_start': request.form.get('lunch_start') or None,
                    'lunch_end': request.form.get('lunch_end') or None,
                    'dinner_start': request.form.get('dinner_start') or None,
                    'dinner_end': request.form.get('dinner_end') or None,
                    'evening_shift_start': request.form.get('evening_shift_start') or None,
                    'has_evening_shift': 'on' in request.form,
                    'morning_rate': float(request.form.get('morning_rate') or 0),
                    'evening_rate': float(request.form.get('evening_rate') or 0),
                    'deduct_lunch_time': 'on' in request.form,
                    'deduct_dinner_time': 'on' in request.form
                }
                company_info[new_company_name] = company_data
                save_company_info(company_info)
            return redirect(url_for('company_list'))

    return render_template('company_add.html')

@app.route('/company_edit/<company_name>', methods=['GET', 'POST'])
def company_edit(company_name):
    company_info = load_company_info()
    company = company_info.get(company_name, {})
    
    if request.method == 'POST':
        if 'edit_company' in request.form:
            if company_name in company_info:
                company_info[company_name] = {
                    'lunch_start': request.form.get('lunch_start') or None,
                    'lunch_end': request.form.get('lunch_end') or None,
                    'dinner_start': request.form.get('dinner_start') or None,
                    'dinner_end': request.form.get('dinner_end') or None,
                    'evening_shift_start': request.form.get('evening_shift_start') or None,
                    'has_evening_shift': 'has_evening_shift' in request.form,  # Checkbox handling
                    'morning_rate': float(request.form.get('morning_rate') or 0),
                    'evening_rate': float(request.form.get('evening_rate') or 0),
                    'deduct_lunch_time': 'deduct_lunch_time' in request.form,  # Checkbox handling
                    'deduct_dinner_time': 'deduct_dinner_time' in request.form  # Checkbox handling
                }
                print(company_info)
                save_company_info(company_info)
            return redirect(url_for('company_list'))
        
        elif 'delete_company' in request.form:
            if company_name in company_info:
                del company_info[company_name]
                save_company_info(company_info)
            return redirect(url_for('company_list'))

    return render_template('company_edit.html', company=company, company_name=company_name)


if __name__ == '__main__':
    initialize_responses()
    app.run(debug=True)
