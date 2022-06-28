# -*- coding: utf-8 -*-
import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chorme_options = Options()
chorme_options.add_argument("--headless")
chorme_options.add_argument("--disable-gpu")


class FliggySpider(scrapy.Spider):
    name = 'fliggySpider'
    allowed_domains = ['www.fliggy.com']
    start_urls = ['https://www.fliggy.com']

    def __init__(self):
        self.browser = webdriver.Chrome()
        super().__init__()

    def start_requests(self):
        pass

    def parse(self, response):
        print(response.body.decode('utf-8'))
        pass
