# !/usr/bin/python3
# -*- encoding: utf-8 -*-
import requests, json, traceback, os, sys
# 获取当前文件绝对路径
curr_dir = os.path.dirname(os.path.abspath(__file__))
# 将需要导入模块代码文件相对于当前文件目录的绝对路径加入到sys.path中
sys.path.append(os.path.join(curr_dir, ".."))
from flight_spider.redisUtil import RedisUtil
import datetime


def get_proxies():
    redisUtil = RedisUtil(db=1)
    ip_url = 'http://http.tiqu.alibabaapi.com/getip3?num=80&type=2&pack=92789&port=11&ts=1&cs=1&lb=1&pb=4&gm=4&regions=&appkey=b3f8aa116dd60459f318745c51547f34'
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Mobile Safari/537.36",
    }
    now_date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H-00-00')
    try:
        res = requests.get(ip_url, headers)
        if res.status_code in [200, 201]:
            json_data = json.loads(res.content.decode())
            print("resp_data", json_data)
            for data in json_data['datas']:
                ip, port = data['ip'], data['port']
                proxy = "https://" + ip + ":" + port
                redisUtil.sset(f'proxies-{now_date}', proxy)
                print(proxy)
            redisUtil.set_expire(f'proxies-{now_date}', 61 * 60)
    except:
        traceback.print_exc()
        pass


if __name__ == '__main__':
    get_proxies()

