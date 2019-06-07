import hashlib
import json
import os
import xml.dom.minidom
from datetime import time
from urllib import request

from utils import log_util
import main
from utils import util
from utils.content_type import judge_type


class ErrorCode(object):
    # OK = "HTTP/1.1 %d\r\n" % object
    OK = "HTTP/1.1 200 OK\r\n"
    NOT_FOUND = "HTTP/1.1 404 Not Found\r\n"


class Session(object):
    def __init__(self):
        self.data = dict()
        self.cook_file = None

    def get_cookie(self, key):
        if key in self.data.keys():
            return self.data[key]
        return None

    def set_cookie(self, key, value):
        self.data[key] = value

    def load_from_xml(self):
        import xml.dom.minidom as minidom
        root = minidom.parse(self.cook_file).documentElement
        for node in root.childNodes:
            if node.nodeName == '#text':
                continue
            else:
                self.set_cookie(node.nodeName, node.childNodes[0].nodeValue)

    def write_xml(self):
        import xml.dom.minidom as minidom
        dom = xml.dom.minidom.getDOMImplementation().createDocument(None, 'Root', None)
        root = dom.documentElement
        for key in self.data:
            node = dom.createElement(key)
            node.appendChild(dom.createTextNode(self.data[key]))
            root.appendChild(node)
        with open(self.cook_file, 'w') as f:
            dom.writexml(f, addindent='\t', newl='\n', encoding='utf-8')


DEFAULT_ERROR_HTML = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
    <title>Error response</title>
</head>
<body>
<div style="width: 100%;text-align:center;">
    <h1>404 Not Found</h1>
</div>
</body>
<html>
"""
# 获取到当前执行文件目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = 'static'
COOKIE_DIR = STATIC_DIR + '/cookie/'


class HttpRequest(object):
    Method = None
    Url = None
    Protocol = None
    Host = None
    Port = None
    Connection = None
    CacheControl = None
    UserAgent = None
    Accept = None
    ContentType = None
    AcceptEncoding = None
    AcceptLanguage = None
    Cookie = None
    csrf_token = None
    session = None
    request_line = None
    request_data = dict()
    response_line = ''
    response_head = dict()
    response_body = ''

    # 解析请求体
    def resolve_headers(self, req):
        # 解析请求方法、url、协议
        request_line, headers = req.split('\r\n', 1)
        self.request_line = request_line
        header_list = request_line.split(' ')
        self.Method = header_list[0].upper()
        # 请求地址和参数分割
        mpath, margs = request.splitquery(header_list[1])  # ?分割
        self.Url = mpath
        self.Protocol = header_list[2]
        # 如果有携带参数，并且请求方式为GET
        if util.not_empty(margs) and self.Method == "GET":
            parameters = margs.split('&')
            for parameter in parameters:
                if util.not_empty(parameter):
                    key, val = parameter.split('=', 1)
                    self.request_data[key] = val

        # 头部信息
        request_headers = headers.split('\r\n\r\n')
        head_options = request_headers[0].split('\r\n')
        for header in head_options:
            key, val = header.split(': ', 1)
            key = key.lower()
            if key == "Host".lower():
                self.Host = val
            elif key == "Connection".lower():
                self.Connection = val
            elif key == "Cache-Control".lower():
                self.CacheControl = val
            elif key == "User-Agent".lower():
                self.UserAgent = val
            elif key == "Accept".lower():
                self.Accept = val
            elif key == "Content-Type".lower():
                self.ContentType = val
            elif key == "Accept-Encoding".lower():
                self.AcceptEncoding = val
            elif key == "Accept-Language".lower():
                self.AcceptLanguage = val
            elif key == "Cookie".lower():
                ck = val.split('; ')
                for k in ck:
                    if k.lower() == "csrftoken":
                        self.csrf_token = k.split("=")[0]
                    else:
                        self.Cookie = k
            # self.head[key] = val

        # 解析参数，并且请求方式为POST
        if len(request_headers) > 1 and self.Method == "POST":
            hd = headers[headers.find("\r\n\r\n"):len(headers)].replace('\r\n\r\n', '')
            if hd.find("Content-Disposition") != -1:
                form = hd.split('\r\n')
                for content in form:
                    if content.find("form-data") != -1:
                        param = content.split(';')[1].split('"')
                        self.request_data[param[1]] = param[2]
            else:
                params = hd.split("&")
                if util.not_empty(params[0]):
                    for param in params:
                        k, v = param.split("=", 1)
                        self.request_data[k] = v

    # 处理请求
    def parse_request(self, req):
        if len(req.split('\r\n', 1)) != 2:
            return
        # 解析请求体
        self.resolve_headers(req)
        log_util.log_request(self.request_line)

        self.url_request(self.Url)

    # 根据url路由返回请求
    def url_request(self, path):

        file_path = get_file_path(path)

        # 如果不是静态文件
        if not os.path.isfile(file_path) and path not in main.urlpatterns:
            self.response_line = ErrorCode.NOT_FOUND
            # self.response_line = http_status(HTTPStatus.NOT_FOUND)
            self.response_head['Content-Type'] = 'text/html'
            self.response_body = DEFAULT_ERROR_HTML.encode("utf-8")
        elif path in main.urlpatterns:
            # 动态调用函数并传参
            result = eval(main.urlpatterns[path])(self)
            # 如果返回的值是文件
            if os.path.isfile(get_file_path(result)):
                self.url_request(result)
                return

            self.response_line = ErrorCode.OK
            # 动态导入模块
            # m = __import__("root.main")
            if util.check_json(result):
                self.response_head['Content-Type'] = 'application/json;charset=utf-8'
            else:
                self.response_head['Content-Type'] = 'text/html;charset=utf-8'

            self.response_body = result
            self.response_head['Set-Cookie'] = self.Cookie
        # 是静态文件
        else:
            self.response_head['Content-Type'] = judge_type(file_path)
            if file_path.find("/public") != -1:
                filename = os.path.basename(file_path)
                self.response_head["Content-Disposition"] = "attachment; filename=" + filename

            # 扩展名,只提供制定类型的静态文件
            extension_name = os.path.splitext(file_path)[1]
            extension_set = {'.css', '.html', '.js'}
            if extension_name in extension_set:
                self.response_line = ErrorCode.OK
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as fd:
                    data = fd.read()
                self.response_body = data
            # 其他文件返回
            else:
                self.response_line = ErrorCode.OK
                with open(file_path, 'rb') as fd:
                    data = fd.read()
                self.response_body = data

    def process_session(self):
        self.session = Session()
        # 没有提交cookie，创建cookie
        if self.Cookie is None:
            self.Cookie = self.generateCookie()
            cookie_file = self.COOKIE_DIR + self.Cookie
            self.session.cook_file = cookie_file
            self.session.write_xml()
        else:
            cookie_file = self.COOKIE_DIR + self.Cookie
            self.session.cook_file = cookie_file
            if os.path.exists(cookie_file):
                self.session.load_from_xml()
            # 当前cookie不存在，自动创建
            else:
                print(self.response_head)
                self.Cookie = self.generate_cookie()
                cookie_file = self.COOKIE_DIR + self.Cookie
                self.session.cook_file = cookie_file
                self.session.write_xml()
        return self.session

    def generate_cookie(self):
        cookie = str(int(round(time.time() * 1000)))
        hl = hashlib.md5()
        hl.update(cookie.encode(encoding='utf-8'))
        return cookie

    # 获取响应体
    def get_response(self):
        # 判断是否为bytes
        if isinstance(self.response_body, bytes):
            body = self.response_body
        # 判断是否为str
        elif isinstance(self.response_body, str):
            body = self.response_body.encode('utf-8', errors='ignore')
        else:
            body = json.dumps(self.response_body, ensure_ascii=False).encode('utf-8', errors='ignore')

        head = util.dict2str(self.response_head)
        headers = (self.response_line + head + "\r\n").encode('utf-8')

        return headers + body


def get_file_path(path):
    if path.find(STATIC_DIR) == -1:
        file_path = STATIC_DIR + path
    elif path.find("/" + STATIC_DIR) != -1:
        file_path = path[path.find(STATIC_DIR):len(path)]

    return file_path
