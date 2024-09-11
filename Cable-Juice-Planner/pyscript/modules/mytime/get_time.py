import datetime
import time

from dateutil.relativedelta import relativedelta

def datetime_to_unix(date_time = None):
    return time.mktime(date_time.timetuple())

#Timestamps
def getTimestampSeconds():
    return getTime().total_seconds()

def getTimestampMinutes():
    return getTime().total_minutes()

#Plus/minus time
def getTime():
    date = datetime.datetime.now()
    return datetime.datetime(date.year, date.month, date.day, date.hour, date.minute, date.second)

def getTimePlusSeconds(offset = 0):
    return getTime() + datetime.timedelta(seconds=offset)

def getTimePlusMinutes(offset = 0):
    return getTime() + datetime.timedelta(minutes=offset)

def getTimePlusHours(offset = 0):
    return getTime() + datetime.timedelta(hours=offset)

def getTimePlusDays(offset = 0):
    return getTime() + datetime.timedelta(days=offset)

def getTimePlusMonths(offset = 0):
    return getTime() + relativedelta(months =+ offset)

def getTimePlusYears(offset = 0):
    return getTime() + relativedelta(years =+ offset)

def getTimeMinusSeconds(offset = 0):
    return getTime() - datetime.timedelta(seconds=offset)

def getTimeMinusMinutes(offset = 0):
    return getTime() - datetime.timedelta(minutes=offset)

def getTimeMinusHours(offset = 0):
    return getTime() - datetime.timedelta(hours=offset)

def getTimeMinusDays(offset = 0):
    return getTime() - datetime.timedelta(days=offset)

def getTimeMinusMonths(offset = 0):
    return getTime() - relativedelta(months =+ offset)

def getTimeMinusYears(offset = 0):
    return getTime() - relativedelta(years =+ offset)