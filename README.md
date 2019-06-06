# key-socket-web
### 基于Python的socket实现获取激活key的web服务器

## 功能
> 1. 接受静态请求，`html`，`png`等文件
> 
> 2. 接受动态请求，脚本类型为`python`
> 
> 3. 提供`Session`服务
> 
> 4. `root`是根目录，包含资源文件
> 
> 5. 使用线程池来管理请求
> 
> 6. 实现路由功能


## 使用
```bash
git clone https://github.com/woytu/key-socket-web.git
# 最后一位参数为端口，如果不输入则默认9000
python3 key-socket-web/server.py 5000
```