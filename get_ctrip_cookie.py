# -*-encoding: utf-8 -*-
# !/bin/usr/python3
from bshead import create_bs_driver
import time, random, datetime, os

from redis_util import RedisUtil

redisUtil = RedisUtil()


def get_ctrip_cookie(from_city_code: str, to_city_code: str, off_date: str):
    _url = f"https://m.ctrip.com/html5/flight/swift/domestic/{from_city_code}/{to_city_code}/{off_date}?dfilter="
    browser = create_bs_driver()
    browser.get(_url)
    print("get_url", _url)
    time.sleep(random.choice([i for i in range(3, 5)]))
    # dictCookies = browser.get_cookies()
    # print(dictCookies)
    # _cookies = []
    # for _cookie in dictCookies:
    #     for key, value in _cookie.items():
    #         k = _cookie.get('name')
    #         v = _cookie.get('value')
    #         __cookie = f"{k}={v}"
    #         _cookies.append(__cookie)
    #         break
    # cookies = "; ".join(_cookies)
    # redisUtil.set(f"ctrip:{off_date}-cookie", "cookies", cookies)
    browser.quit()
    # return cookies


if __name__ == '__main__':
    now_date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
    __now_day = datetime.datetime.strptime(now_date, "%Y-%m-%d")
    off_date = __now_day + datetime.timedelta(days=random.choice([j for j in range(10)]))
    __off_date = datetime.datetime.strftime(off_date, "%Y-%m-%d")
    path = os.path.abspath(".") + os.sep + 'city_tw_data_3U.txt'
    with open(path, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        line = eval(lines[random.choice([i for i in range(1, 1010)])])
        from_city_code, to_city_code, off_date = line['from_city_code'], line['to_city_code'], __off_date
    get_ctrip_cookie(from_city_code, to_city_code, off_date)
