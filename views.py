#! /Users/michael/anaconda3/bin/python
# -*- coding: utf-8 -*-
# @Author: michael
# @Date:   2018-07-17 16:20:26
# @Last Modified by:   ruxtain
# @Last Modified time: 2018-07-19 08:42:51

from cgi import FieldStorage 
from urllib.parse import parse_qs, quote

import mimetypes
import glob
import os

import secure

root = os.path.dirname(__file__)
storage = os.path.join(root, 'storage')


def _buffer(ifile, blocksize=1048576):
    '''用于读取大文件'''
    while True:
        chunk = ifile.read(blocksize)
        if not chunk:
            break
        yield chunk

def _is_file(item):
    '''
    遍历 cgi.FieldStorage 的值，找到是文件的那项
    这样前端修改 <input> 的 name 标签也不影响后台
    '''
    return getattr(item, '_binary_file', None) and item.filename

def _save_file(file, name):
    with open(os.path.join(storage, name), 'wb') as f:
        for chunk in _buffer(file):
            f.write(chunk)

def render(name, context={}):
    '''
    name: 模板文件名
    context: 替换模板内容的字典
    return: 返回字节串
    '''
    with open(os.path.join(root, 'templates' ,name), 'r', encoding='utf-8') as f:
        content = f.read()
        content = content % context
        return content.encode('utf-8')

def login_required(url):
    '''
    未登录的用户会跳转了形参 url 指定的位置
    关于装饰器，啰嗦一句，装饰器返回的结果就是被装饰函数调用后返回的结果，
    所以里面的函数一定要调用，或者直接返回“调用”后的返回值

    注释1: 关于返回值。302 的跳转完全的浏览器乖乖听服务器的指示而跳转。
    假如浏览器不配合，拿到 302 当作 200 处理，那么我的数据会泄露吗？
    不会，因为我对这个未经登录的请求返回的是 b''，所以浏览器是否配合不影响安全性。
    '''
    def decor(func):
        def wrapper(env):
            if secure.is_login(env): # 登录了的话 什么都不做
                return func(env)
            else:                    # 没登录则跳转
                status = '302 FOUND' # 有 302 就不需要再制作页面内容了
                headers = [
                    ('Content-Type', 'text/html; charset=utf-8'),
                    ('Status', '302'),
                    ('Location', url),
                ]
                return status, headers, b'' #(注释1)
        return wrapper
    return decor

def page_404(env):
    status = '404 NOT FOUND'
    headers = [('Content-Type', 'text/html; charset=utf-8')]
    return status, headers, b'<h1>404 ERROR</h1><p>Page not found</p>'    

def login(env):

    status = '200 OK'
    headers = [('Content-Type', 'text/html; charset=utf-8')]

    if env['REQUEST_METHOD'] == 'GET':
        body = render("login.html")

    elif env['REQUEST_METHOD'] == 'POST':
        length = int(env['CONTENT_LENGTH'])
        post_data = env['wsgi.input'].read(length)

        form = parse_qs(post_data.decode('utf-8'))
        username = form.get('username', [''])[0]
        password = form.get('password', [''])[0]
        if secure.auth(username, password):
            body = '登录成功！'.encode('utf-8')
            session_id = secure.set_session(username)
            headers.append(('Set-Cookie', 'sid={}'.format(session_id))) 
            status = '302 FOUND' # 覆盖之前的200 ok
            headers.append(('Location', '/')) 
            # wsgi 服务器自带了一个 sessionid.. 我后面看，现在先用自定义的
        else:
            body = '<h2>登录失败..联系服务器机主老谭问问看..</h2><a href="/">带我回登录页~</a>'.encode('utf-8')

    return status, headers, body

@login_required('/login')
def logout(env):
    secure.del_session(env)
    status = '302 FOUND'
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Location', '/login'),
    ]
    return status, headers, b''

@login_required('/login')
def index(env):
    status = '200 OK'
    body = render("index.html", {"username": secure.get_username(env)})
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(body))),
    ]
    return status, headers, body

@login_required('/login')
def details(env):
    status = '200 OK'
    headers = [('Content-Type', 'text/html; charset=utf-8')]
    trs = ''
    for file in glob.glob(storage + '/*'):
        file = os.path.basename(file)
        link = '/download?filename={}'.format(file)
        info = secure.get_file_info(file)

        size =  secure._format_file_size(info['size'])
        datetime = info['datetime']
        username = info['username']

        tr = '<tr><td><a href="{}" >{}</a></td><td>{}</td><td>{}</td><td>{}</td><tr>'.format(link, file, size, datetime, username)
        trs += tr
    trs += '<p><a href="/">回到首页</a></p>'
    return status, headers, render("details.html", context={"文件信息": trs})

@login_required('/login')
def home(env):
    status = '200 OK'
    headers = [('Content-Type', 'text/html; charset=utf-8')]
    trs = ''
    for file in glob.glob(storage + '/*'):
        file = os.path.basename(file)
        link = '/download?filename={}'.format(file)
        info = secure.get_file_info(file)

        size =  secure._format_file_size(info['size'])
        datetime = info['datetime']
        username = info['username']

        tr = '<tr><td><a href="{}" >{}</a></td><td>{}</td><td>{}</td><td>{}</td><tr>'.format(link, file, size, datetime, username)
        trs += tr
    context = {
        "username": secure.get_username(env),
        "file_info": trs,
    }
    return status, headers, render("home.html", context=context)

@login_required('/login')
def upload(env):
    status = '302 FOUND' # 有 302 就不需要再制作页面内容了
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Status', '302'), # must be str
        ('Location', '/'),
    ]
    form = FieldStorage(environ=env, fp=env['wsgi.input'])
    for key in form.keys():
        data = form[key]
        if _is_file(data):
            name = data.filename # basename
            file = data.file
            _save_file(file, name)
            username = secure.get_username(env)
            secure.insert_file_info(filename=name, username=username)
    return status, headers, b''

@login_required('/login')
def download(env):
    qs = parse_qs(env['QUERY_STRING'])
    filename = qs.get('filename', [''])[0] 

    filepath = os.path.join(storage, filename)
    with open(filepath, 'rb') as f:
        body = f.read()

    filetype = mimetypes.guess_type(filename)[0]
    if not filetype: # 无法识别的我就默认说它是二进制流
        filetype = 'application/octet-stream'
    status = '200 OK'
    headers = [
        ('Content-Type', '{}'.format(filetype)), # 下载文件的文件类型
        ('Content-Length', str(len(body))), # 有用的吧
        ('Content-Disposition', 'attachment; filename={}'.format(quote(filename))),  # 下载文件的文件名 中文名必须用 quote
    ]
    return status, headers, body













