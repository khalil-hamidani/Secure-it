# -*- coding: iso-8859-1 -*-
# pylint: disable-msg=W0302

"""
An Anti-ORM, a simple utility functions to ease the writing of SQL statements
with Python DBAPI-2.0 bindings.  This is not an ORM, but it's just as tasty!

This is a only set of support classes that make it easier to write your own
queries yet have some automation with the annoying tasks of setting up lists of
column names and values, as well as doing the type conversions automatically.

And most importantly...

   THERE IS NO FRIGGIN' MAGIC IN HERE.

Some notes:

* You always have to pass in the connection objects that the operations are
  performed on.  This allows connection pooling to be entirely separate from
  this library.

* There is never any automatic commit performed here, you must commit your
  connection by yourself after you've executed the appropriate commands.

Usage
=====

Most of the convenience functions accept a WHERE condition and a tuple or list
of arguments, which are simply passed on to the DBAPI interface.


Declaring Tables
----------------

The table must declare the SQL table's name on the 'table' class attribute and
should derive from MormTable.

You do not need to declare columns on your tables.  However, if you need custom
conversions--right now, only string vs. unicode are useful--you declare a
'converters' mapping from SQL column name to the converter to be used, just for
the columns which require conversion (you can leave others alone).  You can
create your own custom converters if so desired.

The class of objects that are returned by the query methods can be defaulted by
setting 'objcls' on the table.  This class should/may derive from MormObject,
e.g.::

  class TestTable(MormTable):
      table = 'test1'
      objcls = Person
      converters = {
          'firstname': MormConvUnicode(),
          'lastname': MormConvUnicode(),
          'religion': MormConvString()
          }


Insert (C)
----------
Insert some new row in a table::

  TestTable.insert(connection,
                   firstname=u'Adriana',
                   lastname=u'Sousa',
                   religion='candomblé')

Select (R)
----------
Add a where condition, and select some columns::

  for obj in TestTable.select(connection,
                              'WHERE id = %s', (2,), cols=('id', 'username')):
      # Access obj.id, obj.username

The simplest version is simply accessing everything::

  for obj in TestTable.select(connection):
      # Access obj.id, obj.username and more.

Update (U)
----------
Update statements are provided as well::

  TestTable.update(connection,
                   'WHERE id = %s', (2,),
                   lastname=u'Depardieu',
                   religion='candomblé')

Delete (D)
----------
Deleting rows can be done similarly::

  TestTable.delete('WHERE id = %s', (1,))


Lower-Level APIs
----------------

See the tests at the of this file for examples on how to do things at a
lower-level, which is necessary for complex queries (not that it hurts too much
either).  In particular, you should have a look at the MormDecoder and
MormEncoder classes.


See doc/ in distribution for additional notes.
"""

__author__ = 'Martin Blais <blais@furius.ca>'


__all__ = ['MormTable', 'MormObject', 'MormError',
           'MormConv', 'MormConvUnicode', 'MormConvString',
           'MormDecoder', 'MormEncoder']



class NODEF(object):
    """
    No-defaults constant.
    """



class MormObject(object):
    """
    An instance of an initialized decoded row.
    This is just a dummy container for attributes.
    """


class MormTable(object):
    """
    Class for declarations that relate to a table.

    This acts as the base class on which derived classes add custom conversions.
    An instance of this class acts as a wrapper decoder and iterator object,
    whose behaviour depends on the custom converters.
    """

    #---------------------------------------------------------------------------

    table = None
    "Table name in the database."

    pkseq = None
    "Sequence for primary key."

    objcls = MormObject
    "Class of objects to create"

    converters = {}
    "Custom converter map for columns"

    #---------------------------------------------------------------------------
    # Misc methods.

    @classmethod
    def tname(cls):
        assert cls.table is not None
        return cls.table

    @classmethod
    def encoder(cls, **cols):
        """
        Encode the given columns according to this class' definition.
        """
        return MormEncoder(cls, cols)

    @classmethod
    def decoder(cls, desc):
        """
        Create a decoder for the column names described by 'desc'.  'desc' can
        be either a sequence of column names, or a cursor from which we will
        fetch the description.  You will still have to pass in the cursor for
        decoding later on.
        """
        return MormDecoder(cls, desc)

    #---------------------------------------------------------------------------
    # Methods that only read from the connection

    @classmethod
    def count(cls, conn, cond=None, args=None, distinct=None):
        """
        Counts the number of selected rows.
        """
        assert conn is not None

        # Perform the select.
        cursor = MormDecoder.do_select(conn, (cls,), ('1',),
                                       cond, args, distinct)

        # Return the number of matches.
        return cursor.rowcount

    @classmethod
    def select(cls, conn, cond=None, args=None, cols=None,
               objcls=None, distinct=None):
        """
        Convenience method that executes a select and returns an iterator for
        the results, wrapped in objects with attributes
        """
        assert conn is not None

        # Perform the select.
        cursor = MormDecoder.do_select(conn, (cls,), cols,
                                       cond, args, distinct)

        # Create a decoder using the description on the cursor.
        dec = MormDecoder(cls, cursor)

        # Return an iterator over the cursor.
        return dec.iter(cursor, objcls)

    @classmethod
    def select_all(cls, conn, cond=None, args=None, cols=None,
                   objcls=None, distinct=None):
        """
        Convenience method that executes a select and returns a list of all the
        results, wrapped in objects with attributes
        """
        assert conn is not None

        # Perform the select.
        cursor = MormDecoder.do_select(conn, (cls,), cols,
                                       cond, args, distinct)

        # Create a decoder using the description on the cursor.
        dec = MormDecoder(cls, cursor)

        # Fetch all the objects from the cursor and decode them.
        objects = []
        for row in cursor.fetchall():
            objects.append(dec.decode(row, objcls=objcls))

        return objects

    @classmethod
    def select_one(cls, conn, cond=None, args=None, cols=None,
                   objcls=None, distinct=None):
        """
        Convenience method that executes a select the first object that matches,
        and that also checks that there is a single object that matches.
        """
        it = cls.select(conn, cond, args, cols, objcls, distinct)
        if len(it) > 1:
            raise MormError("select_one() matches more than one row.")
        try:
            o = it.next()
        except StopIteration:
            o = None
        return o

    @classmethod
    def get(cls, conn, cols=None, default=NODEF, **constraints):
        """
        Convenience method that gets a single object by its primary key.
        """
        cons, args = [], []
        for colname, colvalue in list(constraints.items()):
            cons.append('%s = %%s' % colname)
            args.append(colvalue)

        cond = 'WHERE ' + ' AND '.join(cons)
        it = cls.select(conn, cond, args, cols)
        try:
            if len(it) == 0:
                if default is NODEF:
                    raise MormError("Object not found (%s)." % str(constraints))
                else:
                    return default
            return it.next()
        finally:
            del it

    @classmethod
    def getsequence(cls, conn, pkseq=None):
        """
        Return a sequence number.
        This allows us to quickly get the last inserted row id.
        """
        if pkseq is None:
            pkseq = cls.pkseq
            if pkseq is None:
                if cls.table is None:
                    raise MormError("No table specified for "
                                       "getting sequence value")

                # By default use PostgreSQL convention.
                pkseq = '%s_id_seq' % cls.table

        # Run the query.
        assert conn
        cursor = conn.cursor()

        cursor.execute("SELECT currval(%s)", (pkseq,))
        seq = cursor.fetchone()[0]

        return seq


    #---------------------------------------------------------------------------
    # Methods that write to the connection

    @classmethod
    def execute(cls, conn, query, args=None, objcls=None):
        """
        Execute an arbitrary read-write SQL statement and return a decoder for
        the results.
        """
        assert conn
        cursor = conn.cursor()
        cursor.execute(query, args)
        
        # Get a decoder with the cursor results.
        dec = MormDecoder(cls, cursor)

        # Return an iterator over the cursor.
        return dec.iter(cursor, objcls)

    @classmethod
    def insert(cls, conn, cond=None, args=None, **fields):
        """
        Convenience method that creates an encoder and executes an insert
        statement.  Returns the encoder.
        """
        enc = cls.encoder(**fields)
        return enc.insert(conn, cond, args)

    @classmethod
    def create(cls, conn, cond=None, args=None, pk='id', **fields):
        """
        Convenience method that creates an encoder and executes an insert
        statement, and then fetches the data back from the database (because of
        defaults) and returns the new object.

        Note: this assumes that the primary key is composed of a single column.
        Note2: this does NOT commit the transaction.
        """
        cls.insert(conn, cond, args, **fields)
        pkseq = '%s_%s_seq' % (cls.table, pk)
        seq = cls.getsequence(conn, pkseq)
        return cls.get(conn, **{pk: seq})

    @classmethod
    def update(cls, conn, cond=None, args=None, **fields):
        """
        Convenience method that creates an encoder and executes an update
        statement.  Returns the encoder.
        """
        enc = cls.encoder(**fields)
        return enc.update(conn, cond, args)

    @classmethod
    def delete(cls, conn, cond=None, args=None):
        """
        Convenience method that deletes rows with the given condition.  WARNING:
        if you do not specify any condition, this deletes all the rows in the
        table!  (just like SQL)
        """
        if cond is None:
            cond = ''
        if args is None:
            args = []

        # Run the query.
        assert conn
        cursor = conn.cursor()
        cursor.execute("DELETE FROM %s %s" % (cls.table, cond),
                       list(args))
        return cursor



class MormError(Exception):
    """
    Error happening in this module.
    """



class MormConv(object):
    """
    Base class for all automated type converters.
    """
    def from_python(self, value):
        """
        Convert value from Python into a type suitable for insertion in a
        database query.
        """
        return value

    def to_python(self, value):
        """
        Convert value from the type given by the database connection into a
        Python type.
        """
        return value



# Encoding from the DBAPI-2.0 client interface.
dbapi_encoding = 'UTF-8'

class MormConvUnicode(MormConv):
    """
    Conversion between database-encoded string to unicode type.
    """
    def from_python(self, vuni):
        if isinstance(vuni, str):
            vuni = vuni.decode()
        return vuni # Keep as unicode, DBAPI takes care of encoding properly.

    def to_python(self, vstr):
        if vstr is not None:
            return vstr.decode(dbapi_encoding)

class MormConvString(MormConv):
    """
    Conversion between database-encoded string to unicode type.
    """
    # Default value for the desired encoding for the string.
    encoding = 'ISO-8859-1'

    def __init__(self, encoding=None):
        MormConv.__init__(self)
        if encoding:
            self.encoding = encoding
        self.sameenc = (encoding == dbapi_encoding)

    def from_python(self, vuni):
        if isinstance(vuni, str):
            vuni = vuni.decode(self.encoding)
        # Send as unicode, DBAPI takes care of encoding with the appropriate
        # client encoding.
        return vuni

    def to_python(self, vstr):
        if vstr is not None:
            if self.sameenc:
                return vstr
            else:
                return vstr.decode(dbapi_encoding).encode(self.encoding)



class MormEndecBase(object):
    """
    Base class for classes that accept list of tables.
    """
    def __init__(self, tables):

        # Accept multiple formats for tables list.
        self.tables = []
        if not isinstance(tables, (tuple, list)):
            assert issubclass(tables, MormTable)
            tables = (tables,)
        for cls in tables:
            assert issubclass(cls, MormTable)
        self.tables = tuple(tables)
        """Tables is a list of tables that this decoder will use, in order.  You
        can also pass in a single table class, or a sequence of table"""
        assert self.tables

    def table(self):
        return self.tables[0].tname()

    def tablenames(self):
        return ','.join(x.tname() for x in self.tables)



class MormDecoder(MormEndecBase):
    """
    Decoder class that takes care of creating instances with appropriate
    attributes for a specific row.
    """
    def __init__(self, tables, desc):
        MormEndecBase.__init__(self, tables)

        if isinstance(desc, (tuple, list)):
            colnames = desc
        else:
            assert desc is not None
            colnames = [x[0] for x in desc.description]

        assert colnames
        self.colnames = colnames
        """List of column names to restrict decoding.."""

        # Note: dotted notation inputs are ignored for now.
        #
        # if colnames is not None: # Remove dotted notation if present.
        #     self.colnames = [c.split('.')[-1] for c in colnames]
        self.attrnames = dict((c, c.split('.')[-1]) for c in colnames)
        assert len(self.attrnames) == len(self.colnames)

    def cols(self):
        """
        Return a list of field names, suitable for insertion in a query.
        """
        return ', '.join(self.colnames)

    def decode(self, row, obj=None, objcls=None):
        """
        Decode a row.
        """
        if len(self.colnames) != len(row):
            raise MormError("Row has incorrect length for decoder.")

        # Convert all the values right away.  We assume that the query is
        # minimal and that we're going to need to access all the values.
        if obj is None:
            if objcls is not None:
                # Use the given class if present.
                obj = objcls()
            else:
                # Otherwise look in the list of tables, one-by-one until we find
                # an object class to use.
                for table in self.tables:
                    if table.objcls is not None:
                        obj = table.objcls()
                        break
                else:
                    # Otherwise just use the default
                    obj = MormObject()

        for cname, cvalue in zip(self.colnames, row):
            if '.' in cname:
                # Get the table with the matching name and use the converter on
                # this table if there is one.
                comps = cname.split('.')
                tablename, cname = comps[0], comps[-1]
                for cls in self.tables:
                    if cls.tname() == tablename:
                        converter = cls.converters.get(cname, None)
                        if converter is not None:
                            cvalue = converter.to_python(cvalue)
                        break
            else:
                # Look in the table list for the first appropriate found
                # converter.
                for cls in self.tables:
                    converter = cls.converters.get(cname, None)
                    if converter is not None:
                        cvalue = converter.to_python(cvalue)
                        break

            ## setattr(obj, self.attrnames[cname], cvalue)
            setattr(obj, cname, cvalue)
        return obj

    def iter(self, cursor, objcls=None):
        """
        Create an iterator on the given cursor.
        This also deals with the case where a cursor has no results.
        """
        if cursor is None:
            raise MormError("No cursor to iterate.")
        return MormDecoderIterator(self, cursor, objcls)


    #---------------------------------------------------------------------------

    @staticmethod
    def do_select(conn, tables, colnames=None, cond=None, condargs=None,
                  distinct=None):
        """
        Guts of the select methods.  You need to pass in a valid connection
        'conn'.  This returns a new cursor from the given connection.

        Note that this method is limited to be able to select on a single table
        only.  If you want to select on multiple tables at once you will need to
        do the select yourself.
        """
        tablenames = ','.join(x.tname() for x in tables)

        if colnames is None:
            colnames = ('*',)

        if cond is None:
            cond = ''
        if condargs is None:
            condargs = []
        else:
            assert isinstance(condargs, (tuple, list, dict))

        assert conn is not None

        # Run the query.
        cursor = conn.cursor()

        distinct = distinct and 'DISTINCT' or ''
        sql = "SELECT %s %s FROM %s %s" % (distinct, ', '.join(colnames),
                                           tablenames, cond)
        cursor.execute(sql, condargs)

        return cursor



class MormDecoderIterator(object):
    """
    Iterator for a decoder.
    """
    def __init__(self, decoder, cursor, objcls=None):
        self.decoder = decoder
        self.cursor = cursor
        self.objcls = objcls

    def __len__(self):
        return self.cursor.rowcount

    def __iter__(self):
        return self

    def next(self, obj=None, objcls=None):
        if self.cursor.rowcount == 0:
            raise StopIteration

        if objcls is None:
            objcls = self.objcls

        row = self.cursor.fetchone()
        if row is None:
            raise StopIteration
        else:
            return self.decoder.decode(row, obj, objcls)



class MormEncoder(MormEndecBase):
    """
    Encoder class.  This class converts and contains a set of argument according
    to declared table conversions.  This is mainly used to create INSERT or
    UPDATE statements.
    """
    def __init__(self, tables, fields):
        MormEndecBase.__init__(self, tables)

        self.colnames = []
        """Names of all the columns of the encoder."""

        self.colvalues = []
        """Encoded values of all the fields of the encoder."""

        # Set column names and values, converting if necessary.
        for cname, cvalue in list(fields.items()):
            self.colnames.append(cname)

            # Apply converter to value if necessary
            for cls in self.tables:
                converter = cls.converters.get(cname, None)
                if converter is not None:
                    cvalue = converter.from_python(cvalue)
                    break

            self.colvalues.append(cvalue)

    def cols(self):
        return ', '.join(self.colnames)

    def values(self):
        """
        Returns the list of converted values.
        This is useful to let DBAPI do the automatic quoting.
        """
        return self.colvalues

    def plhold(self):
        """
        Returns a string for holding replacement values in the query string,
        e.g.: %s, %s, %s
        """
        return ', '.join(['%s'] * len(self.colvalues))

    def set(self):
        """
        Returns a string for holding 'set values' syntax in the query string,
        e.g.: col1 = %s, col2 = %s, col3 = %s
        """
        return ', '.join(('%s = %%s' % x) for x in self.colnames)

    def insert(self, conn, cond=None, args=None):
        """
        Execute a simple insert statement with the contained values.  You can
        only use this on a single table for now.  Note: this does not commit the
        connection.
        """
        assert len(self.tables) == 1
        if cond is None:
            cond = ''
        if args is None:
            args = []

        # We must be given a valid connection in 'conn'.
        assert conn

        # Run the query.
        cursor = conn.cursor()

        sql = ("INSERT INTO %s (%s) VALUES (%s) %s" %
               (self.table(), self.cols(), self.plhold(), cond))
        cursor.execute(sql, list(self.values()) + list(args))

        return cursor

    def update(self, conn, cond=None, args=None):
        """
        Execute a simple update statement with the contained values.  You can
        only use this on a single table for now.  Note: this does not commit the
        connection.  If you supply your own connection, we return the cursor
        that we used for the query.
        """
        assert len(self.tables) == 1
        if cond is None:
            cond = ''
        if args is None:
            args = []

        # We must be given a valid connection in 'conn'.
        assert conn

        # Run the query.
        cursor = conn.cursor()

        sql = "UPDATE %s SET %s %s" % (self.table(), self.set(), cond)
        cursor.execute(sql, list(self.values()) + list(args))

        return cursor

