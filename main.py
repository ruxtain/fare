#! /Users/michael/anaconda3/bin/python
# -*- coding: utf-8 -*-
# @Author: michael
# @Date:   2018-07-17 14:28:14
# @Last Modified by:   michael
# @Last Modified time: 2018-07-19 08:42:11

from wsgiref.simple_server import make_server
from cgi import FieldStorage 
import socket
import views

def url_route(url):
    '''找不到对应 url 的，返回一个 page_404'''
    return url_mapping.get(url, views.page_404)

def app(env, callback):
    url = env['PATH_INFO']
    worker = url_route(url) # 根据 url 找到对应的 view 函数 (抽象函数)
    status, headers, body = worker(env)
    callback(status, headers)
    return [body]

url_mapping = {
    '/': views.home,
    '/login': views.login,
    '/logout': views.logout,
    '/details': views.details,
    '/upload': views.upload,
    '/download': views.download,
}
        
if __name__ == '__main__':
    host = 'localhost'
    port = 8000
    with make_server(host, port, app) as server:
        print('Listening on {}:{} ...'.format(host, port))
        server.serve_forever()















