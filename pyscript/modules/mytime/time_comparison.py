from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def monthsBetween(now, then, error_value=0):
    try:
        now = now.replace(tzinfo=None)
        then = then.replace(tzinfo=None)

        months_diff = (then.year - now.year) * 12 + (then.month - now.month)

        return months_diff
    except:
        return error_value
    
def daysBetween(now, then, error_value=0):
    try:
        now = now.replace(tzinfo=None)
        then = then.replace(tzinfo=None)
        now_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        then_date = then.replace(hour=0, minute=0, second=0, microsecond=0)
        duration = then_date - now_date
        duration_in_s = duration.total_seconds()
        return int(divmod(duration_in_s, 86400)[0])
    except:
        return error_value

def hoursBetween(now, then, error_value=0):
    try:
        now = now.replace(tzinfo=None)
        then = then.replace(tzinfo=None)
        now_date = now.replace(minute=0, second=0, microsecond=0)
        then_date = then.replace(minute=0, second=0, microsecond=0)
        duration = then_date - now_date
        duration_in_s = duration.total_seconds()
        return divmod(duration_in_s, 3600)[0]
    except:
        return error_value

def minutesBetween(now, then, error_value=0):
    try:
        now = now.replace(tzinfo=None)
        then = then.replace(tzinfo=None)
        now_date = now.replace(second=0, microsecond=0)
        then_date = then.replace(second=0, microsecond=0)
        duration = then_date - now_date
        duration_in_s = duration.total_seconds()
        return divmod(duration_in_s, 60)[0]
    except Exception as e:
        _LOGGER.error(f"now={now}({type(now)}) then={then}({type(then)})")
        _LOGGER.error(e)
        return error_value

def secondsBetween(now, then, error_value=0):
    try:
        now = now.replace(tzinfo=None)
        then = then.replace(tzinfo=None)
        now_date = now.replace(microsecond=0)
        then_date = then.replace(microsecond=0)
        duration = then_date - now_date
        return duration.total_seconds()
    except:
        return error_value

def inBetween(check, start, end):
    #return check <= start < end if check <= end else check <= start or start < end
    return start <= check < end if start <= end else start <= check or check < end