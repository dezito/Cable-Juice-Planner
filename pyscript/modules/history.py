import datetime
import time

import numpy as np

from homeassistant.components.recorder import history as hass_history
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.components.recorder.util import session_scope
from homeassistant.util import dt as dt_util

from typing import Literal


ENTITY_UNAVAILABLE_STATES = (None, "unavailable", "unknown")

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)


HISTORY_CACHE_TIMEOUT = 30.0

HISTORY_CACHE = {
    "history": {},
    "statistics": {},
}


def _datetime_cache_key(dt):
    """
    Creates a stable datetime value for use as part of a cache key.

    Microseconds are removed so repeated requests within the same second can use the same cached data.

    Parameters:
    - dt (datetime): The datetime to normalize.

    Returns:
    - The datetime with microseconds removed.
    """
    if isinstance(dt, datetime.datetime):
        return dt.replace(microsecond=0)

    return dt


def _cache_get(cache_type, key, timeout=None):
    """
    Retrieves a value from the cache and optionally checks whether it has expired.

    Parameters:
    - cache_type (str): The cache category to retrieve the value from.
    - key: The key identifying the cached value.
    - timeout (float): Maximum cache age in seconds. None disables expiration and 0 disables cache usage.

    Returns:
    - A tuple containing whether a cached value was found and the cached value.
    """
    if timeout == 0:
        return False, None

    cached = HISTORY_CACHE[cache_type].get(key)

    if cached is None:
        return False, None

    if timeout is not None and time.monotonic() - cached["timestamp"] >= timeout:
        HISTORY_CACHE[cache_type].pop(key, None)
        return False, None

    return True, cached["value"]


def _cache_set(cache_type, key, value):
    """
    Stores a value in the cache together with the current timestamp.

    Parameters:
    - cache_type (str): The cache category to store the value in.
    - key: The key identifying the cached value.
    - value: The value to cache.
    """
    HISTORY_CACHE[cache_type][key] = {
        "value": value,
        "timestamp": time.monotonic(),
    }


def clear_cache(cache_type=None, key=None):
    """
    Clears cached Home Assistant history and statistics data.

    If no cache type is specified, the complete cache is cleared. If a cache type is specified without a key,
    all entries of that cache type are cleared.

    Parameters:
    - cache_type (str): The cache category to clear.
    - key: The specific cache entry to clear.
    """
    if cache_type is None:
        for cache in HISTORY_CACHE.values():
            cache.clear()
        return

    if cache_type not in HISTORY_CACHE:
        return

    if key is None:
        HISTORY_CACHE[cache_type].clear()
    else:
        HISTORY_CACHE[cache_type].pop(key, None)


def timestamps_correction(from_datetime, to_datetime):
    """
    Ensures that the supplied datetime values are ordered correctly.

    Parameters:
    - from_datetime (datetime): The first datetime.
    - to_datetime (datetime): The second datetime.

    Returns:
    - A tuple containing the earliest datetime followed by the latest datetime.
    """
    _LOGGER = globals()['_LOGGER'].getChild("timestamps_correction")

    try:
        from_time = min(from_datetime, to_datetime)
        to_time = max(from_datetime, to_datetime)

    except Exception as e:
        _LOGGER.error(f"Error in timestamps_correction for from_datetime:{from_datetime} to_datetime:{to_datetime}: {e}")
        from_time = from_datetime
        to_time = to_datetime

    return from_time, to_time


def interpolate_data(sensor_data, from_datetime, to_datetime, num_points):
    """
    Interpolates numeric sensor data between two timestamps while preserving non-numeric values.

    Parameters:
    - sensor_data (dict): Dictionary containing timestamps and their corresponding values.
    - from_datetime (datetime|float): The start of the interpolation range.
    - to_datetime (datetime|float): The end of the interpolation range.
    - num_points (int): The number of interpolated points to generate.

    Returns:
    - A dictionary containing interpolated numeric values and preserved non-numeric values.
    """
    _LOGGER = globals()['_LOGGER'].getChild("interpolate_data")

    interpolated_dict = {}

    from_datetime = from_datetime if isinstance(from_datetime, (int, float)) else datetime.datetime.timestamp(from_datetime)
    to_datetime = to_datetime if isinstance(to_datetime, (int, float)) else datetime.datetime.timestamp(to_datetime)

    try:
        sorted_data = sorted(sensor_data.items())

        numeric_data = []
        non_numeric_data = {}

        for timestamp, value in sorted_data:
            timestamp = timestamp if isinstance(timestamp, (int, float)) else datetime.datetime.timestamp(timestamp)

            try:
                float_value = float(value)
                numeric_data.append((timestamp, float_value))

            except ValueError:
                non_numeric_data[timestamp] = value

        if numeric_data:
            existing_timestamps, existing_values = zip(*numeric_data)

            float_timestamps = np.linspace(from_datetime, to_datetime, num_points)

            interpolated_values = np.interp(float_timestamps, existing_timestamps, existing_values)

            for ts, val in zip(float_timestamps, interpolated_values):
                dt = datetime.datetime.fromtimestamp(ts)
                interpolated_dict[dt] = val

        for ts, val in non_numeric_data.items():
            if isinstance(ts, (int, float)):
                ts = datetime.datetime.fromtimestamp(ts)

            interpolated_dict[ts] = val

    except Exception as e:
        _LOGGER.error(f"Error in interpolate_data: {e}")

    return interpolated_dict


def fetch_statistics_data(hass: HomeAssistant, entity_id: str, start_time: datetime.datetime, end_time: datetime.datetime, state_type: Literal["max", "mean", "min"], force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Fetches long-term statistics for a specified entity within a given datetime range.

    The result is cached based on entity ID, datetime range and statistic type. Setting force to True bypasses
    the cache and retrieves new statistics directly from Home Assistant.

    Parameters:
    - hass (HomeAssistant): The Home Assistant instance.
    - entity_id (str): The entity ID to fetch statistics for.
    - start_time (datetime): The start of the datetime range.
    - end_time (datetime): The end of the datetime range.
    - state_type (Literal["max", "mean", "min"]): The type of statistic to fetch.
    - force (bool): Forces new statistics to be fetched from Home Assistant, ignoring the cache.
    - cache_timeout (float): Number of seconds the cached statistics are valid. 0 disables cache for this call.

    Returns:
    - A dictionary containing timestamps and statistic values.
    """
    _LOGGER = globals()['_LOGGER'].getChild("fetch_statistics_data")

    result = {}

    try:
        start_time = start_time.replace(minute=0, second=0, microsecond=0)
        end_time = end_time.replace(minute=0, second=0, microsecond=0)

        if start_time == end_time:
            end_time = start_time + datetime.timedelta(hours=1)

        start_utc = dt_util.as_utc(start_time)
        end_utc = dt_util.as_utc(end_time)

        cache_key = (entity_id, _datetime_cache_key(start_utc), _datetime_cache_key(end_utc), state_type)

        if not force:
            cached, cached_result = _cache_get("statistics", cache_key, cache_timeout)

            if cached:
                return cached_result.copy()

        stats = statistics_during_period(
            hass=hass,
            start_time=start_utc,
            end_time=end_utc,
            statistic_ids=[entity_id],
            period="hour",
            units=None,
            types={state_type}
        )

        if entity_id in stats:
            for entry in stats[entity_id]:
                timestamp = entry["start"]
                value = entry[state_type]
                result[timestamp] = value

            result = interpolate_data(result, start_utc, end_utc, 100)

        else:
            _LOGGER.debug(f"No data found for entity_id: {entity_id}")

        _cache_set("statistics", cache_key, result.copy())

    except Exception as e:
        _LOGGER.error(f"Error in fetch_statistics_data for {entity_id} between {start_time} and {end_time}: {e}")

    return result


def fetch_history_data(hass: HomeAssistant, entity_id: str, start_time: datetime.datetime, end_time: datetime.datetime, force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Fetches historical state data for a specified entity within a given datetime range.

    The result is cached based on entity ID and datetime range. Setting force to True bypasses the cache
    and retrieves new history data directly from Home Assistant.

    Parameters:
    - hass (HomeAssistant): The Home Assistant instance.
    - entity_id (str): The entity ID to fetch history for.
    - start_time (datetime): The start of the datetime range.
    - end_time (datetime): The end of the datetime range.
    - force (bool): Forces new history data to be fetched from Home Assistant, ignoring the cache.
    - cache_timeout (float): Number of seconds the cached history data is valid. 0 disables cache for this call.

    Returns:
    - A dictionary containing timestamps and historical state values.
    """
    _LOGGER = globals()['_LOGGER'].getChild("fetch_history_data")

    state_dict = {}

    try:
        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)

        if entity_id is None or entity_id == "" or entity_id not in state.names(domain=entity_id.split(".")[0]):
            return state_dict

        cache_key = (entity_id, _datetime_cache_key(start_time), _datetime_cache_key(end_time))

        if not force:
            cached, cached_state_dict = _cache_get("history", cache_key, cache_timeout)

            if cached:
                return cached_state_dict.copy()

        hist_data = hass_history.get_significant_states(
            hass=hass,
            start_time=start_time,
            end_time=end_time,
            entity_ids=[entity_id],
            filters=None,
            include_start_time_state=True,
            significant_changes_only=False,
            minimal_response=False,
            no_attributes=False,
            compressed_state_format=False,
        )

        if entity_id in hist_data:
            entity_state_dict = {}

            for d in hist_data[entity_id]:
                try:
                    entity_state_dict[d.last_updated.timestamp()] = d.state

                except Exception as e:
                    _LOGGER.error(f"Error in fetch_history_data: {e}")

            state_dict = interpolate_data(entity_state_dict, start_time, end_time, 100)

        else:
            _LOGGER.debug(f"No data found for entity_id: {entity_id}")

        _cache_set("history", cache_key, state_dict.copy())

    except Exception as e:
        _LOGGER.error(f"Error in fetch_history_data for {entity_id} between {start_time} and {end_time}: {e}")

    return state_dict


def get_values(entity_id, from_datetime, to_datetime, float_type=False, convert_to=None, include_timestamps=False, error_state=None, force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Fetches historical state values for a specified entity within a given datetime range
    from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to fetch historical values for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - float_type (bool): Whether to convert state values to float.
    - convert_to: Optional unit to convert the values to.
    - include_timestamps (bool): Whether to return timestamps together with the values.
    - error_state: The value to return in case of an error.
    - force (bool): Forces new history data to be fetched from Home Assistant, ignoring the cache.
    - cache_timeout (float): Number of seconds the cached history data is valid. 0 disables cache for this call.

    Returns:
    - A list or dictionary of state values or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_values")
    from power_convert import power_convert

    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)

    states = {}

    try:
        history_data = fetch_history_data(hass, entity_id, from_datetime, to_datetime, force=force, cache_timeout=cache_timeout)

        if isinstance(history_data, dict):
            for ts, value in history_data.items():
                try:
                    if value not in ENTITY_UNAVAILABLE_STATES:
                        if float_type is True:
                            try:
                                value = float(value)

                            except:
                                continue

                        value = value if convert_to is None else power_convert(value, entity_id, convert_to=convert_to)

                        states[ts] = value

                except:
                    pass

        if states:
            if include_timestamps:
                return states

            return list(states.values())

    except Exception as e:
        _LOGGER.error(f"Error in get_values for {entity_id} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime} states:{states}: {e}")

    return error_state


def get_longterm_values(entity_id, from_datetime, to_datetime, state_type: Literal["max", "mean", "min"], convert_to=None, include_timestamps=False, error_state=None, force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Fetches historical state values for a specified entity within a given datetime range
    from the Home Assistant statistics API.

    Parameters:
    - entity_id (str): The entity ID to fetch historical values for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - state_type (Literal["max", "mean", "min"]): The type of statistic to fetch.
    - convert_to: Optional unit to convert the values to.
    - include_timestamps (bool): Whether to return timestamps together with the values.
    - error_state: The value to return in case of an error.
    - force (bool): Forces new statistics to be fetched from Home Assistant, ignoring the cache.
    - cache_timeout (float): Number of seconds the cached statistics are valid. 0 disables cache for this call.

    Returns:
    - A list or dictionary of state values or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_longterm_values")
    from power_convert import power_convert

    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)

    states = {}

    try:
        history_data = fetch_statistics_data(hass, entity_id, from_datetime, to_datetime, state_type, force=force, cache_timeout=cache_timeout)

        if isinstance(history_data, dict):
            for ts, value in history_data.items():
                try:
                    if value not in ENTITY_UNAVAILABLE_STATES:
                        value = value if convert_to is None else power_convert(value, entity_id, convert_to=convert_to)

                        states[ts] = value

                except:
                    pass

        if states:
            if include_timestamps:
                return states

            return list(states.values())

    except Exception as e:
        _LOGGER.error(f"Error in get_longterm_values for {entity_id} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime} states:{states}: {e}")

    return error_state


def get_min_value(entity_id, from_datetime, to_datetime, convert_to=None, error_state=None, force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Fetches the minimum state value for a specified entity within a given datetime range
    from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to fetch the minimum value for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - convert_to: Optional unit to convert the value to.
    - error_state: The value to return in case of an error.
    - force (bool): Forces new history and statistics data to be fetched from Home Assistant.
    - cache_timeout (float): Number of seconds cached history and statistics data are valid.

    Returns:
    - The minimum state value or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_min_value")

    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)

    states = get_values(entity_id, from_datetime, to_datetime, float_type=True, convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)
    longterm_states = get_longterm_values(entity_id, from_datetime, to_datetime, state_type="min", convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)

    if states is not None and longterm_states is not None:
        states.extend(longterm_states)

    elif states is None and longterm_states is not None:
        states = longterm_states

    try:
        if states:
            min_value = min(states)
            _LOGGER.debug(f"The min value of {entity_id} between {from_datetime} and {to_datetime} is {min_value}: {states}")
            return min_value

        else:
            _LOGGER.debug(f"No data found for {entity_id} between {from_datetime} and {to_datetime}")

    except Exception as e:
        _LOGGER.error(f"Error in get_min_value for {entity_id} between {from_datetime} and {to_datetime} states:{states}: {e}")

    return error_state


def get_max_value(entity_id, from_datetime, to_datetime, convert_to=None, error_state=None, force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Fetches the maximum state value for a specified entity within a given datetime range
    from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to fetch the maximum value for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - convert_to: Optional unit to convert the value to.
    - error_state: The value to return in case of an error.
    - force (bool): Forces new history and statistics data to be fetched from Home Assistant.
    - cache_timeout (float): Number of seconds cached history and statistics data are valid.

    Returns:
    - The maximum state value or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_max_value")

    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)

    states = get_values(entity_id, from_datetime, to_datetime, float_type=True, convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)
    longterm_states = get_longterm_values(entity_id, from_datetime, to_datetime, state_type="max", convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)

    if states is not None and longterm_states is not None:
        states.extend(longterm_states)

    elif states is None and longterm_states is not None:
        states = longterm_states

    try:
        if states:
            max_value = max(states)
            _LOGGER.debug(f"The max value of {entity_id} between {from_datetime} and {to_datetime} is {max_value}: {states}")
            return max_value

        else:
            _LOGGER.debug(f"No data found for {entity_id} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime}")

    except Exception as e:
        _LOGGER.error(f"Error in get_max_value for {entity_id} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime} states:{states}: {e}")

    return error_state


def get_average_value(entity_id, from_datetime, to_datetime, convert_to=None, error_state=None, force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Calculates the average state value for a specified entity within a given datetime range
    from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to calculate the average value for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - convert_to: Optional unit to convert the values to.
    - error_state: The value to return in case of an error.
    - force (bool): Forces new history and statistics data to be fetched from Home Assistant.
    - cache_timeout (float): Number of seconds cached history and statistics data are valid.

    Returns:
    - The average state value or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_average_value")

    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)

    states = get_values(entity_id, from_datetime, to_datetime, float_type=True, convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)
    longterm_states = get_longterm_values(entity_id, from_datetime, to_datetime, state_type="mean", convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)

    if states is not None and longterm_states is not None:
        states.extend(longterm_states)

    elif states is None and longterm_states is not None:
        states = longterm_states

    try:
        if states:
            avg_value = sum(states) / len(states)
            _LOGGER.debug(f"The average value of {entity_id} between {from_datetime} and {to_datetime} is {avg_value}")
            return avg_value

        else:
            _LOGGER.debug(f"No data found for {entity_id} between {from_datetime} and {to_datetime}")

    except Exception as e:
        _LOGGER.error(f"Error in get_average_value for {entity_id} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime} states:{states}: {e}")

    return error_state


def get_delta_value(entity_id, from_datetime, to_datetime, convert_to=None, error_state=None, force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Calculates the difference (delta) between the first and last state values for a specified entity
    within a given datetime range from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to calculate the delta value for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - convert_to: Optional unit to convert the values to.
    - error_state: The value to return in case of an error.
    - force (bool): Forces new history and statistics data to be fetched from Home Assistant.
    - cache_timeout (float): Number of seconds cached history and statistics data are valid.

    Returns:
    - The delta state value or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_delta_value")

    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)

    states = get_values(entity_id, from_datetime, to_datetime, float_type=True, convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)
    longterm_states = get_longterm_values(entity_id, from_datetime, to_datetime, state_type="mean", convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)

    if states is not None and longterm_states is not None:
        states.extend(longterm_states)

    elif states is None and longterm_states is not None:
        states = longterm_states

    try:
        if states and isinstance(states, list):
            first_state = states[0]
            last_state = states[-1]
            delta = last_state - first_state

            _LOGGER.debug(f"first_state:{first_state} last_state:{last_state} delta:{delta}\n states:{states}")
            _LOGGER.debug(f"The delta value of {entity_id} between {from_datetime} and {to_datetime} is {delta}")

            return delta

        else:
            _LOGGER.debug(f"No data found for {entity_id} between {from_datetime} and {to_datetime}")

    except Exception as e:
        _LOGGER.error(f"Error in get_delta_value for {entity_id} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime} states:{states}: {e}")

    return error_state


def get_last_value(entity_id, float_type=False, convert_to=None, error_state="unknown", force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Fetches the last state value for a specified entity within the last day from the Home Assistant API.

    Supports converting the state to a float type if specified.

    Parameters:
    - entity_id (str): The entity ID to fetch the last value for.
    - float_type (bool): Whether to convert the state value to a float.
    - convert_to: Optional unit to convert the value to.
    - error_state: The value to return in case of an error.
    - force (bool): Forces new history data to be fetched from Home Assistant, ignoring the cache.
    - cache_timeout (float): Number of seconds the cached history data is valid.

    Returns:
    - The last state value as a float if float_type is True, otherwise in its original form, or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_last_value")

    to_datetime = datetime.datetime.now().replace(microsecond=0)
    from_datetime = to_datetime - datetime.timedelta(days=1)

    states = get_values(entity_id, from_datetime, to_datetime, float_type=float_type, convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)

    try:
        if states and isinstance(states, list):
            last_value = states[-1]

            _LOGGER.debug(f"The last value of {entity_id} between {from_datetime} and {to_datetime} is {last_value}")

            return last_value

        else:
            _LOGGER.warning(f"No data found for {entity_id} between {from_datetime} and {to_datetime} returning {error_state}")

    except Exception as e:
        _LOGGER.error(f"Error in get_last_value for {entity_id} float_type:{float_type} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime} states:{states}: {e}")

    return error_state


def get_previous_value(entity_id, float_type=False, convert_to=None, error_state="unknown", force=False, cache_timeout=HISTORY_CACHE_TIMEOUT):
    """
    Fetches the previous state value for a specified entity within the last day from the Home Assistant API.

    The previous value is the most recent value that differs from the latest state value.

    Parameters:
    - entity_id (str): The entity ID to fetch the previous value for.
    - float_type (bool): Whether to convert the state value to a float.
    - convert_to: Optional unit to convert the value to.
    - error_state: The value to return in case of an error.
    - force (bool): Forces new history data to be fetched from Home Assistant, ignoring the cache.
    - cache_timeout (float): Number of seconds the cached history data is valid.

    Returns:
    - The previous state value, or the latest value if no different previous value exists.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_previous_value")

    to_datetime = datetime.datetime.now().replace(microsecond=0)
    from_datetime = to_datetime - datetime.timedelta(days=1)

    states = get_values(entity_id, from_datetime, to_datetime, float_type=float_type, convert_to=convert_to, error_state=None, force=force, cache_timeout=cache_timeout)

    try:
        if states is None and float_type is True:
            _LOGGER.warning(f"No data found for {entity_id} between {from_datetime} and {to_datetime} returning {error_state}")
            return error_state

        if states and isinstance(states, list):
            last_value = states[-1]

            for value in states[::-1]:
                if value != last_value:
                    _LOGGER.debug(f"The previous value of {entity_id} between {from_datetime} and {to_datetime} is {value}")
                    return value

            _LOGGER.debug(f"The previous value of {entity_id} between {from_datetime} and {to_datetime} is the same as the last value: {last_value}")

            return last_value

        try:
            if float_type is True:
                return float(error_state)

        except:
            _LOGGER.debug(f"entity_id: float_type is True, but error_state is {error_state}. Returning 0.0 as failsafe")
            return 0.0

    except Exception as e:
        _LOGGER.error(f"Error in get_previous_value for {entity_id} float_type:{float_type} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime} states:{states}: {e}")

    return error_state