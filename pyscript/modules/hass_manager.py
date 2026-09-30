from dateutil import parser
import time

import astral.sun
import homeassistant.helpers.sun as hass_sun
import homeassistant.helpers.device as device_helper

from mytime import getTime
from history import get_last_value

from logging import getLogger


ENTITY_UNAVAILABLE_STATES = (None, "unavailable", "unknown")

BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)


HASS_CACHE_TIMEOUT = 30.0

HASS_CACHE = {
    "state": {},
    "attributes": {},
    "manufacturer": {},
    "identifiers": {},
    "integration": {},
    "sun_events": {},
}

def _cache_get(cache_type, key, timeout=None):
    """
    Retrieves a value from the cache and optionally checks whether it has expired.

    Parameters:
    - cache_type (str): The cache category to retrieve the value from.
    - key: The key identifying the cached value.
    - timeout (float): Maximum cache age in seconds. None disables expiration and 0 disables cache usage.
    """
    if timeout == 0:
        return False, None

    cached = HASS_CACHE[cache_type].get(key)

    if cached is None:
        return False, None

    if timeout is not None and time.monotonic() - cached["timestamp"] >= timeout:
        HASS_CACHE[cache_type].pop(key, None)
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
    HASS_CACHE[cache_type][key] = {
        "value": value,
        "timestamp": time.monotonic(),
    }

def _attr_cache_get(entity_id, attr, timeout=None):
    """
    Retrieves an individual entity attribute from the cache.

    Parameters:
    - entity_id (str): The entity ID the attribute belongs to.
    - attr (str): The attribute name.
    - timeout (float): Maximum cache age in seconds. None disables expiration and 0 disables cache usage.
    """
    if timeout == 0:
        return False, None

    entity_cache = HASS_CACHE["attributes"].get(entity_id)

    if entity_cache is None:
        return False, None

    cached = entity_cache.get(attr)

    if cached is None:
        return False, None

    if timeout is not None and time.monotonic() - cached["timestamp"] >= timeout:
        entity_cache.pop(attr, None)

        if not entity_cache:
            HASS_CACHE["attributes"].pop(entity_id, None)

        return False, None

    return True, cached["value"]

def _attr_cache_set(entity_id, attr, value):
    """
    Stores an individual entity attribute in the cache.

    Parameters:
    - entity_id (str): The entity ID the attribute belongs to.
    - attr (str): The attribute name.
    - value: The attribute value to cache.
    """
    HASS_CACHE["attributes"].setdefault(entity_id, {})[attr] = {
        "value": value,
        "timestamp": time.monotonic(),
    }

def _attr_cache_set_all(entity_id, attributes):
    """
    Stores all attributes of an entity individually in the cache.

    Parameters:
    - entity_id (str): The entity ID the attributes belong to.
    - attributes (dict): Dictionary containing the attributes to cache.
    """
    timestamp = time.monotonic()
    entity_cache = HASS_CACHE["attributes"].setdefault(entity_id, {})

    for attr, value in attributes.items():
        entity_cache[attr] = {
            "value": value,
            "timestamp": timestamp,
        }

def clear_cache(cache_type=None, key=None):
    """
    Clears cached Home Assistant data.

    If no cache type is specified, the complete cache is cleared. If a cache type is specified without a key,
    all entries of that cache type are cleared.

    Parameters:
    - cache_type (str): The cache category to clear.
    - key: The specific cache entry to clear.
    """
    if cache_type is None:
        for cache in HASS_CACHE.values():
            cache.clear()
        return

    if cache_type not in HASS_CACHE:
        return

    if key is None:
        HASS_CACHE[cache_type].clear()
    else:
        HASS_CACHE[cache_type].pop(key, None)

def get_state(
    entity_id=None,
    try_history=True,
    float_type=False,
    error_state="unknown",
    force=False,
    cache_timeout=HASS_CACHE_TIMEOUT,
):
    """
    Retrieves the current state of a specified entity in Home Assistant. If the state is unknown or unavailable,
    and try_history is True, it attempts to fetch the last known state from history. For input_datetime entities,
    it parses the state into a datetime object.

    The raw Home Assistant state is cached for cache_timeout seconds. Setting force to True bypasses the cache
    and retrieves a new value directly from Home Assistant.

    Parameters:
    - entity_id (str): The entity ID to fetch the state for.
    - try_history (bool): Whether to attempt fetching the last known state from history.
    - float_type (bool): Converts the state to a float if possible.
    - error_state (str): The state to return in case of errors.
    - force (bool): Forces a new value to be fetched from Home Assistant, ignoring the cache.
    - cache_timeout (float): Number of seconds the cached state is valid. 0 disables cache for this call.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_state")
    output = None

    if entity_id == "":
        return error_state

    domain = None

    if entity_id and "." in entity_id:
        domain = entity_id.split(".")[0]

    try:
        if entity_id is None:
            raise Exception("entity_id argument is None")

        if domain is None:
            raise Exception(f"Invalid entity_id: {entity_id}")

        cached = False

        if not force:
            cached, output = _cache_get("state", entity_id, cache_timeout)

        if not cached:
            if entity_id not in state.names(domain=domain):
                raise Exception(f"Entity not found in Home Assistant: {entity_id}")

            output = state.get(entity_id)

            _cache_set("state", entity_id, output)

        if try_history and output in ENTITY_UNAVAILABLE_STATES:
            output = get_last_value(entity_id, float_type=float_type,error_state=error_state)

        if float_type:
            output = (float(output) if output not in ENTITY_UNAVAILABLE_STATES else error_state)
    except Exception as e:
        if entity_id == "":
            entity_id = None

        _LOGGER.error(f"Can't get state for {entity_id}, output is {output}\n{e}")
        return error_state

    try:
        if domain == "input_datetime":
            output = parser.parse(output)
    except Exception:
        pass

    return output

def get_attr(
    entity_id=None,
    attr=None,
    error_state="unknown",
    force=False,
    cache_timeout=HASS_CACHE_TIMEOUT,
):
    """
    Fetches a specific attribute value of a Home Assistant entity. If the attribute name is not provided,
    it returns all attributes of the entity.

    Individual attributes are cached for cache_timeout seconds. Setting force to True bypasses the cache and
    retrieves the attributes directly from Home Assistant. Fetching all attributes always retrieves the complete
    attribute dictionary from Home Assistant and updates the individual attribute cache.

    Parameters:
    - entity_id (str): The entity ID to fetch the attribute for.
    - attr (str): The specific attribute to retrieve. If None, all attributes are returned.
    - error_state (str): The state to return in case of errors.
    - force (bool): Forces new attributes to be fetched from Home Assistant, ignoring the cache.
    - cache_timeout (float): Number of seconds a cached attribute is valid. 0 disables cache for this call.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_attr")

    try:
        if entity_id is None:
            raise Exception("entity_id argument is None")

        if attr is not None and not force:
            cached, value = _attr_cache_get(entity_id, attr, cache_timeout)

            if cached:
                return value

        attributes = state.getattr(entity_id)

        if not isinstance(attributes, dict):
            raise Exception(f"Attributes for {entity_id} are not a dict")

        _attr_cache_set_all(entity_id, attributes)

        if attr is None:
            return attributes

        return attributes[attr]
    except Exception as e:
        if entity_id == "":
            entity_id = None

        _LOGGER.error(f"Can't get attribute for {entity_id}['{attr}']\n{e}")
        return error_state

def set_state(entity_id=None, new_state=None, error_state="unknown"):
    """
    Sets a new state for a specified Home Assistant entity. Handles different domains (number, switch, light, etc.)
    accordingly, including parsing datetime for input_datetime entities and executing domain-specific services.

    After successfully setting the state, the state cache is updated immediately with the new value.

    Parameters:
    - entity_id (str): The entity ID to set the new state for.
    - new_state (str|int|datetime): The new state value.
    - error_state (str): The state to revert to in case of errors.
    """
    _LOGGER = globals()['_LOGGER'].getChild("set_state")

    try:
        if entity_id is None or new_state is None:
            raise Exception("One argument is None")

        domain = entity_id.split(".")[0]
        cache_state = new_state

        if domain == "number":
            number.set_value(entity_id=entity_id, value=new_state)
        elif domain == "switch":
            if new_state == "on":
                switch.turn_on(entity_id=entity_id)
            elif new_state == "off":
                switch.turn_off(entity_id=entity_id)
            else:
                raise Exception(f"Unknown command {new_state}")
        elif domain == "light":
            try:
                new_state = int(new_state)
            except:
                pass

            if new_state == "on":
                light.turn_on(entity_id=entity_id)

                cache_state = "on"
            elif isinstance(new_state, (int, float)) and new_state > 0:
                light.turn_on(entity_id=entity_id, brightness=new_state)

                cache_state = "on"
            elif new_state == "off" or new_state == 0:
                light.turn_off(entity_id=entity_id)

                cache_state = "off"
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
                service_value = new_state

                try:
                    service_value = parser.parse(new_state)
                except:
                    pass

                eval(f"{domain}.set_datetime(entity_id = '{entity_id}', datetime = '{service_value}')")
            elif "number" in domain or "text" in domain:
                eval(f"{domain}.set_value(entity_id = '{entity_id}', value = '{new_state}')")
            elif "select" in domain:
                eval(f"{domain}.select_option(entity_id = '{entity_id}', option = '{new_state}')")
            else:
                raise Exception(f"Unknown service for {domain}")
        else:
            state.set(entity_id, new_state)

        _cache_set("state", entity_id, cache_state)
    except Exception as e:
        if entity_id == "":
            entity_id = None

        _LOGGER.error(f"Can't set state for {entity_id} with new state {new_state} {e}")

        try:
            state.set(entity_id, error_state)
            _cache_set("state", entity_id, error_state)
        except Exception as e:
            _LOGGER.error(f"Can't set state for {entity_id} with error state {error_state} {e}")
            return False
        
    return True

def set_attr(entity_id=None, attr=None):
    """
    Sets an attribute for a specified Home Assistant entity. The entity ID must include the attribute name.

    After successfully setting the attribute, the individual attribute cache is updated directly without
    requiring an additional read from Home Assistant.

    Parameters:
    - entity_id (str): The entity ID including the attribute name, for example sensor.example.attribute_name.
    - attr: The new attribute value.
    """
    _LOGGER = globals()['_LOGGER'].getChild("set_attr")

    try:
        if entity_id is None:
            raise Exception("entity_id argument is None")

        if entity_id.count(".") != 2:
            raise Exception(f"entity_id dont have attribute {entity_id}")

        domain, entity, attribute_name = entity_id.split(".", 2)
        base_entity_id = f"{domain}.{entity}"

        state.setattr(entity_id, attr)

        _attr_cache_set(base_entity_id, attribute_name, attr)

        return True
    except Exception as e:
        if entity_id == "":
            entity_id = None

        _LOGGER.error(f"Can't set attribute for {entity_id} with {attr}\n{e}")
        return False

def get_manufacturer(entity_id, force=False):
    """
    Retrieves the manufacturer of the device associated with a specified Home Assistant entity.

    The manufacturer is cached without a timeout because it normally does not change during runtime.

    Parameters:
    - entity_id (str): The entity ID to retrieve the manufacturer for.
    - force (bool): Forces a new value to be retrieved from Home Assistant, ignoring the cache.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_manufacturer")

    if not force:
        cached, value = _cache_get("manufacturer", entity_id)

        if cached:
            return value

    device_class = None

    try:
        device_registry = hass.data["device_registry"]
        device_class = device_registry.async_get(device_helper.async_entity_id_to_device_id(hass, entity_id))
        value = (device_class.manufacturer if device_class is not None else None)
        _cache_set("manufacturer", entity_id, value)

        return value
    except Exception as e:
        _LOGGER.error(f"Cant get manufacturer from {entity_id} {device_class}: {e}")
        return None

def get_identifiers(entity_id, force=False):
    """
    Retrieves the device identifiers associated with a specified Home Assistant entity.

    The identifiers are cached without a timeout because they normally do not change during runtime.

    Parameters:
    - entity_id (str): The entity ID to retrieve device identifiers for.
    - force (bool): Forces new identifiers to be retrieved from Home Assistant, ignoring the cache.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_identifiers")

    if not force:
        cached, value = _cache_get("identifiers", entity_id)

        if cached:
            return value

    device_class = None

    try:
        device_registry = hass.data["device_registry"]
        device_class = device_registry.async_get(device_helper.async_entity_id_to_device_id(hass, entity_id))
        value = (list(device_class.identifiers) if device_class is not None else None)
        _cache_set("identifiers", entity_id, value)
        
        return value
    except Exception as e:
        _LOGGER.error(f"Cant get identifiers from {entity_id} {device_class}: {e}")
        return None

def get_integration(entity_id, force=False):
    """
    Retrieves the integration name associated with a specified Home Assistant entity.

    The integration is determined from the device identifiers and cached without a timeout.

    Parameters:
    - entity_id (str): The entity ID to retrieve the integration for.
    - force (bool): Forces the integration and identifiers to be retrieved again, ignoring the cache.
    """
    if not force:
        cached, value = _cache_get("integration", entity_id)

        if cached:
            return value

    try:
        identifiers = get_identifiers(entity_id, force=force)
        integration = identifiers[0][0]
    except:
        integration = None

    _cache_set("integration", entity_id, integration)

    return integration


def get_sun_events(dt=None, force=False):
    """
    Retrieves sun events for a specified date, including dawn, sunrise, noon, sunset, and midnight.

    Sun events are cached per date without a timeout because the calculated events for a specific date do not
    change during runtime. Setting force to True recalculates the events for the requested date.

    Parameters:
    - dt (datetime): The date to retrieve sun events for. Uses the current date and time if not provided.
    - force (bool): Forces the sun events to be recalculated, ignoring the cache.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_sun_events")

    dt = dt or getTime()
    cache_key = dt.date()

    if not force:
        cached, value = _cache_get("sun_events", cache_key)

        if cached:
            return value

    try:
        try:
            astral_observer = hass_sun.get_astral_observer(hass)

            output = {
                "dawn": astral.sun.dawn(astral_observer, dt).astimezone().replace(tzinfo=None),
                "sunrise": astral.sun.sunrise(astral_observer, dt).astimezone().replace(tzinfo=None),
                "noon": astral.sun.noon(astral_observer, dt).astimezone().replace(tzinfo=None),
                "sunset": astral.sun.sunset(astral_observer, dt).astimezone().replace(tzinfo=None),
                "midnight": astral.sun.midnight(astral_observer, dt).astimezone().replace(tzinfo=None),
            }
        except AttributeError:
            location = hass_sun.get_astral_location(hass)

            output = {
                "dawn": location[0].dawn(dt).replace(tzinfo=None),
                "sunrise": location[0].sunrise(dt).replace(tzinfo=None),
                "noon": location[0].noon(dt).replace(tzinfo=None),
                "sunset": location[0].sunset(dt).replace(tzinfo=None),
                "midnight": location[0].midnight(dt).replace(tzinfo=None),
            }

        _cache_set("sun_events", cache_key, output)

        return output
    except Exception as e:
        _LOGGER.error(f"Can't get sun events: {e}")

        return {
            "dawn": None,
            "sunrise": None,
            "noon": None,
            "sunset": None,
            "midnight": None,
        }

def reload_integration(entity_id=None):
    """
    Reloads the Home Assistant config entry associated with a specified entity.

    Parameters:
    - entity_id (str): The entity ID whose integration/config entry should be reloaded.
    """
    _LOGGER = globals()['_LOGGER'].getChild("reload_integration")
    
    _LOGGER.warning(f"Reloading integration for {entity_id}")
    homeassistant.reload_config_entry(entity_id=entity_id)