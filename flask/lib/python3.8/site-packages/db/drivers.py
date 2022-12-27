import urlparse
import sys
import os

import db

_AUTO_REGISTER = True
_DRIVERS = {}


def disable_autoregistration():
    global _AUTO_REGISTER
    _AUTO_REGISTER = False


def autoregister_class(driver_class, scheme=None):
    if _AUTO_REGISTER and scheme not in _DRIVERS:
        register_class(driver_class, scheme=scheme)


def register_class(driver_class, scheme=None):
    if not scheme:
        scheme = driver_class.URL_SCHEME
    _DRIVERS[scheme] = driver_class
    mod = sys.modules[__name__]
    setattr(mod, scheme, driver_class)


def unregister_scheme(scheme):
    del _DRIVERS[scheme]
    del globals[scheme]


def unregister_class(driver_class):
    for scheme, e_driver_class in _DRIVERS.iteritems():
        if e_driver_class == driver_class:
            unregister_scheme(scheme)


class Driver(object):
    PARAM_STYLE = "pyformat"

    def __init__(self, *args, **kwargs):
        self.conn_args = args
        self.conn_kwargs = kwargs

    @classmethod
    def from_url(cls, url):
        raise NotImplementedError

    def acquire(self):
        raise NotImplementedError

    def release(self, conn):
        pass

    def ignore(self, _ex):
        return False

    def cursor(self, conn):
        cursor = conn.cursor()
        self.setup_cursor(cursor)
        return cursor

    def setup_cursor(self, cursor):
        pass

    def fixup_cursor(self, cursor):
        pass

    def wrap_results(self, cursor, results):
        return results


__all__ = [
    "disable_autoregistration",
    "autoregister_class",
    "register_class",
    "unregister_scheme",
    "unregister_class",
    "Driver",
]
