
# fare
fare as in [f]ile sh[are].

一个基于 WSGI 的局域网文件共享服务器。

+ 纯基于文件系统的数据储存方式
+ 支持登录（所有用户信息和 session 信息用 json 形式储存）
+ 支持记录简单的文件信息

## 运行环境

支持 Python3.x。完全使用标准库，无须安装其他依赖。

## 使用方法

将 main.py 中 host 换成你的局域网 IP，然后直接运行项目根目录下的 main.py 即可。

默认有一个名为 test，密码为 test 的用户帐号可供测试。