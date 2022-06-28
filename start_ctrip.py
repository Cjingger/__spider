#!/usr/bin/python

from scrapy.cmdline import execute
import sys

if __name__ == '__main__':
    if len(sys.argv) == 8:
        a = sys.argv[1]
        b = sys.argv[2]
        c = sys.argv[3]
        d = sys.argv[4]
        e = sys.argv[5]
        f = sys.argv[6]
        g = sys.argv[7]
        execute(f"scrapy crawl ctripSpider -a file_name={a} -a from_line={b} -a to_line={c} -a from_date={d} -a to_date={e} -a is_low_price={f} -a task_time={g}".split())