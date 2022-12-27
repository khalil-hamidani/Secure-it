# Copyright (C) 2006 Martin Blais. All Rights Reserved.

"""
An implementation of a DBAPI-2.0 connection pooling system in a multi-threaded
environment.

Initialization
--------------

To use connection pooling, you must first create a connection pool object::

    pool = ConnectionPool(dbapi,
                          database='test',
                          user='blais')
    antipool.initpool(pool)

where 'dbapi' is the module that you want to use that implements the DBAPI-2.0
interface.  You need only create a single instance of this object for your
process, and you could make database globally accessible.

Configuration
-------------

The connection pool has a few configuration options.  See the constructor's
'options' parameter for details.

.. important::

   Important note: By default, a connection is reserved exclusively for
   read-only operations.  If you are running your program in single-threaded
   mode and your code is written properly by discriminating between RO and RW
   operations with dbpool().connection() and dbpool().connection_ro(), two
   connections will be created!  Therefore, if you're running your program in a
   single thread, you should always set the 'disable_ro' option to True, to
   avoid the extra resource consumption.  Single-threaded programs could do with
   a single RW connection just fine (unless you're specifying the
   'user_readonly' option, this makes no difference).


Acquiring Connections
---------------------

Then, when you want to get a connection to perform some operations on the
database, you call the connection() method and use it the usual DBAPI way::

    conn = dbpool().connection()
    cursor = conn.cursor()
    ...
    conn.commit()


Read-Only Connections
---------------------

If the connection objects can be shared between threads, the connection pool
allows you to perform an optimization which consists in sharing the connection
between all the threads, for read-only operations.  When you know that you will
not need to modify the database for a transaction, get your connection using the
connection_ro() method::

    conn = dbpool().connection_ro()
    cursor = conn.cursor()
    ...

Since this will not work for operations that write to the database, you should
NEVER perform inserts, deletes or updates using these special connections.  We
do not check the SQL that gets executed, but we specifically do not provide a
commit() method on the connection wrapper so that your code blows up if you try
to commit, which will help you find bugs if you make mistakes with this.

Releasing Connections
---------------------

The connection objects that are provided by the pool are created on demand, and
a goal of the pool is to minimize the amount of resources needed by your
application.  The connection objects will normally automatically be released to
the pool once they get collected by your Python interpreter.  However, the
Python implementation that you are using may be keeping the connection objects
alive for some time you have finished using them.  Therefore, in order to
minimize the number of live connections at any time, you should always release
the connection objects with the release() method after you have finished using
them::

    conn = dbpool().connection()
    ...
    ...
    conn.release()

We recommend using a try-finally form to make it exception-safe::

    conn = dbpool().connection()
    try:
        cursor = conn.cursor()
        ...
    finally:
        conn.release()

Note that if you forget to release the connections it does not create a leak, it
only causes a slightly less efficient use of the connection resources.  No big
deal.

Using the 'with' statement
--------------------------
::

    with conn, cursor = dbpool().connection(1):
        ...


Convenience for Single Operations with Anti-ORM
-----------------------------------------------

A convenience wrapper object exists for single operations, you can wrap your
antiorm tables with ConnOp(...)  and call the same methods on them minus the
connection parameter.  The calls automatically acquire and release a connection
object, and commit if relevant.


Forking
-------





Convenience Decorators
~~~~~~~~~~~~~~~~~~~~~~

There are also ``@connected`` and ``@connected_ro`` decorators that can be used
to add a 'conn' parameter to functions, in a spirit similar to ConnOp.

Finalization
------------

On application exit, you should finalize the connection pool explicitly, to
close the database connections still present in the pool::

    dbpool().finalize()

It will finalize itself automatically if you forget, but in the interpreter's
finalization stage, which happens in a partially destroyed environment.  It is
always safer to finalize explicitly.

Testing
-------

To run a multi-threaded simulation program using this module, just run it
directly.  The --debug option provides more verbose output of the connection
pool behaviour.

Supported Databases
-------------------

Currently, we have tested this module with the following databases:

* PostgreSQL (8.x)


"""

__author__ = 'Martin Blais <blais@furius.ca>'
__copyright__ = 'Copyright (C) 2006 Martin Blais. All Rights Reserved.'


# stdlib imports
import os, types, threading, gc, warnings
from datetime import datetime, timedelta


__all__ = ('ConnectionPool', 'Error', 'dbpool', 'ConnOp')


# Create an alias for Python 3.x compatibility
try:
    xrange
except NameError:
    xrange = range


def dbpool():
    """
    Returns the unique database pool for this process.  Most often there is only
    a single pool per-process, so we provide this function as a global starting
    point for getting connections.  Use it like this:

       from antipool import dbpool
       ...
       conn = dbpool().connection()
       ...
    """
    return _pool_instance

_pool_instance = None

def initpool(pool):
    """
    Initialize the connection pool.
    You must do this once before you start using the singleton.
    """
    global _pool_instance
    _pool_instance = pool

#-------------------------------------------------------------------------------
# Support for initializing from the command-line.
def addopts(parser):
    """
    Add appropriate options on an optparse parser.
    """
    parser.add_option('--database', '--db', action='store',
                      default=None,
                      help="Database name")
    parser.add_option('--dbuser', action='store',
                      default=None,
                      help="Database user")
    parser.add_option('--dbpassword', '--dbpass', action='store',
                      default=None,
                      help="Database password")
    parser.add_option('--dbhost', action='store',
                      default='localhost',
                      help="Database hostname")
    parser.add_option('--dbport', action='store', type='int',
                      default=5432,
                      help="Database port")

def initfromopts(dbapi, opts):
    """
    Initialize a global connection pool using the parameters parsed from the
    command-line options.
    """
    params = {}
    for pname, oname in (('database', 'database'),
                         ('user', 'dbuser'),
                         ('password', 'dbpassword'),
                         ('host', 'dbhost'),
                         ('port', 'dbport')):
        pvalue = getattr(opts, oname, None)
        if pvalue is not None:
            params[pname] = pvalue

    pool = ConnectionPool(dbapi, **params)
    initpool(pool)



class ConnOp(object):
    """
    Wrapper class that provides a temporary interface for tables, that
    automatically fetches an appropriate connection from the antipool connection
    pool, and that automatically releases or commit this connection.
    """

    def __init__(self, table):
        self.table = table
        """Table object that is being mapped."""

    def _run_with_conn_ro(self, funname, *args, **kwds):
        """
        Run a read-only operation using a read-only connection object from the
        global antipool connection pool.
        """
        fun = getattr(self.table, funname)

        rv = None

        conn = dbpool().connection_ro()
        try:
            try:
                newargs = (conn,) + args
                rv = fun(*newargs, **kwds)
            except Exception:
                conn.rollback()
                raise
        finally:
            conn.release()
        return rv

    def _run_with_conn(self, funname, *args, **kwds):
        """
        Run a read-write operation using a read-only connection object from the
        global antipool connection pool.
        """
        fun = getattr(self.table, funname)

        rv = None

        conn = dbpool().connection()
        try:
            try:
                newargs = (conn,) + args
                rv = fun(*newargs, **kwds)
            except Exception:
                conn.rollback()
                raise
            else:
                # Automatically commit.
                conn.commit()
        finally:
            conn.release()
        return rv


    # Read-only methods.

    # Note: we do not provide select on purpose, since the cursor (the fetch
    # context) must be maintained afterwards, to fetch the results.

    def count(self, *args, **kwds):
        return self._run_with_conn_ro('count', *args, **kwds)

    def select_all(self, *args, **kwds):
        return self._run_with_conn_ro('select_all', *args, **kwds)

    def select_one(self, *args, **kwds):
        return self._run_with_conn_ro('select_one', *args, **kwds)

    def get(self, *args, **kwds):
        return self._run_with_conn_ro('get', *args, **kwds)

    def getsequence(self, *args, **kwds):
        return self._run_with_conn_ro('getsequence', *args, **kwds)

    # Read-write methods.

    def insert(self, *args, **kwds):
        return self._run_with_conn('insert', *args, **kwds)

    def create(self, *args, **kwds):
        return self._run_with_conn('create', *args, **kwds)

    def update(self, *args, **kwds):
        return self._run_with_conn('update', *args, **kwds)

    def delete(self, *args, **kwds):
        return self._run_with_conn('delete', *args, **kwds)


# Decorators

def connected_ro(fun):
    """
    Decorator that fetches a connection and that outputs a database error
    appropriately.  This passed a connection as one of the keyword arguments
    under the name 'conn'.
    """
    def wfun(*args, **kwds):
        conn = dbpool().connection_ro()
        try:
            assert 'conn' not in kwds
            kwds['conn'] = conn
            return fun(*args, **kwds)
        finally:
            conn.release()
    return wfun

def connected(fun):
    """
    Decorator, similar to connected_ro() but that passes a RW connection and
    that commits automatically.

    FIXME: we want to make the automatic commit optional.
    FIXME: we would like to also ask for some cursors to be automatically passed
           ain.
    """
    def wfun(*args, **kwds):
        conn = dbpool().connection()
        try:
            assert 'conn' not in kwds
            kwds['conn'] = conn
            r = fun(*args, **kwds)
            conn.commit()
            return r
        finally:
            conn.release()
    return wfun




class ConnectionPoolInterface(object):
    """
    Interface for a connection pool.  This is documentation for the public
    interface that you are supposed to use.
    """
    def module(self):
        """
        Get access to the DBAPI-2.0 module.  This is necessary for some of the
        standard objects it provides, e.g. Binary().
        """

    def connection(self, nbcursors=0, readonly=False):
        """
        Acquire a connection for read an write operations.

        As a convenience, additionally create a number of cursors and return
        them along with the connection, for example::

           conn, curs1, curs2 = dbpool.connection(2)

        Invoke with readonly=True if you need a read-only connection
        (alternatively, you can use the connection_ro() method below).
        """

    def connection_ro(self, nbcursors=0):
        """
        Acquire a connection for read-only operations.
        See connection() for details.
        """

    def finalize(self):
        """
        Finalize the pool, which closes remaining open connections.
        """



class ConnectionPool(ConnectionPoolInterface):
    """
    A pool of database connections that can be shared by a number of threads.
    """

    _def_minconn = 5
    """The minimum number of connections to keep around."""

    _def_maxconn = None
    """The maximum number of connections to ever allocate (None means that there
    is no limit).  When the maximum is reached, acquiring a new connection is a
    blocking operation."""

    _def_minkeepsecs = 5 # seconds
    """The minimum amount of seconds that we should keep connections around
    for."""

    _def_disable_rollback = False
    """Should we disable the rollback on released connections?"""

    def __init__(self, dbapi, options=None, **params):
        """
        'dbapi': the DBAPI-2.0 module interface for creating connections.
        'minconn': the minimum number of connections to keep around.
        'maxconn': the maximum allowed number of connections to the DB.
        'debug': flag to enable printing debugging output.
        '**params': connection parameters for creating a new connection.
        """
        self.dbapi = dbapi
        """The DBAPI-2.0 module interface."""

        self._params = params
        if not params:
            raise Error("You need to specify valid connection parameters in "
                        "order to creat4e a connection pool.")
        """The parameters for creating a connection."""

        self._pool = []
        self._pool_lock = threading.Condition(threading.RLock())
        """A pool of database connections and an associated lock for access."""

        self._nbconn = 0
        """The total number read-write database connections that were handed
        out.  This does not include the RO connection, if it is created."""

        self._roconn = None
        self._roconn_lock = threading.Lock()
        self._roconn_refs = 0
        """A connection for read-only access and an associated lock for
        creation.  We also store the number of references to it that were
        handled to clients."""

        if options is None:
            options = {}

        self._debug = options.pop('debug', False)
        if self._debug:
            assert hasattr(self._debug, 'write')
            self._log_lock = threading.Lock()
            """Lock used to serialize debug output between threads."""

        disable_ro = options.pop('disable_ro', False)
        if not disable_ro and dbapi.threadsafety < 2:
            # Note: Configure with disable_ro to remove this warning
            # message.
            warnings.warn(
                "Warning: Your DBAPI module '%s' does not support sharing "
                "connections between threads." % str(dbapi))

            # Disable the RO connection by force.
            disable_ro = True

        if disable_ro:
            # Disable create the unique RO connection.
            self.connection_ro = self._connection_ro_crippled
        self._ro_shared = not disable_ro

        self._minconn = options.pop('minconn', self._def_minconn)

        self._maxconn = options.pop('maxconn', self._def_maxconn)
        if self._maxconn is not None:
            # Reserve one of the available connections for the RO connection.
            if not self._ro_shared:
                self._maxconn -= 1
            assert self._maxconn > 0

        self._minkeepsecs = options.pop('minkeepsecs', self._def_minkeepsecs)

        self._disable_rollback = options.pop('disable_rollback',
                                             self._def_disable_rollback)

        self._user_ro = options.pop('user_readonly', None)
        """User for read-only connections.  You might want to setup different
        privileges for that user in your database configuration."""

        self._debug_unreleased = options.pop('debug_unreleased', None)
        assert (self._debug_unreleased is None or
                isinstance(self._debug_unreleased, types.FunctionType))

        """Function to call when the connection wrappers are being closed as a
        result of being collected.  This is used to trigger some kind of check
        when you forget to release some connections explicitly."""

        self._isolation_level = options.pop('isolation_level', None)

    def ro_shared(self):
        """
        Returns true if the read-only connections are shared between the
        threads.
        """
        return self._ro_shared

    def module(self):
        """
        (See base class.)
        """
        return self.dbapi

    def _log(self, msg):
        """
        Debugging information logging.
        """
        if self._debug:
            self._log_lock.acquire()
            curthread = threading.currentThread()
            self._debug.write('   [%s %s] %s\n' %
                              (curthread.getName(), os.getpid(), msg))
            self._log_lock.release()

    def _create_connection(self, read_only):
        """
        Create a new connection to the database.
        """
        self._log('Connection Create%s' % (read_only and ' (READ ONLY)' or ''))
        params = self._params
        if read_only and self._user_ro:
            params = params.copy()
            params['user'] = self._user_ro

        newconn = self.dbapi.connect(*(), **params)

        # Set the isolation level if specified in the options.
        if self._isolation_level is not None:
            newconn.set_isolation_level(self._isolation_level)
        return newconn

    def _close(self, conn):
        """
        Close the given connection for the database.
        """
        self._log('Connection Close')
        return conn.close()

    @staticmethod
    def _add_cursors(conn_wrapper, nbcursors):
        """
        Return an appropriate value depending on the number of cursors requested
        for a connection wrapper.
        """
        if nbcursors == 0:
            return conn_wrapper
        else:
            r = [conn_wrapper]
            for i in xrange(nbcursors):
                r.append(conn_wrapper.cursor())
            return r

    def _get_connection_ro(self):
        """
        Acquire a read-only connection.
        """
        self._roconn_lock.acquire()
        self._log('Acquire RO')
        try:
            if not self._roconn:
                self._roconn = self._create_connection(True)
            self._roconn_refs += 1
        finally:
            self._roconn_lock.release()
        return self._roconn

    def connection_ro(self, nbcursors=0):
        """
        (See base class.)
        """
        return self._add_cursors(
            ConnectionWrapperRO(self._get_connection_ro(), self), nbcursors)

    def _acquire(self):
        """
        Acquire a connection from the pool, for read an write operations.

        Note that if the maximum number of connections has been reached, this
        becomes a blocking operation.
        """
        self._pool_lock.acquire()
        self._log('Acquire (begin)  Pool: %d  / Created: %s' %
                  (len(self._pool), self._nbconn))
        try:
            # Apply maximum number of connections constraint.
            if self._maxconn is not None:
                # Sanity check.
                assert self._nbconn <= self._maxconn

                while not self._pool and self._nbconn == self._maxconn:
                    # Block until a connection is released.
                    self._log('Acquire (wait)  Pool: %d  / Created: %s' %
                              (len(self._pool), self._nbconn))
                    self._pool_lock.wait()
                    self._log('Acquire (signaled)  Pool: %d  / Created: %s' %
                              (len(self._pool), self._nbconn))

                # Assert that we have a connection in the pool or that we can
                # create a new one if needed, i.e. what we waited for just
                # before.  (This is now a useless sanity check.)
                assert self._pool or self._nbconn < self._maxconn

            if self._pool:
                conn, last_released = self._pool.pop()
            else:
                # Make sure that we never create a new connection if we have
                # reached the maximum.
                if self._maxconn is not None:
                    assert self._nbconn < self._maxconn

                conn = self._create_connection(False)
                self._nbconn += 1

            self._log('Acquire (end  )  Pool: %d  / Created: %s' %
                      (len(self._pool), self._nbconn))
        finally:
            self._pool_lock.release()
        return conn

    def _connection_ro_crippled(self, nbcursors=0):
        """
        Replacement for connection_ro() that actually uses the pool to get its
        connections.  This is used when the dbapi does not allow threads to
        share a connection.
        """
        conn = self._acquire()
        return self._add_cursors(ConnectionWrapperCrippled(conn, self),
                                 nbcursors)

    def _get_connection(self):
        """
        Acquire a read-write connection.
        """
        return self._acquire()

    def connection(self, nbcursors=0, readonly=False):
        """
        (See base class.)
        """
        if readonly:
            return self.connection_ro(nbcursors)
        return self._add_cursors(
            ConnectionWrapper(self._get_connection(), self), nbcursors)

    def _release_ro(self, conn):
        """
        Release a reference to the read-only connection.  You should not use
        this directly, you should instead call release() or close() on the
        connection object.
        """
        self._roconn_lock.acquire()

        try:
            if conn is self._roconn:
                assert self._roconn

                self._roconn_refs -= 1
                self._log('Release RO')

                # Make sure a released connection is not blocking anything else, so
                # rollback.  Technically this should not block anything, since the
                # only operations that are carried out on this connection are RO,
                # but we won't risk a deadlock because the user made a programming
                # error.
                try:
                    if not self._disable_rollback:
                        conn.rollback()
                except self.dbapi.Error:
                    # This connection is hosed somehow, we should ditch it.
                    self._log('Ditching hosed RO connection: %s' % conn)
                    self._roconn = None
                    self._roconn_refs = 0
            else:
                # Ignored the release of other hosed connections.
                self._log('Hosed connection %s released after ditched.' % conn)
        finally:
            self._roconn_lock.release()

    def _release(self, conn):
        """
        Release a reference to a read-and-write connection.
        """
        self._pool_lock.acquire()
        try:
            self._log('Release (begin)  Pool: %d  / Created: %s' %
                      (len(self._pool), self._nbconn))

            # Make sure a released connection is not blocking anything else.
            try:
                if not self._disable_rollback:
                    conn.rollback()
            except self.dbapi.Error:
                # Oopsy, this connection is hosed somehow.  We need to ditch it.
                self._log('Ditching hosed connection: %s' % conn)
                conn = None
                self._nbconn -= 1
                return

            assert conn is not self._roconn # Sanity check.

            self._pool.append( (conn, datetime.now()) )
            self._scaledown()
            assert self._pool or self._nbconn < self._maxconn
            self._log('Release (notify)  Pool: %d  / Created: %s' %
                      (len(self._pool), self._nbconn))
            self._pool_lock.notify()
            self._log('Release (notified)  Pool: %d  / Created: %s' %
                      (len(self._pool), self._nbconn))

            self._log('Release (end  )  Pool: %d  / Created: %s' %
                      (len(self._pool), self._nbconn))
        finally:
            self._pool_lock.release()

    def _scaledown(self):
        """
        Scale down the number of connection according to the following
        heuristic: we want keep a minimum number of extra connections in the
        pool ready for usage.  We delete all connections above that number if
        they have last been used beyond a fixed timeout.
        """
        self._pool_lock.acquire()
        try:
            self._log('Scaledown')

            # Calculate a recent time limit beyond which we always keep the
            # connections.
            minkeepsecs = datetime.now() - timedelta(seconds=self._minkeepsecs)

            # Calculate the number of connections that we can get rid of.
            n = len(self._pool) - self._minconn
            if n > 0:
                filtered_pool = []
                for poolitem in self._pool:
                    conn, last_released = poolitem
                    if n > 0 and last_released < minkeepsecs:
                        self._close(conn)
                        self._nbconn -= 1
                        n -= 1
                    else:
                        filtered_pool.append(poolitem)
                self._pool = filtered_pool
        finally:
            self._pool_lock.release()

        # Note: we could keep the pool sorted by last_released to minimize the
        # scaledown time, so that the first items in the pool are always the
        # oldest, the most likely to be deletable.

    def finalize(self):
        """
        Close all the open connections and finalize (prepare for reuse).
        """
        # Make sure that all connections lying about are collected before we go
        # on.
        try:
            gc.collect()
        except (TypeError, AttributeError):
            # We've detected that we're being called in an incomplete
            # finalization state, we just bail out, leaving the connections
            # to take care of themselves.
            return

        self._roconn_lock.acquire()
        self._pool_lock.acquire()
        try:
            if not self._pool and not self._roconn:
                assert self._nbconn == 0
                return # Already finalized.

            # Check that all the connections have been returned to us.
            assert len(self._pool) == self._nbconn

            assert self._roconn_refs == 0
            if self._roconn is not None:
                self._close(self._roconn)
                self._roconn = None

            # Release all the read-write pool's connections.
            for conn, last_released in self._pool:
                self._close(conn)

            poolsize = len(self._pool)
            self._pool = []

            self._log('Finalize  Pool: %d  / Created: %s' %
                      (poolsize, self._nbconn))

            # Reset statistics.
            self._nbconn = 0
        finally:
            self._roconn_lock.release()
            self._pool_lock.release()

    def __del__(self):
        """
        Destructor.
        """
        self.finalize()

    def getstats(self):
        """
        Return internal statistics.  This is used for producing graphs depicting
        resource requirements over time.  Returns the total number of
        connections open (including the RO connection) and the current number of
        connections held in the internal pool.
        """
        total_conn = 0
        self._roconn_lock.acquire()
        try:
            if self._roconn:
                total_conn += 1
        finally:
            self._roconn_lock.release()

        self._pool_lock.acquire()
        total_conn += self._nbconn
        try:
            pool_size = len(self._pool)
        finally:
            self._pool_lock.release()

        return total_conn, pool_size

    def forget_connections(self):
        """
        Forget all the existing connections and close the sockets.  This MUST be
        called from a child process right after forking.
        """
        self._roconn_lock = threading.Lock()
        self._pool_lock = threading.Condition(threading.RLock())

        self._roconn = None
        self._pool = []
        self._nbconn = 0

## FIXME: todo, close the file descriptors (unix ::close()
## FIXME: continue this, you need to fix the test: test_fork.py




class ConnectionWrapperRO(object):
    """
    A wrapper object that behaves like a database connection for read-only
    operations.  You cannot close() this explicitly, you should call release().

    Important: you should always try to explicitly release these objects, in
    order to minimize the number of open connections in the pool.  If you do not
    release explicitly, the pool has to keep the connection open.  Here is the
    preferred way to do this:

       connection = dbpool.connection()
       try:
           # you code here
       finally:
           connection.release()

    Note that this connection wrapper does not allow committing.  It is meant
    for read-only operations (i.e. SELECT). See class ConnectionWrapper for the
    commit method.
    """
    def __init__(self, conn, pool):
        assert conn
        self._conn = conn
        self._connpool = pool

    def __del__(self):
        if self._conn:
            unrel = self._connpool._debug_unreleased
            if unrel:
                unrel(self)
            self.release()

    def _getconn(self):
        if self._conn is None:
            raise Error("Error: Connection already closed.")
        else:
            return self._conn

    def release(self):
        self._release_impl(self._getconn())
        self._connpool = self._conn = None

    def _release_impl(self, conn):
        self._connpool._release_ro(conn)

    def cursor(self, *args, **kw):
        return self._getconn().cursor(*args, **kw)

    def commit(self):
        raise Error("Error: You cannot commit on a read-only connection.")

    def rollback(self):
        return self._getconn().rollback()

    # Support for the context object.

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        
class ConnectionWrapperCrippled(ConnectionWrapperRO):
    """
    A wrapper object that releases to the pool.  It still does not provide a
    commit() method however.
    """
    def _release_impl(self, conn):
        self._connpool._release(conn)

class ConnectionWrapper(ConnectionWrapperCrippled):
    """
    A wrapper object that allows write operations and provides a commit()
    method.  See ConnectionWrapperRO for more details.
    """
    def commit(self):
        return self._getconn().commit()

    # Support for the context object.

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.release()


class Error(Exception):
    """
    Error for connection wrappers.
    """


