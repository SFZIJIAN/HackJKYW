import datetime
import json
import logging
import re
from collections import namedtuple

import requests
from lxml.etree import HTML, _Element
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

TIME_UPDATE_DURATION = 200
HOST = 'http://115.220.1.205:8014'
CRAWL = 'Crawl'
STOP = 'Stop'
APP_INFO = {
    'trans_no': 'SG0023',
    'member_num': '',
    'card_type': '2',    # 健康卡: 1    社保卡: 2
    'card_number': 'C09C46724',
    'qq_id': 1  # 我: None  你: 1   陈: 2)
}

Doctor = namedtuple('Doctor', [
    'hospital_id',
    'department_id',
    'doctor_id'
])
Time = namedtuple('Time', [
    'docName',
    'dept',
    'title',
    'hospName',
    'scheDate',
    'weekDay',
    'outTime',
    'rated_num',
    'last_num',
    'reg_fee',
    'clinicFee',
    'schedule_num'
])
Span = namedtuple('Span', [
    'hospName',
    'dept',
    'yysjd',
    'docName',
    'title',
    'last_num',
    'reg_fee',
    'clinicFee',
    'yysjd_num',
    'schedule_num'
])


class Window(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.init_ui()
        self.setWindowTitle('Hack JKYW')
        self.resize(800, 600)

        self.date_timer = QTimer(self)
        self.date_timer.timeout.connect(self.display_time)
        self.date_timer.start(TIME_UPDATE_DURATION)

        self.grab_timer = QTimer(self)
        self.grab_timer.timeout.connect(self.grab)

        self.init_network()
        with open('doctors.json', 'r', encoding='utf-8') as f:
            self.doctors = \
                [Doctor(**doctor) for doctor in json.loads(f.read())]

        self.doctor_combo.addItems(map(self.get_doctor_name, self.doctors))

    def crawl_times(self, doctor: Doctor) -> list[Time]:
        def fetch():
            res = self.session.get(
                HOST + '/MakeApp/DoctorDetail',
                data=doctor._asdict()
            )
            assert res.status_code == 200
            return HTML(res.text)

        def parse(s):
            """
            turnPage('http://115.233.252.63:7070/AttachmentPath/Docs/689145490010071_M.jpg','/MakeApp/TimeList?docName=杨玉梅&dept=甲状腺内科门诊&title=副主任医师&hospName=浙江大学医学院附属第四医院&scheDate=2023-04-15&weekDay=星期六&outTime=上午&rated_num=15&last_num=1&reg_fee=0&clinicFee=80&schedule_num=6891454900230415560730')
            """
            s = str(s)
            match = re.search(
                r"'/MakeApp/TimeList\?docName=(.*?)&dept=(.*?)&title=(.*?)&hospName=(.*?)&scheDate=(.*?)&weekDay=(.*?)&outTime=(.*?)&rated_num=(.*?)&last_num=(.*?)&reg_fee=(.*?)&clinicFee=(.*?)&schedule_num=(.*?)'\)",
                s
            )

            return Time(*match.groups())

        return list(map(parse, fetch().xpath('/html/body/section/div[3]/table/tbody/tr/td/a/@onclick')))

    def crawl_spans(self, time: Time) -> list[Span]:
        def fetch():
            res = self.session.get(
                HOST + '/MakeApp/TimeList',
                data=time._asdict()
            )
            assert res.status_code == 200
            return HTML(res.text)

        def parse(s):
            """
            window.location.href='/MakeApp/MakeAppTip?hospName=浙江大学医学院附属第四医院&dept=甲状腺内科门诊&yysjd=2023-04-15 11:03&docName=杨玉梅&title=副主任医师&last_num=1&reg_fee=0&clinicFee=80&yysjd_num=25&schedule_num=6891454900230415560730'
            """
            s = str(s)
            match = re.search(
                r"window.location.href='/MakeApp/MakeAppTip\?hospName=(.*?)&dept=(.*?)&yysjd=(.*?)&docName=(.*?)&title=(.*?)&last_num=(.*?)&reg_fee=(.*?)&clinicFee=(.*?)&yysjd_num=(.*?)&schedule_num=(.*?)'",
                s
            )

            return Span(*match.groups())

        return list(map(parse, fetch().xpath('/html/body/section/div[2]/ul/li/@onclick')))

    @Slot()
    def display_time(self) -> None:
        self.title_label.setText(
            f'<h1>{self.windowTitle()}</h1><p>{datetime.datetime.now()}</p>')

    @Slot()
    def fetch_time(self) -> None:
        index = self.doctor_combo.currentIndex()
        if index == -1:
            QMessageBox.critical('No doctor selected')
            return
        logging.debug(f'fetch time of {self.doctor_combo.currentText()}')
        doctor = self.doctors[index]

        self.times = self.crawl_times(doctor)
        self.time_combo.clear()
        self.span_combo.clear()
        if self.times:
            self.time_combo.addItems(
                [f'{time.scheDate} {time.outTime}' for time in self.times])
        else:
            QMessageBox.information(self, 'Info', 'No times available')

    @Slot()
    def fetch_span(self) -> None:
        index = self.time_combo.currentIndex()
        if index == -1:
            QMessageBox.critical(self, 'Error', 'No time selected')
            return
        logging.debug(f'fetch time of {self.time_combo.currentText()}')
        time = self.times[index]

        self.spans = self.crawl_spans(time)
        self.span_combo.clear()
        if self.spans:
            self.span_combo.addItems(
                [f'{span.yysjd}' for span in self.spans])
        else:
            QMessageBox.information(self, 'Info', 'No spans available')

    @Slot()
    def grab(self) -> None:
        res = self.session.post(
            HOST + '/MakeApp/checkMakeApp',
            data={**self.current_span._asdict(), **APP_INFO}
        )
        assert res.status_code == 200
        json = res.json()
        self.message = json['info']['ret_info']
        logging.info(self.message)
        self.message_label.setText(f'Message: {self.message}')
        if self.message == '锁号成功':
            self.crawl_button.click()
            QMessageBox.information(self, 'Info', 'Success!')

    @Slot()
    def crawl(self) -> None:
        text = self.crawl_button.text()

        if text == CRAWL:
            index = self.span_combo.currentIndex()
            if index == -1:
                QMessageBox.critical(self, 'Error', 'No span selected')
                return
            logging.debug('crawl')
            self.current_span = self.spans[index]
            self.grab_timer.start()

            self.doctor_combo.setDisabled(True)
            self.time_combo.setDisabled(True)
            self.span_combo.setDisabled(True)
            self.fetch_time_button.setDisabled(True)
            self.fetch_span_button.setDisabled(True)

            self.crawl_button.setText(STOP)
        elif text == STOP:
            logging.debug('stop')
            self.grab_timer.stop()
            self.current_span = None

            self.doctor_combo.setEnabled(True)
            self.time_combo.setEnabled(True)
            self.span_combo.setEnabled(True)
            self.fetch_time_button.setEnabled(True)
            self.fetch_span_button.setEnabled(True)

            self.crawl_button.setText(CRAWL)
        else:
            logging.error(f'Unknown text: {text}')

    def get_doctor_name(self, doctor: Doctor) -> str:
        def fetch():
            res = self.session.get(
                HOST + '/MakeApp/DoctorDetail',
                data=doctor._asdict()
            )
            assert res.status_code == 200
            return HTML(res.text)

        return fetch().xpath('/html/body/section/ul/li[1]/ul/li[1]/text()')[0].strip()

    def init_network(self) -> None:
        self.session = requests.session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.46'
        }
        assert self.session.post(
            HOST + '/Account/post_login',
            data={'name': '19527986531', 'pwd': '492548'},
        ).status_code == 200

        logging.debug(f'Cookie: {dict(self.session.cookies)}')

    def init_ui(self) -> None:
        self.title_label = QLabel(self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.message_label = QLabel('Message: ', self)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.crawl_button = QPushButton(CRAWL, self)

        self.doctor_combo = QComboBox(self)
        self.time_combo = QComboBox(self)
        self.span_combo = QComboBox(self)

        self.fetch_time_button = QPushButton('Fetch', self)
        self.fetch_span_button = QPushButton('Fetch', self)

        self.fetch_time_button.clicked.connect(self.fetch_time)
        self.fetch_span_button.clicked.connect(self.fetch_span)
        self.crawl_button.clicked.connect(self.crawl)

        self.init_layout()

    def init_layout(self) -> None:
        self.v = QVBoxLayout(self)

        self.doctor_layout = QVBoxLayout()
        self.time_layout = QHBoxLayout()
        self.span_layout = QHBoxLayout()
        self.crawl_layout = QVBoxLayout()

        self.doctor_group = QGroupBox('Select Doctor', self)
        self.time_group = QGroupBox('Select Time', self)
        self.span_group = QGroupBox('Select Span', self)
        self.crawl_group = QGroupBox('Crawl', self)

        self.doctor_group.setLayout(self.doctor_layout)
        self.time_group.setLayout(self.time_layout)
        self.span_group.setLayout(self.span_layout)
        self.crawl_group.setLayout(self.crawl_layout)

        self.v.addWidget(self.title_label)
        self.v.addWidget(self.doctor_group)
        self.v.addWidget(self.time_group)
        self.v.addWidget(self.span_group)
        self.v.addWidget(self.crawl_group)

        self.doctor_layout.addWidget(self.doctor_combo)
        self.time_layout.addWidget(self.time_combo)
        self.span_layout.addWidget(self.span_combo)
        self.crawl_layout.addWidget(self.message_label)
        self.crawl_layout.addWidget(self.crawl_button)

        self.time_layout.addWidget(self.fetch_time_button)
        self.span_layout.addWidget(self.fetch_span_button)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.session.close()
        return super().closeEvent(event)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s][%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    app = QApplication()
    app.setFont(QFont('Microsoft YaHei UI', 12))

    w = Window()
    w.show()

    app.exec()
