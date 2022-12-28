import urlparse

from collections import namedtuple

import db
import sqlite3


class Sqlite3Driver(db.drivers.Driver):
    PARAM_STYLE = "qmark"
    URL_SCHEME = "sqlite3"

    def __init__(self, *args, **kwargs):
        super(Sqlite3Driver, self).__init__(*args, **kwargs)
        self.conn = self._connect(*self.conn_args, **self.conn_kwargs)

    def _connect(self, *args, **kwargs):
        """Wraps sqlite3.connect forcing the options required for a
           db style connection to work.  As of this writing that consists
           of installing a NamedTupleCursor factory but may grow more involved
           over time as things change.
        """

        conn = sqlite3.connect(*args, **kwargs)
        conn.row_factory = self._namedtuple_factory
        return conn

    @staticmethod
    def _namedtuple_factory(cursor, row):
        fields = [col[0] for col in cursor.description]
        Row = namedtuple("Row", fields)
        return Row(*row)

    def connect(self):
        return self.conn

    @classmethod
    def from_url(cls, url):
        parsed = urlparse.urlparse(url)
        if parsed.scheme == "sqlite3":
            return cls(parsed.path[1:])


db.drivers.autoregister_class(Sqlite3Driver)
