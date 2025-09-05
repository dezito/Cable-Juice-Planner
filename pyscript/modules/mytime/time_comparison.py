from datetime import datetime

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def monthsBetween(start: datetime, end: datetime, precise: bool=False, error_value=0) -> int:
    """
    Calculate the number of full months between two datetime objects.
    If precise is False, the calculation ignores the day and time components,
    considering only the year and month.
    _
    Parameters:
    - start (datetime): The start datetime.
    - end (datetime): The end datetime.
    - precise (bool): If False, ignores day and time components.
    - error_value (int): The value to return in case of an error.
    Returns:
    - int: The number of full months between start and end, or error_value on error
    """
    _LOGGER = globals()['_LOGGER'].getChild("monthsBetween")
    try:
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        if not precise:
            start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        months = (end.year - start.year) * 12 + (end.month - start.month)
        if end.day < start.day:
            months -= 1
        return months
    except Exception:
        _LOGGER.error(f"Error in monthsBetween with start {start} ({type(start)}) and end {end} ({type(end)})")
        return error_value

def daysBetween(start: datetime, end: datetime, precise: bool=False, error_value=0) -> int:
    """
    Calculate the number of full days between two datetime objects.
    If precise is False, the calculation ignores the time components,
    considering only the date components.
    Parameters:
    - start (datetime): The start datetime.
    - end (datetime): The end datetime.
    - precise (bool): If False, ignores time components.
    - error_value (int): The value to return in case of an error.
    Returns:
    - int: The number of full days between start and end, or error_value on error
    """
    _LOGGER = globals()['_LOGGER'].getChild("daysBetween")
    try:
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        if not precise:
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = end.replace(hour=0, minute=0, second=0, microsecond=0)
        return (end - start).days
    except Exception:
        _LOGGER.error(f"Error in daysBetween with start {start} ({type(start)}) and end {end} ({type(end)})")
        return error_value

def hoursBetween(start: datetime, end: datetime, precise: bool=False, error_value=0) -> int:
    """
    Calculate the number of full hours between two datetime objects.
    If precise is False, the calculation ignores the minute, second, and microsecond components,
    considering only the hour component.
    Parameters:
    - start (datetime): The start datetime.
    - end (datetime): The end datetime.
    - precise (bool): If False, ignores minute, second, and microsecond components.
    - error_value (int): The value to return in case of an error.
    Returns:
    - int: The number of full hours between start and end, or error_value on error
    """
    _LOGGER = globals()['_LOGGER'].getChild("hoursBetween")
    try:
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        if not precise:
            start = start.replace(minute=0, second=0, microsecond=0)
            end = end.replace(minute=0, second=0, microsecond=0)
        return int((end - start).total_seconds() // 3600)
    except Exception:
        _LOGGER.error(f"Error in hoursBetween with start {start} ({type(start)}) and end {end} ({type(end)})")
        return error_value

def minutesBetween(start: datetime, end: datetime, precise: bool=False, error_value=0) -> int:
    """
    Calculate the number of full minutes between two datetime objects.
    If precise is False, the calculation ignores the second and microsecond components,
    considering only the minute component.
    Parameters:
    - start (datetime): The start datetime.
    - end (datetime): The end datetime.
    - precise (bool): If False, ignores second and microsecond components.
    - error_value (int): The value to return in case of an error.
    Returns:
    - int: The number of full minutes between start and end, or error_value on error
    """
    _LOGGER = globals()['_LOGGER'].getChild("minutesBetween")
    try:
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        if not precise:
            start = start.replace(second=0, microsecond=0)
            end = end.replace(second=0, microsecond=0)
        return int((end - start).total_seconds() // 60)
    except Exception:
        _LOGGER.error(f"Error in minutesBetween with start {start} ({type(start)}) and end {end} ({type(end)})")
        return error_value

def secondsBetween(start: datetime, end: datetime, precise: bool=False, error_value=0) -> int:
    """
    Calculate the number of full seconds between two datetime objects.
    If precise is False, the calculation ignores the microsecond component,
    considering only the second component.
    Parameters:
    - start (datetime): The start datetime.
    - end (datetime): The end datetime.
    - precise (bool): If False, ignores microsecond component.
    - error_value (int): The value to return in case of an error.
    Returns:
    - int: The number of full seconds between start and end, or error_value on error
    """
    _LOGGER = globals()['_LOGGER'].getChild("secondsBetween")
    try:
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        if not precise:
            start = start.replace(microsecond=0)
            end = end.replace(microsecond=0)
        return int((end - start).total_seconds())
    except Exception:
        _LOGGER.error(f"Error in secondsBetween with start {start} ({type(start)}) and end {end} ({type(end)})")
        return error_value

def inBetween(check, start, end):
    """
    Check if 'check' datetime is between 'start' and 'end' datetimes.
    Handles cases where the interval spans midnight.
    Parameters:
    - check (datetime): The datetime to check.
    - start (datetime): The start of the interval.
    - end (datetime): The end of the interval.
    Returns:
    - bool: True if 'check' is between 'start' and 'end', False otherwise.
    """
    #return check <= start < end if check <= end else check <= start or start < end
    return start <= check < end if start <= end else start <= check or check < end