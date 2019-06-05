# -*- coding:utf-8 -*-
import json
import os
import xml.dom.minidom

# 返回码
import main
from contenttype import judge_type


class ErrorCode(object):
    OK = "HTTP/1.1 200 OK\r\n"
    NOT_FOUND = "HTTP/1.1 404 Not Found\r\n"


# 将字典转成字符串
def dict2str(d):
    s = ''
    for i in d:
        val = ''
        if d[i] is not None:
            val = d[i]
        s = s + i + ': ' + val + '\r\n'
    return s


def check_json(input_str):
    try:
        json.loads(input_str)
        return True
    except BaseException:
        return False


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


class HttpRequest(object):
    RootDir = 'root'
    NotFoundHtml = RootDir + '/404.html'
    CookieDir = RootDir + '/cookie/'

    def __init__(self):
        self.Method = None
        self.Url = None
        self.Protocol = None
        self.Host = None
        self.Port = None
        self.Connection = None
        self.CacheControl = None
        self.UserAgent = None
        self.Accept = None
        self.ContentType = None
        self.AcceptEncoding = None
        self.AcceptLanguage = None
        self.Cookie = None
        self.csrf_token = None
        self.session = None
        self.request_data = dict()
        self.response_line = ''
        self.response_head = dict()
        self.response_body = ''

    # 解析请求体
    def resolve_headers(self, request):
        # 解析请求方法、url、协议
        request_line, headers = request.split('\r\n', 1)
        header_list = request_line.split(' ')
        self.Method = header_list[0].upper()
        # 请求地址和参数分割
        ur = header_list[1].split("?")
        self.Url = ur[0]
        self.Protocol = header_list[2]
        # 如果有携带参数，并且请求方式为GET
        if len(ur) > 1 and self.Method == "GET":
            parameters = ur[1].split('&')
            for parameter in parameters:
                if parameter != '':
                    key, val = parameter.split('=', 1)
                    self.request_data[key] = val

        # 头部信息
        request_headers = headers.split('\r\n\r\n')
        head_options = request_headers[0].split('\r\n')
        for header in head_options:
            key, val = header.split(': ', 1)
            if key.lower() == "Host".lower():
                self.Host = val
            elif key.lower() == "Connection".lower():
                self.Connection = val
            elif key.lower() == "Cache-Control".lower():
                self.CacheControl = val
            elif key.lower() == "User-Agent".lower():
                self.UserAgent = val
            elif key.lower() == "Accept".lower():
                self.Accept = val
            elif key.lower() == "Content-Type".lower():
                self.ContentType = val
            elif key.lower() == "Accept-Encoding".lower():
                self.AcceptEncoding = val
            elif key.lower() == "Accept-Language".lower():
                self.AcceptLanguage = val
            elif key.lower() == "Cookie".lower():
                k, v = val.split('; ', 1)
                if k.lower() == "csrftoken":
                    self.csrf_token = v
                else:
                    self.Cookie = v
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
                for param in params:
                    k, v = param.split("=", 1)
                    self.request_data[k] = v

    # 处理请求
    def pass_request(self, request):
        request = request.decode('utf-8')
        if len(request.split('\r\n', 1)) != 2:
            return
        # 解析请求体
        self.resolve_headers(request)

        self.url_request(self.Url)

    # 根据url路由返回请求
    def url_request(self, path):
        # 如果不是静态文件
        if not os.path.isfile(HttpRequest.RootDir + path) and path not in main.urlpatterns:
            f = open(HttpRequest.NotFoundHtml, 'r')
            self.response_line = ErrorCode.NOT_FOUND
            self.response_head['Content-Type'] = 'text/html'
            self.response_body = f.read()
        elif path in main.urlpatterns:
            # 动态调用函数并传参
            result = eval(main.urlpatterns[path])(self)
            if result.find(".html") != -1:
                self.url_request(result)
                return

            self.response_line = ErrorCode.OK
            # 动态导入模块
            # m = __import__("root.main")
            if check_json(result):
                result = result.encode('utf-8')
                self.response_head['Content-Type'] = 'application/json;charset=utf-8'
            else:
                self.response_head['Content-Type'] = 'text/html;charset=utf-8'

            self.response_body = result
            self.response_head['Set-Cookie'] = self.Cookie
        # 是静态文件
        else:
            path = HttpRequest.RootDir + path
            # 扩展名,只提供制定类型的静态文件
            extension_name = os.path.splitext(path)[1]
            extension_set = {'.css', '.html', '.js'}
            if extension_name in extension_set:
                f = open(path, 'r', encoding='utf-8', errors='ignore')
                self.response_line = ErrorCode.OK
                self.response_head['Content-Type'] = judge_type(path)
                self.response_body = f.read()
            # 其他文件返回
            else:
                self.response_line = ErrorCode.OK
                self.response_head['Content-Type'] = judge_type(path)
                with open(path, 'rb') as fd:
                    data = fd.read()
                self.response_body = data

    def process_session(self):
        self.session = Session()
        # 没有提交cookie，创建cookie
        if self.Cookie is None:
            self.Cookie = self.generateCookie()
            cookie_file = self.CookieDir + self.Cookie
            self.session.cook_file = cookie_file
            self.session.write_xml()
        else:
            cookie_file = self.CookieDir + self.Cookie
            self.session.cook_file = cookie_file
            if os.path.exists(cookie_file):
                self.session.load_from_xml()
            # 当前cookie不存在，自动创建
            else:
                self.Cookie = self.generate_cookie()
                cookie_file = self.CookieDir + self.Cookie
                self.session.cook_file = cookie_file
                self.session.write_xml()
        return self.session

    def generate_cookie(self):
        import time, hashlib
        cookie = str(int(round(time.time() * 1000)))
        hl = hashlib.md5()
        hl.update(cookie.encode(encoding='utf-8'))
        return cookie

    def get_response_head(self):
        return dict2str(self.response_head)
