import http.client
import socket
import time
import requests

from .display import *
from .flow import *
__all__ = [
    'FIDDLER_PROXY', 'proxy', 'request_get',
    'request_post', 'socket_connection'
]

FIDDLER_PROXY = { 
    'http'  : 'http://127.0.0.1:8888',
    'https' : 'https://127.0.0.1:8888'
}
# Set this to fiddler_proxy to make the traffic go through Fiddler
proxy: dict[str, str]|None = None

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
                allow_redirects=allow_redirects, timeout=5, proxies=proxy
            )
        else:
            r: requests.Response = session.post(
                url, headers=headers, cookies=cookies, auth=auth, 
                allow_redirects=allow_redirects, timeout=5, proxies=proxy,
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
        wait_time_between_retries=wait_time_between_retries,
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
        wait_time_between_retries=wait_time_between_retries, url=url,
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