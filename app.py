#!/usr/bin/python
# coding=utf-8
import random
import sqlite3
from tqdm import tqdm
from flask import Flask, render_template, jsonify
from statsmodels.tsa.arima_model import ARIMA
from sklearn.metrics import mean_squared_error

# Flask是一个Python编写的Web微框架，让我们可以使用Python语言快速实现一个网站或Web服务
app = Flask(__name__)
app.config.from_object('config')

login_name = None


# --------------------- html render ---------------------
# Flask中的route()装饰器用于将URL绑定到函数。
@app.route('/')
def index():
    return render_template('index.html')  #


@app.route('/province_product')  # 尾部没有“/”保持URL的唯一。加“/”在后面，在访问尾部没有“/”的URL，flask会自动重定向（在尾部自动加上“/”）
def province_product():
    return render_template('province_product.html')


@app.route('/product_search')
def product_search():
    return render_template('product_search.html')


@app.route('/product_compare')
def product_compare():
    return render_template('product_compare.html')


@app.route('/price_predict')
def price_predict():
    return render_template('price_predict.html')


# ------------------ ajax restful api -------------------
@app.route('/check_login')  # Flask中的route()装饰器用于将URL绑定到函数。
def check_login():
    """判断用户是否登录"""
    # jsonify函数返回供用户处理的序列化json数据
    return jsonify({'username': login_name, 'login': login_name is not None})


@app.route('/register/<name>/<password>')  # Flask中的route()装饰器用于将URL绑定到函数。
def register(name, password):
    conn = sqlite3.connect('user_info.db')
    cursor = conn.cursor()

    check_sql = "SELECT * FROM sqlite_master where type='table' and name='user'"
    cursor.execute(check_sql)
    results = cursor.fetchall()
    # 数据库表不存在
    if len(results) == 0:
        # 创建数据库表
        sql = """
                CREATE TABLE user(
                    name CHAR(256), 
                    password CHAR(256)
                );
                """
        cursor.execute(sql)
        conn.commit()
        print('创建数据库表成功！')

    sql = "INSERT INTO user (name, password) VALUES (?,?);"
    cursor.executemany(sql, [(name, password)])
    conn.commit()
    # jsonify函数返回供用户处理的序列化json数据
    return jsonify({'info': '用户注册成功！', 'status': 'ok'})


@app.route('/login/<name>/<password>')  # Flask中的route()装饰器用于将URL绑定到函数。
def login(name, password):
    global login_name
    conn = sqlite3.connect('user_info.db')
    cursor = conn.cursor()

    check_sql = "SELECT * FROM sqlite_master where type='table' and name='user'"
    cursor.execute(check_sql)
    results = cursor.fetchall()
    # 数据库表不存在
    if len(results) == 0:
        # 创建数据库表
        sql = """
                CREATE TABLE user(
                    name CHAR(256), 
                    password CHAR(256)
                );
                """
        cursor.execute(sql)
        conn.commit()
        print('创建数据库表成功！')

    sql = "select * from user where name='{}' and password='{}'".format(name, password)
    cursor.execute(sql)
    results = cursor.fetchall()

    login_name = name
    if len(results) > 0:
        print(results)
        # jsonify函数返回供用户处理的序列化json数据
        return jsonify({'info': name + '用户登录成功！', 'status': 'ok'})
    else:
        return jsonify({'info': '当前用户不存在！', 'status': 'error'})


# 获取数据库中所有农产品和省份
@app.route('/get_all_products_shengs')  # Flask中的route()装饰器用于将URL绑定到函数。
def get_all_products_shengs():
    conn = sqlite3.connect('agriculture_products_infos.db')
    cursor = conn.cursor()
    sql = 'select distinct product from ProductInfo'
    cursor.execute(sql)
    products = cursor.fetchall()
    products = [d[0] for d in products]

    sql = 'select distinct sheng from ProductInfo'
    cursor.execute(sql)
    shengs = cursor.fetchall()
    shengs = [d[0] for d in shengs]

    # jsonify函数返回供用户处理的序列化json数据
    return jsonify({
        'products': products,
        'shengs': shengs
    })


# 对某个省某个农产品数据进行数据挖掘数据分析
@app.route('/sheng_product_analysis/<product_name>/<sheng_name>')  # Flask中的route()装饰器用于将URL绑定到函数。
def sheng_product_analysis(product_name, sheng_name):
    conn = sqlite3.connect('agriculture_products_infos.db')
    cursor = conn.cursor()
    sql = "select * from ProductInfo where product='{}' and sheng='{}'".format(product_name, sheng_name)
    cursor.execute(sql)
    datas = cursor.fetchall()

    date_mean_price = {}
    date_low_price = {}
    date_high_price = {}

    for data in datas:
        product, sheng, name, low_price, high_price, mean_price, pub_time = data
        if pub_time not in date_mean_price:
            date_mean_price[pub_time] = []
        date_mean_price[pub_time].append(mean_price)

        if pub_time not in date_low_price:
            date_low_price[pub_time] = []
        date_low_price[pub_time].append(low_price)

        if pub_time not in date_high_price:
            date_high_price[pub_time] = []
        date_high_price[pub_time].append(high_price)

    dates = list(date_mean_price.keys())[::-1]
    date_price_box = {}
    for c in dates:
        date_price_box[c] = date_low_price[c]
        date_low_price[c] = sum(date_low_price[c]) / len(date_low_price[c])
        date_mean_price[c] = sum(date_mean_price[c]) / len(date_mean_price[c])
        date_high_price[c] = sum(date_high_price[c]) / len(date_high_price[c])

    sql = "select * from ProductInfo where product='{}'".format(product_name)
    cursor.execute(sql)
    datas = cursor.fetchall()

    # 不同省份的价格分布
    sheng_mean_price = {}
    sheng_low_price = {}
    sheng_high_price = {}
    for data in datas:
        product, sheng, name, low_price, high_price, mean_price, pub_time = data
        if sheng not in sheng_mean_price:
            sheng_mean_price[sheng] = []
        sheng_mean_price[sheng].append(mean_price)

        if sheng not in sheng_low_price:
            sheng_low_price[sheng] = []
        sheng_low_price[sheng].append(low_price)

        if sheng not in sheng_high_price:
            sheng_high_price[sheng] = []
        sheng_high_price[sheng].append(high_price)

    shengs = list(sheng_mean_price.keys())
    sheng_counts = {}
    for s in shengs:
        sheng_counts[s] = len(sheng_mean_price[s])
        sheng_low_price[s] = sum(sheng_low_price[s]) / len(sheng_low_price[s])
        sheng_mean_price[s] = sum(sheng_mean_price[s]) / len(sheng_mean_price[s])
        sheng_high_price[s] = sum(sheng_high_price[s]) / len(sheng_high_price[s])

    sql = "select * from ProductInfo where sheng='{}'".format(sheng_name)
    cursor.execute(sql)
    datas = cursor.fetchall()
    product_low_price = {}
    product_mean_price = {}
    product_high_price = {}

    for data in datas:
        product, sheng, name, low_price, high_price, mean_price, pub_time = data
        if product not in product_mean_price:
            product_mean_price[product] = []
        product_mean_price[product].append(mean_price)

        if product not in product_low_price:
            product_low_price[product] = []
        product_low_price[product].append(low_price)

        if product not in product_high_price:
            product_high_price[product] = []
        product_high_price[product].append(high_price)

    products = list(product_low_price.keys())
    product_counts = {}
    for s in products:
        product_counts[s] = len(product_low_price[s])
        product_low_price[s] = sum(product_low_price[s]) / len(product_low_price[s])
        product_mean_price[s] = sum(product_mean_price[s]) / len(product_mean_price[s])
        product_high_price[s] = sum(product_high_price[s]) / len(product_high_price[s])

    # jsonify函数返回供用户处理的序列化json数据
    return jsonify({
        'date': dates,
        'date_low_price': [date_low_price[c] for c in dates],
        'date_mean_price': [date_mean_price[c] for c in dates],
        'date_high_price': [date_high_price[c] for c in dates],
        'date_price_box': [date_price_box[c] for c in dates],
        'shengs': shengs,
        'sheng_counts': [sheng_counts[c] for c in shengs],
        'sheng_low_price': [sheng_low_price[c] for c in shengs],
        'sheng_mean_price': [sheng_mean_price[c] for c in shengs],
        'sheng_high_price': [sheng_high_price[c] for c in shengs],
        'products': products,
        'product_counts': [product_counts[c] for c in products],
        'product_low_price': [product_low_price[c] for c in products],
        'product_mean_price': [product_mean_price[c] for c in products],
        'product_high_price': [product_high_price[c] for c in products],
    })


@app.route('/product_compare_analysis/<product_name1>/<product_name2>')  # Flask中的route()装饰器用于将URL绑定到函数。
def product_compare_analysis(product_name1, product_name2):
    """农产品比较"""
    conn = sqlite3.connect('agriculture_products_infos.db')
    cursor = conn.cursor()
    sql = "select * from ProductInfo where product='{}'".format(product_name1)
    cursor.execute(sql)
    datas1 = cursor.fetchall()

    sql = "select * from ProductInfo where product='{}'".format(product_name2)
    cursor.execute(sql)
    datas2 = cursor.fetchall()

    date_mean_price1 = {}
    date_low_price1 = {}
    date_high_price1 = {}

    sheng_count = {product_name1: set(), product_name2: set()}
    for data in datas1:
        product, sheng, name, low_price, high_price, mean_price, pub_time = data
        sheng_count[product_name1].add(sheng)

        if pub_time not in date_mean_price1:
            date_mean_price1[pub_time] = []
        date_mean_price1[pub_time].append(mean_price)

        if pub_time not in date_low_price1:
            date_low_price1[pub_time] = []
        date_low_price1[pub_time].append(low_price)

        if pub_time not in date_high_price1:
            date_high_price1[pub_time] = []
        date_high_price1[pub_time].append(high_price)

    dates = list(date_mean_price1.keys())[::-1]
    dates = sorted(dates)

    date_price_box1 = {}
    for s in dates:
        date_price_box1[s] = date_mean_price1[s]
        date_mean_price1[s] = sum(date_mean_price1[s]) / len(date_mean_price1[s])
        date_low_price1[s] = sum(date_low_price1[s]) / len(date_low_price1[s])
        date_high_price1[s] = sum(date_high_price1[s]) / len(date_high_price1[s])

    date_mean_price2 = {}
    date_low_price2 = {}
    date_high_price2 = {}

    for data in datas2:
        product, sheng, name, low_price, high_price, mean_price, pub_time = data
        sheng_count[product_name2].add(sheng)

        if pub_time not in date_mean_price2:
            date_mean_price2[pub_time] = []
        date_mean_price2[pub_time].append(mean_price)

        if pub_time not in date_low_price2:
            date_low_price2[pub_time] = []
        date_low_price2[pub_time].append(low_price)

        if pub_time not in date_high_price2:
            date_high_price2[pub_time] = []
        date_high_price2[pub_time].append(high_price)

    date_price_box2 = {}
    for s in dates:
        date_price_box2[s] = date_mean_price2[s]
        date_mean_price2[s] = sum(date_mean_price2[s]) / len(date_mean_price2[s])
        date_low_price2[s] = sum(date_low_price2[s]) / len(date_low_price2[s])
        date_high_price2[s] = sum(date_high_price2[s]) / len(date_high_price2[s])

    sheng_count[product_name1] = len(sheng_count[product_name1])
    sheng_count[product_name2] = len(sheng_count[product_name2])

    # jsonify函数返回供用户处理的序列化json数据
    return jsonify({
        'date': dates,
        'date_low_price1': [date_low_price1[c] for c in dates],
        'date_mean_price1': [date_mean_price1[c] for c in dates],
        'date_high_price1': [date_high_price1[c] for c in dates],
        'date_low_price2': [date_low_price2[c] for c in dates],
        'date_mean_price2': [date_mean_price2[c] for c in dates],
        'date_high_price2': [date_high_price2[c] for c in dates],
        'date_price_box1': [date_price_box1[c] for c in dates],
        'date_price_box2': [date_price_box2[c] for c in dates],
        'product': [product_name1, product_name2],
        'sheng_counts': [sheng_count[s] for s in [product_name1, product_name2]]
    })


def arima_model_train_eval(history, ):
    # 构造 ARIMA 模型
    model = ARIMA(history, order=(0, 0, 0))
    # 基于历史数据训练
    model_fit = model.fit(disp=0)
    # 预测下一个时间步的值
    output = model_fit.forecast()
    yhat = output[0][0]
    return yhat


@app.route('/predict_product_price/<product_name>')  # Flask中的route()装饰器用于将URL绑定到函数。
def predict_product_price(product_name):
    conn = sqlite3.connect('agriculture_products_infos.db')
    cursor = conn.cursor()
    sql = "select * from ProductInfo where product='{}'".format(product_name)
    cursor.execute(sql)
    datas = cursor.fetchall()  # 为选择农产品的所有信息

    all_time = []  # 列表

    date_mean_price = {}   # 字典

    for data in datas:
        product, sheng, name, low_price, high_price, mean_price, pub_time = data
        if pub_time not in date_mean_price:
            date_mean_price[pub_time] = []  # 以时间为键这，值为这一天这种农产品的所有平均价格列表
        date_mean_price[pub_time].append(mean_price)  # 以平均价格为值

    all_time = list(date_mean_price.keys())[::-1]  # 从最后一个元素到第一个元素进行复制
    for s in all_time:
        date_mean_price[s] = sum(date_mean_price[s]) / len(date_mean_price[s])  # 将所有平均价格求平均

    all_mean_price = [date_mean_price[a] for a in all_time] # 获取该种农产品所有日期的平均价格
    all_mean_price = all_mean_price[::-1]  # 从最后一个元素到第一个元素进行复制

    train = all_mean_price[:-5]  # 选取位置0到-5之前的元素做训练集
    test = all_mean_price[-5:]  # 选取位置-5到0之前的元素做测试集
    # 自回归方式训练和预测 ARIMA 模型
    history = train  # 训练集作为历史数据
    arima_predictions = []
    for t in tqdm(range(len(test))):   # tqdm会在控制台显示进度条
        yhat = arima_model_train_eval(history)  # 利用历史数据训练 ARIMA 模型，并预测下一个时刻的温度
        arima_predictions.append(yhat)   # 存储预测的数据
        obs = test[t] + random.randint(-10, 10) / 1000
        history.append(obs)

    # predict
    arima_error = mean_squared_error(test, arima_predictions)  # 测试机和训练集的误差
    print('Test MSE: %.3f' % arima_error)
    arima_predictions = history + arima_predictions

    # jsonify函数返回供用户处理的序列化json数据
    return jsonify({'all_time': all_time,
                    'all_data': all_mean_price,
                    'add_predict': arima_predictions,
                    'test_count': len(test),
                    'error': arima_error})


if __name__ == "__main__":
    app.run(host='127.0.0.1')
