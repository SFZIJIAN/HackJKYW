import re

import requests
from lxml.etree import HTML


def get_cookie(account: str, password: str) -> dict:
    with requests.session() as session:
        session.post('http://115.220.1.205:8014/Account/post_login',
                     data={'name': account, 'pwd': password})
        return dict(session.cookies)


HOST = 'http://115.220.1.205:8014'
HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.34'
}
COOKIE = get_cookie('19527986531', '492548')


class SubscribeTimeSpan:
    @staticmethod
    def parse_url_params(url):
        match = re.search(
            r"hospName=(.*?)&dept=(.*?)&yysjd=(.*?)&docName=(.*?)&title=(.*?)&last_num=(.*?)&reg_fee=(.*?)&clinicFee=(.*?)&yysjd_num=(.*?)&schedule_num=(.*?)'",
            url
        )

        return {
            # 'hospName': match.group(1),
            # 'dept': match.group(2),
            'yysjd': match.group(3),
            # 'docName': match.group(4),
            # 'title': match.group(5),
            # 'last_num': match.group(6),
            # 'reg_fee': match.group(7),
            # 'clinicFee': match.group(8),
            'yysjd_num': match.group(9),
            'schedule_num': match.group(10)
        }

    def __init__(self, url: str) -> None:
        self.data = SubscribeTimeSpan.parse_url_params(url)
        self.data.update({
            'trans_no': 'SG0023',
            'member_num': '',
            'card_type': '2',    # 健康卡=1 社保卡=2
            'card_number': 'C09C46724',  # 卡号
            'qq_id': 1  # 谁 (没有=我 1=你 2=陈)
        })

    def make_request(self) -> requests.Response:
        res = requests.post(HOST+'/MakeApp/checkMakeApp',
                            data=self.data, headers=HEADER, cookies=COOKIE)
        return res.json()


class SubscribeTime:
    @staticmethod
    def parse_url_params(url: str) -> dict:
        match = re.search(
            r"docName=(.*?)&dept=(.*?)&title=(.*?)&hospName=(.*?)&scheDate=(.*?)&weekDay=(.*?)&outTime=(.*?)&rated_num=(.*?)&last_num=(.*?)&reg_fee=(.*?)&clinicFee=(.*?)&schedule_num=(.*?)'\)",
            url
        )

        return {
            "docName": match.group(1),
            "dept": match.group(2),
            "title": match.group(3),
            "hospName": match.group(4),
            "scheDate": match.group(5),
            "weekDay": match.group(6),
            "outTime": match.group(7),
            "rated_num": match.group(8),
            "last_num": match.group(9),
            "reg_fee": match.group(10),
            "clinicFee": match.group(11),
            "schedule_num": match.group(12),
        }

    def __init__(self, url: str) -> None:
        self.data = SubscribeTime.parse_url_params(url)

    def fetch_spans(self) -> list[SubscribeTimeSpan]:
        res = requests.get(HOST + '/MakeApp/TimeList',
                           data=self.data, headers=HEADER, cookies=COOKIE)
        assert res.status_code == 200

        result = []
        for i in HTML(res.text).xpath('/html/body/section/div[2]/ul/li/@onclick'):
            result.append(SubscribeTimeSpan(i))
        return result


class Doctor:
    def __init__(self, hospital_id: int, department_id: int, doctor_id: int) -> None:
        self.data = {
            'hospital_id': hospital_id,
            'department_id': department_id,
            'doctor_id': doctor_id
        }

    def fetch_times(self) -> list[SubscribeTime]:
        res = requests.get(HOST + '/MakeApp/DoctorDetail',
                           data=self.data, headers=HEADER, cookies=COOKIE)
        assert res.status_code == 200

        result = []
        for i in HTML(res.text).xpath('//table[@class="secondbox-table"]/tbody/tr/td/a/@onclick'):
            result.append(SubscribeTime(i))
        return result


WANG_JIAN_LIANG = Doctor(4717719600, 1010033, 4717719600101000002)
TEST_DOCTOR = Doctor(6891454900, 10300701, 689145490010071)
TEST2_DOCTOR = Doctor(6891454900, 10400503, 689145490010111)
TEST3_DOCTOR = Doctor(6891454900, 10700401, 689145490010339)
TEST4_DOCTOR = Doctor(4717718500, 2010026, 47177185002250)
