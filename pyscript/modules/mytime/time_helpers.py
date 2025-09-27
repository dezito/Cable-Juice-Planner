
import dateutil.parser
import datetime
import calendar

from .get_time import getTime

from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def remove_local_timezone(date_time):
    try:
        return date_time.replace(tzinfo=None)
    except Exception as e:
        _LOGGER.error(f"Error in remove_local_timezone with date_time {date_time} ({type(date_time)}) error: {e}")
    return date_time

#Get
def getSecond(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getSecond")
    
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getSecond with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(date).second
    except Exception as e:
        _LOGGER.error(f"Error in getSecond with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getSecond with date {date} ({type(date)}) error: {e}")

def getMinute(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getMinute")
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getMinute with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(date).minute
    except Exception as e:
        _LOGGER.error(f"Error in getMinute with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getMinute with date {date} ({type(date)}) error: {e}")

def getHour(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getHour")
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getHour with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(date).hour
    except Exception as e:
        _LOGGER.error(f"Error in getHour with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getHour with date {date} ({type(date)}) error: {e}")

def getDay(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getDay")
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getDay with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(date).day
    except Exception as e:
        _LOGGER.error(f"Error in getDay with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getDay with date {date} ({type(date)}) error: {e}")

def getTimeStartOfDay(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getTimeStartOfDay")
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getTimeStartOfDay with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(datetime.datetime(date.year, date.month, date.day, 0, 0, 0, 0))
    except Exception as e:
        _LOGGER.error(f"Error in getTimeStartOfDay with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getTimeStartOfDay with date {date} ({type(date)}) error: {e}")

def getTimeEndOfDay(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getTimeEndOfDay")
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getTimeEndOfDay with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(datetime.datetime(date.year, date.month, date.day, 23, 59, 59, 0))
    except Exception as e:
        _LOGGER.error(f"Error in getTimeEndOfDay with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getTimeEndOfDay with date {date} ({type(date)}) error: {e}")

def getDayOfWeek(date = None):
    """Get day of week in int value
    Range 0-6

    Returns:
        int: ex. SATURDAY = 5
    """
    _LOGGER = globals()['_LOGGER'].getChild("getDayOfWeek")
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getDayOfWeek with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(date).weekday()
    except Exception as e:
        _LOGGER.error(f"Error in getDayOfWeek with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getDayOfWeek with date {date} ({type(date)}) error: {e}")

def getDayOfWeekText(date = None, translate = False):
    _LOGGER = globals()['_LOGGER'].getChild("getDayOfWeekText")
    
    weekdays = {
        "monday": "mandag",
        "tuesday": "tirsdag",
        "wednesday": "onsdag",
        "thursday": "torsdag",
        "friday": "fredag",
        "saturday": "lørdag",
        "sunday": "søndag"
    }
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getDayOfWeekText with date {date} ({type(date)}) is not datetime")
        
        day = calendar.day_name[remove_local_timezone(date).weekday()].lower()
        
        try:
            if translate:
                return weekdays[day]
        except:
            pass
        return day
    except Exception as e:
        _LOGGER.error(f"Error in getDayOfWeekText with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getDayOfWeekText with date {date} ({type(date)}) error: {e}")

def getMonth(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getMonth")
    
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getMonth with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(date).month
    except Exception as e:
        _LOGGER.error(f"Error in getMonth with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getMonth with date {date} ({type(date)}) error: {e}")

def getMonthFirstDay(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getMonthFirstDay")
    
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getMonthFirstDay with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(datetime.datetime(year=date.year, month=date.month, day=1, hour=0, minute=0, second=0, microsecond=0))
    except Exception as e:
        _LOGGER.error(f"Error in getMonthFirstDay with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getMonthFirstDay with date {date} ({type(date)}) error: {e}")

def getMonthLastDay(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getMonthLastDay")
    
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getMonthLastDay with date {date} ({type(date)}) is not datetime")
        
        date = remove_local_timezone(datetime.datetime(year=date.year, month=date.month + 1, day=1, hour=23, minute=59, second=59, microsecond=0))
        return date - datetime.timedelta(days=1)
    except Exception as e:
        _LOGGER.error(f"Error in getMonthLastDay with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getMonthLastDay with date {date} ({type(date)}) error: {e}")

def getYear(date = None):
    _LOGGER = globals()['_LOGGER'].getChild("getYear")
    
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in getYear with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(date).year
    except Exception as e:
        _LOGGER.error(f"Error in getYear with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in getYear with date {date} ({type(date)}) error: {e}")

def date_to_string(date = None, format = "%m/%d/%Y %H:%M:%S"):
    _LOGGER = globals()['_LOGGER'].getChild("date_to_string")
    
    try:
        if date is None:
            date = getTime()
            
        if not isinstance(date, (list, tuple)):
            date = [date]
            
        output = []
        for d in date:
            if not isinstance(d, datetime.datetime):
                raise Exception(f"Error in date_to_string with date {date} ({type(date)}) is not datetime")
            
            output.append(d.strftime(format))
        return ", ".join(output)
    except Exception as e:
        _LOGGER.error(f"Error in date_to_string with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in date_to_string with date {date} ({type(date)}) error: {e}")

def toDateTime(date = None):
    try:
        dt = dateutil.parser.isoparse(date)
        return remove_local_timezone(dt)
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
    _LOGGER = globals()['_LOGGER'].getChild("reset_time_to_hour")
    
    try:
        if date is None:
            date = getTime()
        if not isinstance(date, datetime.datetime):
            raise Exception(f"Error in reset_time_to_hour with date {date} ({type(date)}) is not datetime")
        
        return remove_local_timezone(date).replace(minute=0, second=0, microsecond=0)
    except Exception as e:
        _LOGGER.error(f"Error in reset_time_to_hour with date {date} ({type(date)}) error: {e}")
        raise Exception(f"Error in reset_time_to_hour with date {date} ({type(date)}) error: {e}")

def is_day(timestamp = None):
    _LOGGER = globals()['_LOGGER'].getChild("is_day")
    
    try:
        if not timestamp:
            timestamp = getTime()
        if not isinstance(timestamp, datetime.datetime):
            raise Exception(f"Error in is_day with timestamp {timestamp} ({type(timestamp)}) is not datetime")

        sunrise = remove_local_timezone(get_astral_event_date(hass, SUN_EVENT_SUNRISE, timestamp.date()))
        sunset = remove_local_timezone(get_astral_event_date(hass, SUN_EVENT_SUNSET, timestamp.date()))

        if not sunrise or not sunset:
            raise ValueError(f"Could find sunrise or sunset: timestamp: {timestamp} sunrise:{sunrise}, sunset:{sunset}")

        return sunrise <= remove_local_timezone(timestamp) <= sunset
    except Exception as e:
        _LOGGER.error(f"Error in is_day with timestamp {timestamp} ({type(timestamp)}) error: {e}")
        raise Exception(f"Error in is_day with timestamp {timestamp} ({type(timestamp)}) error: {e}")

def add_months(current_date, months_to_add):
    _LOGGER = globals()['_LOGGER'].getChild("add_months")
    
    try:
        if current_date is None:
            current_date = getTime()
        if not isinstance(current_date, datetime.datetime):
            raise Exception(f"Error in add_months with current_date {current_date} ({type(current_date)}) is not datetime")
        
        new_date = datetime.datetime(current_date.year + (current_date.month + months_to_add - 1) // 12,
                            (current_date.month + months_to_add - 1) % 12 + 1,
                            current_date.day, current_date.hour, current_date.minute, current_date.second)
        return remove_local_timezone(new_date)
    except Exception as e:
        _LOGGER.error(f"Error in add_months with current_date {current_date} ({type(current_date)}) months_to_add {months_to_add} error: {e}")
        raise Exception(f"Error in add_months with current_date {current_date} ({type(current_date)}) months_to_add {months_to_add} error: {e}")