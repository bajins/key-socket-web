import json

urlpatterns = {"": "main.index", "/": "main.index", "/login": "main.login", "/login-page": "main.login_page"}


def index(request):
    return "/index.html"


def login_page(request):
    return "/login.html"


def login(request):
    if request.Method != "POST":
        return json.dumps({'code': 401, 'msg': "请求方式错误"})
    name = request.request_data.get("name", "")
    if name.strip() == '':
        return json.dumps({'code': 300, 'msg': "请输入名称"})
    password = request.request_dataget("password", "")
    if password.strip() == '':
        return json.dumps({'code': 300, 'msg': "请输入密码"})

    request.process_session().set_cookie('name', '123')
    request.process_session().write_xml()
    return json.dumps({'code': 200, 'msg': "登录成功"})

    # if request.process_session().get_cookie('name') is not None:
    #     return 'hello, ' + request.process_session().get_cookie('name')
    # with open('root/login.html', 'r') as f:
    #     data = f.read()
    # return data
