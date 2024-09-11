__version__ = "1.0.0"
from history import *

from dateutil import parser

import homeassistant.helpers.device as device_helper

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def get_state(entity_id=None, try_history=True, float_type=False, error_state="unknown"):
    """
    Retrieves the current state of a specified entity in Home Assistant. If the state is unknown or unavailable,
    and try_history is True, it attempts to fetch the last known state from history. For input_datetime entities,
    it parses the state into a datetime object.

    Parameters:
    - entity_id (str): The entity ID to fetch the state for.
    - try_history (bool): Whether to attempt fetching the last known state from history.
    - float_type (bool): Converts the state to a float if possible.
    - error_state (str): The state to return in case of errors.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_state")
    output = None
    
    if entity_id == "":
        return error_state
    
    try:
        if entity_id is None: raise Exception("entity_id argument is None")
        
        if entity_id not in state.names(domain=entity_id.split(".")[0]):
            raise Exception(f"Entity not found in Home Assistant: {entity_id}")
        
        output = state.get(entity_id)
        
        if try_history and output in ["unknown", "unavailable"]:
            output = get_last_value(entity_id, float_type=float_type, error_state=error_state)
            
        if float_type is True:
            output = float(output)
    except Exception as e:
        if entity_id == "":
            entity_id == None
        _LOGGER.error(f"Can't get state for {entity_id}, output is {output}\n{e}")
        return error_state
    
    try:
        domain = entity_id.split(".")[0]
        if domain == "input_datetime":
            output = parser.parse(output)
    except Exception as e:
        pass
    return output

def get_attr(entity_id=None, attr=None, error_state="unknown"):
    """
    Fetches a specific attribute value of a Home Assistant entity. If the attribute name is not provided,
    it returns all attributes of the entity.

    Parameters:
    - entity_id (str): The entity ID to fetch the attribute for.
    - attr (str): The specific attribute to retrieve.
    - error_state (str): The state to return in case of errors.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_attr")
    try:
        if entity_id is None: raise Exception("entity_id argument is None")
        
        if attr is None:
            return state.getattr(entity_id)
        
        return state.getattr(entity_id)[attr]
    except Exception as e:
        if entity_id == "":
            entity_id == None
        _LOGGER.error(f"Can't get attribute for {entity_id}['{attr}'], output is {output}\n{e}")
        return error_state

def set_state(entity_id=None, new_state=None, error_state="unknown"):
    """
    Sets a new state for a specified Home Assistant entity. Handles different domains (number, switch, light, etc.)
    accordingly, including parsing datetime for input_datetime entities and executing domain-specific services.

    Parameters:
    - entity_id (str): The entity ID to set the new state for.
    - new_state (str|int|datetime): The new state value.
    - error_state (str): The state to revert to in case of errors.
    """
    _LOGGER = globals()['_LOGGER'].getChild("set_state")
    domain = entity_id.split(".")[0]
    try:
        if entity_id is None or new_state is None:
            raise Exception("One argument is None")
        
        if domain == "number":
            number.set_value(entity_id = entity_id, value = new_state)
        elif domain == "switch":
            if new_state == "on":
                switch.turn_on(entity_id = entity_id)
            elif new_state == "off":
                switch.turn_off(entity_id = entity_id)
            else:
                raise Exception(f"Unknown command {new_state}")
        elif domain == "light":
            try:
                new_state = int(new_state)
            except:
                pass
            if new_state == "on":
                light.turn_on(entity_id = entity_id)
            elif new_state > 0:
                light.turn_on(entity_id = entity_id, brightness=new_state)
            elif new_state == "off" or new_state == 0:
                light.turn_off(entity_id = entity_id)
            else:
                raise Exception(f"Unknown command {new_state}")
        elif "input_" in domain:
            if "boolean" in domain:
                service = "turn_off"
                if new_state == "on":
                    service = "turn_on"
                eval(f"{domain}.{service}(entity_id = '{entity_id}')")
            elif "button" in domain:
                eval(f"{domain}.press(entity_id = '{entity_id}')")
            elif "datetime" in domain:
                try:
                    new_state = parser.parse(new_state)
                except:
                    pass
                eval(f"{domain}.set_datetime(entity_id = '{entity_id}', datetime = '{new_state}')")
            elif "number" in domain or "text" in domain:
                eval(f"{domain}.set_value(entity_id = '{entity_id}', value = '{new_state}')")
            elif "select" in domain:
                eval(f"{domain}.select_option(entity_id = '{entity_id}', option = '{new_state}')")
            else:
                raise Exception(f"Unknown service for {domain}")
        else:
            state.set(entity_id, new_state)
    except Exception as e:
        if entity_id == "":
            entity_id == None
        _LOGGER.error(f"Can't set state for {entity_id} with new state {new_state} {e}")
        try:
            state.set(entity_id, error_state)
        except Exception as e:
            _LOGGER.error(f"Can't set state for {entity_id} with error state {error_state} {e}")
            return False
    return True

def set_attr(entity_id=None, attr=None):
    """
    Sets an attribute for a specified Home Assistant entity. This function is designed to work with entities
    that have a domain-specific structure in their entity ID.

    Parameters:
    - entity_id (str): The entity ID to set the attribute for.
    - attr (dict): The attribute(s) to set.
    """
    _LOGGER = globals()['_LOGGER'].getChild("set_attr")
    try:
        if entity_id is None: raise Exception("entity_id argument is None")
        if entity_id.count('.') != 2: raise Exception(f"entity_id dont have attribute {entity_id}")
        
        state.setattr(entity_id, attr)
        
        return True
    except Exception as e:
        if entity_id == "":
            entity_id == None
        _LOGGER.error(f"Can't set attribute for {entity_id} with {attr}\n{e}")
    
def get_manufacturer(entity_id):
    _LOGGER = globals()['_LOGGER'].getChild("get_manufacturer")
    device_registry = hass.data['device_registry']
    
    try:
        device_class = device_registry.async_get(device_helper.async_entity_id_to_device_id(hass, entity_id))
        if device_class is None:
            return None
        
        return device_class.manufacturer
    except Exception as e:
        _LOGGER.error(f"Cant get manufacturer from {entity_id} {device_class}: {e}")
    return None
    
def get_identifiers(entity_id):
    _LOGGER = globals()['_LOGGER'].getChild("get_identifiers")
    device_registry = hass.data['device_registry']
    
    try:
        device_class = device_registry.async_get(device_helper.async_entity_id_to_device_id(hass, entity_id))
        if device_class is None:
            return None
        
        return device_class.identifiers
    except Exception as e:
        _LOGGER.error(f"Cant get identifiers from {entity_id} {device_class}: {e}")
    return None

def get_integration(entity_id):
    try:
        integration = [item[0] for item in get_identifiers(entity_id)][0]
    except:
        integration = None
    return entity_id, integration


def reload_integration(entity_id=None):
    _LOGGER = globals()['_LOGGER'].getChild("reload_integration")
    _LOGGER.warning(f"Reloading integration for {entity_id}")
    homeassistant.reload_config_entry(entity_id = entity_id)
