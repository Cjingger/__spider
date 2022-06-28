import scrapy


class YlSpiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    off_date = scrapy.Field()
    from_city = scrapy.Field()
    from_city_code = scrapy.Field()
    to_city = scrapy.Field()
    to_city_code = scrapy.Field()
    company = scrapy.Field()
    company_no = scrapy.Field()
    plane_no = scrapy.Field()
    start_time = scrapy.Field()
    end_time = scrapy.Field()
    discount = scrapy.Field()
    create_time = scrapy.Field()
    price = scrapy.Field()
    platform = scrapy.Field()
    flight_type = scrapy.Field()
    plane_type = scrapy.Field()
    flight_transfer = scrapy.Field()
    task_time = scrapy.Field()
    server_ip = scrapy.Field()
    insert_time = scrapy.Field()
    from_city_airport =scrapy.Field()
    to_city_airport = scrapy.Field()


class YlRedisItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    off_date = scrapy.Field()
    from_city = scrapy.Field()
    from_city_code = scrapy.Field()
    to_city = scrapy.Field()
    to_city_code = scrapy.Field()
    company = scrapy.Field()
    company_no = scrapy.Field()
    plane_no = scrapy.Field()
    start_time = scrapy.Field()
    end_time = scrapy.Field()
    platform = scrapy.Field()
    flight_type = scrapy.Field()
    plane_type = scrapy.Field()
    flight_transfer = scrapy.Field()
    task_time = scrapy.Field()
    create_time = scrapy.Field()
    from_city_airport = scrapy.Field()
    to_city_airport = scrapy.Field()


class YlBatchItem(scrapy.Item):
    # define the fields for your item here like:
    from_city_code = scrapy.Field()
    to_city_code = scrapy.Field()
    off_date = scrapy.Field()
    server_ip = scrapy.Field()
    csv_file_name = scrapy.Field()
    flight_number = scrapy.Field()