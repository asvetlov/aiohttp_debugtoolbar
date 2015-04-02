import binascii
import os
from functools import partial
from itertools import islice
from collections import deque
import ipaddress
import sys
import aiohttp_mako

APP_KEY = 'aiohttp_debugtollbar'
TEMPLATE_KEY = 'aiohttp_debugtollbar_mako'

REDIRECT_CODES = (301, 302, 303, 304)
STATIC_PATH = 'static/'
ROOT_ROUTE_NAME = 'debugtoolbar.main'
STATIC_ROUTE_NAME = 'debugtoolbar.static'
EXC_ROUTE_NAME = 'debugtoolbar.exception'


def hexlify(value):
    # value must be int or bytes
    if isinstance(value, int):
        value = bytes(str(value), encoding='utf-8')
    return str(binascii.hexlify(value), encoding='utf-8')


# TODO: refactor to simpler container or change to ordered dict
class ToolbarStorage(deque):
    """Deque for storing Toolbar objects."""

    def __init__(self, max_elem):
        super(ToolbarStorage, self).__init__([], max_elem)

    def get(self, request_id, default=None):
        dict_ = dict(self)
        return dict_.get(request_id, default)

    def put(self, request_id, request):
        self.appendleft((request_id, request))

    def last(self, num_items):
        """Returns the last `num_items` Toolbar objects"""
        return list(islice(self, 0, num_items))


class ExceptionHistory:

    def __init__(self):
        self.frames = {}
        self.tracebacks = {}
        self.eval_exc = 'show'


def addr_in(addr, hosts):
    for host in hosts:
        if ipaddress.ip_address(addr) in ipaddress.ip_network(host):
            return True
    return False


def replace_insensitive(string, target, replacement):
    """Similar to string.replace() but is case insensitive
    Code borrowed from: http://forums.devshed.com/python-programming-11/case-insensitive-string-replace-490921.html
    """
    no_case = string.lower()
    index = no_case.rfind(target.lower())
    if index >= 0:
        return string[:index] + replacement + string[index + len(target):]
    else: # no results so return the original string
        return string

render = partial(aiohttp_mako.render_string, app_key=TEMPLATE_KEY)



def common_segment_count(path, value):
    """Return the number of path segments common to both"""
    i = 0
    if len(path) <= len(value):
        for x1, x2 in zip(path, value):
            if x1 == x2:
                i += 1
            else:
                return 0
    return i


def format_fname(value, _sys_path=None):
    if _sys_path is None:
        _sys_path = sys.path # dependency injection
    # If the value is not an absolute path, the it is a builtin or
    # a relative file (thus a project file).
    if not os.path.isabs(value):
        if value.startswith(('{', '<')):
            return value
        if value.startswith('.' + os.path.sep):
            return value
        return '.' + os.path.sep + value

    # Loop through sys.path to find the longest match and return
    # the relative path from there.
    prefix_len = 0
    value_segs = value.split(os.path.sep)
    for path in _sys_path:
        count = common_segment_count(path.split(os.path.sep), value_segs)
        if count > prefix_len:
            prefix_len = count
    return '<%s>' % os.path.sep.join(value_segs[prefix_len:])


def escape(s, quote=False):
    """Replace special characters "&", "<" and ">" to HTML-safe sequences.  If
    the optional flag `quote` is `True`, the quotation mark character is
    also translated.

    There is a special handling for `None` which escapes to an empty string.

    :param s: the string to escape.
    :param quote: set to true to also escape double quotes.
    """
    if s is None:
        return ''

    if not isinstance(s, (str, bytes)):
        s = str(s)
    if isinstance(s, bytes):
        try:
            s.decode('ascii')
        except:
            s = s.decode('utf-8', 'replace')
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    if quote:
        s = s.replace('"', "&quot;")
    return s
# TODO: remove somehow
def text_(s, encoding='latin-1', errors='strict'):
    if isinstance(s, bytes):
        return s.decode(encoding, errors)
    return s # pragma: no cover