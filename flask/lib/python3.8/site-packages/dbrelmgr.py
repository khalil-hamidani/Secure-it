"""
Helpers for initializing and dropping schemas.
"""

# stdlib imports
import logging

# antiorm imports
from antipool import dbpool


def reset_sql(schemas):
    """
    Drop and recreate the given schemas.
    """
    drop_sql(schemas)
    initialize_sql(schemas)


def initialize_sql(schemas):
    """
    Insures that the given schemas are created.
    """
    conn, cursor = dbpool().connection(1)
    try:
        cursor.execute("""
          SELECT table_name FROM information_schema.tables
        """)
        tables = set(x[0] for x in cursor.fetchall())

        for table_name, schema in schemas:
            if table_name not in tables:
                logging.info('Creating SQL schema %s' % table_name)
                cursor.execute(schema)

        conn.commit()
    finally:
        conn.release()

def drop_sql(schemas):
    """
    Drop the given list of schemes.
    """
    dbapi = dbpool().module()
    conn, cursor = dbpool().connection(1)
    try:
        cursor.execute("""
          SELECT table_name FROM information_schema.tables
        """)
        tables = set(x[0] for x in cursor.fetchall())

        names = [x for x, s in schemas if x in tables]
        for n in names:
            try:
                cursor.execute('DROP TABLE "%s" CASCADE' % n)
                conn.commit()
            except dbapi.Error:
                conn.rollback() # ignore errors due to dependencies.
    finally:
        conn.release()

