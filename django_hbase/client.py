from django.conf import settings

import happybase


class HBaseClient:
    conn = None

    @classmethod
    def get_connection(cls):
        try:
            cls.conn.tables()
        except:
            cls.conn = happybase.Connection(settings.HBASE_HOST)
        return cls.conn
