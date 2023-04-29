import json
import re
import time

import requests
from lxml.etree import HTML
from requests.cookies import RequestsCookieJar


def get_cookie() -> RequestsCookieJar:
    with open('private.json', 'r', encoding='utf-8') as f:
        user = json.loads(f.read())
        account, password = user['account'], user['password']

    with requests.session() as session:
        res = session.post(
            HOST + '/Account/post_login',
            data={'name': account, 'pwd': password},
            headers=HEADER
        )
        return res.cookies


def update_cookie():
    global last_update_time
    global COOKIE

    now = time.time()
    if now - last_update_time > 60:
        COOKIE = get_cookie()
        last_update_time = now


HOST = 'http://115.220.1.205:8014'
HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.46'
}
COOKIE = None
APP_INFO = {
    'trans_no': 'SG0023',
    'member_num': '',
    'card_type': '2',    # 健康卡: 1    社保卡: 2
    'card_number': 'C09C46724',
    'qq_id': 1  # 我: None  你: 1   陈: 2)
}


class SubscribeTimeSpan:
    @staticmethod
    def parse(s):
        """
        window.location.href='/MakeApp/MakeAppTip?hospName=浙江大学医学院附属第四医院&dept=甲状腺内科门诊&yysjd=2023-04-15 11:03&docName=杨玉梅&title=副主任医师&last_num=1&reg_fee=0&clinicFee=80&yysjd_num=25&schedule_num=6891454900230415560730'
        """
        s = str(s)
        match = re.search(
            r"window.location.href='/MakeApp/MakeAppTip\?hospName=(.*?)&dept=(.*?)&yysjd=(.*?)&docName=(.*?)&title=(.*?)&last_num=(.*?)&reg_fee=(.*?)&clinicFee=(.*?)&yysjd_num=(.*?)&schedule_num=(.*?)'",
            s
        )

        return SubscribeTimeSpan(
            # 'hospName': match.group(1),
            # 'dept': match.group(2),
            match.group(3),
            # 'docName': match.group(4),
            # 'title': match.group(5),
            # 'last_num': match.group(6),
            # 'reg_fee': match.group(7),
            # 'clinicFee': match.group(8),
            match.group(9),
            match.group(10)
        )

    def __init__(self, yysjd: str, yysjd_num: str, schedule_num: str) -> None:
        self.data = {
            'yysjd': yysjd,
            'yysjd_num': yysjd_num,
            'schedule_num': schedule_num,
        }

    def make_request(self) -> dict:
        update_cookie()
        res = requests.post(
            HOST + '/MakeApp/checkMakeApp',
            data={**self.data, **APP_INFO}, headers=HEADER, cookies=COOKIE
        )
        return res.json()


class SubscribeTime:
    @staticmethod
    def parse(s: str) -> dict:
        """
        turnPage('http://115.233.252.63:7070/AttachmentPath/Docs/689145490010071_M.jpg','/MakeApp/TimeList?docName=杨玉梅&dept=甲状腺内科门诊&title=副主任医师&hospName=浙江大学医学院附属第四医院&scheDate=2023-04-15&weekDay=星期六&outTime=上午&rated_num=15&last_num=1&reg_fee=0&clinicFee=80&schedule_num=6891454900230415560730')
        """
        s = str(s)
        match = re.search(
            r"'/MakeApp/TimeList\?docName=(.*?)&dept=(.*?)&title=(.*?)&hospName=(.*?)&scheDate=(.*?)&weekDay=(.*?)&outTime=(.*?)&rated_num=(.*?)&last_num=(.*?)&reg_fee=(.*?)&clinicFee=(.*?)&schedule_num=(.*?)'\)",
            s
        )

        return SubscribeTime(
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4),
            match.group(5),
            match.group(6),
            match.group(7),
            match.group(8),
            match.group(9),
            match.group(10),
            match.group(11),
            match.group(12)
        )

    def __init__(self,
                 docName: str,
                 dept: str,
                 title: str,
                 hospName: str,
                 scheDate: str,
                 weekDay: str,
                 outTime: str,
                 rated_num: str,
                 last_num: str,
                 reg_fee: str,
                 clinicFee: str,
                 schedule_num: str
                 ) -> None:
        self.data = {
            "docName": docName,
            "dept": dept,
            "title": title,
            "hospName": hospName,
            "scheDate": scheDate,
            "weekDay": weekDay,
            "outTime": outTime,
            "rated_num": rated_num,
            "last_num": last_num,
            "reg_fee": reg_fee,
            "clinicFee": clinicFee,
            "schedule_num": schedule_num,
        }

        self.fetch_info()

    def fetch_info(self) -> None:
        def fetch():
            update_cookie()
            res = requests.get(
                HOST + '/MakeApp/TimeList',
                data=self.data, headers=HEADER, cookies=COOKIE
            )
            assert res.status_code == 200
            return HTML(res.text)

        html = fetch()

        self.spans: SubscribeTimeSpan = list(map(SubscribeTimeSpan.parse, html.xpath(
            '/html/body/section/div[2]/ul/li/@onclick')))

    def params(self) -> str:
        return urlencode(self.data)


class Doctor:
    def __init__(self, hospital_id: str, department_id: str, doctor_id: str) -> None:
        self.data = {
            'hospital_id': hospital_id,
            'department_id': department_id,
            'doctor_id': doctor_id
        }

        self.fetch_info()

    def fetch_info(self) -> None:
        def fetch():
            update_cookie()
            res = requests.get(
                HOST + '/MakeApp/DoctorDetail',
                data=self.data, headers=HEADER, cookies=COOKIE
            )
            assert res.status_code == 200
            return HTML(res.text)

        html = fetch()

        self.name = html.xpath(
            '/html/body/section/ul/li[1]/ul/li[1]/text()')[0].strip()
        self.location = html.xpath(
            '/html/body/section/div[1]/p/text()')[0].strip()
        self.times: list[SubscribeTime] = list(map(SubscribeTime.parse, html.xpath(
            '/html/body/section/div[3]/table/tbody/tr/td/a/@onclick')))

    def params(self) -> str:
        return urlencode(self.data)


def search_doctors(name: str) -> list[Doctor]:
    def fetch(index):
        update_cookie()
        res = requests.post(
            HOST + '/MakeApp2/BatchLoadDocList',
            data={'keyword': name, 'index': index}, headers=HEADER, cookies=COOKIE
        )
        assert res.status_code == 200
        return res.json()

    result = []
    index = 1
    json = fetch(index)
    while json['itemList']:
        index += 1
        result += json['itemList']
        json = fetch(index)
    return result
