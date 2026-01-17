import enum
import http.client
import re
import socket
import time

import requests
import urllib3.util.url
from pydantic import field_validator

from .display import *
from .encoding import *
from .flow import *

__all__ = [
    'IP_PATTERN_STR', 'IP_PATTERN', 'URL_PATTERN',
    'Scheme', 'Host',
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

class Scheme(enum.StrEnum):
    HTTP = 'http'
    HTTPS = 'https'

class Host(Serializable):
    scheme: Scheme|None = None
    domain: str|None = None
    """The domain of the host. E.g: `www.google.com`"""
    ip: str|None = None
    port: int|None = None
    
    @field_validator('scheme')
    @classmethod
    def validate_scheme(cls, value: Scheme|str|None) -> Scheme|None:
        if value is not None and not isinstance(value, Scheme):
            value = Scheme(value.lower())

        return value
    
    @field_validator('ip')
    @classmethod
    def validate_ip(cls, value: str|None) -> str|None:
        if value is not None:
            match = IP_PATTERN.match(value)
            if match is None:
                raise ValueError('Invalid IP', value)

            value = match.group(0)

        return value
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, value: int|str|None) -> int|None:
        if value is not None:
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError:
                    raise ValueError('Invalid port', value)

            if not 0 <= value <= 65535:
                raise ValueError('Invalid port', value)
            
        return value

    @property
    def base_url(self) -> str|None:
        """The base URL of the host.
        
        This value is generated using `scheme`, `domain`/`ip` and `port`
        if they are available. Otherwise, it'll be `None`.

        When setting this, you can pass any full URL as value.
        If possible, `scheme`, `domain`/`ip` and `port` will be extracted from it.
        """
        base = self.domain or self.ip
        if base is None:
            return None
        
        if self.scheme is not None:
            base = f'{self.scheme}://{base}'
        if self.port is not None:
            base += f':{self.port}'

        return base
    
    @base_url.setter
    def base_url(self, value: str):
        match = URL_PATTERN.match(value)
        if match is None or match.group(4) is None:
            raise ValueError('Invalid URL', value)

        self.scheme = self.validate_scheme(match.group(3))
        self.ip = self.validate_ip(match.group(5))
        self.domain = match.group(6)
        self.port = self.validate_port(match.group(9))

    def __str__(self) -> str:
        return self.base_url or ''

def _request(url: str, raw_url: bool, headers, cookies, session: requests.Session|None, auth,
             allow_redirects: bool, verify: bool,
             retry_on_connection_error: bool,
             retry_on_unexpected_status_code: bool, 
             expected_status_codes: list[int],
             data=None,
             timeout: int = 5) -> requests.Response | None:
    if session is None:
        session = requests.Session()
    # Combine the session's headers and cookies with the ones passed
    # as args, priorizing these last ones
    h = session.headers
    if headers is not None:
        h.update(headers)
    headers = h

    c = session.cookies
    if cookies is not None:
        c.update(cookies)
    cookies = c

    method = 'GET' if data is None else 'POST'
    r = requests.Request(
        method=method, url=url,
        headers=headers, cookies=cookies,
        auth=auth or session.auth,
        data=data
    )
    prep = r.prepare()

    if raw_url:
        # Set URL after preparing the request to use it as-is
        # Useful when trying to do things like path traversals
        prep.url = url

        # Even if we use a prepared request and override its URL,
        # when sending it the URL is still re-encoded by urllib3, so
        # we need to temporarily override this
        o_normalizable_schemes = urllib3.util.url._NORMALIZABLE_SCHEMES     # type: ignore
        urllib3.util.url._NORMALIZABLE_SCHEMES = ()     # type: ignore

    try:
        r = session.send(
            prep, allow_redirects=allow_redirects,
            verify=verify, timeout=timeout
        )

        if raw_url:
            urllib3.util.url._NORMALIZABLE_SCHEMES = o_normalizable_schemes # type: ignore

        if not r.status_code in expected_status_codes:
            description = http.client.responses.get(r.status_code, 'Unknown')
            error(f'{method}: Unexpected status code {r.status_code} ({description})')
            if retry_on_unexpected_status_code:
                raise RetryInterrupt

            return None

        return r
    except requests.exceptions.ConnectionError:
        error(f'{method}: Connection Error. Is the URL "{url}" valid?')
        if retry_on_connection_error:
            raise RetryInterrupt
    except requests.exceptions.Timeout:
        error(f'{method}: Timeout')
        if retry_on_connection_error:
            raise RetryInterrupt
    except requests.exceptions.RequestException as e:
        error(f'{method}: Exception: {e}')

    return None

def request_get(url: str, raw_url: bool = False, verbose: bool = True, 
                headers=None, cookies=None, session: requests.Session|None = None, auth=None,
                allow_redirects: bool = True, verify: bool = True,
                expected_status_codes: list[int] = [200, 302],
                retry_on_connection_error: bool = True,
                retry_on_unexpected_status_code: bool = False,
                wait_between_retries: float = 0.4,
                max_retries: int = 10, wait_multiplier: float = 1,
                max_wait: float = -1) -> requests.Response | None:
    """Performs a GET request to `url`, using (if provided) `headers`,
    `cookies`, `session`, `auth` and `allow_redirects`.
    
    if `raw_url` is `True`, the URL will be used as-is. This is useful,
    for example, for path traversals.

    If `verify` is `False`, the SSL certificates won't be verified.

    If `verbose` is `True`, prints the URL before performing the request.

    If a connection error happens or the response status code isn't
    in `expected_status_codes` (and `retry_on_connection_error` or
    `retry_on_unexpected_status_code` are `True` respectively), retries
    the request up to `max_retries` times, waiting `wait_between_retries`
    (See `call_retriable_func` for more info)

    If the request is successful, returns its response. Otherwise, returns `None`.
    """
    if verbose:
        debug(f'GET: {url}')

    return call_retriable_func(
        _request, max_retries=max_retries, 
        wait_between_retries=wait_between_retries,
        wait_multiplier=wait_multiplier, max_wait=max_wait,

        url=url, raw_url=raw_url,
        headers=headers, cookies=cookies, session=session, auth=auth,
        allow_redirects=allow_redirects, verify=verify,
        retry_on_connection_error=retry_on_connection_error,
        retry_on_unexpected_status_code=retry_on_unexpected_status_code, 
        expected_status_codes=expected_status_codes
    )

def request_post(url: str, data, raw_url: bool = False, verbose: bool = True, 
                headers=None, cookies=None, session: requests.Session|None = None, auth=None,
                allow_redirects: bool = True, verify: bool = True,
                expected_status_codes: list[int] = [200, 302],
                retry_on_connection_error: bool = True,
                retry_on_unexpected_status_code: bool = False,
                wait_between_retries: float = 0.4,
                max_retries: int = 10, wait_multiplier: float = 1,
                max_wait: float = -1) -> requests.Response | None:
    """Performs a POST request to `url`, using (if provided) `headers`,
    `cookies`, `session`, `auth`, `allow_redirects` and `data`.
    
    if `raw_url` is `True`, the URL will be used as-is. This is useful,
    for example, for path traversals.

    If `verify` is `False`, the SSL certificates won't be verified.

    If `verbose` is `True`, prints the URL before performing the request.
    
    If a connection error happens or the response status code isn't
    in `expected_status_codes` (and `retry_on_connection_error` or
    `retry_on_unexpected_status_code` are `True` respectively), retries
    the request up to `max_retries` times, waiting `wait_between_retries`
    (See `call_retriable_func` for more info)

    If the request is successful, returns its response. Otherwise, returns `None`.
    """
    if verbose:
        debug(f'POST: {url}')

    return call_retriable_func(
        _request, max_retries=max_retries, 
        wait_between_retries=wait_between_retries,
        wait_multiplier=wait_multiplier, max_wait=max_wait,
        
        url=url, raw_url=raw_url,
        data=data, headers=headers, cookies=cookies, session=session, auth=auth,
        allow_redirects=allow_redirects, verify=verify,
        retry_on_connection_error=retry_on_connection_error,
        retry_on_unexpected_status_code=retry_on_unexpected_status_code, 
        expected_status_codes=expected_status_codes
    )

def socket_connection(
        host: str, port: str|int, requests: list[str] = [],
        udp: bool = False, timeout: int = 3, decode_data: bool = True
    ) -> list[str|bytes]| None:
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
    
    result: list[str|bytes] = []
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