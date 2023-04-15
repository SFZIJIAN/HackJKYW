import json
import threading

from flask import Flask, redirect, render_template, request, jsonify

import util

app = Flask(__name__, static_folder='/')

progress = 0.0
message = ''
success = False
TOTAL = 50

with open('doctors.json', 'r', encoding='utf-8') as f:
    items = json.loads(f.read())


def main():
    app.run(debug=True, host='0.0.0.0', port=80)


@app.route('/')
def index_page():
    return redirect('/doctors')


@app.route('/search')
def search_page():
    return render_template('search.html')


@app.route('/search_api')
def search_api():
    return jsonify(util.search_doctors(request.args['keyword']))


@app.route('/doctors')
def doctors_page():
    global items
    doctors = []
    for item in items:
        doctors.append(
            util.Doctor(
                item['hospital_id'],
                item['department_id'],
                item['doctor_id']
            )
        )
    return render_template('doctors.html', doctors=doctors)


@app.route('/doctor')
def doctor_page():
    doctor = util.Doctor(
        request.args['hospital_id'],
        request.args['department_id'],
        request.args['doctor_id']
    )

    return render_template('doctor.html', doctor=doctor)


@app.route('/time')
def time_page():
    time = util.SubscribeTime(
        request.args['docName'],
        request.args['dept'],
        request.args['title'],
        request.args['hospName'],
        request.args['scheDate'],
        request.args['weekDay'],
        request.args['outTime'],
        request.args['rated_num'],
        request.args['last_num'],
        request.args['reg_fee'],
        request.args['clinicFee'],
        request.args['schedule_num']
    )

    return render_template('time.html', time=time)


@app.route('/span')
def span_page():
    span = util.SubscribeTimeSpan(
        request.args['yysjd'],
        request.args['yysjd_num'],
        request.args['schedule_num']
    )

    def go():
        global success
        global progress
        progress = 0
        success = False
        global message

        for i in range(TOTAL):
            json = span.make_request()
            message = json['info']['ret_info']
            if json['info']['ret_info'] == '锁号成功':
                progress = 100.0
                success = True
                break
            progress = (i + 1) * 100 / TOTAL

    thread = threading.Thread(target=go)
    thread.start()

    return render_template('go.html')


@app.route('/progress')
def progress():
    return jsonify({'progress': progress, 'success': success, 'message': message})


if __name__ == '__main__':
    main()
