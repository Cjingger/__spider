# -*- encoding: utf-8 -*-
import os

import xlrd, traceback


def read_xlsx(filename):
    # filename = filename.decode('utf-8')
    map = {}
    workbook = xlrd.open_workbook(filename)
    table = workbook.sheets()[0]
    nrows = table.nrows
    for i in range(nrows):
        try:
            ap_code = "" if table.cell_value(i + 1, 0) == None else table.cell_value(i + 1, 0)
            airport = "" if table.cell_value(i + 1, 2) == None else table.cell_value(i + 1, 2)
            city = "" if table.cell_value(i + 1, 3) == None else table.cell_value(i + 1, 3)
            map[ap_code] = airport
            # map[ap_code] = city
        except Exception as e:
            # traceback.print_exc()
            continue
    return map


def get_airport(ap_code: str, base_path) -> str:
    _base_path = os.getcwd()
    # print(f"base_path {base_path}")
    filename = base_path + os.sep + "ylutils" + os.sep + r"rm_airport.xlsx"
    mapper = read_xlsx(filename)
    return mapper[ap_code].replace("国际", "")


def get_full_airport(ap_code: str, base_path) -> str:
    _base_path = os.getcwd()
    # print(f"base_path {base_path}")
    filename = base_path + os.sep + "ylutils" + os.sep + r"rm_airport.xlsx"
    mapper = read_xlsx(filename)
    return mapper[ap_code]


def get_city(ap_code: str, base_path) -> str:
    _base_path = os.getcwd()
    filename = base_path + os.sep + "ylutils" + os.sep + r"rm_airport.xlsx"
    mapper = read_xlsx(filename)
    return mapper[ap_code]


def get_city_from_airport(airport_name: str, base_path) -> str:
    '''
    根据机场名字匹配所在城市
    '''
    filename = base_path + os.sep + "ylutils" + os.sep + r"rm_airport.xlsx"
    map = {}
    workbook = xlrd.open_workbook(filename)
    table = workbook.sheets()[0]
    nrows = table.nrows
    for i in range(nrows):
        try:
            ap_code = "" if table.cell_value(i + 1, 0) == None else table.cell_value(i + 1, 0)
            _airport = "" if table.cell_value(i + 1, 2) == None else table.cell_value(i + 1, 2)
            airport = _airport.replace("机场", "").replace("国际", "")
            city = "" if table.cell_value(i + 1, 3) == None else table.cell_value(i + 1, 3)
            map[airport] = city
            # map[ap_code] = city
        except Exception as e:
            # traceback.print_exc()
            continue
    return map[airport_name]


if __name__ == '__main__':
    # filename = r"rm_airport.xlsx"
    # read_xlsx(filename)
    code = get_city_from_airport("武隆", os.path.abspath('..'))
    print(code)
