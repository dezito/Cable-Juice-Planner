__version__ = "1.0.0"
__all__ = [
    "sunRise",
    "sunSet"
    "getWeatherData",
    "getForecast",
]
import datetime
import dateutil.parser

from mytime import getTimeStartOfDay, toDateTime
from hass_manager import get_attr

import homeassistant.helpers.sun as sun

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def location():
    return sun.get_astral_location(hass)

def sunRise():
    return location[0].sunrise(datetime.datetime.today()).replace(tzinfo=None)

def sunSet():
    return location[0].sunset(datetime.datetime.today()).replace(tzinfo=None)

def getWeatherData():
    return get_attr("weather.openweathermap")

def getForecast(date = None):
    if date is None:
        date = getTimeStartOfDay()
    
    date = getTimeStartOfDay().replace(year=date.year, month=date.month, day=date.day, hour=date.hour)
    for forecast in getWeatherData()["forecast"]:
        forecastDate = toDateTime(forecast['datetime']).replace(hour=0, minute=0, second=0, tzinfo=None)
        if forecastDate == date:
            return forecast