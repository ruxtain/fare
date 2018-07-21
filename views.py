"""
由于没有使用模板系统
模板文件中无逻辑运算
一切循环判断都在 views.py 里进行
"""

from cgi import FieldStorage 
from urllib.parse import parse_qs, quote

import mimetypes
import glob
import os
import re

import secure

root = os.path.dirname(__file__)
storage = os.path.join(root, 'storage')
os.makedirs(storage, exist_ok=True) # 确保目录存在

def _ellipsis(s, n=33):
    '''
    s 字符串
    n 保留的长度（中文一个字视为2个英文字母的长度）
    多余的部分变成 ...
    '''
    visible = ''
    length = 0
    for i in s:
        if len(i.encode('utf-8')) == len(i): # 英文字符
            length += 1
        else:
            length += 2
        visible += i
        if n <= length:
            break
    if visible != s:
        return visible + ' ...'
    else:
        return s

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

def _rename_file(filename):
    '''
    获得一个文件名，确保没有重复，有重复则加序号 ~1 , ~2
    '''
    target_filename, target_ext = os.path.splitext(filename)

    if target_ext: # 有后缀名
        pattern = '(^' + target_filename + ')~*(\\d*)(\\' + target_ext + '$)'  # 找出一个系列的名字
    else:
        pattern = '(^' + target_filename + ')~*(\\d*)' 

    matched = []
    for existing_filepath in glob.glob(storage + '/*'):
        existing_filename = os.path.basename(existing_filepath)
        match_filename = re.findall(pattern, existing_filename)

        if match_filename:
            match_filename = list(match_filename[0]) # 得到列表
            match_filename.append('') # 使得无后缀的多一项，有后缀也多一项，不过被忽略了
            if match_filename[1] == '':
                match_filename[1] = '0'
            matched.append(match_filename)

    if matched: # 有内容
        last_filename = max(matched, key=lambda i:int(i[1]))
        return "{}~{}{}".format(last_filename[0], int(last_filename[1])+1, last_filename[2])

    else:
        return filename # 原封不动返回


def _save_file(file, filename):
    '''
    3个功能：
    1. 将文件分块储存
    2. 确保没有重名文件，如果有，则用序号重命名，如 x，又上传x，则为 x_1, x_2..
    3. 返回这个最终文件名，以便文件信息录入
    '''
    final_filename = _rename_file(filename)
    with open(os.path.join(storage, final_filename), 'wb') as f:
        for chunk in _buffer(file):
            f.write(chunk)
    return final_filename

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
    关于装饰器，啰嗦一句，装饰器返回的结果必须是一个函数（不要去调用它）
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
        body = render("login.html", context={"error_info": ''})

    elif env['REQUEST_METHOD'] == 'POST':
        length = int(env['CONTENT_LENGTH'])
        post_data = env['wsgi.input'].read(length)

        form = parse_qs(post_data.decode('utf-8'))
        username = form.get('username', [''])[0]
        password = form.get('password', [''])[0]
        if secure.auth(username, password):
            body = '登录成功！'.encode('utf-8')
            # 创建 session 文件并返回 session id 的值
            session_id = secure.set_session(username)
            headers.append(('Set-Cookie', 'sid={}'.format(session_id))) 
            status = '302 FOUND' # 覆盖之前的200 ok
            headers.append(('Location', '/')) 
            # wsgi 服务器自带了一个 sessionid.. 我后面看，现在先用自定义的
        else:
            body = render("login.html", context={"error_info": '<span id="error_info" style="color: #a33">提示: 用户名或者密码错误</span>'})
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
def home(env):
    status = '200 OK'
    headers = [('Content-Type', 'text/html; charset=utf-8')]
    trs = ''
    tr_template = """<tr>
        <td><a title="{filename}" href="{download_link}" >{filename_elp}</a></td>
        <td>{size}</td>
        <td>{datetime}</td>
        <td>{username}</td>
        {delete_td}
    <tr>"""
    for filepath in glob.glob(storage + '/*'):
        filename = os.path.basename(filepath)
        download_link = '/download?filename={}'.format(filename)
        delete_link = '/delete?filename={}'.format(filename)
        info = secure.get_file_info(filename)
        size =  secure._format_file_size(info['size'])
        datetime = info['datetime']
        username = info['username']

        current_user = secure.get_username(env)
        if current_user == username:
            delete_td = '<td><a href="javascript:if(confirm(\'确实要（不可恢复地）删除该内容吗?\')){{location=\'{}\'}}">[删除]</a></td>'.format(delete_link)
        else:
            delete_td = '<td><a style="color: #aaa">[删除]</a></td>'

        tr = tr_template.format(
            download_link = download_link, 
            filename = filename,
            filename_elp = _ellipsis(filename), 
            size = size, 
            datetime = datetime, 
            username = _ellipsis(username), 
            delete_td = delete_td
        )
        trs += tr
    context = {
        "username": secure.get_username(env),
        "file_info": trs,
    }
    return status, headers, render("home.html", context=context)

@login_required('/login')
def upload(env):
    status = '302 FOUND'
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Status', '302'), # must be str
        ('Location', '/'),
    ]
    form = FieldStorage(environ=env, fp=env['wsgi.input'])
    for key in form.keys():
        data = form[key]
        if _is_file(data):
            filename = data.filename # basename
            file = data.file
            final_filename = _save_file(file, filename) # 返回最终文件名，因为保存过程中，可能重命名为 xx_1 xx_2 
            username = secure.get_username(env)
            secure.insert_file_info(filename=final_filename, username=username)
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

@login_required('/login')
def delete(env):
    qs = parse_qs(env['QUERY_STRING'])
    filename = qs.get('filename', [''])[0] 

    current_user = secure.get_username(env)
    info = secure.get_file_info(filename)
    if info["username"] == current_user: # 确保删除者是文件主人；home 里面的校验不足以防止直接的 post 
        secure.del_file_info(filename) # 删除文件信息
        filepath = os.path.join(storage, filename)
        os.remove(filepath) # 删除文件

    status = '302 FOUND'
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Status', '302'), # must be str
        ('Location', '/'),
    ]
    return status, headers, b''



if __name__ == '__main__':
    '''testing'''
    _rename_file('后街女孩OP.mp4')









