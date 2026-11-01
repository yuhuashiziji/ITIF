"""Direct public HTTP transport: validate the connected peer before HTTP is sent."""
import http.client, ipaddress, socket, urllib.parse, urllib.request

def checked_connection(address,timeout=socket._GLOBAL_DEFAULT_TIMEOUT,source_address=None):
    sock=socket.create_connection(address,timeout,source_address)
    try:
        if not ipaddress.ip_address(sock.getpeername()[0]).is_global:
            raise ValueError('拒绝连接本地或内网地址')
        return sock
    except Exception:
        sock.close();raise

class PublicHTTPConnection(http.client.HTTPConnection):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self._create_connection=checked_connection

class PublicHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self._create_connection=checked_connection

class HTTPHandler(urllib.request.HTTPHandler):
    def http_open(self,req):return self.do_open(PublicHTTPConnection,req)

class HTTPSHandler(urllib.request.HTTPSHandler):
    def do_open(self,http_class,req,**kwargs):return super().do_open(PublicHTTPSConnection,req,**kwargs)

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urllib.parse.urlsplit(newurl).scheme not in ('http','https'):raise ValueError('只允许HTTP/HTTPS跳转')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def opener(redirect=None):
    # A proxy would hide the final peer address, so public feed fetches use direct connections.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}),HTTPHandler(),HTTPSHandler(),redirect() if redirect else Redirect())
