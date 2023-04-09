from flask import Flask, render_template, redirect, Markup
import util
import time

app = Flask(__name__, static_folder='/')

times: list[util.SubscribeTime] = []
spans: list[util.SubscribeTimeSpan] = []


@app.route('/')
def index_page():
    return redirect('/times')


@app.route('/times')
def times_page():
    global times
    return render_template('times.html', times=enumerate(times))


@app.route('/spans/<id>')
def spans_page(id):
    global times
    global spans
    spans = times[int(id)].fetch_spans()
    return render_template('spans.html', spans=enumerate(spans))


@app.route('/go/<id>')
def go_page(id):
    global spans
    for i in range(500):
        json = spans[int(id)].make_request()
        if json['info']['ret_info'] == '锁号成功':
            return 'OK!'
        print(json)
    return '失败'
    # return render_template('go.html', data=spans[int(id)].data, cookie=f"ASP.NET_SessionId={util.COOKIE['ASP.NET_SessionId']}")


if __name__ == '__main__':
    times = util.TEST4_DOCTOR.fetch_times()
    app.run(debug=True)
