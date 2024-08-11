__version__ = "1.0.0"
import datetime
import pytz

from homeassistant.components.recorder import history
from homeassistant.core import HomeAssistant
from homeassistant.components.recorder.util import session_scope

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def fetch_history_data(hass: HomeAssistant, entity_id: str, start_time: datetime, end_time: datetime):
    _LOGGER = globals()['_LOGGER'].getChild("fetch_history_data")
    utc = pytz.UTC  # Tidszone
    start_time = utc.localize(start_time)
    end_time = utc.localize(end_time)
    
    state_values = []
    
    if entity_id is None or entity_id == "" or entity_id not in state.names(domain=entity_id.split(".")[0]):
        return state_values
    
    hist_data = history.get_significant_states(
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
        hist_data = history.get_significant_states_with_session(
            hass=hass,
            session=session,
            start_time=start_time,
            end_time=end_time,
            entity_ids=[entity_id],
            include_start_time_state=True,
            significant_changes_only=False
        )'''
        
    if entity_id in hist_data:
        state_values = [state.state for state in hist_data[entity_id] if state.state not in (None, "unknown")]
    else:
        _LOGGER.warning(f"No data found for entity_id: {entity_id}")
            
    return state_values

def get_values(entity_id, from_datetime, to_datetime, float_type=False, convert_to=None, error_state=None):
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
    from power_convert import power_convert
    _LOGGER = globals()['_LOGGER'].getChild("get_values")
    
    from_time = min(from_datetime, to_datetime)
    to_time = max(from_datetime, to_datetime)
    
    history_data = fetch_history_data(hass, entity_id, from_time, to_time)
    
    states = []

    if len(history_data) > 0:
        for value in history_data:
            try:
                if value not in ["unknown", "unavailable"]:
                    if float_type is True:
                        try:
                            value = float(value)
                        except:
                            continue
                    value = value if convert_to is None else power_convert(value, entity_id, output = convert_to)
                    states.append(value)
            except:
                pass

    # Calculate the average value of the entity
    if states:
        return states
    else:
        _LOGGER.warning(f"No data found for {entity_id} between {from_time} and {to_time} float_type:{float_type} convert_to:{convert_to} len(history_data):{len(history_data)}")
        _LOGGER.warning(f"states: {states}")
        _LOGGER.warning(f"history_data: {history_data}")
        
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
    
    from_time = min(from_datetime, to_datetime)
    to_time = max(from_datetime, to_datetime)
    
    states = get_values(entity_id, from_time, to_time, float_type=True, convert_to = convert_to, error_state=None)
    
    if states:
        min_value = min(states)
        _LOGGER.debug(f"The min value of {entity_id} between {from_time} and {to_time} is {min_value}: {states}")
        return min_value
    else:
        _LOGGER.warning(f"No data found for {entity_id} between {from_time} and {to_time}")
        
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
    
    from_time = min(from_datetime, to_datetime)
    to_time = max(from_datetime, to_datetime)
    
    states = get_values(entity_id, from_time, to_time, float_type=True, convert_to = convert_to, error_state=None)
    
    if states:
        max_value = max(states)
        _LOGGER.debug(f"The max value of {entity_id} between {from_time} and {to_time} is {max_value}: {states}")
        return max_value
    else:
        _LOGGER.warning(f"No data found for {entity_id} between {from_time} and {to_time}")
        
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
    
    from_time = min(from_datetime, to_datetime)
    to_time = max(from_datetime, to_datetime)
    
    states = get_values(entity_id, from_time, to_time, float_type=True, convert_to = convert_to, error_state=None)
    
    if states:
        avg_value = sum(states) / len(states)
        avg_value = avg_value
        _LOGGER.debug(f"The average value of {entity_id} between {from_time} and {to_time} is {avg_value}")
        return avg_value
    else:
        _LOGGER.warning(f"No data found for {entity_id} between {from_time} and {to_time}")
        
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
    
    from_time = min(from_datetime, to_datetime)
    to_time = max(from_datetime, to_datetime)
    
    states = get_values(entity_id, from_time, to_time, float_type=True, convert_to = convert_to, error_state=None)
    
    if states:
        first_state = states[0]
        last_state = states[-1]
        delta = last_state - first_state
        _LOGGER.debug(f"first_state:{first_state} last_state:{last_state} delta:{delta}\n states:{states}")
        _LOGGER.debug(f"The delta value of {entity_id} between {from_time} and {to_time} is {delta}")
        return delta
    else:
        _LOGGER.warning(f"No data found for {entity_id} between {from_time} and {to_time}")

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
    
    to_time = datetime.datetime.now()
    from_time = to_time - datetime.timedelta(days=1)
    
    states = get_values(entity_id, from_time, to_time, float_type=float_type, convert_to = convert_to, error_state=None)
    
    if isinstance(states, list) and len(states) != 0:
        last_value = states[-1]
        _LOGGER.debug(f"The last value of {entity_id} between {from_time} and {to_time} is {last_value}")
        return last_value
    else:
        _LOGGER.warning(f"No data found for {entity_id} between {from_time} and {to_time} returning {error_state}")
        
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
    
    to_time = datetime.datetime.now()
    from_time = to_time - datetime.timedelta(days=1)
    
    states = get_values(entity_id, from_time, to_time, float_type=float_type, convert_to = convert_to, error_state=None)
    
    if states:
        last_value = states[-1]
        for value in states[::-1]:
            if value != last_value:
                _LOGGER.debug(f"The previous value of {entity_id} between {from_time} and {to_time} is {value}")
                return value
    else:
        _LOGGER.warning(f"No data found for {entity_id} between {from_time} and {to_time}")
        
    try:
        if float_type is True:
            return float(error_state)
    except:
        _LOGGER.error(f"entity_id: float_type is True, but error_state is {error_state}. Returning 0.0 as failsafe")
        return 0.0
    return error_state