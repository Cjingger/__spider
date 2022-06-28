# !/usr/bin/ven/python3
# -*- coding: utf-8 -*-

import shutil

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from selenium.webdriver.chrome.options import Options
from scrapy.http import HtmlResponse
from scrapy import signals
from scrapy import spiders
from scipy import signal
# from pypinyin import pinyin
# from settings import user_agent_list
import re
import random, datetime
import base64
from PIL import Image
from io import BytesIO
import time
import requests
import io
import cv2, os
import numpy as np
import requests
from selenium.common.exceptions import NoSuchElementException
from lxml import etree
import traceback
from paddleocr import PaddleOCR, draw_ocr
from functools import wraps

# Paddleocr目前支持的多语言语种可以通过修改lang参数进行切换
# 例如`ch`, `en`, `fr`, `german`, `korean`, `japan`
ocr = PaddleOCR(use_angle_cls=True, lang="ch")  # need to run only once to download and load model into memory


# url = "http://192.168.2.115:8002/up_photo"  # 服务器上的ip地址


def timer(func):
    '''
    @wraps 计时器
    '''

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start = datetime.datetime.now()
        res = func(self, *args, **kwargs)
        end = datetime.datetime.now()
        print(f'<{func.__name__}>方法耗时: {(end - start).total_seconds()}')
        return res

    return wrapper


class ClickVerfication:

    def __init__(self, url, detect_api):
        '''
        :param url: 目标网页url
        :param detect_api: 识别图片文字以及所在位置的api
        '''
        self.url = url
        self.detect_api = detect_api
        self.bg_img, self.small_img = '', ''
        self.total, self.sucess, self.fail = 0, 0, 0

    def isElementPresent(self, driver, by, value):
        """
        用来判断元素标签是否存在，
        """
        try:
            element = driver.find_element(by=by, value=value)
        # 原文是except NoSuchElementException, e:
        except NoSuchElementException as e:
            # 发生了NoSuchElementException异常，说明页面中未找到该元素，返回False
            return False
        else:
            # 没有发生异常，表示在页面中找到了该元素，返回True
            return True

    def base64_to_img(self, base64_str, img_name):
        '''
        输入为base64格式字符串，输出为PIL格式图片
        '''
        byte_data = base64.b64decode(base64_str)  # base64转二进制
        image = Image.open(BytesIO(byte_data))  # 将二进制转为PIL格式图片
        image.save(f'{img_name}.png')
        print("<<<<保存图片成功>>>>")

    def download_small_img(self, html: str, img_name):
        '''
        下载小文字图片
        :param html: html页面的text
        :return:
        '''

        parser = etree.HTMLParser(encoding="UTF-8")
        html = etree.HTML(html, parser=parser)
        # html = etree.parse(fr'{html}', parser=parser)
        try:
            small_base64_img = re.findall(r'^data:image/jpg;base64,(.*?)$',
                                          html.xpath('//div[@class="cpt-choose-top"]/img[@class="cpt-small-img"]/@src')[
                                              0], re.S)[0]
            # print("small_base64_img", small_base64_img)
            bg_img_path = os.path.abspath(
                '.') + os.path.sep + 'imgs' + os.path.sep + 'small_imgs' + os.path.sep + f'small_img_{img_name}'
            self.base64_to_img(small_base64_img, bg_img_path)
            return bg_img_path
        except:
            traceback.print_exc()
            return False

    def download_bg_img(self, html: str, img_name):
        '''
        下载验证码大图
        '''
        parser = etree.HTMLParser(encoding="UTF-8")
        html = etree.HTML(html, parser=parser)
        # html = etree.parse(fr'{html}', parser=parser)
        try:
            bg_base64_img = re.findall(r'^data:image/jpg;base64,(.*?)$',
                                       html.xpath('//div[@class="cpt-big-box"]/img[@class="cpt-big-img"]/@src')[0],
                                       re.S)[0]
            # print("bg_base64_img", bg_base64_img)
            bg_img_path = os.path.abspath(
                '.') + os.path.sep + 'imgs' + os.path.sep + 'bg_imgs' + os.path.sep + f'bg_img_{img_name}'
            self.base64_to_img(bg_base64_img, bg_img_path)
            return bg_img_path
        except:
            traceback.print_exc()
            return False

    def identify_bg_img(self, words):
        '''
        识别大背景文字以及对应的坐标
        :param words 小图识别出的文字,用来确定文字对应的位置
        :return:
        '''
        print("***开始识别大图***")
        try:
            all_words_pos, need_words_pos = [], []
            # 识别结果
            res = {}
            # print(res)
            print("#" * 16)
            for item in res['words_result']:
                # 文字及位置信息
                print(item.get('chars'))
                all_words_pos.extend(item.get('chars'))
            for word in words:
                for item in all_words_pos:
                    if word == item['char']:
                        need_words_pos.append(item)

            print(need_words_pos)
            print("#" * 16)
            print("***大图识别完成***")
            return need_words_pos
        except:
            traceback.print_exc()

    def click_words(self, browser, words_pos_info: list):
        '''
        按顺序点击大背景图片中的文字
        :return:
        '''
        bg_img_ele = browser.find_element('xpath', '//div[@class="cpt-big-box"]/img[@class="cpt-big-img"]')
        for pos in words_pos_info:
            ActionChains(browser).move_to_element_with_offset(bg_img_ele, xoffset=pos[0],
                                                                   yoffset=pos[1] + 10).click().perform()
            time.sleep(0.5)

    def get_track(self, distance):
        """
        根据偏移量获取移动轨迹
        :param distance:偏移量
        :return:移动轨迹
        """
        # 移动轨迹
        track = []
        # 当前位移
        current = 0
        # 减速阈值
        mid = distance * 4 / 5
        # 计算间隔
        t = random.randint(2, 4) / 4
        # 初速度
        v = 0

        while current < distance:
            if current < mid:
                # apositive = [2.2, 2.3, 2.5, 2.7, 2.9]
                a = 20
            else:
                # anegitive = [-3.0, -2.8, -2.1, -2.2, -2.5]
                a = -6
            # 初速度v0
            v0 = v
            # 当前速度v = v0 + at
            v = v0 + a * t
            # 移动距离x = v0t + 1/2 * a * t^2
            move = v0 * t + 1 / 2 * a * t * t
            # 当前位移
            current += move
            # 加入轨迹
            track.append(round(move))
        return track

    def return_res(self, img_small_path, res):
        '''
        根据图片信息返回位置坐标
        '''
        res_box = []
        img_small = cv2.imread(img_small_path)
        img_small = cv2.pyrUp(img_small)
        img_small = cv2.pyrUp(img_small)
        result = ocr.ocr(img_small, cls=True)
        for line in result:
            print(line)
            print("输出：", line[1][0])
            ss = line[1][0]
            for i in range(len(ss)):
                for j in res['content']:
                    if j['text'] == ss[i]:
                        res_box.append(j['cord'])
        print("res_box", res_box)
        return res_box

    @timer
    def click_vertification(self, browser):
        '''
        通过识别的大小图位置坐标依次点击点选验证码
        '''
        print("***出现点选验证码***")
        _html = browser.page_source
        img_name = random.choice([i for i in range(1000)])
        self.bg_img, self.small_img = self.download_bg_img(_html, img_name), self.download_small_img(
            _html, img_name)
        if self.bg_img and self.small_img:
            data = {'path': '/testbg'}
            files = {'photo': open(fr'{self.bg_img}.png', 'rb'),
                     'small_photo': open(fr'{self.small_img}.png', 'rb')}
            res = requests.request("POST", url=self.detect_api, files=files, data=data, headers={'Connection': 'close'})
            # 返回的坐标列表pos_info
            res_pos_info = res.json()
            print(res.json())
            # 提交之前先判断一下,大小图字数是否一致,若不等,重新生成图片,重新识别
            while res_pos_info is None:
                browser.find_elements_by_xpath(
                    '//div[@class="cpt-choose-refresh-outer"]/a[@class="cpt-logo cpt-choose-refresh"]').click()
                time.sleep(2)
                img_name = random.choice([i for i in range(1000)])
                if self.download_bg_img(_html, img_name) and self.download_small_img(_html, img_name):
                    res = requests.request("POST", url=self.detect_api, files=files, data=data,
                                           headers={'Connection': 'close'})
                    # 返回的坐标列表pos_info
                    res_pos_info = res.json()
                else:
                    print("下载图片失败,重试")
                    return self.main(browser)
            print("匹配文字成功，开始点击")
            self.total += 1
            self.click_words(browser, res_pos_info['content'])
            browser.find_element('xpath',
                                      '//div[@class="cpt-sub-box"]/a[@class="cpt-logo cpt-choose-submit"]').click()
            time.sleep(2)
            outerHTML = browser.find_element('xpath',
                                                  '//div[@id="list-captcha-choose"]/div[@class="cpt-choose-bg"]').get_attribute(
                'outerHTML')
            # print("outerHTML", outerHTML)
            if "block" in str(outerHTML):
                print("***失败,重试***")
                self.fail += 1
                return self.click_vertification(browser)
            else:
                print("点选验证成功!!!")
                self.sucess += 1
                print(f"点选验证成功率: {round(self.sucess / self.total, 4)}")
                return True

    def main(self, browser):
        '''
        :param browser: 模拟浏览器驱动
        :param url: 目标网页url
        :return:
        '''
        browser.get(self.url)
        browser.implicitly_wait(3)
        try:
            # 首先判断点击疫情提醒'知道了'按钮
            if self.isElementPresent(browser, 'xpath', '//div[@class="pop-button-content"]'):
                btn_content = browser.find_element('xpath', '//div[@class="pop-button-content"]')
                if btn_content.text == "知道了":
                    btn_content.click()
                    print("***已点击<知道>按钮A***")
            time.sleep(1)
            if self.isElementPresent(browser, 'xpath', '//div[@class="pop-button-content"]'):
                btn_content = browser.find_element('xpath', '//div[@class="pop-button-content"]')
                if btn_content.text == "知道了":
                    btn_content.click()
                    print("***已点击<知道>按钮B***")
            # 接着滑动滑块验证码
            if (self.isElementPresent(browser, 'xpath', '//div[@class="pop-drag-verify"]')) or \
                    (self.isElementPresent(browser, 'xpath', '//div[@class=" cpt-drop-box"]')):
                print("***存在滑块验证码***")
                btn = browser.find_element('xpath', '//div[@class="cpt-drop-btn"]')
                bar = browser.find_element('xpath', '//div[@class="cpt-bg-bar"]')
                width = bar.size['width'] - btn.size['width']
                height = bar.size['height']
                print('width', width)
                print('height', height)
                tracks = self.get_track(bar.size['width'])
                start = time.time()
                ActionChains(browser).click_and_hold(btn).perform()
                for track in tracks:
                    ActionChains(browser).move_by_offset(xoffset=track, yoffset=0).perform()
                ActionChains(browser).release().perform()
                end = time.time()
                print(f"滑块耗时: {end - start}")
                time.sleep(1)
                # 判断滑块验证是否成功
                if self.isElementPresent(browser, 'xpath',
                                         '//div[@class="cpt-big-box"]/img[@class="cpt-big-img"]') and \
                        (browser.find_element('xpath',
                                                   '//div[@class="cpt-big-box"]/img[@class="cpt-big-img"]').get_attribute(
                            'src') is not ""):
                    print("***滑动验证成功***")
                    # 滑块验证成功,进行点选验证码验证
                    # 不成功,重试
                    if self.click_vertification(browser):
                        os.remove(fr'{self.bg_img}.png'), os.remove(fr'{self.small_img}.png')

                else:
                    print("***没有出现点选验证码***")
            else:
                print("***没有验证码***")
                pass
        except:
            print(traceback.format_exc())
        finally:
            browser.quit()


class CtripSpiderMiddleware(object):

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        # crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)

        return s

    def spider_opened(self, spider):
        # chorme_options = Options()
        # chorme_options.add_argument("--headless")
        # chorme_options.add_argument("--disable-gpu")
        # prefs = { "profile.managed_default_content_settings.images": 2 }
        # chorme_options.add_experimental_option("prefs", prefs)
        # chorme_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        # self.browser = webdriver.Chrome(options=chorme_options)
        spider.logger.info('Spider opened: %s' % spider.name)

    # def spider_closed(self, spider):
    #     self.browser.quit()

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_request(self, request, spider):
        detect_url = "http://192.168.3.68:8000/up_photo"
        clickVerfication = ClickVerfication(spider.url, detect_url)
        if spider.name == 'ctripSpider' and request.meta.get('is_low_price') == 1:
            # spider.driver.refresh()
            try:
                clickVerfication.main(spider.driver)

            except Exception as e:
                print(e)
            time.sleep(1)
            return HtmlResponse(
                url=spider.driver.current_url,
                body=spider.driver.page_source,
                request=request,
                encoding='utf-8',
            )
        elif spider.name == 'ylSpider' and request.meta.get('is_low_price') == 0:
            spider.driver.get(request.url)
            try:
                clickVerfication.main(spider.driver)
            except Exception as e:
                print(e)
            time.sleep(1)
            return HtmlResponse(
                url=spider.driver.current_url,
                body=spider.driver.page_source,
                request=request,
                encoding='utf-8',
            )


# class RandomUserAgent(object):
#
#     def process_request(self, request, spider):
#         # f = Factory.create()
#         # ua = f.user_agent()
#         # ua = UserAgent()
#         # ua = ua.random
#         ua = random.choice(user_agent_list)
#         ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
#         print(ua)
#         request.headers.setdefault('User-Agent',ua)
#         # print(request.headers.setdefault('User-Agent',ua))
#         return None

class MyIPProxyMiddlware(object):
    """
    ip 代理池
    """

    def process_request(self, request, spider):
        # 从list中选取ip,设置到request请求中
        IP_PROXY_LIST = []
        with open('IPProxy.txt', 'r') as f:
            for line in f:
                line = line.strip()
                IP_PROXY_LIST.append(line)
        ip_proxy = random.choice(IP_PROXY_LIST)
        if ip_proxy:
            request.meta['proxies'] = ip_proxy
            print(f"IP_PROXY:{ip_proxy}")

    def process_exception(self, request, exception, spider):
        print(f"spider:{spider.name}")


# def maintest(browser):
#     if browser == "firefox":
#         browser1 = webdriver.Firefox(executable_path='/Users/haoyu/Downloads/geckodriver')
#         browser1.set_window_size(800, 600)
#         browser1.get(
#             "https://www.ly.com/flights/itinerary/oneway/SHA-PEK?date=2021-12-11&from=%E4%B8%8A%E6%B5%B7&to=%E5%8C%97%E4%BA%AC&fromairport=&toairport=&p=465&childticket=0,0")
#         main(browser1)
#     elif browser == "chrome":
#         browser = webdriver.Chrome()
#         browser.set_window_size(800, 724)
#         browser.get(
#             "https://www.ly.com/flights/itinerary/oneway/SHA-PEK?date=2021-12-11&from=%E4%B8%8A%E6%B5%B7&to=%E5%8C%97%E4%BA%AC&fromairport=&toairport=&p=465&childticket=0,0")
#         main(browser)
#     if browser == None:
#         exit()


def __del__():
    print("del")


if __name__ == '__main__':
    # path = r"/Users/haoyu/Documents/chromedriver"
    # # slider_verification_code(browser, 0)
    # # browser.maximize_window()
    # timestart = time.time()
    from flight_spider.spiders.bshead import create_bs_driver

    url = 'https://m.ctrip.com/html5/flight/swift/domestic/CKG/HGH/2022-06-22?dfilter='
    img_url = "http://192.168.3.68:8000/up_photo"
    # # url = 'https://m.ctrip.com/html5/flight/pages/first?dcity=CGQ&dcityName=%E9%95%BF%E6%98%A5&acity=CZX&acityName=%E5%B8%B8%E5%B7%9E&ddate=2022-06-20&regionType=DOMESTIC'

    clickVerfication = ClickVerfication(url, img_url)
    for i in range(10):
        browser = create_bs_driver(headless=True)
        clickVerfication.main(browser)
        time.sleep(1)

