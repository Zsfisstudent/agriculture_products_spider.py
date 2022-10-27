#!/usr/bin/python
# _*_ coding: utf-8 _*_

"""
农产品数据爬虫
http://www.vipveg.com/price/2021/

"""
import time
import requests
from bs4 import BeautifulSoup
import sqlite3
from tqdm import tqdm


def fetch_agriculture_yeardata(year, month):
    url = 'http://www.vipveg.com/price/{}/'.format(year)
    resp = requests.get(url)
    resp.encoding = 'utf8'
    soup = BeautifulSoup(resp.text, 'lxml')
    table = soup.select('table.border3.f_s_14')[0]
    alinks = table.select('a')

    sheng_code = {
        '甘肃': '2922', '山东': '1357', '新疆': '3103', '山西': '220', '河北': '36', '北京': '2',
        '安徽': '1028', '江苏': '810', '浙江': '926', '湖北': '1692', '辽宁': '465', '四川': '2276',
        '天津': '19', '河南': '1515', '内蒙古': '351', '江西': '1245', '云南': '2577', '湖南': '1809',
        '黑龙江': '650', '宁夏': '3075', '重庆': '2237', '广东': '1946', '陕西': '2804', '福建': '1150',
        '贵州': '2479', '海南': '2213', '广西': '2089', '上海': '792', '西藏': '2723', '青海': '3023'
    }

    conn = sqlite3.connect('agriculture_products_infos2.db')
    cursor = conn.cursor()

    check_sql = "SELECT * FROM sqlite_master where type='table' and name='ProductInfo'"
    cursor.execute(check_sql)
    results = cursor.fetchall()
    # 数据库表不存在
    if len(results) == 0:
        # 创建数据库表
        sql = """
        CREATE TABLE ProductInfo(
            product CHAR(256),
            sheng CHAR(256),
            name CHAR(256),
            low_price float, 
            high_price float,
            mean_price float,
            pub_time CHAR(256)
        );
        """
        cursor.execute(sql)
        conn.commit()
        print('创建数据库表成功！')

    all_keys = ['product', 'sheng', 'name', 'low_price', 'high_price', 'mean_price', 'pub_time']
    insert_sql = "INSERT INTO ProductInfo ({}) VALUES ({});".format(','.join(all_keys), ','.join(['?'] * len(all_keys)))

    # 各省份各蔬菜的价格数据链接
    insert_product_infos = []

    product_sheng_urls = {}
    for alink in alinks:
        sheng_urls = {}

        for sheng in sheng_code:
            product_url = 'http://www.vipveg.com/{}/m{}d-1cta{}by-1p{}.html'.format(alink['href'], month,
                                                                                    sheng_code[sheng], '{}')
            sheng_urls[sheng] = product_url

        product = alink.text[:-2]
        product_sheng_urls[product] = sheng_urls

    for product in tqdm(product_sheng_urls):
        for sheng in product_sheng_urls[product]:
            pro_sheng_count = 0
            # print('抓取 {} {} 的价格数据'.format(sheng, product))

            base_url = product_sheng_urls[product][sheng]
            for page in range(1, 1000):
                try:
                    url = base_url.format(page)
                    resp = requests.get(url)
                    resp.encoding = 'utf8'
                    soup = BeautifulSoup(resp.text, 'lxml')
                    table = soup.select('table.m_t_5')[0]
                    table = table.find('table')
                    trs = table.find_all('tr')

                    for tr in trs:
                        tds = tr.find_all('td')
                        name = tds[0].text
                        low_price = float(tds[2].text[1:].strip())
                        high_price = float(tds[3].text[1:].strip())
                        mean_price = float(tds[4].text[1:].strip())
                        pub_time = tds[5].text

                        product_info = [product, sheng, name, low_price, high_price, mean_price, pub_time]
                        insert_product_infos.append(product_info)
                        pro_sheng_count += 1

                        if len(insert_product_infos) % 10 == 0:
                            cursor.executemany(insert_sql, insert_product_infos)
                            conn.commit()
                            insert_product_infos.clear()
                except:
                    pass

                # 获取最多的页数
                try:
                    max_page = int(soup.find('div', attrs={'id': 'pager'}).span.b.text)
                    if max_page == page:
                        break
                    time.sleep(0.5)
                except:
                    break

            # print('共计 {} 条'.format(pro_sheng_count))

    if insert_product_infos:
        cursor.executemany(insert_sql, insert_product_infos)
        conn.commit()
        insert_product_infos.clear()


# 抓取 19 - 22 年，疫情这几年的数据
for year in [2022]:
    for month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        # for month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
        print('--------------- {} 年 {} 月 ---------------'.format(year, month))
        fetch_agriculture_yeardata(year, month)
