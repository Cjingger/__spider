# -*- coding: utf-8 -*-
import csv
import datetime
import json
import os
import random
import re
import sys
import time
import traceback
import urllib.parse as up
import execjs
import pytz
import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from flight_spider.YlSpiderItem import YlSpiderItem, YlBatchItem
from flight_spider.settings import user_agent_list, user_agent_mobile
from flight_spider.redisUtil import RedisUtil
from flight_spider.spiders.bshead import create_bs_driver
from flight_spider.ylutils.ip_map import ip_map
from flight_spider.ylutils.ylFile import YlFile
from flight_spider.ylutils.ylLog import YlLog
from flight_spider.clickVerfication import ClickVerfication

chorme_options = Options()
chorme_options.add_argument("--headless")
chorme_options.add_argument("--disable-gpu")


class ctripSpider02(scrapy.Spider):
    name = 'ctripSpider02'
    allowed_domains = ['m.ctrip.com']
    start_urls = ['https://m.ctrip.com/html5/flight/home']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        scrapy.Spider.__init__(self, self.name)
        self.driver = create_bs_driver(headless=False)
        # self.driver.set_page_load_timeout(30)
        self.file_name = kwargs.get('file_name')
        self.from_line = kwargs.get('from_line')
        self.to_line = kwargs.get('to_line')
        self.from_date = kwargs.get('from_date')
        self.to_date = kwargs.get('to_date')
        self.is_low_price = kwargs.get('is_low_price')
        self.task_time = kwargs.get('task_time')
        # 当前时间
        self.now_date = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
        self.ylLog = YlLog()
        self.ylFile = YlFile(os.path.abspath('.'))
        self.redisUtil = RedisUtil()
        self.start_time = None
        self.end_time = None
        self.success, self.total, self.fail, self.count, self.exception, self.success_lowest = 0, 0, 0, 0, 0, 0
        print(self.file_name, self.from_line, self.to_line, self.from_date, self.to_date, self.is_low_price,
              self.task_time)
        self.base_path = os.path.abspath('.')
        # 一市两场
        self.airport_map = {
            "PEK": "PEK",
            "PKX": "PEK",
            "PVG": "PVG",
            "SHA": "PVG",
            "CTU": "CTU",
            "TFU": "CTU",
            "ZYI": "ZYI",
            "WMT": "WMT",
            "CKG": "CKG",
            "CQW": "CQW",

        }
        # 一市两场三字码
        self.air_list = ["PEK", "PKX", "PVG", "SHA", "CTU", "TFU", "ZYI", "WMT", "CKG", "CQW"]
        self.ctrip_headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": "application/json",
            "cookie": "",
            "origin": "https://m.ctrip.com",
            "referer": "",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            # "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Mobile Safari/537.36",
            "user-agent": random.choice(user_agent_mobile),
            "x-requested-with": "XMLHttpRequest"
        }
        self.redis_items = self.ylFile.getConfigDict("Redis-Config-pro")
        js = os.path.join(os.path.abspath('spiders'), 'parse.js')
        with open(js, 'r', encoding='utf-8') as file:
            self.js = file.read()

    @property
    def get_uuid(self):
        js = execjs.compile(self.js)
        uuid = js.call('uuid')
        return uuid

    def atob_str(self, from_city_code, to_city_code):
        Q = '09031134419577876545.{"searchParameter":{"cityPairs":[{"departureCode":"%s","arrivalCode":"%s"}],"cabinClasses":["ECONOMY"],"regionType":"DOMESTIC","tripType":"ONE_WAY","start":"","end":""}}' % (from_city_code, to_city_code)
        js = execjs.compile(self.js)
        atob = js.call('he', Q)
        return atob

    def get_micro_sec(self, date_time: str) -> str:
        date_time = datetime.datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        _date_time = str(int(time.mktime(date_time.timetuple())))
        # 3位, 微秒
        __date_time = str("%06d" % date_time.microsecond)[0:3]
        return _date_time + __date_time

    def get_random_ip(self):
        IP_PROXY_LIST = []
        with open(os.path.abspath('.') + '/IPProxy.txt', 'r') as f:
            for line in f:
                line = line.strip()
                IP_PROXY_LIST.append(line)
        ip_proxy = random.choice(IP_PROXY_LIST)
        return re.findall(f'^\w+://(.*?):\d+$', ip_proxy)[0]

    def start_requests(self):
        # 初始化变量
        global cookies, guid, _abtest_userid, session_id
        self.start_time = time.time()
        guid = None
        _abtest_userid = ""
        session_id = ""
        cookies = ""
        list = []
        with open(f"{self.file_name}", "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                line = eval(line)
                list.append(line)

        if int(self.from_line) == -1 or int(self.to_line) == -1:
            file_line = list
        else:
            file_line = list[(int(self.from_line) - 1):int(self.to_line)]

        for i, li in enumerate(file_line):
            from_city = li['from_city_name']
            to_city = li['to_city_name']
            from_city_code = li['from_city_code']
            to_city_code = li['to_city_code']
            # 北京地区做特殊处理
            _to_city_code = "BJS" if to_city.__eq__("北京") else to_city_code
            _from_city_code = "BJS" if from_city.__eq__("北京") else from_city_code
            # 重庆武隆做特殊处理
            from_city = "重庆" if from_city.__eq__("武隆") else from_city
            to_city = "重庆" if to_city.__eq__("武隆") else to_city
            now_time = time.strftime("%F")
            if int(self.from_date) == 0 and int(self.to_date) == 0:
                days = [0]
            elif int(self.from_date) == -1 or int(self.to_date) == -1:
                days = range(15)
            else:
                days = range(int(self.from_date), (int(self.to_date) + 1))
            for j in days:
                flight_time = (datetime.datetime.strptime(now_time, "%Y-%m-%d") + datetime.timedelta(days=j)).strftime(
                    "%Y-%m-%d")
                ua = random.choice(user_agent_list)
                create_time = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).strftime(
                    '%Y-%m-%d %H:%M:%S')
                if self.is_low_price == '0':
                    metadata = {"from_city": from_city,
                                "to_city": to_city,
                                "from_city_code": _from_city_code,
                                "to_city_code": _to_city_code,
                                "index": int(i + 1),
                                "flight_time": flight_time,
                                'is_low_price': 0,
                                'dont_merge_cookies': True,
                                'create_time': create_time,
                                'user-agent': ua}
                else:
                    metadata = {"from_city": from_city,
                                "to_city": to_city,
                                "from_city_code": _from_city_code,
                                "to_city_code": _to_city_code,
                                "index": int(i + 1),
                                "flight_time": flight_time,
                                'is_low_price': 1,
                                'dont_merge_cookies': True,
                                'create_time': create_time,
                                'user-agent': ua}
                # redis中是否已保存cookie
                if self.redisUtil.hash_exist_key(f"ctrip:{self.now_date}-cookie", "cookies"):
                    cookies = str(self.redisUtil.get(f"ctrip:{self.now_date}-cookie", "cookies"), "utf-8")
                    _cookies = cookies.split(";")
                    for coo in _cookies:
                        key = coo.split("=")[0].strip()
                        value = coo.split("=")[1]
                        if key.__eq__("GUID"):
                            guid = value
                        elif key.__eq__("_RGUID"):
                            session_id = value
                        elif "userid" in str(key):
                            _abtest_userid = value
                        # else:
                        #     continue
                    self.ctrip_headers['cookie'] = cookies
                    # self.ctrip_headers[
                    #     'referer'] = f'https://m.ctrip.com/html5/flight/swift/domestic/{_from_city_code}/{_to_city_code}/{flight_time}'
                    self.ctrip_headers[
                        'referer'] = f'https://m.ctrip.com/html5/flight/pages/first?searchtype=domestic&dcode={_from_city_code}&acode={_to_city_code}&ddate={flight_time}'
                    print(f"cookie: {self.ctrip_headers['cookie']}")
                    payload = {
                        "data": "{\"searchParameter\":{\"searchFlightItems\":[{\"departureCode\":\"CKG\",\"arrivalCode\":\"HGH\",\"departureDate\":\"2022-06-24\"}],\"tripType\":\"ONE_WAY\",\"regionType\":\"DOMESTIC\",\"passengers\":{\"ADULT\":1,\"CHILD\":0,\"INFANT\":0}}}",
                        "head": {
                            "auth": "",
                            "cid": guid,
                            "ctok": "",
                            "cver": "1.0",
                            "extension": [{"name": "Flt_SubChannel", "value": ""},
                                          {"name": "mystery", "value": self.atob_str(_from_city_code, _to_city_code)},
                                          {"name": "sessionId", "value": self.get_uuid},
                                          {"name": "pageName", "value": "FIRST"},
                                          {"name": "searchKey", "value": ""},
                                          {"name": "aid", "value": "66672"},
                                          {"name": "sid", "value": "1693366"},
                                          {"name": "ouId", "value": ""},
                                          {"name": "sourceId", "value": ""},
                                          {"name": "exmktID", "value": ""},
                                          {"name": "env", "value": "h5"},
                                          {"name": "version", "value": "2020.11.19"},
                                          {"name": "aid", "value": "66672"},
                                          {"name": "sid", "value": "1693366"},
                                          {"name": "protocal", "value": "https"}],
                            "lang": "01",
                            "sid": "8888",
                            "syscode": "09",
                        }
                    }
                    # detect_url = "http://localhost:8000/up_photo"
                    url = f"https://m.ctrip.com/html5/flight/pages/first?searchtype=domestic&dcode={_from_city_code}&acode={_to_city_code}&ddate={flight_time}"
                    # clickVerfication = ClickVerfication(url, detect_url)
                    # clickVerfication.main(self.driver)
                    self.driver.get(url)
                    time.sleep(1)
                    req_url = "https://m.ctrip.com/restapi/soa2/14488/flightList?subEnv=fat128"
                    yield scrapy.FormRequest(
                        url=req_url,
                        body=json.dumps(payload).encode("utf-8"), method="POST",
                        callback=self.parse_api, dont_filter=True, meta=metadata, headers=self.ctrip_headers)
                else:
                    self.ylLog.debug("cookie过期或者不存在")
                    sys.exit()
            time.sleep(random.choice([i for i in range(1, 3)]))

    def parse_api(self, response):
        global flight_type, flight_transfer
        flight_type, flight_transfer = "", ""
        self.total += 1
        self.ylLog.info(f"采集总次数:{self.total}")
        from_city = response.meta['from_city']
        to_city = response.meta['to_city']
        from_city_code = response.meta['from_city_code']
        to_city_code = response.meta['to_city_code']
        flight_time = response.meta['flight_time']
        userAgent = response.meta['user-agent']
        create_time = response.meta['create_time']
        if response.url == "**":
            self.fail += 1
            msg = f"响应异常,OD为:{from_city}:{from_city_code}={to_city}:{to_city_code}>>>次数:{self.fail}\n"
            self.ylLog.exception(f"{msg}")
        elif response.status in [200, 201]:
            self.ylLog.info(f"<<<<<<成功返回页面>>>>>>")
            self.ylLog.info("响应成功率: %4f" % (self.count / self.total))
            try:
                json_data = json.loads(json.loads(response.body.decode())['data'])
                datas = json_data['listCards']
                # datas = eval(json_data['data'])['listCards']
                # 返回结果为空
                if len(datas) == 0:
                    print('datas', json_data)
                    self.ylLog.info("响应成功率: %4f" % (self.count / self.total))
                    raise ConnectionError
                self.count += 1
                self.ylLog.info("响应成功率: %4f" % (self.count / self.total))
                data_list, count = [], 0
                city_msg = json_data['cityMessage']
                from_city, to_city = str(city_msg).split("|")[0], str(city_msg).split("|")[1]
                for data in datas:
                    # print("datas", datas)
                    count += 1
                    _discount, _price = [], []
                    from_city_code = data['departureAirportCode']
                    from_city_airport = data['departureAirportName']
                    to_city_code = data['arrivalAirportCode']
                    to_city_airport = data['arrivalAirportName']
                    start_time = str(data['departDateTime']).split(" ")[1]
                    start_time = start_time.split(":")[0] + ':' + start_time.split(":")[1]
                    cross_days = data['crossDays']
                    end_time = str(data['arriveDateTime']).split(" ")[1]
                    end_time = end_time.split(":")[0] + ':' + end_time.split(":")[1]
                    plane_no = data['airlines'][0]['displayName']
                    company_no = data['airlines'][0]['code']
                    company = data['airlines'][0]['name']
                    plane_type = data['airlines'][0]['craft']
                    price = str(data['prices']['ECONOMY'])
                    discount = str(data['discounts']['ECONOMY'])
                    total_duration = data['totalDuration']
                    tickets = data['ticketCounts']['ECONOMY']
                    fsitem = data['stops']
                    stop_times = ""
                    if len(fsitem) != 0:
                        flight_transfer, flight_type = data['stops'][0], '经停'
                        stop_times = str(data['stopTimes'][0])
                    print(from_city, from_city_code, from_city_airport, to_city, to_city_code, to_city_airport,
                          start_time, end_time, plane_no, company, price, discount, total_duration, tickets, stop_times)
                    _data = [company, company_no, plane_no, start_time, end_time, from_city, from_city_code, to_city,
                             to_city_code, create_time, str(discount), flight_time, 'ctrip', str(price), '', plane_type,
                             '', from_city_airport, to_city_airport, self.task_time,
                             ip_map[int(self.redis_items['db'])], count]
                    data_list.append(_data)

                # 产品价格与非产品价格一起返回,批量插入
                print(
                    f"爬取数据 -> 起飞时间: {flight_time} OD:{from_city}:{from_city_code}={to_city}:{to_city_code}航班数>>>{len(data_list)}")
                names = ['company', 'company_no', 'plane_no', 'start_time', 'end_time', 'from_city',
                         'from_city_code', 'to_city', 'to_city_code', 'create_time', 'discount', 'off_date',
                         'platform', 'price', 'flight_type', 'plane_type', 'flight_transfer', 'from_city_airport',
                         'to_city_airport', 'task_time', 'server_ip', 'flight_number']
                # 将csv文件放入logs目录下
                csv_file = os.path.join(self.ylLog.second_path,
                                        fr"ctrip-{from_city_code}-{to_city_code}-{flight_time}-{ip_map[int(self.redis_items['db'])]}.csv")
                print("***csv_file_name***", csv_file)
                # with open(csv_file, "w+", encoding="utf-8", newline='') as f:
                #     f_csv = csv.writer(f)
                #     f_csv.writerow(names)
                #     f_csv.writerows(data_list)
                msg = f"起飞时间: {flight_time} OD:{from_city}:{from_city_code}={to_city}:{to_city_code}航班数>>>{count}"
                self.ylLog.info(msg)
                item = YlBatchItem(
                    from_city_code=from_city_code,
                    to_city_code=to_city_code,
                    off_date=flight_time,
                    server_ip=ip_map[int(self.redis_items['db'])],
                    csv_file_name=csv_file,
                    flight_number=len(data_list),
                )
                # yield item
            except Exception as e:
                print(traceback.print_exc())
                path = "/result/error_ua.txt"
                self.ylFile.createFile(path, userAgent + '\n')
                # -------------------d
                xmlpath = fr"/result/{from_city}({from_city_code})-{to_city}({to_city_code})-{flight_time}-exception.html"
                self.ylFile.createFile(xmlpath, response.body.decode(), model='w+')
                self.ylLog.info(f"{xmlpath}写入源码文件成功")
                pass
        else:
            self.fail += 1
            msg = f"状态码异常>>>{self.fail}, 状态码: {response.status}\n"
            self.ylLog.exception(msg)
            path = fr"/errorHtml/{from_city}-{to_city}-{flight_time}-status_error.html"
            self.ylFile.createFile(path, response.body.decode)
