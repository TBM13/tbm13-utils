import http.client
import socket
import time
import re
import requests

from .display import *
from .flow import *
__all__ = [
    'IP_PATTERN_STR', 'IP_PATTERN', 'URL_PATTERN', 'Host',
    'request_get','request_post', 'socket_connection'
]

# 192.168.0.1
IP_PATTERN_STR = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
IP_PATTERN = re.compile(f'^{IP_PATTERN_STR}$')
# 192.168.0.1
# 192.168.0.1:80
# https://192.168.0.1
# http://192.168.1.1:4568/asd/whatever
# group 1 is the full base URL | group 3 is scheme | group 4 is IP/URL
# group 5 is IP | group 6 is URL | group 9 is port
# group 11 is anything after the slash
URL_PATTERN = re.compile(
    r'(^((https?):\/\/)?((' + IP_PATTERN_STR + r')|((\d|\w|\.)+))(\:(\d+))?)(\/(.+)?)?$'
)
class Host:
    def __init__(self, base_url: str = '') -> None:
        self._scheme: int = ''
        self._domain: str = ''
        self._ip: str = ''
        self._port: int = -1

        if len(base_url) > 0:
            self.base_url = base_url

    @property
    def scheme(self) -> str | None:
        """The scheme of the host. If not set, this value is `None`."""
        if len(self._scheme) == 0:
            return None

        return self._scheme
    
    @scheme.setter
    def scheme(self, value: str|None):
        if value is None:
            self._scheme = ''
            return

        value = value.lower()
        if not value in ['http', 'https']:
            error(f'Host: Invalid scheme "{value}"')
            return

        self._scheme = value

    @property
    def ip(self) -> str | None:
        """The IP address of the host. If not set, this value is `None`."""
        if len(self._ip) == 0:
            return None

        return self._ip
    
    @ip.setter
    def ip(self, value: str|None):
        if value is None:
            self._ip = ''
            return

        match = IP_PATTERN.match(value)
        if match is None:
            error(f'Host: Invalid IP "{value}"')
            return

        self._ip = match.group(0)

    @property
    def port(self) -> int | None:
        """The port of the host. If not set, this value is `None`."""
        if self._port == -1:
            return None

        return self._port
    
    @port.setter
    def port(self, value: int|str|None):
        if value is None:
            self._port = -1
            return

        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                error(f'Host: Invalid port "{value}"')
                return

        if value < 0 or value > 65535:
            error(f'Host: Invalid port "{value}"')
            return

        self._port = value

    @property
    def domain(self) -> str | None:
        """The domain of the host. Example: `www.google.com`
        
        If not set, this value is `None`.
        """
        if len(self._domain) == 0:
            return None

        return self._domain

    @domain.setter
    def domain(self, value: str|None):
        if value is None:
            self._domain = ''
            return

        self._domain = value

    @property
    def base_url(self) -> str | None:
        """The base URL of the host.
        
        This value is generated using `scheme`, `domain`/`ip` and `port`
        if they are available. Otherwise, it'll be `None`.

        When setting this, you can pass any full URL as value.
        If possible, `scheme`, `domain`/`ip` and `port` will be extracted from it.
        """
        if self.domain is None and self.ip is None:
            return None
        
        base = self.domain or self.ip
        if self.scheme is not None:
            base = f'{self.scheme}://{base}'
        if self.port is not None:
            base += f':{self.port}'

        return base
    
    @base_url.setter
    def base_url(self, value: str):
        match = URL_PATTERN.match(value)
        if match is None or match.group(4) is None:
            error(f'Host: Invalid URL "{value}"')
            return

        self.scheme = match.group(3)
        self.ip = match.group(5)
        self.domain = match.group(6)
        self.port = match.group(9)

    def __str__(self) -> str:
        return self.base_url or ''

    def __repr__(self) -> str:
        return (
            'Host('
            f'scheme={self.scheme}, '
            f'ip={self.ip}, '
            f'domain={self.domain}, '
            f'port={self.port}, '
            f'base_url={self.base_url}'
            ')'
        )

def _request(url: str, headers, cookies, session, auth,
             allow_redirects: bool, retry_on_connection_error: bool,
             retry_on_unexpected_status_code: bool, 
             expected_status_codes: list[int],
             data=None) -> requests.Response | None:

    request_type = 'GET' if data is None else 'POST'

    try:
        if data is None:
            r: requests.Response = session.get(
                url, headers=headers, cookies=cookies, auth=auth, 
                allow_redirects=allow_redirects, timeout=5
            )
        else:
            r: requests.Response = session.post(
                url, headers=headers, cookies=cookies, auth=auth, 
                allow_redirects=allow_redirects, timeout=5,
                data=data
            )

        if not r.status_code in expected_status_codes:
            description = http.client.responses.get(r.status_code, 'Unknown')
            error(f'{request_type}: Unexpected status code {r.status_code} ({description})')
            if retry_on_unexpected_status_code:
                raise RetryInterrupt

            return None

        return r
    except requests.exceptions.ConnectionError:
        error(f'{request_type}: Connection Error. Is the URL "{url}" valid?')
        if retry_on_connection_error:
            raise RetryInterrupt
    except requests.exceptions.Timeout:
        error(f'{request_type}: Timeout')
        if retry_on_connection_error:
            raise RetryInterrupt
    except requests.exceptions.RequestException as e:
        error(f'{request_type}: Exception: {e}')

    return None

def request_get(url: str, verbose: bool = True, 
                headers=None, cookies=None, session=requests, auth=None,
                allow_redirects: bool = True,
                expected_status_codes: list[int] = [200, 302],
                retry_on_connection_error: bool = True,
                retry_on_unexpected_status_code: bool = False,
                wait_time_between_retries: float = 0.4,
                max_retries: int = 10) -> requests.Response | None:
    """Performs a GET request to `url`, using (if provided) `headers`,
    `cookies`, `session`, `auth` and `allow_redirects`.
    
    If a connection error happens or the response status code isn't
    in `expected_status_codes` (and `retry_on_connection_error` or
    `retry_on_unexpected_status_code` are `True` respectively), retries
    the request up to `max_retries` times, waiting `wait_time_between_retries`
    (See `call_retriable_func` for more info)

    If `verbose` is `True`, prints the URL before performing the request.

    If the request is successful, returns its response. Otherwise, returns `None`.
    """
    if verbose:
        debug(f'GET: {url}')

    return call_retriable_func(
        _request, max_retries=max_retries, 
        wait_between_retries=wait_time_between_retries,
        url=url, headers=headers, cookies=cookies, session=session, auth=auth,
        allow_redirects=allow_redirects,
        retry_on_connection_error=retry_on_connection_error,
        retry_on_unexpected_status_code=retry_on_unexpected_status_code, 
        expected_status_codes=expected_status_codes
    )

def request_post(url: str, data, verbose: bool = True, 
                headers=None, cookies=None, session=requests, auth=None,
                allow_redirects: bool = True,
                expected_status_codes: list[int] = [200, 302],
                retry_on_connection_error: bool = True,
                retry_on_unexpected_status_code: bool = False,
                wait_time_between_retries: float = 0.4,
                max_retries: int = 10) -> requests.Response | None:
    """Performs a POST request to `url`, using (if provided) `headers`,
    `cookies`, `session`, `auth`, `allow_redirects` and `data`.
    
    If a connection error happens or the response status code isn't
    in `expected_status_codes` (and `retry_on_connection_error` or
    `retry_on_unexpected_status_code` are `True` respectively), retries
    the request up to `max_retries` times, waiting `wait_time_between_retries`
    (See `call_retriable_func` for more info)

    If `verbose` is `True`, prints the URL before performing the request.

    If the request is successful, returns its response. Otherwise, returns `None`.
    """
    if verbose:
        debug(f'POST: {url}')

    return call_retriable_func(
        _request, max_retries=max_retries, 
        wait_between_retries=wait_time_between_retries, url=url,
        data=data, headers=headers, cookies=cookies, session=session, auth=auth,
        allow_redirects=allow_redirects,
        retry_on_connection_error=retry_on_connection_error,
        retry_on_unexpected_status_code=retry_on_unexpected_status_code, 
        expected_status_codes=expected_status_codes
    )

def socket_connection(host, port, requests: list[str] = [], udp: bool = False, 
                      timeout: int = 3, decode_data: bool = True) -> list[str] | None:
    socket_kind = socket.SOCK_STREAM
    if udp:
        socket_kind = socket.SOCK_DGRAM

    s = socket.socket(socket.AF_INET, socket_kind)
    s.setblocking(False)
    s.settimeout(timeout)

    try:
        debug(f"SOCKET: Connecting to {host}:{port}")
        s.connect((host, int(port)))
    except Exception as e:
        error(f"Couldn't connect to {host}:{port}")
        error(str(e))
        return None
    
    result = []
    for request in requests:
        debug(f"SOCKET: Sending {request.rstrip()}")
        s.send(request.encode())

        full_data = bytes()
        while True:
            time.sleep(0.2)

            try:
                data = s.recv(512000) # 512 KB
            except socket.error as e:
                if e.args[0] == 'timed out':
                    warn("Timeout")
                    break
                else:
                    raise e
            
            if not data:
                break

            full_data += data
        
        if decode_data:
            full_data = full_data.decode('utf8', 'ignore')

        result.append(full_data)
    
    return result