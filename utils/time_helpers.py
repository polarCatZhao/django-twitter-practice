from datetime import datetime
import pytz


def utc_now():
    return datetime.now(pytz.utc)