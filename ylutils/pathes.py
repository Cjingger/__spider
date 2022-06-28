# -*- encoding: utf-8 -*-
# @Author:jingger
# @Function: 封装目录路径类


class Pathes(object):

    def __init__(self):
        self._windows = ""
        self._linux = ""

    @property
    def path_windows(self):
        return self._windows

    @path_windows.setter
    def set_path_windows(self, path):
        self._windows = path

    @property
    def path_linux(self):
        return self._linux

    @path_linux.setter
    def set_path_linux(self, path):
        self._linux = path

