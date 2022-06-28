import datetime
import json
import os
import traceback

import pymysql
from twisted.enterprise import adbapi
from pymysql import cursors

from flight_spider.YlSpiderItem import YlSpiderItem, YlRedisItem, YlBatchItem
from flight_spider.ylutils import ylutil
from flight_spider.ylutils.ylFile import YlFile
from redis import ConnectionPool, ConnectionError
import redis


class YlTwistPipeline:
    count = 0

    def __init__(self):
        self.ylFile = YlFile(os.path.abspath('.'))
        mysql_items = self.ylFile.getConfigDict("Mysql-Config-pro")
        self.host = mysql_items['host']
        self.port = int(mysql_items['port'])
        self.user = mysql_items['user']
        self.pwd = mysql_items['code']
        self.dataBase = mysql_items['database']
        self.data_base = ['ly', 'ctrip']
        parameter = {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.pwd,
            'database': self.dataBase,
            'cursorclass': cursors.DictCursor
        }
        redis_items = self.ylFile.getConfigDict("Redis-Config-pro")
        self.redis_host = redis_items['host']
        self.redis_port = redis_items['port']
        self.redis_pwd = redis_items['code']
        self.redis_db = redis_items['db']
        self.pool = ConnectionPool(host=self.redis_host, port=self.redis_port, db=self.redis_db,
                                   password=self.redis_pwd, encoding='utf-8',
                                   decode_responses=True)
        self.conn = redis.Redis(connection_pool=self.pool)
        try:
            self.dbpool = adbapi.ConnectionPool('pymysql', **parameter)
            self.today_date = ylutil.re_today()
        except ConnectionError:
            print('cant connect mysql, please check environment')

    def process_item(self, item, spider):
        if isinstance(item, YlSpiderItem):
            # if self.count == 0:
            #     table = self.dbpool.runInteraction(self.create_table)
            #     table.addErrback(self.handle_err, item, spider)
            # else:
            table = self.dbpool.runInteraction(self.create_table, self.today_date)
            query = self.dbpool.runInteraction(self.insert_value, item)
            query.addErrback(self.handle_err, item, spider)
            print("******成功插入数据******")
        elif isinstance(item, YlBatchItem) and spider.name == 'ylSpider05':
            self.load_into_data(item, 'ly')
        elif isinstance(item, YlBatchItem) and spider.name == 'ctripSpider':
            self.load_into_data(item, 'ctrip')
        elif isinstance(item, YlRedisItem):
            msg = {
                "off_date": item['off_date'],
                "from_city": item['from_city'],
                "from_city_code": item['from_city_code'],
                "to_city": item['to_city'],
                "to_city_code": item['to_city_code'],
                "company": item['company'],
                "company_no": item['company_no'],
                "plane_no": item['plane_no'],
                "start_time": item['start_time'],
                "end_time": item['end_time'],
                "platform": item['platform'],
                "flight_type": item['flight_type'],
                "plane_type": item['plane_type'],
                "flight_transfer": item['flight_transfer'],
                "from_city_airport": item['from_city_airport'],
                "to_city_airport": item['to_city_airport'],
                "task_time": item['task_time'],
                "create_time": item['create_time']
            }
            self.conn.sadd(f"{datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')}-{self.redis_db}",
                           json.dumps(msg))
            print("******放入redis缓存******")
        else:
            raise ValueError("No Items!")

    def create_table(self, cursor, table_name: str):
        create_table = r'''CREATE TABLE IF NOT EXISTS {}(
                  `id` int(11) NOT NULL AUTO_INCREMENT,
                  `company` char(50) DEFAULT NULL COMMENT '航班公司',
                  `company_no` char(50) DEFAULT NULL COMMENT '航班公司代码',
                  `plane_no` char(50) DEFAULT NULL COMMENT '航班号',
                  `start_time` char(50) DEFAULT NULL COMMENT '起飞时间',
                  `end_time` char(50) DEFAULT NULL COMMENT '到达时间',
                  `from_city` char(255) DEFAULT NULL COMMENT '起飞城市',    
                  `from_city_code` char(255) DEFAULT NULL COMMENT '起飞机场三字码',
                  `to_city` char(255) DEFAULT NULL COMMENT '到达城市',
                  `to_city_code` char(255) DEFAULT NULL COMMENT '到达机场三字码',
                  `discount` char(255) DEFAULT NULL COMMENT '折扣',
                  `create_time` datetime DEFAULT NULL COMMENT '获取时间',
                  `off_date` char(50) DEFAULT NULL COMMENT '起飞日期',
                  `platform` char(50) DEFAULT NULL COMMENT '平台',
                  `price`  char(255) DEFAULT NULL COMMENT '票价', 
                  `flight_type` char(50) DEFAULT NULL COMMENT '航班类型',
                  `plane_type` char(50) DEFAULT NULL COMMENT '机型',
                  `flight_transfer` char(50) DEFAULT NULL COMMENT '中转航班号',
                  `from_city_airport` char(255) DEFAULT NULL COMMENT '起飞机场',
                  `to_city_airport` char(255) DEFAULT NULL COMMENT '到达机场',
                  `task_time` char(50) DEFAULT NULL COMMENT '跑批任务时间',
                  `server_ip` char(50) DEFAULT NULL COMMENT '服务器ip',
                  `flight_number` int(11) DEFAULT NULL COMMENT '航班数量',
                  `insert_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间',
                  PRIMARY KEY (`id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8;'''.format(table_name)
        cursor.execute(create_table)
        print("***建表成功***")
        # self.count = 1

    def insert_value(self, cursor, item):
        TODAY = self.today_date
        sql = """insert into {} (id, company,company_no,plane_no, start_time, end_time, from_city,from_city_code,to_city,to_city_code, discount, create_time, off_date, platform, price,flight_type,plane_type,flight_transfer,from_city_airport,to_city_airport,task_time,server_ip)  values(null, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s);""".format(
            TODAY)
        cursor.execute(sql, (item.get('company'),
                             item.get('company_no'),
                             item.get('plane_no'),
                             item.get('start_time'),
                             item.get('end_time'),
                             item.get('from_city'),
                             item.get('from_city_code'),
                             item.get('to_city'),
                             item.get('to_city_code'),
                             item.get('discount', 'none'),
                             item.get('create_time'),
                             item.get('off_date'),
                             item.get('platform'),
                             item.get('price'),
                             item.get('flight_type'),
                             item.get('plane_type'),
                             item.get('flight_transfer'),
                             item.get('from_city_airport'),
                             item.get('to_city_airport'),
                             item.get('task_time'),
                             item.get('server_ip'),
                             # item.get('insert_time'),
                             ))

    def load_into_data(self, item, data_base: str):
        TODAY = self.today_date
        try:
            sql = f''' load data local infile '{item.get("csv_file_name")}' replace into table {TODAY} FIELDS TERMINATED BY ',' LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES (company, company_no, plane_no, start_time, end_time, from_city, from_city_code, to_city, to_city_code, create_time, discount, off_date, platform, price, flight_type, plane_type, flight_transfer, from_city_airport, to_city_airport, task_time, server_ip, flight_number);
                    '''
            conn = pymysql.connect(host=self.host, port=3306, user=self.user, passwd=self.pwd, db=data_base,
                                   local_infile=1)
            cursor = conn.cursor()
            cursor.execute('set names utf8')
            cursor.execute('set names utf8')
            cursor.execute('set character_set_connection=utf8')
            self.create_table(cursor, TODAY)
            res = cursor.execute(sql)
            if res < int(item.get('flight_number')):
                print(f"{item.get('from_city_code')}-{item.get('to_city_code')}-{item.get('off_date')}-{item.get('server_ip')}出现数据丢失, 实际插入数据{res}")
            else:
                os.remove(item.get('csv_file_name'))
            conn.commit()
            print("***成功插入数据***")
            cursor.close()
            conn.close()
        except:
            traceback.print_exc()
            pass

    # 报错日志
    def handle_err(self, error, item, spider):
        print('=' * 10 + "error" + '=' * 10)
        print(error)
        print('=' * 10 + "error" + '=' * 10)
