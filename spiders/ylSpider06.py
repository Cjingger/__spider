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
import httpx
from httpx._config import SSLConfig
from flight_spider.ylutils.excel_read import get_airport, get_full_airport, get_city_from_airport
from flight_spider.ylutils.ylLog import YlLog
from flight_spider.ylutils.ylFile import YlFile
from flight_spider.redisUtil import RedisUtil
from flight_spider.settings import user_agent_mobile
from flight_spider.YlSpiderItem import YlSpiderItem, YlBatchItem
import urllib.parse as up
from flight_spider.ylutils.ip_map import ip_map
import csv
from collections import defaultdict


class YlSpider06(scrapy.Spider):
    name = 'ylSpider06'
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
        self.task_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:00:00")
        # self.task_time = kwargs.get('task_time') + '0'
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
        }
        # 一市两场三字码
        self.air_list = ["PEK", "PKX", "PVG", "SHA", "CTU", "TFU", "ZYI", "WMT"]
        self.flight_infos = {}

    @property
    def get_seconds(self) -> int:
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

    def get_headers_2(self, gnjpapphead, ua, link_tracker_id, session_id, cookies):
        headers = {
            "Host": "m.ly.com",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "tcplat": str(gnjpapphead['tcplat']),
            "Origin": "https://m.ly.com",
            "auth": "true",
            "User-Agent": ua,
            "tcversion": str(gnjpapphead['tcversion']),
            "tcuserid": "",
            "Accept": "application/json, text/plain, */*",
            "tcopenid": "",
            # "cache-control": "no-cache",
            "tctracerid": link_tracker_id,
            "tcbusiness": "true",
            "tcsectoken": "",
            "tcsessionid": session_id,
            "Referer": "",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cookie": cookies,
        }
        return headers

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

    def get_default_headers(self, url):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Host": url.split("://")[-1].replace("/", ""),
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
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

    # 从cookie中取得请求体需要的参数
    def get_cookie_params(self, cookies: str):
        global session_id, link_tracker_id, gnjpapphead
        _cookies = cookies.split(";")
        for coo in _cookies:
            key = coo.split("=")[0].strip()
            value = coo.split("=")[1].strip()
            if key.__eq__("serverSessionId"):
                session_id = value
            elif key.__eq__("traceid"):
                link_tracker_id = value
            elif key.__eq__("gnjpapphead"):
                gnjpapphead = eval(up.unquote(value))
        return session_id, link_tracker_id, gnjpapphead

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
                print(f"***{flight_time}***")
                _flight_time = datetime.datetime.strptime(flight_time, "%Y-%m-%d")
                ua = random.choice(user_agent_mobile)
                create_time = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).strftime(
                    '%Y-%m-%d %H:%M:%S')
                metadata = {"from_city": from_city, "to_city": to_city, "from_city_code": _from_city_code,
                            "to_city_code": _to_city_code, "index": int(i + 1), "flight_time": flight_time,
                            'is_low_price': 0 if self.is_low_price == '0' else 1, 'dont_merge_cookies': True,
                            'create_time': create_time, 'user-agent': ua}
                # redis中是否已保存cookie
                if self.redisUtil.hash_exist_key(f"ly:{self.now_date}-cookie", "cookies"):
                    cookies = str(self.redisUtil.get(f"ly:{self.now_date}-cookie", "cookies"), "utf-8")
                    server_session_id, link_tracker_id, gnjpapp_head = self.get_cookie_params(cookies)
                    tctracer_id = gnjpapp_head.get('tctracerid')
                    tcp_plat = int(gnjpapp_head.get('tcplat'))
                    current_milli_time = self.get_seconds
                    server_session_id = f"0-{current_milli_time}" if server_session_id == "" else server_session_id
                    tcversion = gnjpapp_head.get('tcversion')
                    _from_city, _to_city = up.quote(from_city), up.quote(to_city)
                    url = f"https://m.ly.com/touchbook/touch/sbook1/{from_city_code}/{to_city_code}/{_from_city}/{_to_city}/{flight_time}?fromcitycode={_from_city_code}&tocitycode={_to_city_code}&childticket=0,0&fromairport=&toairport={to_city_code}&cabin=0&hasAirPort=3&RefId=10758821&bd_vid="
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
                    metadata['headers'], metadata['form_data'] = headers, form_data
                    yield scrapy.FormRequest(
                        url="https://m.ly.com/touchbook/flightApis/wx/flightquery/flights",
                        body=json.dumps(form_data).encode("utf-8"), method="POST",
                        callback=self.parse_api, dont_filter=True, meta=metadata, headers=headers)
                else:
                    self.ylLog.debug("cookie过期或者不存在")
                    sys.exit()

    '''
    @Description: 需要解析退改价格、托运行李额等数据,所以每个航班都需要callback到parse_lowest_price函数
    '''

    def parse_api(self, response):
        self.total += 1
        self.ylLog.info(f"采集总次数:{self.total}")
        print("res", response)
        global cookies, gnjpapp_head, server_session_id
        gnjpapp_head, server_session_id, cookies = None, "", ""
        from_city = response.meta['from_city']
        to_city = response.meta['to_city']
        from_city_code = response.meta['from_city_code']
        to_city_code = response.meta['to_city_code']
        flight_time = response.meta['flight_time']
        _flight_time = datetime.datetime.strptime(flight_time, "%Y-%m-%d")
        userAgent = response.meta['user-agent']
        create_time = response.meta['create_time']
        headers = response.meta['headers']
        form_data = response.meta['form_data']
        # 北京地区做特殊处理
        _to_city_code = "BJS" if to_city.__eq__("北京") else to_city_code
        _from_city_code = "BJS" if from_city.__eq__("北京") else from_city_code
        # 重庆武隆做特殊处理
        from_city = "重庆" if from_city.__eq__("武隆") else from_city
        to_city = "重庆" if to_city.__eq__("武隆") else to_city
        if response.url == "**":
            self.fail += 1
            msg = f"响应异常,OD为:{from_city}:{from_city_code}={to_city}:{to_city_code}>>>次数:{self.fail}\n"
            self.ylLog.exception(f"{msg}")
        if response.status in [200, 201]:
            self.count += 1
            self.ylLog.info(f"成功返回页面>>>{self.count}")
            self.ylLog.info("响应成功率: %4f" % (self.count / self.total))
            try:
                data = json.loads(response.body.decode())
                # 判断当日是否有航班
                if self.has_node(data.get('body'), "fpc"):
                    data_list = []
                    flights = data['body']['fpc']
                    count = 0
                    for k, v in flights.items():
                        if len(v) == 0:
                            continue
                        else:
                            for flight in v:
                                # 获取PhoenixRuleId
                                phoenix_rule_id = str(flight['newLps']['PhoenixRuleId'])
                                icsf = flight['icsf']
                                # 通过icsf判断是否是共享航班,并且不是产品
                                if not icsf:
                                    print(f"phoenix_rule_id>>> {phoenix_rule_id}")
                                    flight_transfer, flight_type, platform = "", "", "yl"
                                    # 需要退改价格等数据,需要请求每个航班详情数据
                                    count += 1
                                    start_time = flight['dt'].split(" ")[1]
                                    end_time = flight['at'].split(" ")[1]
                                    plane_no = flight['fn']
                                    company = flight['asn']
                                    _from_city_code = flight['dac']
                                    _to_city_code = flight['aac']
                                    from_airport_name = flight['dasn']
                                    to_airport_name = flight['aasn']
                                    _from_city = get_city_from_airport(
                                        str(from_airport_name),
                                        self.base_path) if _from_city_code == "CQW" else from_city
                                    _to_city = get_city_from_airport(
                                        str(to_airport_name),
                                        self.base_path) if _to_city_code == "CQW" else to_city
                                    from_city_airport = get_full_airport(_from_city_code, self.base_path)
                                    to_city_airport = get_full_airport(_to_city_code, self.base_path)
                                    print(
                                        f"<<<from_airport: {_from_city_code}, to_airport: {_to_city_code} off_date: {flight_time}>>>")
                                    headers[
                                        'Referer'] = f"https://m.ly.com/kylintouch/sbook1_5?fromcitycode={from_city_code}&tocitycode={to_city_code}&childticket=0,0&fromairport{_from_city_code}=&toairport{_to_city_code}=&cabin=0&hasAirPort=3&RefId=10758821&bd_vid="
                                    # company_no = re.findall("^(.*?)\d+", str(plane_no), re.I)[0]
                                    company_no = str(plane_no)[0:2]
                                    plane_type = flight['amn']
                                    if self.has_node(flight, 'sc'):
                                        flight_transfer = flight['sc']
                                        flight_type = "经停"
                                    elif self.has_node(flight, "ps"):
                                        try:
                                            flight_transfer = flight['ps']['g5']['g5sc']
                                        except:
                                            flight_transfer = ""
                                            traceback.print_exc()
                                        flight_type = "联程"
                                    else:
                                        flight_transfer = ""
                                        flight_type = "直飞"
                                    metadata = {
                                        "flight_transfer": flight_transfer,
                                        "flight_type": flight_type,
                                        "off_date": flight_time,
                                        "from_city": _from_city,
                                        "from_city_code": _from_city_code,
                                        "to_city": _to_city,
                                        "to_city_code": _to_city_code,
                                        "plane_no": plane_no,
                                        "company": company,
                                        "company_no": company_no,
                                        "platform": platform,
                                        "start_time": start_time,
                                        "end_time": end_time,
                                        "create_time": create_time,
                                        "plane_type": plane_type,
                                        "from_city_airport": from_city_airport,
                                        "to_city_airport": to_city_airport,
                                        "count": count,
                                    }
                                    __data = self.parse_lowest_price(metadata)
                                    data_list.append(__data)
                    # 产品价格与非产品价格一起返回,批量插入
                    print(f"爬取数据 -> 起飞时间: {flight_time} OD:{from_city}:{from_city_code}={to_city}:{to_city_code}航班数>>>{len(data_list)}")
                    names = ['company', 'company_no', 'plane_no', 'start_time', 'end_time', 'from_city', 'from_city_code', 'to_city', 'to_city_code', 'create_time', 'discount', 'off_date', 'platform', 'price', 'flight_type', 'plane_type', 'flight_transfer', 'from_city_airport', 'to_city_airport', 'task_time', 'server_ip', 'flight_number', 'lep_price', 'is_meal', 'baggage']
                    # 将csv文件放入logs目录下
                    csv_file = os.path.join(self.ylLog.second_path, fr"{_from_city_code}-{_to_city_code}-{flight_time}-{ip_map[int(self.redisUtil.db)]}.csv")
                    print("***csv_file_name***", csv_file)
                    with open(csv_file, "w+", encoding="utf-8", newline='') as f:
                        f_csv = csv.writer(f)
                        f_csv.writerow(names)
                        f_csv.writerows(data_list)
                    self.end_time = time.time()
                    self.ylLog.info(f"爬取耗时{self.end_time - self.start_time}")
                    msg = f"起飞时间: {flight_time} OD:{from_city}:{from_city_code}={to_city}:{to_city_code}航班数>>>{count}"
                    self.ylLog.info(msg)
                    item = YlBatchItem(
                        from_city_code=_from_city_code,
                        to_city_code=_to_city_code,
                        off_date=flight_time,
                        server_ip=ip_map[int(self.redisUtil.db)],
                        csv_file_name=csv_file,
                        flight_number=len(data_list),
                    )
                    yield item
                else:
                    self.ylLog.info(f"OD:{from_city}:{from_city_code}={to_city}:{to_city_code}航班数0")
                    pass
            except Exception as e:
                traceback.print_exc()
                path = "/result/error_ua.txt"
                self.ylFile.createFile(path, userAgent + '\n')
                xmlpath = fr"/result/{from_city}({from_city_code})-{to_city}({to_city_code})-{flight_time}-exception.html"
                self.ylFile.createFile(xmlpath, response.body.decode(), model='w+')
                self.ylLog.info(f"{xmlpath}写入源码文件成功")
                pass
        else:
            self.fail += 1
            msg = f"状态码异常>>>{self.fail}, 状态码: {response.status}\n"
            self.ylLog.exception(msg)
            path = fr"/errorHtml/{from_city}-{to_city}-{flight_time}-status_error.html"
            self.ylFile.createFile(path, response.body.decode())



    '''
    @Description: 是产品价格的一个航班就请求详情链接,从经济舱的所有价格中找出非产品价格的并找到最低价格放入管道
    '''

    def parse_lowest_price(self, meta_data: dict) -> list:
        global gnjpapp_head, server_session_id, link_tracker_id, lep_price
        gnjpapp_head, server_session_id, link_tracker_id, lep_price = None, "", "", None
        self.ylLog.info("***解析产品价格航班***")
        from_city = meta_data['from_city']
        from_city_code = meta_data['from_city_code']
        to_city = meta_data['to_city']
        to_city_code = meta_data['to_city_code']
        off_date = meta_data['off_date']
        create_time = meta_data['create_time']
        plane_no = meta_data['plane_no']
        plane_type = meta_data['plane_type']
        start_time = meta_data['start_time']
        end_time = meta_data['end_time']
        flight_transfer = meta_data['flight_transfer']
        flight_type = meta_data['flight_type']
        company = meta_data['company']
        company_no = meta_data['company_no']
        platform = meta_data['platform']
        from_city_airport = meta_data['from_city_airport']
        to_city_airport = meta_data['to_city_airport']
        count = int(meta_data['count'])
        __from_city_code = self.airport_map[
            from_city_code] if from_city_code in self.air_list else from_city_code
        __to_city_code = self.airport_map[
            to_city_code] if to_city_code in self.air_list else to_city_code

        # redis中是否已保存cookie
        if self.redisUtil.hash_exist_key(f"ly:{self.now_date}-cookie", "cookies"):
            cookies = str(self.redisUtil.get(f"ly:{self.now_date}-cookie", "cookies"),
                          "utf-8")
            server_session_id, link_tracker_id, gnjpapp_head = self.get_cookie_params(cookies)
            ua = random.choice(user_agent_mobile)
            form_data = {
                "AirCode": plane_no[0:2],
                "Arrival": __to_city_code,
                "ArrivalName": get_airport(to_city_code, self.base_path).encode(
                    "utf-8").decode(
                    "latin1"),
                "Departure": __from_city_code,
                "DepartureDate": off_date + " " + start_time,
                "DepartureName": get_airport(from_city_code,
                                             self.base_path).encode(
                    "utf-8").decode(
                    "latin1"),
                "GetType": "0",
                "IsBaby": 0,
                "IsBook15": 1,
                "IsFromPhoenix": 1,
                "IsMuilteSite": 1,
                "ProductType": "1",
                "QueryType": "1",
                "SessionId": session_id,
                "TripType": "0",
                "flightno": plane_no,
                "linkTrackerId": link_tracker_id,
                "newCabinDeal": 2,
                "openid": "",
                "plat": int(gnjpapphead['tcplat']),
                "refid": "0",
                "unionid": ""
            }
            headers = self.get_headers_2(gnjpapphead, ua, link_tracker_id, session_id, cookies)
            headers['Referer'] = f'https://m.ly.com/touchbook/touch/sbook1_5?fromcitycode={from_city_code}&tocitycode={to_city_code}&childticket=0,0&fromairport={__from_city_code}&toairport=&cabin=0&hasAirPort=3&RefId=0&bd_vid='
            req_url = "https://m.ly.com/touchbook/flightApis/wx/flightbffquery/query/getkylinflightlist"
            try:
                with httpx.Client(headers=headers) as client:
                    res = client.post(url=req_url, json=form_data, timeout=30, follow_redirects=False)
                    if res.status_code in [200, 201]:
                        self.success_lowest += 1
                        self.ylLog.info(f"成功返回JSON数据>>>{self.success_lowest}")
                        data = json.loads(res.content.decode())
                        # 只取最低价格,所以只从经济舱里面取
                        economy_list = data['body']['newCabinList']['economyList']
                        sell_price, discount, price = [], [], []
                        price_dict = defaultdict()
                        for i, economy_cabin in enumerate(economy_list):
                            # 首先判断是不是产品,不是产品才进行比较出最低价
                            if str(economy_cabin['ruleId']).__eq__("00000"):
                                # 将最低价取出进行比较
                                sell_price.append(int(economy_cabin['clientTicketPrice']))
                                price_dict[int(economy_cabin['clientTicketPrice'])] = i
                            # 没有ruleId为00000的价格,筛选出限时特惠,成人特惠,婴儿不可预订的价格
                            elif len(economy_cabin['limitLabel']) == 0 or (
                                    economy_cabin['limitLabel'][0]['name'] == "限时特惠" or
                                    economy_cabin['limitLabel'][0]['name'] == "婴儿不可预订"
                            ):
                                sell_price.append(int(economy_cabin['clientTicketPrice']))
                                price_dict[int(economy_cabin['clientTicketPrice'])] = i
                            else:
                                continue
                        # 非空判断
                        if len(sell_price) == 0:
                            raise ValueError("No price!")
                        else:
                            # 升序排序, 排在第一个的为最低价
                            sell_price.sort(reverse=False)
                            index = price_dict[sell_price[0]]
                            price.append(str(sell_price[0]))
                            discount.append(economy_list[index]['roomDes'])
                            # 退改价格
                            try:
                                lep_price = economy_list[index]['lep']
                                # lep为空字符串, 取lrp
                                if lep_price == "":
                                    lep_price = economy_list[index]['lrp']
                            except:
                                print("err_from_city_code", from_city_code, "err_to_city_code", to_city_code, "err_off_date", off_date, "err_plane_no", plane_no, "err_economy_cabin", economy_list[index])
                                print(traceback.format_exc())
                            lep_price = int(lep_price) if lep_price is not None and lep_price != "" else None
                            # lep_price = "提前改期免费" if lep_price == 0 else f"退改¥{str(lep_price)}起"
                            # 餐食情况
                            is_meal = str(economy_list[index]['ml'])
                            # 托运行李额
                            baggage = int(economy_list[index]['baggage'])
                            # baggage = "无免费托运行李额" if baggage == 0 else f"托运行李额{str(baggage)}kg"
                            print("from_city_code", from_city_code, "from_city", from_city, "to_city_code",
                                  to_city_code,
                                  "to_city", to_city, "off_date", off_date,
                                  "plane_no", plane_no, "price", price, "discount", discount, "lep_price", lep_price,
                                  "is_meal", is_meal, "baggage", baggage, "from_city_airport", from_city_airport, "to_city_airport", to_city_airport, "create_time", create_time)
                            return [company, company_no, plane_no, start_time, end_time, from_city, from_city_code, to_city, to_city_code, create_time, str(discount[0]), off_date, platform, str(price), flight_type, plane_type, flight_transfer, from_city_airport, to_city_airport, self.task_time, ip_map[int(self.redisUtil.db)], count, lep_price, is_meal, baggage]
                    else:
                        self.fail += 1
                        msg = f"状态码异常>>>{self.fail}, 状态码: {res.status_code}\n"
                        self.ylLog.exception(msg)
                        path = fr"/errorHtml/{from_city}-{to_city}-{off_date}-status_error.html"
                        self.ylFile.createFile(path, res.content.decode())
            except:
                traceback.print_exc()
                path = "/result/error_ua.txt"
                self.ylFile.createFile(path, '\n')
                # -------------------d
                xmlpath = fr"/result/{from_city}({from_city_code})-{to_city}({to_city_code})-{off_date}-exception.html"
                self.ylFile.createFile(xmlpath, res.content.decode(), model='w+')
                self.ylLog.info(f"{xmlpath}写入源码文件成功")
                return []

