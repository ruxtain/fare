#! /Users/michael/anaconda3/bin/python
# -*- coding: utf-8 -*-
# @Author: michael
# @Date:   2018-07-17 19:54:18
# @Last Modified by:   michael
# @Last Modified time: 2018-07-18 11:06:53

'''
对数据进行一些简单的管理
尚未完成。
'''

import json
import os

root = os.path.dirname(__file__)

def create_user():
    username = input('username: ')
    password = input('password: ')
    filepath = os.path.join(root, 'data/users.json')
    with open(filepath, 'a', encoding='utf-8'):
        json.dumps()