import urlparse
import logging
import string
import os

from contextlib import contextmanager
from functools import wraps

from dbapiext import execute_f as execute
from dbapiext import qcompile

logger = logging.getLogger(__name__)

_TABLE_NAME_CHARS = frozenset(string.ascii_letters + string.digits + "_.")

_NAMED_DRIVERS = {}


class DBError(Exception):
    pass


class UnexpectedCardinality(DBError):
    pass


class NoDefaultDatabase(DBError):
    pass


class NoSuchDatabase(DBError):
    pass


class NoDriverForURL(DBError):
    pass


class InvalidDatabaseURL(DBError):
    pass


class NullDriver(DBError):
    pass


def from_url(url, db_name=None):
    if url is None or url.strip() == "":
        raise InvalidDatabaseURL(url)
    parsed = urlparse.urlparse(url)
    if parsed.scheme == "":
        raise InvalidDatabaseURL(url)
    try:
        driver_class = drivers._DRIVERS[parsed.scheme]
    except KeyError:
        raise NoDriverForURL(url)
    driver = driver_class.from_url(url)
    return register(driver, db_name=db_name)


def from_env(var=None, db_name=None):
    var_name = "DATABASE_URL"
    if var is None:
        try:
            env_name = os.environ["ENVIRONMENT"]
            var = env_name.upper() + "_" + var_name
        except KeyError:
            var = var_name
    print "var", var
    url = os.environ[var]
    return from_url(url, db_name=db_name)


def register(driver, db_name=None):
    if driver is None:
        raise NullDriver
    _NAMED_DRIVERS[db_name] = driver
    return get(db_name)


def unregister(db_name):
    del _NAMED_DRIVERS[db_name]


def get_driver(db_name=None):
    try:
        return _NAMED_DRIVERS[db_name]
    except KeyError:
        if db_name is None:
            raise NoDefaultDatabase()
        else:
            raise NoSuchDatabase(db_name)


def clear():
    global _NAMED_DRIVERS
    _NAMED_DRIVERS = {}


def count_dbs():
    return len(_NAMED_DRIVERS)


class Transaction(object):

    def __init__(self, db, conn, cursor):
        self.db = db
        self.conn = conn
        self.cursor = cursor

    def transmogrify(self, sql, *args, **kwargs):
        compiled = qcompile(sql, paramstyle=self.db.driver.PARAM_STYLE)
        return compiled.apply(*args, **kwargs)

    def items(self, sql, *args, **kwargs):
        kwargs.setdefault("paramstyle", self.db.driver.PARAM_STYLE)
        execute(self.cursor, sql, *args, **kwargs)
        self.db.driver.fixup_cursor(self.cursor)
        try:
            results = self.cursor.fetchall()
        except Exception as ex:
            results = None
            if not self.db.driver.ignore_exception(ex):
                raise
        return self.db.driver.wrap_results(self.cursor, results)

    def item(self, sql, *args, **kwargs):
        results = self.items(sql, *args, **kwargs)
        num_results = len(results)
        if num_results != 1:
            raise UnexpectedCardinality(
                "Expected exactly one item but got %d." % num_results)
        return results[0]

    do = items

    def first(self, sql, *args, **kwargs):
        results = self.items(sql, *args, **kwargs)
        if len(results) > 0:
            return results[0]
        return None

    def count(self, from_plus, count_name=None, *args, **kwargs):
        sql = "SELECT COUNT(*) AS n FROM %s" % from_plus
        result = self.item(sql, *args, **kwargs)
        return result.n

    @staticmethod
    def _count_name(from_plus):
        if any(map(lambda c: c not in _TABLE_NAME_CHARS, from_plus)):
            left = from_plus.split(" WHERE ", 1)[0]
            normalized_name = left.replace(" ", "_").replace(",", "")
        else:
            normalized_name = from_plus
        return normalized_name + "_count"

    def call(self, sp_name, *args):
        arg_vars = ",".join(["%X" for _ in args])
        query = "SELECT %s(%s)" % (sp_name, arg_vars)
        results = self.items(query, *args)
        return getattr(results[0], sp_name)


def delegate_tx(f):

    @wraps(f)
    def wrapper(self, sql, *args, **kwargs):
        with self.tx(*args, **kwargs) as tx:
            m = getattr(tx, f.func_name)
            return m(sql, *args, **kwargs)

    return wrapper


def delegate_db(f):

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        m = getattr(self._getdb(), f.func_name)
        return m(*args, **kwargs)

    return wrapper


class Database(object):

    def __init__(self, db_name=None, driver=None, conn=None):
        self.db_name = db_name
        self._driver = driver
        self._conn = conn

    def clone(self):
        new_conn = self.driver.connect()
        return Database(db_name=self.db_name,
                        driver=self.driver,
                        conn=new_conn)

    @property
    def driver(self):
        if self._driver is None:
            self._driver = get_driver(self.db_name)
        return self._driver

    @property
    def conn(self):
        if self._conn is None:
            self._conn = self.driver.connect()
        return self._conn

    @contextmanager
    def txc(self, *args, **kwargs):
        conn = kwargs.pop("_conn", None)
        cursor = kwargs.pop("_cursor", None)

        if conn is None:
            conn = self.conn

        try:
            if cursor is None:
                cursor = self.driver.cursor(conn)
            assert conn is not None
            assert cursor is not None
            yield conn, cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    @contextmanager
    def tx(self, *args, **kwargs):
        with self.txc(*args, **kwargs) as (conn, cursor):
            yield Transaction(self, conn, cursor)

    @delegate_tx
    def transmogrify(self, sql, *args, **kwargs):
        pass

    @delegate_tx
    def items(self, sql, *args, **kwargs):
        pass

    @delegate_tx
    def do(self, sql, *args, **kwargs):
        pass

    @delegate_tx
    def item(self, sql, *args, **kwargs):
        pass

    @delegate_tx
    def first(self, sql, *args, **kwargs):
        pass

    def count(self, from_plus, *args, **kwargs):
        with self.tx(*args, **kwargs) as tx:
            return tx.count(from_plus, *args, **kwargs)

    @delegate_tx
    def call(self, sp_name, *args):
        pass


def get(db_name=None):
    return Database(db_name=db_name)


def connect(db_name=None):
    return get(db_name=db_name).clone()


def release(db_handle):
    db_handle.release()


put = release


class DefaultDatabase(object):

    def _getdb(self):
        return get()

    @delegate_db
    def connect(self, *args, **kwargs):
        return self._getdb().connect(*args, **kwargs)

    @delegate_db
    def tx(self, *args, **kwargs):
        return self._getdb().tx(*args, **kwargs)

    @delegate_db
    def txc(self, *args, **kwargs):
        return self._getdb().txc(*args, **kwargs)

    @delegate_db
    def transmogrify(self, *args, **kwargs):
        return self._getdb().transmogrify(*args, **kwargs)

    @delegate_db
    def items(self, *args, **kwargs):
        return self._getdb().items(*args, **kwargs)

    @delegate_db
    def item(self, *args, **kwargs):
        return self._getdb().item(*args, **kwargs)

    @delegate_db
    def do(self, *args, **kwargs):
        return self._getdb().do(*args, **kwargs)

    @delegate_db
    def first(self, *args, **kwargs):
        return self._getdb().first(*args, **kwargs)

    @delegate_db
    def count(self, *args, **kwargs):
        return self._getdb().count(*args, **kwargs)

    @delegate_db
    def call(self, *args, **kwargs):
        return self._getdb().call(*args, **kwargs)

defaultdb = DefaultDatabase()

connect = defaultdb.connect
tx = defaultdb.tx
txc = defaultdb.txc
transmogrify = defaultdb.transmogrify
items = defaultdb.items
item = defaultdb.item
do = defaultdb.do
first = defaultdb.first
count = defaultdb.count
call = defaultdb.call

from . import drivers

__all__ = [
    "connect",
    "tx",
    "txc",
    "do",
    "transmogrify",
    "items",
    "item",
    "count",
    "first",
    "call",
    "drivers",
]
