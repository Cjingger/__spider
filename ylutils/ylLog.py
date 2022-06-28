# Project：flight_spider_old
# Datetime：2021/12/85:53 下午
# Description：TODO
# @author 汤奇朋
# @version 1.0
import os
import time
from loguru import logger
from flight_spider.ylutils import ylutil


class YlLog:
    def __init__(self):
        self._basePath = os.path.abspath('.')
        now_time = time.strftime("%Y-%m-%d", time.localtime())
        _now_time = time.strftime("%Y-%m-%d%H-00-00", time.localtime())
        self.logPath = os.path.join(self._basePath,'logs')
        ylutil.create_dir(self.logPath, logger)
        self.first_path = os.path.join(self._basePath,'logs',now_time)
        ylutil.create_dir(self.first_path, logger)
        self.second_path = os.path.join(self._basePath,'logs',now_time,_now_time)
        ylutil.create_dir(self.second_path, logger)
        logger.add(f"logs/runtime{now_time}.log", rotation="100MB", encoding="utf-8", enqueue=True, compression="zip",
                   retention="1 week", level="INFO")

    def setLevel(self, level):
        logger.level(level)

    def info(self, message: str):
        logger.info(message)

    def debug(self, message: str):
        logger.debug(message)

    def error(self, message: str):
        logger.error(message)

    def exception(self, message: str):
        logger.exception(message)
