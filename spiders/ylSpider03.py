# -*- coding: utf-8 -*-
# 爬取艺龙网机票信息
import datetime
import json
import os
import sys
import time
import traceback

import random

import pytz
import scrapy
from flight_spider.ylutils.excel_read import get_full_airport, get_city_from_airport
from flight_spider.ylutils.ip_map import ip_map
from flight_spider.ylutils.ylLog import YlLog
from flight_spider.ylutils.ylFile import YlFile
from flight_spider.redisUtil import RedisUtil
from flight_spider.settings import user_agent_list
from flight_spider.YlSpiderItem import YlSpiderItem, YlRedisItem
import urllib.parse as up


class YlSpiderApi(scrapy.Spider):
    name = 'ylSpider03'
    allowed_domains = ['www.ly.com']
    start_urls = ['https://www.ly.com/']

    # redis_key = 'yl:start_urls'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        scrapy.Spider.__init__(self, self.name)
        self.file_name = kwargs.get('file_name')
        self.from_line = kwargs.get('from_line')
        self.to_line = kwargs.get('to_line')
        self.from_date = kwargs.get('from_date')
        self.to_date = kwargs.get('to_date')
        self.is_low_price = kwargs.get('is_low_price')
        self.task_time = kwargs.get('task_time') + '0'
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
        self.redis_items = self.ylFile.getConfigDict("Redis-Config-pro")

    def get_seconds(self):
        datetime_object = datetime.datetime.now()
        now_timetuple = datetime_object.timetuple()
        now_second = time.mktime(now_timetuple)
        mow_millisecond = int(now_second * 1000 + datetime_object.microsecond / 1000)
        return mow_millisecond

    # 判断字典中父节点是否有子节点
    def has_node(self, data: dict, node: str):
        for k, v in data.items():
            if node == k:
                return True
            else:
                continue
        return False

    def switch_ele(self, collection: list, index1: int, index2: int):
        mid = collection[index1]
        collection[index1] = collection[index2]
        collection[index2] = mid

    def get_headers_1(self, tcp_plat, ua, tcversion, tctracer_id, server_session_id, cookies):
        headers = {
            "Host": "m.ly.com",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "tcplat": str(tcp_plat),
            "Origin": "https://m.ly.com",
            "auth": "true",
            "User-Agent": ua,
            "tcversion": tcversion,
            "tcuserid": "",
            "Accept": "application/json, text/plain, */*",
            "tcopenid": "",
            # "cache-control": "no-cache",
            "tctracerid": tctracer_id,
            "tcbusiness": "true",
            "tcsectoken": "",
            "tcsessionid": server_session_id,
            "Referer": "",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cookie": cookies,
        }
        return headers

    '''
    @Description: 冒泡排序,加入flag判断数组是否有序
    '''

    def bubble_sort(self, collection: list):
        flags = 0
        for i, economy_cabin in enumerate(collection):
            for j in range(0, len(collection) - 1 - i):
                # 遍历,将价格最小的对象排在列表第一个(冒泡)
                if int(collection[i]['SellPrice']) > int(collection[i + 1]['SellPrice']):
                    self.switch_ele(collection, j, j + 1)
                    # 不是有序的，flags设置为1
                    flags = 1
                elif flags == 0:
                    return
                else:
                    continue

    '''
    @Description: 读取传参,开启请求
    '''

    def start_requests(self):
        # 初始化变量
        global cookies, gnjpapp_head, server_session_id
        self.start_time = time.time()
        gnjpapp_head = None
        server_session_id = ""
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
                _flight_time = datetime.datetime.strptime(flight_time, "%Y-%m-%d")
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
                if self.redisUtil.hash_exist_key(f"ly:{self.now_date}-cookie", "cookies"):
                    cookies = str(self.redisUtil.get(f"ly:{self.now_date}-cookie", "cookies"), "utf-8")
                    _cookies = cookies.split(";")
                    for coo in _cookies:
                        key = coo.split("=")[0].strip()
                        value = coo.split("=")[1]
                        if key.__eq__("serverSessionId"):
                            server_session_id = value
                        elif key.__eq__("gnjpapphead"):
                            gnjpapp_head = eval(up.unquote(value))
                        else:
                            continue
                    tctracer_id = gnjpapp_head.get('tctracerid')
                    tcp_plat = int(gnjpapp_head.get('tcplat'))
                    current_milli_time = self.get_seconds()
                    server_session_id = f"0-{current_milli_time}" if server_session_id == "" else server_session_id
                    tcversion = gnjpapp_head.get('tcversion')
                    _from_city = up.quote(from_city)
                    _to_city = up.quote(to_city)
                    # url = f"https://m.ly.com/kylintouch/sbook1/{from_city_code}/{to_city_code}/{_from_city}/{_to_city}/{flight_time}?date={flight_time}&from={_from_city}&to={_to_city}&fromairport=&toairport=&p=&childticket=0,0"
                    url = f"https://m.ly.com/kylintouch/sbook1/{from_city_code}/{to_city_code}/{_from_city}/{_to_city}/{flight_time}?fromcitycode={_from_city_code}&tocitycode={_to_city_code}&childticket=0,0&fromairport=&toairport=&cabin=0&hasAirPort=3&RefId=10758821&bd_vid="
                    headers = self.get_headers_1(tcp_plat, ua, tcversion, tctracer_id, server_session_id, cookies)
                    headers['Referer'] = url
                    # 获取sd
                    sd_delta = datetime.timedelta(days=3)
                    sd_date = _flight_time - sd_delta
                    sd = sd_date.strftime("%Y-%m-%d")
                    # 获取ed
                    ed_delta = datetime.timedelta(days=15)
                    ed_date = _flight_time + ed_delta
                    ed = ed_date.strftime("%Y-%m-%d")
                    form_data = {
                        "IsMuilteSite": 1, "aac": "", "acc": _to_city_code, "cabin": 0, "dac": "",
                        "dcc": _from_city_code,
                        "ddate": flight_time, "entrance": 0,
                        "pc": {
                            "sd": sd,
                            "ed": ed,
                        },
                        "plat": int(tcp_plat),
                        "pt": 0
                    }
                    yield scrapy.FormRequest(
                        url="https://m.ly.com/kylintouch/flightApis/wx/flightquery/flights",
                        body=json.dumps(form_data).encode("utf-8"), method="POST",
                        callback=self.parse_api, dont_filter=True, meta=metadata, headers=headers)
                else:
                    self.ylLog.debug("cookie过期或者不存在")
                    sys.exit()

    '''
    @Description: 解析每个OD某一天的所有航班,然后解析航班,如果航班默认的价格不是产品价格,则直接解析数据放入管道,是产品价格就callback到下一函数
    '''

    def parse_api(self, response):
        self.total += 1
        self.ylLog.info(f"采集总次数:{self.total}")
        from_city = response.meta['from_city']
        to_city = response.meta['to_city']
        from_city_code = response.meta['from_city_code']
        to_city_code = response.meta['to_city_code']
        flight_time = response.meta['flight_time']
        userAgent = response.meta['user-agent']
        create_time = response.meta['create_time']
        # 初始化变量
        req_url = "https://m.ly.com/kylintouch/flightApis/wx/flightbffquery/query/getkylinflightlist"
        ua = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Mobile Safari/537.36"
        global gnjpapphead, session_id, link_tracker_id
        gnjpapphead = None
        session_id = ""
        link_tracker_id = ""
        # redis中是否已保存cookie
        if self.redisUtil.hash_exist_key(f"ly:{self.now_date}-cookie", "cookies"):
            cookies = str(self.redisUtil.get(f"ly:{self.now_date}-cookie", "cookies"),
                          "utf-8")
            _cookies = cookies.split(";")
            for coo in _cookies:
                key = coo.split("=")[0].strip()
                value = coo.split("=")[1].strip()
                if key.__eq__("serverSessionId"):
                    session_id = value
                elif key.__eq__("traceid"):
                    link_tracker_id = value
                elif key.__eq__("gnjpapphead"):
                    gnjpapphead = value
            gnjpapphead = eval(up.unquote(gnjpapphead))
            if response.url == "**":
                self.fail += 1
                msg = f"响应异常,OD为:{from_city}:{from_city_code}={to_city}:{to_city_code}>>>次数:{self.fail}\n"
                self.ylLog.exception(f"{msg}")
            elif response.status in [200, 201]:
                self.count += 1
                self.ylLog.info(f"成功返回页面>>>{self.count}")
                self.ylLog.info("响应成功率: %4f" % (self.count / self.total))
                try:
                    data = json.loads(response.body.decode())
                    # 判断当日是否有航班
                    if self.has_node(data.get('body'), "fpc"):
                        flights = data['body']['fpc']
                        count = 0
                        for k, v in flights.items():
                            if len(v) == 0:
                                continue
                            else:
                                for flight in v:
                                    # 获取PhoenixRuleId
                                    phoenix_rule_id = str(flight['newLps']['PhoenixRuleId'])
                                    print(f"phoenix_rule_id: {phoenix_rule_id}")
                                    icsf = flight['icsf']
                                    # 通过icsf判断是否是共享航班,并且不是产品
                                    if not icsf:
                                        flight_transfer, flight_type, platform = "", "", "yl"
                                        # 只有当三字码为CQW时才取get_city_from_airport
                                        if phoenix_rule_id.__eq__("00000"):
                                            count += 1
                                            start_time = flight['dt'].split(" ")[1]
                                            end_time = flight['at'].split(" ")[1]
                                            plane_no = flight['fn']
                                            company = flight['asn']
                                            _from_city_code = flight['dac']
                                            __from_city_code = self.airport_map[
                                                _from_city_code] if _from_city_code in self.air_list else _from_city_code
                                            _to_city_code = flight['aac']
                                            from_airport_name = flight['dasn']
                                            to_airport_name = flight['aasn']
                                            from_city = get_city_from_airport(
                                                str(from_airport_name),
                                                self.base_path) if _from_city_code == "CQW" else from_city
                                            to_city = get_city_from_airport(
                                                str(to_airport_name),
                                                self.base_path) if _to_city_code == "CQW" else to_city
                                            from_city_airport = get_full_airport(_from_city_code, self.base_path)
                                            to_city_airport = get_full_airport(_to_city_code, self.base_path)
                                            print(
                                                f"<<<from_airport: {_from_city_code}, to_airport: {_to_city_code} off_date: {flight_time}>>>")
                                            __to_city_code = self.airport_map[
                                                _to_city_code] if _to_city_code in self.air_list else _to_city_code
                                            plane_type = flight['amn']
                                            # company_no = re.findall("^(.*?)\d+", str(plane_no), re.I)[0]
                                            company_no = str(plane_no)[0:2]
                                            price, discount = [], []
                                            price.append(str(flight['atp']))
                                            for lps in flight['lps']:
                                                if lps['PhoenixRuleId'] == "00000" and int(lps['atp']) == int(
                                                        flight['atp']):
                                                    discount.append(lps['pts'][0]['td'])
                                                else:
                                                    continue
                                            if self.has_node(flight, 'sc'):
                                                flight_transfer = flight['sc']
                                                flight_type = "经停"
                                            elif self.has_node(flight, "ps"):
                                                flight_transfer = flight['ps']['g5']['g5sc']
                                                flight_type = "联程"
                                            else:
                                                flight_transfer = ""
                                                flight_type = "直飞"
                                            item = YlSpiderItem(
                                                off_date=flight_time,
                                                from_city=from_city,
                                                from_city_code=_from_city_code,
                                                to_city=to_city,
                                                to_city_code=_to_city_code,
                                                plane_no=plane_no,
                                                company=company,
                                                company_no=company_no,
                                                platform=platform,
                                                start_time=start_time,
                                                end_time=end_time,
                                                price=str(price),
                                                discount=str(discount),
                                                create_time=create_time,
                                                plane_type=plane_type,
                                                flight_type=flight_type,
                                                flight_transfer=flight_transfer,
                                                from_city_airport=from_city_airport,
                                                to_city_airport=to_city_airport,
                                                task_time=self.task_time,
                                                server_ip=ip_map[int(self.redis_items['db'])],
                                                insert_time=datetime.datetime.now(
                                                    pytz.timezone('Asia/Shanghai')).strftime(
                                                    '%Y-%m-%d %H:%M:%S')
                                            )
                                            print("from_city_code", _from_city_code, "from_city", from_city,
                                                  "to_city_code", _to_city_code, "to_city", to_city, "off_date",
                                                  flight_time,
                                                  "plane_no", plane_no, "price", price, "discount", discount,
                                                  "from_city_airport", from_city_airport, "to_city_airport",
                                                  to_city_airport)
                                            yield item
                                        # 是产品
                                        elif not phoenix_rule_id.__eq__("00000"):
                                            count += 1
                                            start_time = flight['dt'].split(" ")[1]
                                            end_time = flight['at'].split(" ")[1]
                                            plane_no = flight['fn']
                                            company = flight['asn']
                                            _from_city_code = flight['dac']
                                            _to_city_code = flight['aac']
                                            from_airport_name = flight['dasn']
                                            to_airport_name = flight['aasn']
                                            from_city = get_city_from_airport(
                                                str(from_airport_name),
                                                self.base_path) if _from_city_code == "CQW" else from_city
                                            to_city = get_city_from_airport(
                                                str(to_airport_name),
                                                self.base_path) if _to_city_code == "CQW" else to_city
                                            from_city_airport = get_full_airport(_from_city_code, self.base_path)
                                            to_city_airport = get_full_airport(_to_city_code, self.base_path)
                                            print(
                                                f"<<<from_airport: {_from_city_code}, to_airport: {_to_city_code} off_date: {flight_time}>>>")
                                            # company_no = re.findall("^(.*?)\d+", str(plane_no), re.I)[0]
                                            company_no = str(plane_no)[0:2]
                                            plane_type = flight['amn']
                                            if self.has_node(flight, 'sc'):
                                                flight_transfer = flight['sc']
                                                flight_type = "经停"
                                            elif self.has_node(flight, "ps"):
                                                flight_transfer = flight['ps']['g5']['g5sc']
                                                flight_type = "联程"
                                            else:
                                                flight_transfer = ""
                                                flight_type = "直飞"
                                            redis_items = YlRedisItem(
                                                flight_transfer=flight_transfer,
                                                flight_type=flight_type,
                                                off_date=flight_time,
                                                from_city=from_city,
                                                from_city_code=_from_city_code,
                                                to_city=to_city,
                                                to_city_code=_to_city_code,
                                                plane_no=plane_no,
                                                company=company,
                                                company_no=company_no,
                                                platform=platform,
                                                start_time=start_time,
                                                end_time=end_time,
                                                plane_type=plane_type,
                                                from_city_airport=from_city_airport,
                                                to_city_airport=to_city_airport,
                                                task_time=self.task_time,
                                                create_time=create_time
                                            )
                                            print("from_city_code", _from_city_code, "from_city", from_city,
                                                  "to_city_code", _to_city_code, "to_city", to_city, "off_date",
                                                  flight_time, "plane_no", plane_no, "from_city_airport",
                                                  from_city_airport, "to_city_airport",
                                                  "phoenix_rule_id", phoenix_rule_id, "create_time", create_time)
                                            yield redis_items
                        self.end_time = time.time()
                        self.ylLog.info(f"爬取耗时{self.end_time - self.start_time}")
                        msg = f"起飞时间: {flight_time} OD:{from_city}:{from_city_code}={to_city}:{to_city_code}航班数{count}"
                        self.ylLog.info(msg)
                    else:
                        self.ylLog.info(f"OD:{from_city}:{from_city_code}={to_city}:{to_city_code}航班数0")
                        pass
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
        else:
            self.ylLog.debug("cookie过期或者不存在")
            sys.exit()
