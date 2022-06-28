# Project：flight_spider_old
# Datetime：2021/12/84:06 下午
# Description：工具类
# @author 汤奇朋
# @version 1.0

import os
import datetime

from selenium.common.exceptions import NoSuchElementException


def re_today():
    TODAY = datetime.datetime.now().strftime('%Y_%m_%d')
    return TODAY


def create_dir(path: str, logger):
    # 去除首位空格
    path.strip()
    # 去除尾部\
    # path.rstrip("\\")
    path.rstrip("/")
    print(f"path:{path}")
    if os.path.exists(path):
        logger.info(f"{path}目录已存在")
        pass
    else:
        try:
            os.mkdir(path)
            logger.info(f"{path}创建成功")
        except:
            pass


def replace_path(local: str, path):
    """
    判断路径是windows路径还是linux路径
    :param local:
    :param path:
    :return:
    """
    if local.startswith("./ylutils") or "/" in local:
        file_path = os.path.dirname(os.path.dirname(__file__))
        path = local.strip("/")[1:]
        for p in path:
            if r"\\" in p:
                file_path += p
            else:
                continue
    else:
        print("windows路径")


def counter(func):
    def wrapper(*args, **kwargs):
        count = 0
        func(*args, **kwargs)
        count += 1

    return wrapper


def isElementPresent(driver, by, value):
    """
    用来判断元素标签是否存在，
    """
    try:
        element = driver.find_element(by=by, value=value)
        # self.ylLog.info(element)
    # 原文是except NoSuchElementException, e:
    except NoSuchElementException as e:
        # 发生了NoSuchElementException异常，说明页面中未找到该元素，返回False
        return False
    else:
        # 没有发生异常，表示在页面中找到了该元素，返回True
        return True
