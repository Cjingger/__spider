import os
import random
import time, datetime
import traceback

from loguru import logger
from scrapy import signals
from scrapy.core.downloader.handlers.http11 import TunnelError
from scrapy.http import HtmlResponse
from selenium.webdriver.common.action_chains import ActionChains
from twisted.internet import defer
from twisted.internet.error import TimeoutError, DNSLookupError, \
    ConnectionRefusedError, ConnectionDone, ConnectError, \
    ConnectionLost, TCPTimedOutError
from twisted.web.client import ResponseFailed
from urllib3.exceptions import HTTPError
from flight_spider.verifyImage import VerifyImage
from flight_spider.ylutils import ylutil
from flight_spider.redisUtil import RedisUtil


class YlSpiderMiddleware(object):

    def __init__(self):
        self.verifyImage = VerifyImage()
        self.logger = self.verifyImage.ylLog
        self.total, self.success, self.fail = 0, 0, 0
        self.ALL_EXCEPTIONS = (HTTPError, defer.TimeoutError, TimeoutError, DNSLookupError,
                               ConnectionRefusedError, ConnectionDone, ConnectError,
                               ConnectionLost, TCPTimedOutError, ResponseFailed,
                               IOError, TunnelError)

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)

        return s

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)

    def spider_closed(self, spider):
        # spider.driver.quit()
        # print("******driver退出******")
        pass

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        if response is None:
            self.fail += 1
            spider.logger.info(f"响应失败>>>>>>{self.fail}")

        return response

    def process_request(self, request, spider):
        if (spider.name == 'ylSpider') or (spider.name == 'ylSpiderTest') and (request.meta.get('is_low_price')) == 1:
            start = time.time()
            # spider.driver.implicitly_wait(random.choice([i for i in range(3, 6)]))
            spider.driver.get(request.url)
            time.sleep(2)
            try:
                # clf = isElementPresent(spider.driver, "xpath",
                #                        '//img[@id="dx_captcha_basic_slider-img-normal_1"]')
                # 如果验证码所在overlay的div元素可见,则证明还存在验证码
                overlay = ylutil.isElementPresent(spider.driver, "xpath",
                                                  '//div[@class="dx_captcha_loading_overlay"]')
                print("*" * 30)
                if overlay:
                    print('存在验证码！')
                    self.verifyImage.main(spider.driver)
                    time.sleep(1)
                    spider.driver.refresh()
                    # 滑动验证码后验证是否成功，如果不再出现滑块div则成功
                    time.sleep(1)
                    overlay = ylutil.isElementPresent(spider.driver, "xpath",
                                                      '//div[@class="dx_captcha_loading_overlay"]')
                    if overlay:
                        print("******滑动失败******")
                        self.verifyImage.download_fail_imgs(spider)
                        refreshbtn = spider.driver.find_element_by_xpath('//div[@id="dx_captcha_basic_icon-btns_1"]')
                        refreshbtn.click()
                        print("***刷新验证码***")
                        self.verifyImage.main(spider.driver)
                        time.sleep(1)
                        spider.driver.refresh()
                        time.sleep(1)
                        overlay = ylutil.isElementPresent(spider.driver, "xpath",
                                                          '//div[@class="dx_captcha_loading_overlay"]')
                        if overlay:
                            print("******滑动失败******")
                            self.verifyImage.download_fail_imgs(spider)
                            pass
                        else:
                            self.success += 1
                        self.total += 1
                        print("滑块验证成功率 %4f" % (self.success / self.total))
                    else:
                        print("滑动验证成功")
                        self.success += 1
                    self.total += 1
                    print("滑块验证成功率 %4f" % (self.success / self.total))
                    time.sleep(1)
                else:
                    print("不存在验证码")
                    # time.sleep(2)
            except Exception as e:
                # logger.debug(e)
                traceback.print_exc()
            end = time.time()
            print(f"滑块耗时: {end - start}")
            return HtmlResponse(
                url=spider.driver.current_url,
                body=spider.driver.page_source,
                request=request,
                encoding='utf-8',
            )
        elif (spider.name == 'ylSpider') or (spider.name == 'ylSpiderTest') and (request.meta.get('is_low_price')) == 0:
            spider.driver.get(request.url)
            spider.driver.implicitly_wait(6)
            try:
                notice = ylutil.isElementPresent(spider.driver, "xpath", '//div[@class="notice-bottom"]')
                if notice:
                    node_btn = spider.driver.find_element_by_xpath('//div[@class="notice-bottom"]/div[@class="btn"]')
                    ActionChains(spider.driver).click(node_btn).perform()
                    print("点击知道了")
                spider.driver.find_element_by_class_name("btn-select").click()
                time.sleep(2)

                clf = ylutil.isElementPresent(spider.driver, "xpath",
                                              '//img[@id="dx_captcha_basic_slider-img-normal_1"]')
                print("*" * 30)
                if clf:
                    print('存在验证码！')
                    self.verifyImage.main(spider.driver)
                    time.sleep(3)
                    # 滑动验证码后验证是否成功，如果不再出现滑块div则成功
                    bar = ylutil.isElementPresent(spider.driver, "xpath",
                                                  '//div[@id="dx_captcha_basic_bar_1"]')
                    time.sleep(2)
                    if bar:
                        self.logger.info("******滑动失败******")
                        self.verifyImage.download_fail_imgs(spider)
                        self.verifyImage.main(spider.driver)
                        time.sleep(1)
                        spider.driver.refresh()
                        time.sleep(1)
                        if bar:
                            self.logger.info("******滑动失败******")
                            self.verifyImage.download_fail_imgs(spider)
                            pass
                        else:
                            self.logger.info("滑动验证成功")
                            self.success += 1
                        self.total += 1
                        self.logger.info("滑块验证成功率 %4f" % (self.success / self.total))
                        time.sleep(1)
                    else:
                        self.logger.info("滑动验证成功")
                        self.success += 1
                    self.total += 1
                    self.logger.info("滑块验证成功率 %4f" % (self.success / self.total))
                    time.sleep(1)
                else:
                    print("不存在验证码")
                li_list = spider.driver.find_elements_by_class_name("btn-select")
                for li in li_list[1:]:
                    ActionChains(spider.driver).click(li).perform()
                    time.sleep(1)
            except Exception as e:
                self.logger.debug(e)
            return HtmlResponse(
                url=spider.driver.current_url,
                body=spider.driver.page_source,
                request=request,
                encoding='utf-8',
            )

    def process_exception(self, request, exception, spider):
        # 捕获几乎所有的异常
        if isinstance(exception, self.ALL_EXCEPTIONS):
            # 在日志中打印异常类型
            self.logger.info("存在异常>>>:{}".format(exception))
            # 随意封装一个response，返回给spider
            response = HtmlResponse(url="**")
            # response = HtmlResponse(url=request.url)
            return response
        self.logger.info("不包含的异常: %s" % exception)


class MyIPProxyMiddlware(object):
    """
    ip 代理池
    """

    def __init__(self):
        self._basePath = os.path.abspath('.')
        print(self._basePath)

    # @classmethod
    # def from_crawler(cls, crawler):
    #     return cls(ip=crawler.settings.get['PEOXIES'])

    def process_request(self, request, spider):
        # redisUtil = RedisUtil(db=1)
        # now_date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H-00-00')
        # ip_proxy = redisUtil.sranmember(f'proxies-{now_date}')
        # if ip_proxy:
        #     # request.meta['proxies'] = ip_proxy
        #     request.meta['REMOTE_ADDR'] = ip_proxy
        #     print(f"IP_PROXY: {ip_proxy}")
        # 从list中选取ip,设置到request请求中
        IP_PROXY_LIST = []
        with open(r'../../../ctripSpider/IPProxy.txt', 'r') as f:
            for line in f:
                line = line.strip()
                IP_PROXY_LIST.append(line)
        ip_proxy = random.choice(IP_PROXY_LIST)
        if ip_proxy:
            request.meta['proxies'] = ip_proxy
            print(f"IP_PROXY:{ip_proxy}")

    def process_exception(self, request, exception, spider):
        print(f"spider:{spider.name}")
