# -*- coding: utf-8 -*-
# 爬取艺龙网机票信息
import datetime
import re
import time
import pytz
import random
import scrapy
from flight_spider.ylutils.ylLog import YlLog
from flight_spider.ylutils.ylFile import YlFile
from flight_spider.ylutils import ylutil
from flight_spider.settings import user_agent_mobile
from flight_spider.YlSpiderItem import YlSpiderItem
from .bshead import create_bs_driver


class YlSpider(scrapy.Spider):
    name = 'ylSpider'
    allowed_domains = ['www.ly.com']
    start_urls = ['https://www.ly.com/']

    # redis_key = 'yl:start_urls'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        scrapy.Spider.__init__(self, self.name)
        self.driver = create_bs_driver()
        self.driver.set_page_load_timeout(20)
        self.file_name = kwargs.get('file_name')
        self.from_line = kwargs.get('from_line')
        self.to_line = kwargs.get('to_line')
        self.from_date = kwargs.get('from_date')
        self.to_date = kwargs.get('to_date')
        self.is_low_price = kwargs.get('is_low_price')
        self.task_time = kwargs.get('task_time')
        self.task_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:00:00")
        self.ylLog = YlLog()
        self.ylFile = YlFile()
        self.pc = 1
        self.success, self.total, self.fail, self.count, self.exception = 0, 0, 0, 0, 0
        print(self.file_name, self.from_line, self.to_line, self.from_date, self.to_date, self.is_low_price,
              self.task_time)

    def __del__(self):
        self.driver.quit()

    def start_requests(self):
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
            now_time = time.strftime("%F")
            print(from_city, from_city_code, to_city, to_city_code, now_time)
            if int(self.from_date) == 0 and int(self.to_date) == 0:
                days = [0]
            elif int(self.from_date) == -1 or int(self.to_date) == -1:
                days = range(15)
            else:
                days = range(int(self.from_date), (int(self.to_date) + 1))
            for j in days:
                flight_time = (datetime.datetime.strptime(now_time, "%Y-%m-%d") + datetime.timedelta(days=j)).strftime(
                    "%Y-%m-%d")
                self.ylLog.info(f"******起飞时间:{flight_time}******")
                self.ylLog.info(
                    f"采集OD:{from_city}:{from_city_code}={to_city}:{to_city_code}")
                ua = random.choice(user_agent_mobile)
                if self.is_low_price == '0':
                    metadata = {"from_city": from_city,
                                "to_city": to_city,
                                "from_city_code": from_city_code,
                                "to_city_code": to_city_code,
                                "index": int(i + 1),
                                "flight_time": flight_time,
                                'is_low_price': 0,
                                'dont_merge_cookies': True,
                                'user-agent': ua}
                else:
                    metadata = {"from_city": from_city,
                                "to_city": to_city,
                                "from_city_code": from_city_code,
                                "to_city_code": to_city_code,
                                "index": int(i + 1),
                                "flight_time": flight_time,
                                'is_low_price': 1,
                                'dont_merge_cookies': True,
                                'user-agent': ua}
                yield scrapy.Request(
                    url=f"https://www.ly.com/flights/itinerary/oneway/{from_city_code}-{to_city_code}?from={from_city}&to={to_city}&date={flight_time}&fromairport={from_city_code}&toairport={to_city_code}&p=465&childticket=0,0",
                    callback=self.parse, dont_filter=True, meta=metadata)
        self.driver.quit()

    def parse(self, response):
        self.total += 1
        self.ylLog.info(f"采集总次数:{self.total}")
        from_city = response.meta['from_city']
        from_city_code = response.meta['from_city_code']
        to_city = response.meta['to_city']
        to_city_code = response.meta['to_city_code']
        flight_time = response.meta['flight_time']
        userAgent = response.meta['user-agent']
        if response.url == "**":
            self.fail += 1
            msg = f"响应异常,OD为:{from_city}:{from_city_code}={to_city}:{to_city_code}>>>次数:{self.fail}\n"
            self.ylLog.exception(f"{msg}")
        elif response.status in [200, 201]:
            self.count += 1
            self.ylLog.info(f"成功返回页面>>>{self.count}")
            self.ylLog.info("响应成功率: %4f" % (self.count / self.total))

            list = response.url.split('&')
            flight_time = list[2].split('date=')[-1]

            from_city = response.meta['from_city']
            from_city_code = response.meta['from_city_code']
            to_city = response.meta['to_city']
            to_city_code = response.meta['to_city_code']
            create_time = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d  %H:%M:%S')
            # -----手机h5端
            if ylutil.isElementPresent(self.driver, "xpath", '//div[@class="calendar-scroll-container"]'):
                self.ylLog.info("mobile html")
                try:
                    flights = response.xpath('.//div[@class="flight-desc"]')
                    self.ylLog.info("flights length is " + str(len(flights)))
                    for f in flights:
                        start_time = f.xpath(
                            './/div[@class="flight-info"]/div[@class="flight-left"]/div[@class="bc-info"]/div[@class="bc-info-time"]//text()').extract_first(
                            '').strip()

                        try:
                            flight_type = f.xpath(
                                './/div[@class="flight-info"]/div[@class="flight-left"]/div[@class="fly-arrowCenter"]/div[@class="fly-arrows"]/span[@class="fly-turn"]//text()').extract_first(
                                '')
                            if flight_type.strip() == '':
                                flight_type = '直飞'
                        except Exception as e:
                            flight_type = '直飞'
                            pass
                        end_time = f.xpath(
                            './/div[@class="flight-info"]/div[@class="flight-left"]/div[@class="ac-info"]/div[@class="ac-info-time"]//text()').extract_first(
                            '').strip()
                        price = f.xpath(
                            './/div[@class="flight-info"]/div[@class="flight-right"]/div[@class="right-price"]/span[@class="re-price"]//text()').extract()
                        discount = f.xpath(
                            './/div[@class="flight-info"]/div[@class="flight-right"]/div[@class="remain-label cabin-lable"]/span//text()').extract()
                        compFligtNo = f.xpath(
                            './/div[@class="flight-service-label"]/div[@class="flight-label-con"]/div[@class="label-com"]//text()').extract()

                        comp_flight_no = compFligtNo[0].strip()
                        company = re.search(r'[\u4e00-\u9fa5]+', comp_flight_no).group()
                        plane_no = comp_flight_no.replace(company, '')
                        company_no = plane_no[0:2]
                        plane_type = compFligtNo[2].strip()
                        discount = str(discount)
                        price = str(price)
                        flight_transfer = []
                        flight_transfer = str(flight_transfer)
                        print(start_time, flight_type, end_time, price, discount, company, company_no, plane_no,
                              plane_type)
                        item = YlSpiderItem(
                            off_date=flight_time,
                            from_city=from_city,
                            from_city_code=from_city_code,
                            to_city=to_city,
                            to_city_code=to_city_code,
                            plane_no=plane_no,
                            company=company,
                            company_no=company_no,
                            platform='yl',
                            start_time=start_time,
                            end_time=end_time,
                            price=price,
                            discount=discount,
                            create_time=create_time,
                            plane_type=plane_type,
                            flight_type=flight_type,
                            flight_transfer=flight_transfer,
                            task_time=self.task_time
                        )
                        # print(item)
                        yield item
                except Exception as e:
                    path = "/result/error_ua.txt"
                    self.ylFile.createFile(path, userAgent + '\n')
                    self.ylLog.info(f"{path}写入源码文件成功")
                    # -------------------
                    xmlpath = fr"/result/{from_city}({from_city_code})-{to_city}({to_city_code})-{flight_time}-normal.html"
                    self.ylFile.createFile(xmlpath, response.body.decode(), model='w+')
                    self.ylLog.info(f"{xmlpath}写入源码文件成功")
                    pass
            # pc HTML5端
            elif ylutil.isElementPresent(self.driver, "xpath", '//div[@class="head-calendar-scroll"]'):
                self.ylLog.info("pc html")
                path = "/result/pc_ua.txt"
                self.ylFile.createFile(path, userAgent + '\n')
                self.ylLog.info(f"{path}写入源码文件成功")
                # -------------------
                xmlpath = fr"/result/{from_city}({from_city_code})-{to_city}({to_city_code})-{flight_time}-normal.html"
                self.ylFile.createFile(xmlpath, response.body.decode(), model='w+')
                self.ylLog.info(f"{xmlpath}写入源码文件成功")
                flights = response.xpath('//div[@class="flight-item"]')
                msg = f"{from_city}到{to_city}页面航班数:{len(flights)}\n"
                self.ylLog.info(msg)
                for f in flights:
                    flight_transfer = []
                    try:
                        flight_transfer = f.xpath('.//div[@class="logo-small-side"]/span/text()').extract()
                    except Exception as e:
                        pass
                    flight_name = f.xpath('.//p[@class="flight-item-name"]/text()').extract_first('')
                    plane_type = f.xpath('.//span[@class="flight-item-type"]/text()').extract_first('')
                    start_time = f.xpath('.//div[contains(@class,"f-startTime")]//strong/text()').extract_first('')
                    end_time = f.xpath('.//div[contains(@class,"f-endTime")]//strong/text()').extract_first('')
                    price_d = f.xpath('.//div[@class="head-prices"]//strong//text()').extract_first('').replace('¥', '')
                    flight_type = f.xpath('.//div[@class="trigger"]/em/text()').extract()
                    # print('----')
                    # print(flight_type)
                    # print('----')
                    discount_d = f.xpath('.//div[@class="head-prices"]//i[@class="gray-style"]//text()').extract_first()
                    discount = [discount_d]
                    price = [price_d]
                    discount_price_list = f.xpath(
                        './/div[@class="flight-item-cabins-lists"]//div[@class="cabins-item"]')

                    for list in discount_price_list:
                        all_test = list.xpath('./text()').extract()
                        price_li = list.xpath('.//div[@class="price-show"]//strong/text()').extract_first('').replace(
                            '¥', '')
                        discount_li = list.xpath('.//div[@class="price-show"]//b/text()').extract_first('')
                        price.append(price_li)
                        discount.append(discount_li)

                    a, b = flight_name.split('航空')
                    company = a + '航空'
                    plane_no = b
                    company_no = b[:2]
                    if len(flight_type) > 0:
                        flight_type = str(flight_type)
                    else:
                        flight_type = '直飞'

                    if len(flight_transfer) > 0:
                        d_list = []
                        for i in flight_transfer:
                            print(i)
                            p = i.strip()
                            d_list.append(p)
                            print(p)
                            flight_transfer = str(d_list)
                    else:
                        flight_transfer = str(flight_transfer)

                    discount = str(discount)
                    price = str(price)
                    item = YlSpiderItem(
                        off_date=flight_time,
                        from_city=from_city,
                        from_city_code=from_city_code,
                        to_city=to_city,
                        to_city_code=to_city_code,
                        plane_no=plane_no,
                        company=company,
                        company_no=company_no,
                        platform='yl',
                        start_time=start_time,
                        end_time=end_time,
                        price=price,
                        discount=discount,
                        create_time=create_time,
                        plane_type=plane_type,
                        flight_type=flight_type,
                        flight_transfer=flight_transfer,
                        task_time=self.task_time
                    )
                    # print(item)
                    yield item
        else:
            self.fail += 1
            msg = f"状态码异常>>>{self.fail}, 状态码: {response.status}\n"
            self.ylLog.exception(msg)
            path = fr"/errorHtml/{from_city}-{to_city}-{flight_time}-status_error.html"
            self.ylFile.createFile(path, response.body.decode)
