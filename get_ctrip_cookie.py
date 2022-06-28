# -*-encoding: utf-8 -*-
# !/bin/usr/python3

# !/usr/bin/python3
# -*- encoding: utf-8 -*-
import mitmproxy.http
from mitmproxy import ctx
import traceback, os
from mitmdump import DumpMaster, Options
from redis_util import RedisUtil
import datetime

redisUtil = RedisUtil()


class catch_cookies(object):
    '''
    利用mitmproxy模拟一个完整的HTTP通信周期获取\修改数据
    '''

    def __init__(self):
        self.cookie = ""
        self.num = 0
        # self.filter_host, self.url_path 做加密处理
        self.filter_host = "m.ctrip.com"
        # self.url_path = "https://m.ctrip.com/restapi/soa2/14022/flightListSearch"
        # self.url_path = "https://m.ctrip.com/restapi/soa2/14488/flightList"
        self.url_path = "https://m.ctrip.com/html5/flight/swift/domestic"
        # self.url_path = "m.ctrip.com/html5/flight/pages/first"

    # 与服务器建立代理连接,仅仅是client与proxy连接,不会触发request,response以及其他http事件
    def http_conn(self, flow: mitmproxy.http.HTTPFlow):
        pass

    # 来自client的 HTTP 请求的头部被成功读取, body还是空的
    def request_headers(self, flow: mitmproxy.http.HTTPFlow):
        pass

    # 来自client的 HTTP 请求被成功完整读取(包括请求头cookie以及body)
    def request(self, flow: mitmproxy.http.HTTPFlow):
        self.num += 1
        if self.num > 2:
            pass
        if (flow.request.host == self.filter_host) and (self.url_path in str(flow.request.url)):
            ctx.log.info(u"处理第 %d 个请求" % self.num)
            print("处理第 %d 个请求" % self.num)
            try:
                self.cookie = ""
                for key, value in flow.request.cookies.items():
                    # if "wengine_vpn_ticket" not in key:
                    #     pass
                    # else:
                    coo = "{}={}; ".format(key, value)
                    self.cookie += coo
                    # self.cookie += flow.request.cookies[i]
                self.cookie = str(self.cookie).strip('; ')
                print("cookie", self.cookie)
                now_date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
                redisUtil.set(f"ctrip:{now_date}-cookie", "cookies", self.cookie)
                redisUtil.set_expire(f'ctrip:{now_date}-cookie', 60 * 60)
                print("***cookie捕获成功***")
                # 将cookie写进文本里,再写一个程序读取,直接在此模块导入redis会报没有redis模块(未解决)
                with open(r'./cookies.txt', 'w', encoding="utf-8") as file:
                    file.write(self.cookie)
                    print("cookie写入成功\033[0m")
            except:
                print(traceback.print_exc())

        else:
            return

    # 来自server的 HTTP的响应头部被成功读取, body还是空的
    def response_headers(self, flow: mitmproxy.http.HTTPFlow):
        pass

    # 来自server的 HTTP 响应被成功完整读取
    def response(self, flow: mitmproxy.http.HTTPFlow):
        pass

    # 处理响应异常, HTTP错误
    def error(self, flow: mitmproxy.http.HTTPFlow):
        pass


addons = [
    catch_cookies()
]


if __name__ == '__main__':
    # from mitmproxy.tools.main import mitmweb
    #
    # mitmweb()
    opts = Options(listen_host='0.0.0.0', listen_port=8080, scripts=__file__)
    m = DumpMaster(opts)
    m.run()
