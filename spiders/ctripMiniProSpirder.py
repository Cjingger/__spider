# !/usr/bin/python3
# -*- coding: utf-8 -*-
# 爬取携程网小程序信息
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


class MiniProCtripSpider(scrapy.Spider):
    name = 'ctrip'
    allowed_domains = ['m.ctrip.com']
    start_urls = ['https://m.ly.com/']

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
        }
        # 一市两场三字码
        self.air_list = ["PEK", "PKX", "PVG", "SHA", "CTU", "TFU", "ZYI", "WMT"]
        self.redis_items = self.ylFile.getConfigDict("Redis-Config-pro")
        self.flight_infos = {}

    def start_requests(self):
        pass