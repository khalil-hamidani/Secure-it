"""
An extention to DBAPI-2.0 for more easily building SQL statements.

This extension allows you to call a DBAPI Cursor's execute method with a string
that contains format specifiers for escaped and/or unescaped arguments.  Escaped
arguments are specified using `` %X `` or `` %S `` (capital X or capital S).
You can also mix positional and keyword arguments in the call, and this takes
advantage of the Python call syntax niceties.  Also, lists passed in as
parameters to be formatted are automatically detected and joined by commas (this
works for both unescaped and escaped parameters-- lists to be escaped have their
elements escaped individually).  In addition, if you pass in a dictionary
corresponding to an escaped formatting specifier, the dictionary is rendered as
a list of comma-separated <key> = <value> pairs, such as are suitable for an
INSERT statement.

For performance, the results of analysing and preparing the query is kept in a
cache and reused on subsequence calls, similarly to the re or struct library.

(This is intended to become a reference implementation for a proposal for an
extension to tbe DBAPI-2.0.)

.. note:: for now the transformation only works with DBAPIs that supports
          parametric arguments in the form of Python's syntax for now
          (e.g. psycopg2).  It could easily be extended to support other DBAPI
          syntaxes.

For more details and motivation, see the accompanying explanation document at
http://furius.ca/pubcode/pub/conf/lib/python/dbapiext.html

5-minute usage instructions:

  Run execute_f() with a cursor object and appropriate arguments::

    execute_f(cursor, ' SELECT %s FROM %(t)s WHERE id = %S ', cols, id, t=table)

  Ideally, we should be able to monkey-patch this method onto the cursor class
  of the DBAPI library (this may not be possible if it is an extension module).

  By default, the result of analyzing each query is cached automatically and
  reused on further invocations, to minimize the amount of analysis to be
  performed at runtime.  If you want to do this explicitly, first compile your
  query, and execute it later with the resulting object, e.g.::

    analq = qcompile(' SELECT %s FROM %(t)s WHERE id = %S ')
    ...
    analq.execute(cursor, cols, id, t=table)

**Note to developers: this module contains tests, if you make any changes,
please make sure to run and fix the tests.**


Also, a formatting specifier is provided for where clauses: ``%A``, which joins
its contained entries with ``AND``. The only accepted data types are list of
pairs or a dictionary. Maybe we could provide an OR version (``%A`` and
``%O``).


Future Work
===========

- We could provide a reduce() method on the QueryAnalyzer, that will apply the
  given parameters and save the calculated arguments for later use; This would
  allow us to apply queries using multiple calls, to fill in only certain
  parameters at a time.  This method would return a new QueryAnalyzer, albeit
  one that would contain some pre-cooked apply_kwds and delay_kwds to be
  accumulated to in the apply call.

- Provide a simple test function that would allow people to test their queries
  without having to create a TestCursor.


"""

# stdlib imports
import re
from datetime import date, datetime
from itertools import starmap
from itertools import count
from pprint import pprint

# These imports only work in Python 2.x, but the built-ins are fine in 3.x.
try:
    from itertools import imap
    from itertools import izip
except ImportError:
    imap = map
    izip = zip

# The first module is Python 2.x, the second is 3.x.
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


__all__ = ('execute_f', 'qcompile', 'set_paramstyle', 'execute_obj')


# Create aliases for Python 3.x compatibility
try:
    xrange
except NameError:
    xrange = range
try:
    unicode
except NameError:
    unicode = str


# Convenince function since Python 3.x has new syntax for next
def _next(i):
    try:
        return i.next()
    except AttributeError:
        return next(i)

# Ditto for dictionary iterators
def _iteritems(d):
    try:
        return d.iteritems()
    except AttributeError:
        return d.items()

def _iterkeys(d):
    try:
        return d.iterkeys()
    except AttributeError:
        return d.keys()


class QueryAnalyzer(object):
    """
    Analyze and contain a query string in a way that we can quickly put it back
    together when given the actual arguments.  This object contains knowledge of
    which arguments are positional and keyword, and is able to conditionally
    apply escaping when necessary, and expand lists as well.

    This is meant to be kept around or cached for efficiency.
    """

    # Note: the last few formatting characters are extra, from us.
    re_fmt = '[#0 +-]?([0-9]+|\\*)?(\\.[0-9]*)?[hlL]?[diouxXeEfFgGcrsSAO]'

    regexp = re.compile('%%(\\(([a-zA-Z0-9_]+)\\))?(%s)' % re_fmt)

    def __init__(self, query, paramstyle=None):
        self.orig_query = query

        self.positional = []
        """List of positional arguments to be consumed later.  The list consists
        of keynames."""

        self.components = None
        "A sequence of strings or match objects."

        if paramstyle is None:
            paramstyle = _def_paramstyle
        self.paramstyle = paramstyle
        self.init_style(paramstyle)
        "The parameter style supported by the underlying DBAPI."

        self.analyze() # Initialize.

    def init_style(self, paramstyle):
        "Pre-calculate style-specific constants."
        if paramstyle == 'pyformat':
            self.style_fmt = '%%%%(%(name)s)s'
            self.style_argstype = dict
        elif paramstyle == 'named':
            self.style_fmt = ':%(name)s'
            self.style_argstype = dict
        elif paramstyle == 'qmark':
            self.style_fmt = '?'
            self.style_argstype = list
        elif paramstyle == 'format':
            self.style_fmt = '%%%%s'
            self.style_argstype = list
        elif paramstyle == 'numeric':
            self.style_fmt = ':%(no)d'
            self.style_argstype = list
        # Non-standard. For our modified Sybase (from 0.37).
        elif paramstyle == 'atnamed':
            self.style_fmt = '@%(name)s'
            self.style_argstype = dict
        else:
            raise ValueError(
                "Parameter style '%s' is not supported." % paramstyle)

    def analyze(self):
        query = self.orig_query

        poscount = count(1)

        comps = self.components = []
        for x in gensplit(self.regexp, query):
            if isinstance(x, (str, unicode)):
                comps.append(x)
            else:
                keyname, fmt = x.group(2, 3)
                if keyname is None:
                    keyname = '__p%d' % _next(poscount)
                    self.positional.append(keyname)
                sep = ', '
                if fmt in 'XS':
                    fmt = 's'
                    escaped = True
                elif fmt in 'A':
                    fmt = 's'
                    escaped = True
                    sep = ' AND '
                elif fmt in 'O':
                    fmt = 's'
                    escaped = True
                    sep = ' OR '
                else:
                    escaped = False
                comps.append( (keyname, escaped, sep, fmt) )

    def __str__(self):
        """
        Return the string that would be used before application of the
        positional and keyword arguments.
        """
        style_fmt = self.style_fmt
        oss = StringIO()
        no = count(1)
        for x in self.components:
            if isinstance(x, (str, unicode)):
                oss.write(x)
            else:
                keyname, escaped, sep, fmt = x
                if escaped:
                    oss.write(style_fmt % {'name': keyname,
                                           'no': _next(no)})
                else:
                    oss.write('%%(%s)%s' % (keyname, fmt))
        return oss.getvalue()

    def apply(self, *args, **kwds):
        if len(args) != len(self.positional):
            raise TypeError('not enough arguments for format string')

        # Merge the positional arguments in the keywords dict.
        for name, value in izip(self.positional, args):
            assert name not in kwds
            kwds[name] = value

        # Patch up the components into a string.
        listexpans = {} # cached list expansions.
        apply_kwds, delay_kwds = {}, self.style_argstype()

        no = count(1)
        style_fmt = self.style_fmt
        dict_fmt = '%%(key)s = %s' % style_fmt
        output = []
        for x in self.components:
            if isinstance(x, (str, unicode)):
                out = x
            else:
                keyname, escaped, sep, fmt = x

                # Split keyword lists.
                # Expand into lists of words.
                value = kwds[keyname]
                if isinstance(value, (tuple, list, set)):
                    try:
                        words = listexpans[keyname] # Try cache.
                    except KeyError:
                        # Compute list expansion.
                        words = ['%s_l%d__' % (keyname, x)
                                 for x in xrange(len(value))]
                        listexpans[keyname] = words

                    if escaped:
                        outfmt = [style_fmt %
                                  {'name': x, 'no': _next(no)} for x in words]
                    else:
                        outfmt = ['%%(%s)%s' % (x, fmt) for x in words]

                elif isinstance(value, dict):
                    # If a dict is passed in, the format specified *must* be for
                    # escape; we detect this and raise an appropriate error.
                    if not escaped:
                        raise ValueError("Attempting to format a dict in "
                                         "an SQL statement without escaping.")

                    # Convert dict in a list of comma-separated 'name=value' pairs.
                    items = list(value.items())
                    words = ['%s_key_%s__' % (keyname, x[0]) for x in items]
                    value = [x[1] for x in items]
                    outfmt = [dict_fmt % {'key': k, 'name': word}
                              for word, (k, v) in izip(words, items)]

                else:
                    words, value = (keyname,), (value,)
                    if escaped:
                        outfmt = [style_fmt % {'name': keyname, 'no': _next(no)}]
                    else:
                        outfmt = ['%%(%s)%s' % (keyname, fmt)]

                if escaped:
                    okwds = delay_kwds
                else:
                    okwds = apply_kwds

                # Dispatch values on the appropriate output dictionary.
                assert len(words) == len(value)
                if isinstance(okwds, dict):
                    okwds.update(izip(words, value))
                else:
                    okwds.extend(value)

                # Create formatting string.
                out = sep.join(outfmt)

            output.append(out)

        # Apply positional arguments, here, now.
        newquery = ''.join(output)

        # Return the string with the delayed arguments as formatting specifiers,
        # to be formatted by DBAPI, and the delayed arguments.
        return newquery % apply_kwds, delay_kwds

    def execute(self, cursor_, *args, **kwds):
        """
        Execute the analyzed query on the given cursor, with the given arguments
        and keywords.
        """
        # Translate this call into a compatible call to execute().
        cquery, ckwds = self.apply(*args, **kwds)

        # Execute the transformed query.
        return cursor_.execute(cquery, ckwds)


def gensplit(regexp, s):
    """
    Regexp-splitter generator.  Generates strings and match objects.
    """
    c = 0
    for mo in regexp.finditer(s):
        yield s[c:mo.start()]
        yield mo
        c = mo.end()
    yield s[c:]



_def_paramstyle = 'pyformat'

def set_paramstyle(style_or_dbapi):
    """
    Sets the default paramstyle to be used by the underlying DBAPI.
    You can pass in a DBAPI module object or a string. See PEP249 for details.
    """
    global _def_paramstyle
    if isinstance(style_or_dbapi, str):
        _def_paramstyle = style_or_dbapi
    else:
        _def_paramstyle = style_or_dbapi.paramstyle
    assert _def_paramstyle in ('qmark', 'numeric',
                               'named', 'format', 'pyformat')



qcompile = QueryAnalyzer
"""
Compile a query in a compatible query analyzer.
"""



# Query cache used to avoid having to analyze the same queries multiple times.
# Hashed on the query string.
_query_cache = {}

# Note: we use cursor_ and query_ because we often call this function with
# vars() which include those names on the caller side.
def execute_f(cursor_, query_, *args, **kwds):
    """
    Fancy execute method for a cursor.  (Note: this is implemented as a function
    but is really meant to be a method to replace or complement the standard
    method Cursor.execute() from DBAPI-2.0.)

    Convert fancy query arguments into a DBAPI-compatible set of arguments and
    execute.

    This method supports a different syntax than the DBAPI execute() method:

    - By default, %s placeholders are not escaped.

    - Use the %S or %(name)S placeholder to specify escaped strings.

    - You can specify positional arguments without having to place them in an
      extra tuple.

    - Keyword arguments are used as expected to fill in missing values.
      Positional arguments are used to fill non-keyword placeholders.

    - Arguments that are tuples, lists or sets will be automatically joined by colons.
      If the corresponding formatting is %S or %(name)S, the members of the
      sequence will be escaped individually.

    See qcompile() for details.

    Note that this function accepts a '_paramstyle' optional argument, to set
    which parameter style to use.
    """
    debug = debug_convert or kwds.pop('__debug__', None)
    if debug:
        print('\n' + '=' * 80)
        print('\noriginal =')
        print(query_)
        print('\nargs =')
        pprint(args)
        print('\nkwds =')
        pprint(kwds)

    # Get the cached query analyzer or create one.
    try:
        q = _query_cache[query_]
    except KeyError:
        _query_cache[query_] = q = qcompile(
            query_,
            paramstyle=kwds.pop('paramstyle', None))

    if debug:
        print('\nquery analyzer =', str(q))

    # Translate this call into a compatible call to execute().
    cquery, ckwds = q.apply(*args, **kwds)

    if debug:
        print('\ntransformed =')
        print(cquery)
        print('\nnewkwds =')
        pprint(ckwds)

    # Execute the transformed query.
    return cursor_.execute(cquery, ckwds)


# Add support for ntuple wrapping (std in 2.6).
try:
    from collections import namedtuple

    # Patch from Catherine Devlin <catherine dot devlin at gmail dot com>:
    #
    #   "Column names with ``$`` and ``#`` are legal in SQL, but not in
    #   namedtuple field names. This throws exceptions when you try to
    #   execute_obj on queries with such column names. For the apps I write
    #   (rooting around in Oracle data dictionary views), there's no avoiding
    #   the ``$`` and ``#`` characters. Therefore, I added code to munge column
    #   names until they are namedtuple-legal. Another alternative would be to
    #   simply change the error message raised into something that would suggest
    #   that the user use column aliases in the SQL statement to change column
    #   names into something namedtuple-legal."  (2010-05-25)
    from collections import _iskeyword
    not_alphanumeric = re.compile('[^a-zA-Z0-9]')
    def rename_duplicates(lst, append_char = '_'):
        newlist = []
        for itm in lst:
            while itm in newlist:
                itm += append_char
            newlist.append(itm)
        return newlist
    def _fix_fieldname(fieldname):
        "Ensure that a field name will pass collection.namedtuple's criteria."
        fieldname = not_alphanumeric.sub('_', fieldname)
        while _iskeyword(fieldname):
            fieldname = fieldname + '_'
        return fieldname
    def ntuple(typename, field_names, verbose=False):
        field_names = [_fix_fieldname(fn) for fn in field_names.split()]
        field_names = rename_duplicates(field_names)
        return namedtuple(typename, ' '.join(field_names), verbose)

except ImportError:
    ntuple = None

if ntuple:
    from operator import itemgetter

    def execute_obj(conn, *args, **kwds):
        """
        Run a query on the given connection or cursor and yield ntuples of the
        results.  'curs' can be either a Connection or a Cursor object.
        """
        # Convert to a cursor if necessary.
        if re.search('Cursor', conn.__class__.__name__, re.I):
            curs = conn
        else:
            curs = conn.cursor()

        # Execute the query.
        execute_f(curs, *args, **kwds)

        # Yield all the results wrapped up in an ntuple.
        names = list(map(itemgetter(0), curs.description))
        TupleCls = ntuple('Row', ' '.join(names))
        return starmap(TupleCls, imap(tuple, curs))
else:
    execute_obj = None



#-------------------------------------------------------------------------------

class _TestCursor(object):
    """
    Fake cursor that fakes the escaped replacments like a real DBAPI cursor, but
    simply returns the final string.
    """
    execute_f = execute_f

    def execute(self, query, args):
        return self.render_fake(query, args).strip()

    @staticmethod
    def render_fake(query, kwds):
        """
        Take arguments as the DBAPI of execute() accepts and fake escaping the
        arguments as the DBAPI implementation would and return the resulting
        string.  This is used only for testing, to make testing easier and more
        intuitive, to view the completed queries without the replacement
        variables.
        """
        for key, value in list(kwds.items()):
            if isinstance(value, type(None)):
                kwds[key] = 'NULL'
            elif isinstance(value, str):
                kwds[key] = repr(value)
            elif isinstance(value, unicode):
                kwds[key] = repr(value.encode('utf-8'))
            elif isinstance(value, (date, datetime)):
                kwds[key] = repr(value.isoformat())

        result = query % kwds

        if debug_convert:
            print('\n--- 5. after full replacement (fake dbapi application)')
            print(result)

        return result


def _multi2one(s):
    "Join a multi-line string in a single line."
    s = re.sub('[ \n]+', ' ', s).strip()
    return re.sub(', ', ',', s)


import unittest
class TestExtension(unittest.TestCase):
    """
    Tests for the extention functions.
    """
    def compare_nows(self, s1, s2):
        """
        Compare two strings without considering the whitespace.
        """
        s1 = _multi2one(s1)
        s2 = _multi2one(s2)
        self.assertEquals(s1, s2)

    def test_basic(self):
        "Basic replacement tests."

        cursor = _TestCursor()

        simple, isimple, seq = 'SIMPLE', 42, ('L1', 'L2', 'L3')
        for query, args, kwds, expect in (

            # With simple arguments.
            (' %s ', (simple,), dict(), " SIMPLE "),
            (' %S ', (simple,), dict(), " 'SIMPLE' "),
            (' %X ', (simple,), dict(), " 'SIMPLE' "),
            (' %d ', (isimple,), dict(), " 42 "),
            (' %(k)s ', (), dict(k=simple), " SIMPLE "),
            (' %(k)d ', (), dict(k=isimple), " 42 "),
            (' %(k)S ', (), dict(k=simple), " 'SIMPLE' "),
            (' %(k)X ', (), dict(k=simple), " 'SIMPLE' "),

            # Same but with lists.
            (' %s ', (seq,), dict(), " L1,L2,L3 "),
            (' %S ', (seq,), dict(), " 'L1','L2','L3' "),
            (' %X ', (seq,), dict(), " 'L1','L2','L3' "),
            (' %(k)s ', (), dict(k=seq), " L1,L2,L3 "),
            (' %(k)S ', (), dict(k=seq), " 'L1','L2','L3' "),
            (' %(k)X ', (), dict(k=seq), " 'L1','L2','L3' "),

            ):

            # Normal invocation.
            self.compare_nows(
                cursor.execute_f(query, *args, **kwds),
                expect)

            # Repeated destination formatting string.
            self.compare_nows(
                cursor.execute_f(query + query, *(args + args) , **kwds),
                expect + expect)


    def test_misc(self):

        d = date(2006, 7, 28)

        cursor = _TestCursor()

        self.compare_nows(
            cursor.execute_f('''
              INSERT INTO %(table)s (%s)
                SET VALUES (%S)
                WHERE id = %(id)S
                  AND name IN (%(name)S)
                  AND name NOT IN (%(name)S)
            ''',
                         ('col1', 'col2'),
                         (42, "bli"),
                         id="02351440-7b7e-4260",
                         name=[45, 56, 67, 78],
                         table='table'),
              """
              INSERT INTO table (col1, col2)
                SET VALUES (42, 'bli')
                WHERE id = '02351440-7b7e-4260'
                  AND name IN (45, 56, 67, 78)
                  AND name NOT IN (45, 56, 67, 78)
              """)


        # Note: this should fail in the old text.
        self.compare_nows(
            cursor.execute_f(''' %(id)s AND %(id)S ''',
                         id=['fulano', 'mengano']),
              """ fulano,mengano AND 'fulano','mengano' """)


        self.compare_nows(
            cursor.execute_f('''
              SELECT %s FROM %s WHERE id = %S
            ''',
                         ('id', 'name', 'title'), 'books',
                         '02351440-7b7e-4260'),
            """SELECT id,name,title FROM books
               WHERE id = '02351440-7b7e-4260'""")

        self.compare_nows(
            cursor.execute_f('''
           SELECT %s FROM %s WHERE id = %(id)S %(id)S
        ''', ('id', 'name', 'title'), 'books', id=d),
            """SELECT id,name,title FROM books
               WHERE id = '2006-07-28' '2006-07-28'""")

        self.compare_nows(
            cursor.execute_f(''' %(id)S %(id)S ''', id='02351440-7b7e-4260'),
            " '02351440-7b7e-4260' '02351440-7b7e-4260' ")

        self.compare_nows(
            cursor.execute_f(''' %s %(id)S %(id)s ''',
                         'books',
                         id='02351440-7b7e-4260'),
            "  books '02351440-7b7e-4260' 02351440-7b7e-4260  ")

        self.compare_nows(
            cursor.execute_f('''
              SELECT %s FROM %(table)s WHERE col1 = %S AND col2 < %(val)S
            ''', ('col1', 'col2', 'col3'), 'value1', table='my-table', val=42),
            """ SELECT col1,col2,col3 FROM my-table
                WHERE col1 = 'value1' AND col2 < 42 """)

        self.compare_nows(
            cursor.execute_f("""
              INSERT INTO thumbnails
                (basename, photo1, photo2, photo3)
                VALUES (%S, %S)
                """, 'PHOTONAME', ('BIN1', 'BIN2', 'BIN3')),
            """
              INSERT INTO thumbnails
                (basename, photo1, photo2, photo3)
                VALUES ('PHOTONAME', 'BIN1', 'BIN2', 'BIN3')
                """)


    def test_null(self):
        cursor = _TestCursor()
        self.compare_nows(
            cursor.execute_f('''
              INSERT INTO poodle (hair)
                SET VALUES (%S)
            ''', None),
              """
              INSERT INTO poodle (hair)
                SET VALUES (NULL)
              """)


    def test_paramstyles(self):

        d = date(2006, 7, 28)

        cursor = _TestCursor()

        query = '''
              Simple: %s  Escaped: %S
              Kwd: %(bli)s KwdEscaped: %(bli)S
            '''
        args = ('hansel', 'gretel')
        kwds = dict(bli='bethel')

        test_data = {
            'pyformat': ("""
              Simple: hansel  Escaped: %(__p2)s
              Kwd: bethel KwdEscaped: %(bli)s
            """, {'__p2': 'gretel', 'bli': 'bethel'}),

            'named': ("""
              Simple: hansel  Escaped: :__p2
              Kwd: bethel KwdEscaped: :bli
            """, {'__p2': 'gretel', 'bli': 'bethel'}),

            'qmark': ("""
              Simple: hansel  Escaped: ?
              Kwd: bethel KwdEscaped: ?
            """, ['gretel', 'bethel']),

            'format': ("""
              Simple: hansel  Escaped: %s
              Kwd: bethel KwdEscaped: %s
            """, ['gretel', 'bethel']),

            'numeric': ("""
              Simple: hansel  Escaped: :1
              Kwd: bethel KwdEscaped: :2
            """, ['gretel', 'bethel']),
            }

        for style, (estr, eargs) in _iteritems(test_data):
            qstr, qargs = qcompile(query, paramstyle=style).apply(
                *args, **kwds)

            self.compare_nows(qstr, estr)
            self.assertEquals(qargs, eargs)

        # Visual debugging.
        print_it = 0
        for style in _iterkeys(test_data):
            qanal = qcompile("""
              %S %(c1)S %S %S %(c2)S
            """, paramstyle=style)

            qstr, qargs = qanal.apply(1, 2, 3, c1='CC1', c2='CC2')
            if print_it:
                print(qstr)
                print(qargs)

    def test_dict(self):
        "Tests for passing in a dictionary argument."

        cursor = _TestCursor()
        data = {'brazil': 'portuguese',
                'peru': 'spanish',
                'japan': 'japanese',
                'philipines': 'tagalog'}

        self.assertRaises(ValueError, execute_f,
                          cursor, ' unescaped: %s ', data)

        res = execute_f(cursor, ' UPDATE %s SET %S; ', 'mytable', data)
        self.compare_nows(res, """
           UPDATE mytable
             SET brazil = 'portuguese',
                 japan = 'japanese',
                 philipines = 'tagalog',
                 peru = 'spanish';       """)

    def test_and(self):
        "Tests for passing in a dictionary argument."

        cursor = _TestCursor()
        keydata = {'udid': '11111111111111111111',
                   'imgid': 17}
        valuedata = {'rating': 9}

        self.assertRaises(ValueError, execute_f,
                          cursor, ' unescaped: %s ', keydata)

        res = execute_f(cursor, ' UPDATE %s SET %S WHERE %A; ', 'mytable',
                        valuedata, keydata)
        self.compare_nows(res, """
           UPDATE mytable
             SET rating = 9
             WHERE udid = '11111111111111111111' AND imgid = 17;
        """)

        res = execute_f(cursor, ' UPDATE %s SET %S WHERE %O; ', 'mytable',
                        valuedata, keydata)
        self.compare_nows(res, """
           UPDATE mytable
             SET rating = 9
             WHERE udid = '11111111111111111111' OR imgid = 17;
        """)


    def test_sqlite3(self):
        import sqlite3 as dbapi
        set_paramstyle(dbapi)
        conn = dbapi.connect(':memory:')
        curs = conn.cursor()
        execute_f(curs, """
           CREATE TABLE books (
              author TEXT,
              title TEXT,
              PRIMARY KEY (title)
           );
        """)
        execute_f(curs, """
           INSERT INTO books VALUES (%S);
        """, ("Tolstoy", "War and Peace"))

        execute_f(curs, """
           INSERT INTO books (author) VALUES (%S);
        """, "Dostoyesvki")


debug_convert = 0
if __name__ == '__main__':
    unittest.main() # or use nosetests


