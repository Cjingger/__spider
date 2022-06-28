# Project：flight_spider_old
# Datetime：2021/12/87:13 下午
# Description：验证图片的一些逻辑
# @author 汤奇朋
# @version 1.0
import io
import os
import cv2
import time
import base64
import requests
from PIL import Image
from io import BytesIO
from flight_spider.ylutils.ylLog import YlLog
from flight_spider.ylutils.ylFile import YlFile

from selenium.webdriver.common.action_chains import ActionChains

url = "http://8.131.87.225:8002/up_photo"
data = {'path': '/testbg'}


class VerifyImage:
    def __init__(self):
        self.ylLog = YlLog()
        self.ylFile = YlFile(os.path.abspath('.'))
        print('VerifyImage')

    def small_image(self, url, time_node):
        # 获取小图（拼图）将其转化为jpg
        res = requests.get(url)
        byte_stream = BytesIO(res.content)
        roiImg = Image.open(byte_stream)
        imgByteArr = io.BytesIO()
        roiImg.save(imgByteArr, format='png')
        imgByteArr = imgByteArr.getvalue()
        self.ylFile.createFile(fr"/imgs/a_{time_node}.png", imgByteArr, model='wb', encod=None)
        # with open(fr'{_path}/ylutils/imgs/a_{time_node}.png', 'wb') as f:
        #     # with open(fr"D:\Spider\flight_spider\flight_spider\ylutils\imgs\a_{time_node}.png", 'wb') as f:
        #     f.write(imgByteArr)

    # 下载滑块验证失败的图片
    def download_fail_imgs(self, spider):
        # creatFile("../ylutils/imgs/testa_error")
        # creatFile("./ylutils/imgs/testbg_error")
        # creatFile("../ylutils/imgs/imgrec_error")
        try:
            small_img_url = spider.driver.find_element_by_xpath(
                '//div[@id="dx_captcha_basic_sub-slider_1"]/img').get_attribute(
                "src")
            time_node = time.time()
            if "https" in small_img_url:
                self.small_image(small_img_url, time_node)
            else:
                ss = small_img_url.split(',')
                if len(ss) == 2:
                    img = base64.b64decode(small_img_url.split(',')[-1])
                    self.ylFile.createFile(fr"/imgs/a_{time_node}.png", img, model='wb', encod=None)
                else:
                    print("获取图像错误")
                    pass
            # 2、获取有缺口验证图片
            bc_img = self.bc_image(spider.driver, time_node)
            bc_img.save(
                f'{self.ylLog._basePath}/imgs/bc_img_{time_node}.png')
        except Exception as e:
            self.ylLog.exception(str(e))

    def small_image_error(self, url, time_node):
        # 获取小图（拼图）将其转化为jpg
        res = requests.get(url)
        byte_stream = BytesIO(res.content)
        roiImg = Image.open(byte_stream)
        imgByteArr = io.BytesIO()
        roiImg.save(imgByteArr, format='png')
        imgByteArr = imgByteArr.getvalue()
        self.ylFile.createFile(fr'/imgs/a_{time_node}.png', imgByteArr, model='wb', encod=None)

    def bc_image(self, driver, time_node):
        """
        获取滑块验证码背景图片
        :param driver:chrome对象
        :return:背景图片
         """
        driver.save_screenshot(fr"{self.ylLog._basePath}/imgs/yanzhengma_{time_node}.png")
        # 通过画图软件直接获取相应图片的坐标值
        # left = 855
        # top = 400
        # right = 1500
        # bottom = 700
        left = 248
        top = 193
        right = 548
        bottom = 343
        im = Image.open(f'{self.ylLog._basePath}/imgs/yanzhengma_{time_node}.png')
        # im = Image.open(fr'D:\Spider\flight_spider\flight_spider\ylutils\imgs\yanzhengma_{time_node}.png')
        im = im.crop((left, top, right, bottom))
        self.ylLog.info("截取截图中背景图")
        return im

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
        t = 0.2
        # 初速度
        v = 0

        while current < distance:
            if current < mid:
                # 加速度为正2
                # apositive = [2.2, 2.3, 2.5, 2.7, 2.9]
                a = 20
            else:
                # 加速度为负3
                # anegitive = [-3.0, -2.8, -2.1, -2.2, -2.5]
                a = -30
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

    # 图片转为 灰度图片
    def img2gray(self, image):
        img_rgb = cv2.imread(image)  # 读入图片
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)  # 转灰度图片
        # cv2.imwrite(image, img_gray)  # 保存图片，第一个参数：path, 第二个参数：保存的图片
        return img_gray

    # 锐化边缘
    def canny_edge(self, image):
        img = self.img2gray(image)
        # img = cv2.imread(image, 0)
        blur = cv2.GaussianBlur(img, (5, 5), 0)  # 用高斯滤波处理原图像降噪
        canny = cv2.Canny(blur, threshold1=200, threshold2=300)  # 锐化图片
        # cv2.imwrite(image, canny)  # 保存图片
        # cv2.imshow('candy', can)  # 弹出图片
        # cv2.waitKey()
        # cv2.destroyAllWindows()  # 关闭窗口
        return canny

    def main(self, driver):
        print("出现滑块验证，验证中>>>>>>>>>")
        # 1、出现滑块验证，获取验证小图片
        small_img_url = driver.find_element_by_xpath('//div[@id="dx_captcha_basic_sub-slider_1"]/img').get_attribute("src")
        print(small_img_url)
        time_node = time.time()
        if "https" in small_img_url:
            self.small_image(small_img_url, time_node)
        else:
            ss = small_img_url.split(',')
            if len(ss) == 2:
                img = base64.b64decode(small_img_url.split(',')[-1])
                self.ylFile.createFile(fr"/imgs/a_{time_node}.png", img, model='wb', encod=None)
                # with open(fr".\testa\a_{time_node}.png", 'wb') as f:
                # with open(fr"{self.ylLog._basePath}/imgs/a_{time_node}.png", 'wb') as f:
                #     f.write(img)
            else:
                print("获取图像错误")

        bc_img = self.bc_image(driver, time_node)
        bc_img.save(fr'{self.ylLog._basePath}/imgs/bc_img_{time_node}.png')
        # bc_img.save(fr'{self.ylLog._basePath}/datas/captcha/test/bc_img_{time_node}.png')
        files = {'photo': open(f'{self.ylLog._basePath}/imgs/bc_img_{time_node}.png', 'rb')}
        req = requests.request("POST", url=url, files=files, data=data, headers={'connection':'close'})
        print(req.text)
        value = int(req.text)
        # print("value:", value + 16)
        print("value:", value)
        if value != 0:
            # 根据距离获取位移的轨迹路
            # track = self.get_track(value/2 +8)
            track = self.get_track(value + 10)
            node = driver.find_element_by_xpath('//img[@id="dx_captcha_basic_slider-img-normal_1"]')
            ActionChains(driver).click_and_hold(on_element=node).perform()
            for x in track:
                ActionChains(driver).move_by_offset(xoffset=x, yoffset=0).perform()
                if x == track[-1]:
                    driver.save_screenshot(fr'{self.ylLog._basePath}/imgs/testtrack/track_{time_node}.png')
            ActionChains(driver).release().perform()
            time.sleep(0.5)

    # 从验证失败的有缺口背景图片中找到相对画出的图片
    def pick_error_img(self, time_node: float):
        time_node = str(time_node).split(".")[0]
        file_list = os.listdir(fr'{self.ylFile._basePath}/data/captcha/result')
        # file_list = os.listdir(r'.\datas\captcha\result')
        try:
            for file in file_list:
                bc_time = str(file).split("_")[-1].split(".")[0]
                if bc_time in time_node:
                    return file
                else:
                    continue
        except Exception as e:
            print(e)