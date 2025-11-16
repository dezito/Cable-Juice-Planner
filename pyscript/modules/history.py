import datetime
import numpy as np

from homeassistant.components.recorder import history as hass_history
from homeassistant.core import HomeAssistant
from homeassistant.components.recorder.util import session_scope
from homeassistant.util import dt as dt_util

ENTITY_UNAVAILABLE_STATES = (None, "unavailable", "unknown")

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def timestamps_correction(from_datetime, to_datetime):
    try:
        from_time = min(from_datetime, to_datetime)
        to_time = max(from_datetime, to_datetime)
    except Exception as e:
        _LOGGER.error(f"Error in timestamps_correction for from_datetime:{from_datetime} to_datetime:{to_datetime}: {e}")
        from_time = from_datetime
        to_time = to_datetime
        
    return from_time, to_time

def interpolate_sensor_data(sensor_data, from_datetime, to_datetime, num_points):
    interpolated_dict = {}
    
    try:
        sorted_data = sorted(sensor_data.items())
        
        numeric_data = []
        non_numeric_data = {}

        for timestamp, value in sorted_data:
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
        _LOGGER.error(f"Error in interpolate_sensor_data: {e}")

    return interpolated_dict

def fetch_history_data(hass: HomeAssistant, entity_id: str, start_time: datetime, end_time: datetime):
    _LOGGER = globals()['_LOGGER'].getChild("fetch_history_data")
    
    state_dict = {}
    
    try:
        #start_time = dt_util.as_utc(start_time)
        #end_time = dt_util.as_utc(end_time)
        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)
        
        if entity_id is None or entity_id == "" or entity_id not in state.names(domain=entity_id.split(".")[0]):
            return state_dict
        
        hist_data = hass_history.get_significant_states(
            hass = hass,
            start_time = start_time,
            end_time = end_time,
            entity_ids = [entity_id],
            filters = None,
            include_start_time_state = True,
            significant_changes_only = False,
            minimal_response = False,
            no_attributes = False,
            compressed_state_format = False,
        )
        
        '''with session_scope(hass=hass, read_only=True) as session:
            hist_data = hass_history.get_significant_states_with_session(
                hass=hass,
                session=session,
                start_time=start_time,
                end_time=end_time,
                entity_ids=[entity_id],
                filters = None,
                include_start_time_state = True,
                significant_changes_only = False,
                minimal_response = False,
                no_attributes = False,
                compressed_state_format = False,
            )'''
            
        if entity_id in hist_data:
            #entity_state_dict = {d.last_reported_timestamp: d.state for d in hist_data[entity_id]}
            entity_state_dict = {}
            for d in hist_data[entity_id]:
                try:
                    entity_state_dict[d.last_updated.timestamp()] = d.state
                except Exception as e:
                    _LOGGER.error(f"Error in fetch_history_data: {e}")
            
            start_timestamp = datetime.datetime.timestamp(start_time)
            end_timestamp = datetime.datetime.timestamp(end_time)
            state_dict = interpolate_sensor_data(entity_state_dict, start_timestamp, end_timestamp, 100)
        else:
            _LOGGER.debug(f"No data found for entity_id: {entity_id}")
    except Exception as e:
        _LOGGER.error(f"Error in fetch_history_data for {entity_id} between {start_time} and {end_time}: {e}")
            
    return state_dict

def get_values(entity_id, from_datetime, to_datetime, float_type=False, convert_to=None, include_timestamps=False, error_state=None):
    """
    Fetches historical state values for a specified entity within a given datetime range
    from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to fetch historical values for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - error_state: The value to return in case of an error.

    Returns:
    - A list of state values or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_values")
    from power_convert import power_convert
    
    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)
    
    states = {}
    
    try:
        history_data = fetch_history_data(hass, entity_id, from_datetime, to_datetime)
        

        if "full_charge_recommended" in entity_id or "last_full_charge" in entity_id:
            _LOGGER.debug(f"get_values history_data for {entity_id} between {from_datetime} and {to_datetime}: {history_data}")
            
        if isinstance(history_data, dict):
            for ts, value in history_data.items():
                try:
                    if value not in ENTITY_UNAVAILABLE_STATES:
                        if float_type is True:
                            try:
                                value = float(value)
                            except:
                                continue
                        value = value if convert_to is None else power_convert(value, entity_id, convert_to = convert_to)
                        
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

def get_min_value(entity_id, from_datetime, to_datetime, convert_to=None, error_state=None):
    """
    Fetches the minimum state value for a specified entity within a given datetime range
    from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to fetch the minimum value for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - error_state: The value to return in case of an error.

    Returns:
    - The minimum state value or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_min_value")
    
    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)
    
    states = get_values(entity_id, from_datetime, to_datetime, float_type=True, convert_to = convert_to, error_state=None)
        
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

def get_max_value(entity_id, from_datetime, to_datetime, convert_to=None, error_state=None):
    """
    Fetches the maximum state value for a specified entity within a given datetime range
    from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to fetch the maximum value for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - error_state: The value to return in case of an error.

    Returns:
    - The maximum state value or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_max_value")
    
    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)
    
    states = get_values(entity_id, from_datetime, to_datetime, float_type=True, convert_to = convert_to, error_state=None)
        
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

def get_average_value(entity_id, from_datetime, to_datetime, convert_to=None, error_state=None):
    """
    Calculates the average state value for a specified entity within a given datetime range
    from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to calculate the average value for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - error_state: The value to return in case of an error.

    Returns:
    - The average state value or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_average_value")
    
    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)
    
    states = get_values(entity_id, from_datetime, to_datetime, float_type=True, convert_to = convert_to, error_state=None)
        
    try:
        if states:
            avg_value = sum(states) / len(states)
            avg_value = avg_value
            _LOGGER.debug(f"The average value of {entity_id} between {from_datetime} and {to_datetime} is {avg_value}")
            return avg_value
        else:
            _LOGGER.debug(f"No data found for {entity_id} between {from_datetime} and {to_datetime}")
    except Exception as e:
        _LOGGER.error(f"Error in get_average_value for {entity_id} convert_to:{convert_to} error_state:{error_state} between {from_datetime} and {to_datetime} states:{states}: {e}")
        
    return error_state

def get_delta_value(entity_id, from_datetime, to_datetime, convert_to=None, error_state=None):
    """
    Calculates the difference (delta) between the first and last state values for a specified entity
    within a given datetime range from the Home Assistant API.

    Parameters:
    - entity_id (str): The entity ID to calculate the delta value for.
    - from_datetime (datetime): The start of the datetime range.
    - to_datetime (datetime): The end of the datetime range.
    - error_state: The value to return in case of an error.

    Returns:
    - The delta state value or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_delta_value")
    
    from_datetime, to_datetime = timestamps_correction(from_datetime, to_datetime)
    
    states = get_values(entity_id, from_datetime, to_datetime, float_type=True, convert_to = convert_to, error_state=None)
        
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

def get_last_value(entity_id, float_type=False, convert_to=None, error_state="unknown"):
    """
    Fetches the last state value for a specified entity within the last day from the Home Assistant API.
    Supports converting the state to a float type if specified.

    Parameters:
    - entity_id (str): The entity ID to fetch the last value for.
    - float_type (bool): Whether to convert the state value to a float.
    - error_state: The value to return in case of an error.

    Returns:
    - The last state value as a float if float_type is True, otherwise in its original form, or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_last_value")
    
    to_datetime = datetime.datetime.now()
    from_datetime = to_datetime - datetime.timedelta(days=1)
        
    states = get_values(entity_id, from_datetime, to_datetime, float_type=float_type, convert_to = convert_to, error_state=None)
    
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

def get_previous_value(entity_id, float_type=False, convert_to=None, error_state="unknown"):
    """
    Fetches the last state value for a specified entity within the last day from the Home Assistant API.
    Supports converting the state to a float type if specified.

    Parameters:
    - entity_id (str): The entity ID to fetch the last value for.
    - float_type (bool): Whether to convert the state value to a float.
    - error_state: The value to return in case of an error.

    Returns:
    - The last state value as a float if float_type is True, otherwise in its original form, or the error state if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_previous_value")
    
    to_datetime = datetime.datetime.now()
    from_datetime = to_datetime - datetime.timedelta(days=1)
    
    states = get_values(entity_id, from_datetime, to_datetime, float_type=float_type, convert_to = convert_to, error_state=None)
    
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