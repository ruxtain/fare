#! /Users/michael/anaconda3/bin/python
# -*- coding: utf-8 -*-
# @Author: michael
# @Date:   2018-07-17 19:12:27
# @Last Modified by:   ruxtain
# @Last Modified time: 2018-07-19 09:20:06

'''

用一个 json 文件（字典）保存所有的用户信息
每次新人注册更新这个字典
（由于是内部共享，不开放注册，用户信息直接写死）。

用一个 json 文件（字典）保存所有的文件信息，
文件名，上传时间，文件大小和上传者

用一堆 session 文件保存 session。

约定：
filename 指 basename
filepath 指 全路径

'''

from urllib.parse import parse_qs
import uuid
import time
import json
import os

expire_in = 86400 # 24 hours
root = os.path.dirname(__file__)
users_path = os.path.join(root, 'data/users.json')
sessions_path = os.path.join(root, 'data/sessions')
file_storage_path = os.path.join(root, 'storage')
file_info_path = os.path.join(root, 'data/file_info')

os.makedirs(sessions_path, exist_ok=True)
os.makedirs(file_info_path, exist_ok=True)

def _format_file_size(size): # Byte
    if size > 1024**3: # GB
        size = '{:.2f} GB'.format(size/(1024**3))
    elif size > 1024**2: # MG
        size = '{:.2f} MB'.format(size/(1024**2))
    elif size > 1024:
        size = '{:.2f} KB'.format(size/(1024))
    else:
        size = '{:.2f} Bytes'.format(size)
    return size

def get_users():
    with open(users_path, encoding='utf-8') as f:
        users = json.loads(f.read())
        return users

def auth(username, password):
    '''根据用户名和密码确认用户是否登录'''
    users = get_users()
    _password = users.get(username)
    if not password:
        return False
    else:
        return _password == password

def is_login(env):
    '''
    env: 和普通 view 函数的输入值一样
    通过比对用户发送的 cookie 和服务端的 session 确认用户是否出于登入状态
    username 暂时没用上..晚点看
    '''
    session = get_session(env) # 字典
    if session:
        return time.time() <= float(session['expire']) # 还没有过期
    else:
        return False

def get_session_file(env):
    '''
    session 文件存在则返回文件名
    不存在返回 False
    '''
    try:
        raw_cookies = env['HTTP_COOKIE']
        cookies = parse_qs(raw_cookies.replace(' ', '')) # 字典
    except KeyError:
        return False
    try:
        session_id = cookies['sid'][0]
    except KeyError:
        return False
    session_file = os.path.join(sessions_path, session_id)
    return session_file if os.path.exists(session_file) else False


def del_session(env):
    '''
    删除掉对应的 session 让用户从服务器登出
    配合 view 的跳转完成登出动作
    '''
    session_file = get_session_file(env)
    if session_file:
        os.remove(session_file)

def set_session(username):
    '''
    用户登录时，根据用户名和时间戳生成
    '''
    session_id = str(uuid.uuid1())
    # exist_ok 意思是目录已经存在的话 不报错
    os.makedirs(sessions_path, mode=0o755, exist_ok=True)
    session_file = os.path.join(sessions_path, session_id)
    # 单纯用时间戳表示用户的登录过期时间
    session_data = {'username': username, 'expire': str(time.time() + expire_in)}
    with open(session_file, 'w', encoding='utf-8') as f:
        f.write(json.dumps(session_data))
    return session_id # 返回 session_id 方便生成 cookie
        
def get_session(env):
    '''
    根据用户访问时带的 cookies 里的 sid 来找对应的 session
    以字典形式返回 session 文件的数据
    cookie 格式不符合要求或者 session 文件不存在则返回 False
    '''
    session_file = get_session_file(env) # 找不到则为 False
    if session_file:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session = json.loads(f.read()) 
                return session
        except FileNotFoundError:
            return False
    else:
        return False

def get_username(env):
    '''
    只要带 session id，就可以在页面上显示用户的名字，并给一个退出登录的选择
    因为已经登录的人才会调用这个函数，所以不再校验是否登录
    '''
    session = get_session(env)
    if session:
        return session['username']
    else:
        return '匿名者' # 这行永不会用到
    

def insert_file_info(filename, username):
    '''
    file_basename: 文件名
    username: 用户名
    保存用户上传文件的信息，每次谁谁什么时候上传...
    '''
    filepath = os.path.join(file_storage_path, filename) # 文件的全路径
    infopath = os.path.join(file_info_path, filename+'.data') # 文件信息的全路径
    info = {
        'username': username, 
        'datetime': time.strftime(r'%F %T'),
        'size': os.path.getsize(filepath)
    }
    with open(infopath, 'w', encoding='utf-8') as f:
        f.write(json.dumps(info))

def get_file_info(filename):
    infopath = os.path.join(file_info_path, filename+'.data')
    with open(infopath, 'r', encoding='utf-8') as f:
        info = json.loads(f.read())
        return info
    

















































