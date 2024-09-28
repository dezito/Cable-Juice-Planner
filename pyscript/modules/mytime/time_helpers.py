
import dateutil.parser
import datetime
import calendar

from .get_time import getTime

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

#Get
def getSecond(date = None):
    if not date:
        date = getTime()
    return date.second

def getMinute(date = None):
    if not date:
        date = getTime()
    return date.minute

def getHour(date = None):
    if not date:
        date = getTime()
    return date.hour

def getDay(date = None):
    if not date:
        date = getTime()
    return date.day

def getTimeStartOfDay(date = None):
    if not date:
        date = getTime()
    return datetime.datetime(date.year, date.month, date.day, 0, 0, 0, 0)

def getTimeEndOfDay(date = None):
    if not date:
        date = getTime()
    return datetime.datetime(date.year, date.month, date.day, 23, 59, 59, 0)

def getDayOfWeek(date = None):
    """Get day of week in int value
    Range 0-6

    Returns:
        int: ex. SATURDAY = 5
    """
    _LOGGER = globals()['_LOGGER'].getChild("getDayOfWeek")
    if not date:
        date = getTime()
    return date.weekday()

def getDayOfWeekText(date = None, translate = False):
    """Get day of week text
    If datetime return OpenHAB DateTime Item day of week text
    else return current time day of week text

    Args:
        datetime (org.openhab.core.library.items.DateTimeItem, optional): OpenHAB DateTime Item. Defaults to None.

    Returns:
        str: Day in text form
    """
    weekdays = {
        "monday": "mandag",
        "tuesday": "tirsdag",
        "wednesday": "onsdag",
        "thursday": "torsdag",
        "friday": "fredag",
        "saturday": "lørdag",
        "sunday": "søndag"
    }
    if not date:
        date = getTime()
    
    day = calendar.day_name[date.weekday()].lower()
    
    try:
        if translate:
            return weekdays[day]
    except:
        pass
    return day

def getMonth(date = None):
    if not date:
        date = getTime()
    return date.month

def getMonthFirstDay(date = None):
    if not date:
        date = getTime()
    return datetime.datetime(date.year, date.month, 1, 0, 0, 0, 0)

def getMonthLastDay(date = None):
    if not date:
        date = getTime()
    date = datetime.datetime(date.year, date.month + 1, 1, 23, 59, 59, 0)
    return date - datetime.timedelta(days=1)

def getYear(date = None):
    if not date:
        date = getTime()
    return getTime().year

def date_to_string(date = None, format = "%m/%d/%Y %H:%M:%S"):
    if not date:
        date = getTime()
    if not isinstance(date, (list, tuple)):
        date = [date]
        
    output = []
    for d in date:
        output.append(d.strftime(format))
    return ", ".join(output)

def toDateTime(date = None):
    try:
        return dateutil.parser.isoparse(date)
    except:
        return date
    
def resetDatetime():
    return getTimeStartOfDay().replace(year = 1900, month=1, day=1)

def reset_time_to_hour(date = None):
    """
    Resets the minute, second, microsecond to zero.
    
    Args:
    date (datetime): The datetime object to be reset.
    
    Returns:
    datetime: A new datetime object with the minute, second, microsecond set to zero.
    """
    if not date:
        date = getTime()
    return date.replace(minute=0, second=0, microsecond=0)