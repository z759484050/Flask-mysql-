from flask import Blueprint, redirect, render_template, request, url_for, session, jsonify
from app.models import *
from utils.ch_login import is_login
from utils.util import get_page
import time
import os

home = Blueprint('home', __name__)


@home.route('/index', methods=['GET'])
def index():
    return render_template('home/index.html')


@home.route('/head', methods=['GET'])
@is_login
def head():
    '''
    home的head
    :return:
    '''
    if request.method == 'GET':
        user = session.get('username')
        return render_template('home/head.html', user=user)


@home.route('/left', methods=['GET'])
def left():
    '''
    左侧菜单栏
    :return:
    '''
    if request.method == 'GET':
        return render_template('home/left.html')


@home.route('/part_list', methods=['GET', 'POST'])
@is_login
def part_list():
    '''
    显示零件信息列表
    :return:
    '''
    if request.method == 'GET':
        parts, paginate = get_page(request, Part, 'part_id')
        suppliers = Supplier.query.order_by('supplier_id').all()
        # 返回获取到的零件信息给前端页面
        return render_template('home/part_list.html', parts=enumerate(parts),
                               suppliers=suppliers, paginate=paginate)


@home.route('/part_add', methods=['POST'])
def part_add():
    if request.method == 'POST':
        try:
            # 获取前端传过来的数据
            part_name = request.json['part_name']
            part_price = request.json['part_price']
            part_psupp = request.json['part_psupp']
            part_ssupp = request.json['part_ssupp']

            if len(part_ssupp) == 0:
                part_ssupp = None

            # 判断信息是否合法
            if (len(part_name) and len(part_price) and len(part_psupp)):
                part_old = Part.query.filter_by(part_name=part_name).first()
                if len(part_name) > 16:
                    msg = '零件名称不能超过16位字符'
                    return msg
                elif part_old != None:
                    msg = '零件名称已经存在，不可重复'
                    return msg
                elif part_psupp == part_ssupp:
                    msg = '主要供应商和次要供应商不能相同'
                    return msg

                # 添加信息
                part = Part(part_name=part_name, part_price=part_price,
                            p_supplier_id=part_psupp, s_supplier_id=part_ssupp)
                part.save()
                msg = '1'
                return msg
            else:
                msg = '输入的数据不能为空'
                return msg
        except Exception as e:
            msg = str(e)
            return msg


@home.route('/part_delete', methods=['POST'])
def part_delete():
    if request.method == 'POST':
        try:
            # 获取前端传过来的数据
            part_id = request.json['part_id']
            print(part_id)
            # 如果该零件已经生成订货信息，则考虑两种情况
            order_written = Order.query.filter(Order.part_id == part_id, Order.order_status == 1,
                                               Order.purchased_num < Order.order_num).first()
            if order_written != None:
                status = '2'
                msg = '该零件信息所存在于一个订货信息中(%08d)，且该该零件未采购完，因此无法删除该零件信息' % order_written.order_id
                return {'status': status, 'msg': msg}
            else:
                # 删除符合条件的订货信息
                order = Order.query.filter_by(part_id=part_id).all()
                db.session.delete(order)
                # 删除符合条件的事务信息
                affair = Affair.query.filter_by(part_id=part_id, affair_status=0).all()
                db.session.delete(affair)
                # 删除零件在库存清单中的数据
                store = Store.query.filter_by(part_id=part_id).first()
                db.session.delete(store)
                # 删除零件信息
                part = Part.query.filter_by(part_id=part_id).first()
                db.session.delete(part)

                db.session.commit()

                # 计算删除的信息数量
                store_len = 0 if store == None else len(store)
                order_len = 0 if order == None else len(order)
                affair_len = 0 if affair == None else len(affair)

                msg = '零件信息删除成功，同时删除了与该零件有关的%d条库存信息、%d条订货信息和%d条事务信息' % (store_len, order_len, affair_len)
                status = '1'
                return {'status': status, 'msg': msg}
        except Exception as e:
            msg = str(e)
            status = '2'
            return {'status': status, 'msg': msg}


@home.route('/part_alter', methods=['POST'])
def part_alter():
    if request.method == 'POST':
        try:
            # 获取前端传过来的数据
            part_id = request.json['part_id']
            part_name = request.json['part_name']
            part_price = float(request.json['part_price'])
            psupp_id = request.json['psupp_id']
            ssupp_id = request.json['ssupp_id']

            if (len(part_name)):
                part_old = Part.query.filter(Part.part_name == part_name, Part.part_id != part_id).first()
                if len(part_name) > 16:
                    msg = '零件名称不能超多16位字符'
                    return msg
                elif part_old != None:
                    msg = '零件名称已经存在，不可重复'
                    return msg
                else:
                    # 修改零件信息
                    part = Part.query.filter_by(part_id=part_id).first()
                    part.part_name = part_name
                    part.part_price = part_price
                    part.p_supplier_id = psupp_id
                    part.s_supplier_id = ssupp_id
                    db.session.commit()

                    msg = '1'
                    return msg
            else:
                msg = '零件名称不能为空'
                return msg

        except Exception as e:
            msg = str(e)
            return msg


@home.route('/affair_list', methods=['GET'])
@is_login
def affair_list():
    '''
    显示事务信息列表
    :return:
    '''
    if request.method == 'GET':
        affair_ls, paginate = get_page(request, Affair, 'affair_id')
        orders = Order.query.filter(Order.order_status == 1, Order.purchased_num < Order.order_num).all()
        # 返回获取到的事务信息给前端页面
        return render_template('home/affair_list.html', affair_ls=enumerate(affair_ls), paginate=paginate, orders=orders)


@home.route('/affair_opt', methods=['GET'])
def affair_opt():
    if request.method == 'GET':
        # 返回获取到的事务信息给前端页面
        store_id_name = Store.query.order_by('part_id').all()
        # 返回获取到的订单信息
        orders = Order.query.filter(Order.order_status == 1, Order.purchased_num < Order.order_num).all()
        return render_template('home/affair_opt.html', store_id_name=store_id_name, orders=orders)


# @home.route('/affair_search', methods=['POST'])
# def affair_search():
#     if request.method == 'POST':
#         fuzzy_data = request.json['fuzzy_data']
#         fuzzy_data = fuzzy_data.strip()
#         fuzzy_search = Part.query.filter(Part.part_name.like(fuzzy_data + '%') if fuzzy_data is not None else "").all()
#         name_list = list()
#         for idx, name in enumerate(fuzzy_search):
#             name_list.append({idx: name.part_name})
#         return jsonify(name_list)


@home.route('/affair_submit', methods=['POST'])
def affair_submit():
    if request.method == 'POST':
        try:
            # 获取前端传来的数据
            part_id = request.json['part_id']
            part_num = request.json['part_num']
            is_in = request.json['is_in']
            order_id = request.json['order_id']
            print(order_id)

            if part_num <= 0:
                msg = '出入库零件的数量需要大于0'
                return msg

            store = Store.query.filter_by(part_id=part_id).first()
            # 判断零件数量是否合法
            # 如果是入库
            if is_in:
                if order_id != None:
                    order_list = Order.query.filter_by(order_id=order_id).first()
                    if order_list.part_id != part_id:
                        msg = '入库零件的信息与订单信息中零件的信息不匹配'
                        return msg
                    # 如果大于最大上限
                    elif (part_num + store.store_num) > store.store_max:
                        msg = '该零件入库后，库存数量大于库存最大值，因此该零件无法进行入库操作'
                        return msg
                    # else:
                    # # 添加库存
                    # store.store_num = store.store_num + part_num
                    # # 更新对应的订货信息
                    # order = Order.query.filter_by(order_id=order_id).first()
                    # order.purchased_num = min((order.purchased_num + part_num), order.order_num)
                    # time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    # curr_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    # order.order_time = curr_time
                    # db.session.commit()
                else:
                    if (part_num + store.store_num) > store.store_max:
                        msg = '该零件入库后，库存数量大于库存最大值，因此该零件无法进行入库操作'
                        return msg
            else:
                # 如果是出库
                # 判断出库是否大于库存量
                if part_num > store.store_num:
                    msg = '该零件库存量少于零件出库数量，因此该零件无法进行出库操作'
                    return msg
                # else:
                #     # 减少库存数量
                #     store.store_num = store.store_num - part_num
                #     db.session.commit()
                else:
                    order_id = None

            # 更新事务信息
            affair = Affair(part_id=part_id, order_id=order_id, affair_type=is_in,
                            affair_num=part_num, affair_finish_time=None, affair_status=0)
            affair.save()

            msg = '1'
            return msg
        except Exception as e:
            msg = str(e)
            return msg


@home.route('/affair_delete', methods=['POST'])
def affair_delete():
    if request.method == 'POST':
        '''
        删除事务信息
        '''
        try:
            affair_id = request.json['affair_id']
            affair = Affair.query.filter_by(affair_id=affair_id).first()
            if affair.affair_status == 1:
                msg = '该事务已经被处理，不可删除'
                return msg
            else:
                db.session.delete(affair)
                db.session.commit()
        except Exception as e:
            msg = str(e)
            return msg


@home.route('/affair_alter', methods=['POST'])
def affair_alter():
    if request.method == 'POST':
        try:
            affair_id = request.json['affair_id']
            part_id = request.json['part_id']
            order_id = request.json['order_id']
            affair_type = request.json['affair_type']
            affair_num = request.json['affair_num']

            store = Store.query.filter_by(part_id=part_id).first()

            # 如果是入库
            if affair_type == 1:
                if order_id != None:
                    order = Order.query.filter_by(order_id=order_id, part_id=part_id).first()
                    if order == None:
                        msg = '入库零件的信息与订单信息中零件的信息不匹配'
                        return msg
                    else:
                        if affair_num + store.store_num > store.store_max:
                            msg = '入库零件数量加上现存库存数量超过库存最大值，因此无法修改事务信息'
                            return msg
                        else:
                            affair = Affair.query.filter_by(affair_id=affair_id).first()
                            affair.affair_type = affair_type
                            affair.order_id = order_id
                            affair.affair_num = affair_num
                            db.session.commit()
                            msg = '1'
                            return msg
            else:
                # 如果是出库
                if affair_num > store.store_num:
                    msg = '出库零件的数量大于库存数量，因此无法修改事务信息'
                    return msg
                else:
                    affair = Affair.query.filter_by(affair_id=affair_id).first()
                    affair.affair_type = affair_type
                    affair.order_id = None
                    affair.affair_num = affair_num
                    db.session.commit()
                    msg = '1'
                    return msg

        except Exception as e:
            msg = str(e)
            return msg


@home.route('/supplier_list', methods=['GET'])
@is_login
def supplier_list():
    '''
    显示供应商信息列表
    :return:
    '''
    if request.method == 'GET':
        suppliers, paginate = get_page(request, Supplier, 'supplier_id')
        # 返回获取到的事务信息给前端页面
        return render_template('home/supplier_list.html', suppliers=enumerate(suppliers), paginate=paginate)


@home.route('/supplier_add', methods=['POST'])
def supplier_add():
    if request.method == 'POST':
        try:
            # 获取前端传过来的数据
            supplier_conname = request.json['supplier_conname']
            supplier_name = request.json['supplier_name']
            supplier_contact = request.json['supplier_contact']
            supplier_address = request.json['supplier_address']

            # 判断信息是否合法
            if (len(supplier_conname) and len(supplier_name) and len(supplier_contact) and len(supplier_address)):
                supplier_old = Supplier.query.filter_by(supplier_name=supplier_name,
                                                        supplier_contact_name=supplier_conname).first()
                if len(supplier_conname) > 20:
                    msg = '供应商（公司）名称不能超过20位字符'
                    return msg
                elif len(supplier_name) > 16:
                    msg = '联系人姓名不能超过16位字符'
                    return msg
                elif len(supplier_contact) > 11:
                    msg = '供应商联系方式不能超过11位字符'
                    return msg
                elif len(supplier_address) > 50:
                    msg = '供应商地址不能超过50位字符'
                    return msg
                elif supplier_old != None:
                    msg = '该供应商信息已经存在，不可重复'
                    return msg

                # 添加信息
                supplier = Supplier(supplier_contact_name=supplier_conname, supplier_name=supplier_name,
                                    supplier_contact=supplier_contact, supplier_address=supplier_address)
                supplier.save()
                msg = '1'
                return msg
            else:
                msg = '输入的数据不能为空'
                return msg
        except Exception as e:
            msg = str(e)
            return msg


@home.route('/supplier_delete', methods=['POST'])
def supplier_delete():
    if request.method == 'POST':
        try:
            supplier_id = request.json['supplier_id']
            # 判断该供应商是否是某一零件的主键
            part1 = Part.query.filter_by(p_supplier_id=supplier_id).first()
            if part1 != None:
                part_id = part1.part_id
                part_name = part1.part_name
                msg = '该供应商是%s(%08d)的主要供应商，无法删除' % (part_name, part_id)
                return msg

            # 判断该供应商是否是某一零件的次要供应商
            part2 = Part.query.filter_by(s_supplier_id=supplier_id).all()
            if part2 != None:
                # 将次要供应商都设为None
                for part in part2:
                    part.s_supplier_id = None
                db.session.commit()

            supplier = Supplier.query.filter_by(supplier_id=supplier_id).first()
            db.session.delete(supplier)
            db.session.commit()
            msg = '1'
            return msg
        except Exception as e:
            msg = str(e)
            return msg


@home.route('/supplier_alter', methods=['POST'])
def supplier_alter():
    if request.method == 'POST':
        try:
            # 获取前端数据
            supplier_id = request.json['supplier_id']
            supplier_conname = request.json['supplier_conname']
            supplier_name = request.json['supplier_name']
            supplier_contact = request.json['supplier_contact']
            supplier_address = request.json['supplier_address']

            if (len(supplier_conname) and len(supplier_name) and len(supplier_contact) and len(supplier_address)):
                supplier_old = Supplier.query.filter(Supplier.supplier_name == supplier_name,
                                                     Supplier.supplier_contact_name == supplier_conname,
                                                     Supplier.supplier_id != supplier_id).first()
                if len(supplier_conname) > 20:
                    msg = '供应商名称不能超过20位字符字符'
                    return msg
                elif len(supplier_name) > 16:
                    msg = '联系人姓名不能超过16位字符字符'
                    return msg
                elif len(supplier_contact) > 11:
                    msg = '供应商联系方式不能超过11位字符'
                    return msg
                elif len(supplier_address) > 50:
                    msg = '供应商地址不能超过50位字符'
                    return msg
                elif supplier_old != None:
                    msg = '该供应商信息已经存在，不可重复'
                    return msg

                # 修改对应的信息
                supplier = Supplier.query.filter_by(supplier_id=supplier_id).first()
                supplier.supplier_contact_name = supplier_conname
                supplier.supplier_name = supplier_name
                supplier.supplier_contact = supplier_contact
                supplier.supplier_address = supplier_address
                db.session.commit()

                msg = '1'
                return msg
            else:
                msg = '数据不能为空'
                return msg

        except Exception as e:
            msg = str(e)
            return msg


@home.route('/order_list', methods=['GET'])
@is_login
def order_list():
    '''
    显示订货信息列表
    :return:
    '''
    if request.method == 'GET':
        orders, paginate = get_page(request, Order, 'order_id')
        # 返回获取到的事务信息给前端页面
        return render_template('home/order_list.html', orders=enumerate(orders), paginate=paginate)


@home.route('/get_orderurl', methods=['POST'])
def get_orderurl():
    if request.method == 'POST':
        try:
            def listdir(path, order_name):  # 传入存储的list
                for file_name in os.listdir(path):
                    file_path = os.path.join(path, file_name)
                    if os.path.isdir(file_path):
                        listdir(file_path, order_name)
                    else:
                        order_name.append(file_name)

            order_name = []
            strtime_ = time.strftime("%Y-%m-%d")
            last_order = '订货报表' + strtime_ + '.xls'
            order_dir = 'static/order_folder/'
            listdir(order_dir, order_name)

            if len(order_name) == 0:
                status = '2'
                msg = '当前无订货报表可以导出'
                return {'status': status, 'msg': msg}
            elif last_order in order_name:
                status = '1'
                msg = '是否需要导出今天(%s)的订货报表' % strtime_
                order_url = '/' + order_dir + last_order
                last_order_name = last_order.replace('.xls', '')
                return {'status': status, 'msg': msg, 'url': order_url, 'order_name': last_order_name}
            else:
                last_order_name = order_name[-1].replace('.xls', '')
                status = '1'
                msg = '今天的订货报表尚未生成，只能导出' + last_order_name + '的订货报表'
                order_url = '/' + order_dir + last_order_name + '.xls'
                return {'status': status, 'msg': msg, 'url': order_url, 'order_name': last_order_name}

        except Exception as e:
            status = '2'
            msg = str(e)
            return {'status': status, 'msg': msg}


@home.route('/store_list', methods=['GET'])
@is_login
def store_list():
    '''
    显示库存清单列表
    :return:
    '''
    if request.method == 'GET':
        stores, paginate = get_page(request, Store, 'store_id')
        parts = Part.query.with_entities(Part.part_id, Part.part_name).order_by('part_id').all()
        # 返回获取到的事务信息给前端页面
        return render_template('home/store_list.html', stores=enumerate(stores),
                               parts=parts, paginate=paginate)


@home.route('/store_add', methods=['POST'])
def store_add():
    if request.method == 'POST':
        try:
            # 获取前端的数据
            part_id = request.json['part_id']
            store_num = request.json['store_num']
            store_cv = request.json['store_cv']
            store_max = request.json['store_max']

            is_exist = Store.query.filter_by(part_id=part_id).first()

            if is_exist != None:
                msg = '该零件已经存在于库存清单中'
                return msg

            if store_max < store_cv:
                msg = '零件的库存临界值不能大于库存最大值'
                return msg
            elif store_max < store_num:
                msg = '零件的库存最大值不能小于当前库存量'
                return msg

            # 添加数据
            store = Store(part_id=part_id, store_num=store_num, store_cv=store_cv, store_max=store_max)
            store.save()

            msg = '1'
            return msg
        except Exception as e:
            msg = str(e)
            return msg


@home.route('/store_alter', methods=['POST'])
def store_alter():
    if request.method == 'POST':
        try:
            store_id = request.json['store_id']
            store_num = request.json['store_num']
            store_cv = request.json['store_cv']
            store_max = request.json['store_max']

            if store_max < store_cv:
                msg = '零件的库存临界值不能大于库存最大值'
                return msg
            elif store_max < store_num:
                msg = '零件的库存最大值不能小于当前库存量'
                return msg

            # 更新库存信息
            store = Store.query.filter_by(store_id=store_id).first()
            store.store_num = store_num
            store.store_cv = store_cv
            store.store_max = store_max
            db.session.commit()

            msg = '1'
            return msg

        except Exception as e:
            msg = str(e)
            return msg


@home.route('/change_password', methods=['GET'])
def change_password():
    if request.method == 'GET':
        return render_template('home/change_password.html')


@home.route('/change_submit', methods=['POST'])
def change_submit():
    if request.method == 'POST':
        try:
            # 获取原密码信息
            user_id = session['user_id']
            ori_password = request.json['ori_password']
            new_password = request.json['new_password']

            user = Users.query.filter_by(user_id=user_id, password=ori_password).first()
            if user == None:
                msg = '原密码错误'
                return msg
            elif ori_password == new_password:
                msg = '新密码不等于原密码相同'
                return msg
            else:
                user.password = new_password
                db.session.commit()

                msg = '1'
                return msg
        except Exception as e:
            msg = str(e)
            return msg


@home.route('/loginout', methods=['GET'])
def loginout():
    '''
    退出登录
    :return:
    '''
    if request.method == 'GET':
        # 清空session
        session.clear()
        # 跳转到登录页面

        return redirect(url_for('login.index'))
