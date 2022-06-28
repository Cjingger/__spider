from __future__ import division
import time, cv2
import requests
from models import *
from utils.utils import *
from utils.datasets import *
from os.path import dirname, join
import os
import sys
import time
import datetime
import argparse
from PIL import Image

import torch
from torch.utils.data import DataLoader
from torchvision import datasets
from torch.autograd import Variable

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.ticker import NullLocator
import shutil

from flask import Flask, request
import flask
from werkzeug.utils import secure_filename
from flask.json import jsonify
import os
from gevent.pywsgi import WSGIServer
# from gevent import monkey

# monkey.patch_all()

from paddleocr import PaddleOCR, draw_ocr

# Paddleocr目前支持的多语言语种可以通过修改lang参数进行切换
# 例如`ch`, `en`, `fr`, `german`, `korean`, `japan`
ocr = PaddleOCR(use_angle_cls=True, lang="ch")  # need to run only once to download and load model into memory

app = Flask(__name__)

UPLOAD_FOLDER = 'upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
basedir = os.path.abspath(os.path.dirname(__file__))
# basedir = "/Users/haoyu/Documents/wide-and-deep-learning-keras/testimg"
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'JPG', 'PNG', 'gif', 'GIF'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


# detect.py主要的工作过程
# 1.解析命令行输入的各种参数，如果没有就使用默认的参数
# 2.打印出当前的各种参数
# 3.创建model
# 4.加载model的权重
# 5.加载测试图像
# 6.加载data/coco.names中的类别名称
# 7.算出batch中所有图片的地址img_paths和检测结果detctions
# 8.为detections里每个类别的物体选择一种颜色，把检测到的bboxes画到图上


def findLeftCord(testImgPath, fname):
    # 1. 解析命令行输入的各种参数，如果没有就使用默认的参数
    parser = argparse.ArgumentParser()  # 创建一个解析对象
    parser.add_argument("--image_folder", type=str, default=testImgPath, help="path to dataset")
    parser.add_argument("--model_def", type=str, default="config/yolov3-captcha.cfg",
                        help="path to model definition file")
    parser.add_argument("--weights_path", type=str, default="checkpoints/yolov3_ckpt_96.pth",
                        help="path to weights file")
    parser.add_argument("--class_path", type=str, default="data/captcha/classes.names", help="path to class label file")
    parser.add_argument("--conf_thres", type=float, default=0.7, help="object confidence threshold")
    parser.add_argument("--nms_thres", type=float, default=0.4, help="iou thresshold for non-maximum suppression")
    parser.add_argument("--batch_size", type=int, default=1, help="size of the batches")
    parser.add_argument("--n_cpu", type=int, default=0, help="number of cpu threads to use during batch generation")
    parser.add_argument("--img_size", type=int, default=416, help="size of each image dimension")
    parser.add_argument("--checkpoint_model", type=str, help="path to checkpoint model")
    opt = parser.parse_args()  # 进行解析
    print(opt)  # 打印出当前的各种参数
    leftCord = 0
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # 判断是否有gpu

    output_folder = join(dirname(opt.image_folder), 'result')

    os.makedirs(output_folder, exist_ok=True)  # 创建多级目录

    # Set up model 创建模型
    model = Darknet(opt.model_def, img_size=opt.img_size).to(device)

    # 调用darknet模型，parse_model_config，解析模型参数，生成模型参数列表，调用creat_modules，
    # 根据模型参数列表生成相应的convolutional、maxpool、upsample、route、shortcut、yolo层
    # 加载模型的权重
    if opt.weights_path.endswith(".weights"):
        # Load darknet weights
        model.load_darknet_weights(opt.weights_path)
    else:
        # Load checkpoint weights
        # model.load_state_dict(torch.load(opt.weights_path))
        model.load_state_dict(torch.load(opt.weights_path, map_location="cuda" if torch.cuda.is_available() else "cpu"))

    model.eval()  # Set in evaluation mode测试模式

    # 加载测试图像
    print("opt.image_folder:", opt.image_folder)
    dataloader = DataLoader(
        ImageFolder(opt.image_folder, img_size=opt.img_size),
        batch_size=opt.batch_size,
        shuffle=False,
        num_workers=opt.n_cpu,
    )
    # 加载data/coco.names中的类别名称
    classes = load_classes(opt.class_path)  # Extracts class labels from file

    Tensor = torch.cuda.FloatTensor if torch.cuda.is_available() else torch.FloatTensor

    imgs = []  # Stores image paths
    img_detections = []  # Stores detections for each image index

    # print("\nPerforming object detection:")
    prev_time = time.time()
    # 算出batch中所有图片的地址img_paths和检测结果detectionc
    for batch_i, (img_paths, input_imgs) in enumerate(dataloader):
        # Configure input
        input_imgs = Variable(input_imgs.type(Tensor))
        print("input_imgs:", input_imgs.shape)

        # Get detections
        print(fname)
        print(img_paths[0])
        if fname in img_paths[0]:
            print("1111111111111")
            with torch.no_grad():  # torch.no_grad()中的数据不需要计算梯度，也不会进行反向传播
                detections = model(input_imgs)  # 通过Darknet的forward()函数得到检测结果，yolo_outputs
                # print("detections:", detections)
                # 非极大值抑制
                detections = non_max_suppression(detections, opt.conf_thres, opt.nms_thres)

            # Log progress
            current_time = time.time()
            inference_time = datetime.timedelta(seconds=current_time - prev_time)
            prev_time = current_time
            # print("\t+ Batch %d, Inference Time: %s" % (batch_i, inference_time))

            # Save image and detections
            imgs.extend(img_paths)
            print("imgs:", imgs[0])
            img_detections.extend(detections)
            break
        else:
            print("2222222222222222222")
            continue

    # Bounding-box colors 选一种bbox颜色
    cmap = plt.get_cmap("tab20b")
    colors = [cmap(i) for i in np.linspace(0, 1, 20)]

    print("\nSaving images:")
    # 为每一个类别的物体选择一种颜色，把检测到的bboxes画到图上
    # Iterate through images and save plot of detections
    res = []
    for img_i, (path, detections) in enumerate(zip(imgs, img_detections)):

        print("(%d) Image: '%s'" % (img_i, path))

        # Create plot
        img = np.array(Image.open(path))
        plt.figure()
        fig, ax = plt.subplots(1)  # 由ax获取当前坐标轴
        ax.imshow(img)

        # Draw bounding boxes and labels of detections
        i = 0
        if detections is not None:  # 有检测结果时才需要画出来
            # Rescale boxes to original image
            detections = rescale_boxes(detections, opt.img_size, img.shape[:2])  # detections结果扩展到原图大小，检测时输入图像大小为416x416
            unique_labels = detections[:, -1].cpu().unique()  # 返回参数数组中所有不同的值，并按照从小到大排序可选参数
            n_cls_preds = len(unique_labels)  # 标签的个数
            bbox_colors = random.sample(colors, n_cls_preds)  # 在很多种colors中，随机挑选出标签数n_cls_preds种，即为一类物体分配一种颜色
            for x1, y1, x2, y2, conf, cls_conf, cls_pred in detections:  # detections里用的是左上右下点
                print("\t+ Label: %s, Conf: %.5f" % (classes[int(cls_pred)], cls_conf.item()))

                box_w = x2 - x1
                box_h = y2 - y1
                color = bbox_colors[int(np.where(unique_labels == int(cls_pred))[0])]  # 依据预测的类，查找到该用那种颜色
                # Create a Rectangle patch 创建一个长方形的框
                bbox = patches.Rectangle((x1 + box_w / 2, y1 + box_h / 2), box_w, box_h, linewidth=2, edgecolor=color,
                                         facecolor="none")
                print('bbox', (x1, y1, box_w, box_h), 'offset', x1)
                # Add the bbox to the plot
                ax.add_patch(bbox)
                # Add label
                plt.text(
                    x1,
                    y1,
                    s=classes[int(cls_pred)],
                    color="white",
                    verticalalignment="top",
                    bbox={"color": color, "pad": 0},
                )
                # only one
                print(x1)
                print(img.shape[0], img.shape[1])
                crop = img[int(y1 + box_h / 2):int(y1 + 3 * box_h / 2), int(x1 + box_w / 2):int(x1 + 3 * box_w / 2)]
                if len(crop) == 0:
                    continue
                ss = ''
                result = ocr.ocr(crop, cls=True)
                if len(result) == 0:
                    crop = cv2.pyrUp(crop)
                    crop = cv2.pyrUp(crop)
                    result = ocr.ocr(crop, cls=True)
                    if len(result) != 0:
                        for line in result:
                            print(line)
                            print("输出：", line[1][0])
                            ss = line[1][0]
                            res.append({'text': ss, 'cord': (int(x1 + box_w), int(y1 + box_h))})
                            break
                    else:
                        crop = cv2.pyrUp(crop)
                        crop = cv2.pyrUp(crop)
                        blur_img = cv2.GaussianBlur(crop, (0, 0), 7)
                        crop = cv2.addWeighted(crop, 7, blur_img, -0.5, 0)

                        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2YCrCb)
                        channelsYUV = cv2.split(crop)
                        t = channelsYUV[0]

                        clache = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
                        p = clache.apply(t)

                        channels = cv2.merge([p, channelsYUV[1], channelsYUV[2]])
                        crop = cv2.cvtColor(channels, cv2.COLOR_YCrCb2BGR)
                        result = ocr.ocr(crop, cls=True)
                        if len(result) != 0:
                            for line in result:
                                print(line)
                                print("输出：", line[1][0])
                                ss = line[1][0]
                                res.append({'text': ss, 'cord': (int(x1 + box_w), int(y1 + box_h))})
                                break
                else:
                    for line in result:
                        print(line)
                        print("输出：", line[1][0])
                        ss = line[1][0]
                        if ss != '':
                            res.append({'text': ss, 'cord': (int(x1 + box_w), int(y1 + box_h))})
                            break
                cv2.imwrite(str(i) + '.jpg', crop)
                i += 1
                # crop = cv2.pyrUp(crop)
                # crop = cv2.pyrUp(crop)
                # result = ocr.ocr(crop, cls=True)
                # ss = ''
                # for line in result:
                #     print(line)
                #     print("输出：", line[1][0])
                #     ss = line[1][0]
                #     if ss != '':
                #         res.append({'text': ss, 'cord': (int(x1 + box_w), int(y1 + box_h))})

        # Save generated image with detections
        plt.axis("off")  # 关闭坐标轴
        plt.gca().xaxis.set_major_locator(NullLocator())
        plt.gca().yaxis.set_major_locator(NullLocator())
        path = eval(repr(path).replace('\\', '/'))
        filename = path.split("/")[-1].split(".")[0]
        plt.savefig(f"{output_folder}/{filename}.png", bbox_inches="tight", pad_inches=0.0)  # 保存文件
        plt.close()
        # os.remove(path)
    # return {'content': res}
    return res


def return_res(img_small, res):
    res_box = []
    img_small = cv2.pyrUp(img_small)
    img_small = cv2.pyrUp(img_small)
    result = ocr.ocr(img_small, cls=True)
    for line in result:
        print(line)
        print("输出：", line[1][0])
        ss = line[1][0]
        for i in range(len(ss)):
            for j in res:
                if j['text'] == ss[i]:
                    res_box.append(j['cord'])
    return res_box


# def return_res(img_small_path, res):
#     res_box = []
#     img_small = cv2.imread(img_small_path)
#     img_small = cv2.pyrUp(img_small)
#     img_small = cv2.pyrUp(img_small)
#     result = ocr.ocr(img_small, cls=True)
#     for line in result:
#         print(line)
#         print("输出：", line[1][0])
#         ss = line[1][0]
#         for i in range(len(ss)):
#             for j in res:
#                 if j['text'] == ss[i]:
#                     res_box.append(j['cord'])
#     return res_box


# 上传文件
@app.route('/up_photo', methods=['GET', 'POST'], strict_slashes=False)
def api_upload():
    print("启动成功")
    file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    f = flask.request.files['photo']
    ff = flask.request.files['small_photo']
    print("f:", f)
    print("ff:", ff)
    if f and allowed_file(f.filename):
        fname = secure_filename(f.filename)
        print(fname)
        # ext = fname.rsplit('.', 1)[1]
        # new_filename = "test" + '.' + ext
        filepath = os.path.join(file_dir, fname)
        f.save(filepath)
        leftCord = findLeftCord(file_dir, fname)
        # leftCord = findLeftCord(filepath)
        print(leftCord)
        if ff and allowed_file(ff.filename):
            ffname = secure_filename(ff.filename)
            print(ffname)
            filepath1 = os.path.join(file_dir, ffname)
            ff.save(filepath1)
            img_small = cv2.imread(filepath1)
            res_box = return_res(img_small,leftCord)
            return {'content': res_box}
    else:
        return {}


if __name__ == '__main__':
    app.run(host="0.0.0.0", port='8000', threaded=False, debug=False, processes=10)
    # http_server = WSGIServer(('0.0.0.0', 8000), app)
    # http_server.serve_forever()
