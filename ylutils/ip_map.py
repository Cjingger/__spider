# -*- coding: utf-8 -*-
# !/bin/usr/python3

from collections import defaultdict

ip_list = ['82.157.23.62', '82.157.34.205', '101.42.117.230', '82.156.215.244', '49.232.210.32',
           '140.143.229.189', '81.70.94.54', '81.70.248.131', '62.234.122.128']
ip_map = dict()
for i, ip in enumerate(ip_list):
    ip_map[i+1] = ip

