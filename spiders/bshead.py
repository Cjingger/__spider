# -*- coding: utf-8 -*-


"""
web浏览器配置文件
走有头，无头浏览器
"""
import random

from selenium import webdriver

# from msedge.selenium_tools import Edge, EdgeOptions
from flight_spider.settings import user_agent_list, user_agent_mobile

types = ["chrome", "firefox", "edge"]


def create_bs_driver(type="chrome", headless=False):
    global driver
    """ 
    :param type:
    :param headless:  是否为无头浏览器，True---无头，  False---有头
    :return:
    """
    if type == "firefox":  # 火狐浏览器
        print('firefox')
        firefox_opt = webdriver.FirefoxOptions()
        firefox_opt.add_argument("--headless") if headless else None
        driver = webdriver.Firefox(firefox_options=firefox_opt)
    elif type == "chrome":  # 谷歌浏览器
        chrome_opt = webdriver.ChromeOptions()
        chrome_opt.add_argument('--no-sandbox')
        chrome_opt.add_argument("--disable-setuid-sandbox")
        chrome_opt.add_argument('--disable-dev-shm-usage')
        chrome_opt.add_argument('window-size=800x600')
        chrome_opt.add_argument('disable-gpu')
        # 无痕模式
        chrome_opt.add_argument('--incognito')
        chrome_opt.add_argument(f'user-agent={random.choice(user_agent_list)}')
        # chrome_opt.add_argument(f'user-agent={random.choice(user_agent_mobile)}')
        # 启动开发者模式 webdriver会始终输出undefined
        chrome_opt.add_argument("--headless") if headless else None
        chrome_opt.add_experimental_option("useAutomationExtension", False)
        # chrome_opt.add_argument('blink-settings=imagesEnabled=false')
        # chrome_opt.add_experimental_option('excludeSwitches', ['enable-automation'])
        # chrome_opt.add_experimental_option("detach", True)
        chrome_opt.add_argument("--disable-blink-features")
        chrome_opt.add_argument("--disable-blink-features=AutomationControlled")
        # driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', chrome_options=chrome_opt)
        driver = webdriver.Chrome(chrome_options=chrome_opt)

        # driver.set_window_size(813, 730)
        # 删除所有cookie
        # driver.delete_all_cookies()

    else:
        return None
    return driver
