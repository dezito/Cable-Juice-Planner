__version__ = "1.0.0"
import functools
import math
from pprint import pformat

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def in_between(check, start, end):
    """
    Checks if a given value falls within a specified range, inclusive of the start and exclusive of the end. 
    Handles wrap-around logic for ranges that span the boundary (e.g., overnight).

    Parameters:
    - check (datetime|int|float): The value to check.
    - start (datetime|int|float): The start of the range.
    - end (datetime|int|float): The end of the range.
    """
    _LOGGER = globals()['_LOGGER'].getChild("in_between")
    #return check <= start < end if check <= end else check <= start or start < end
    return start <= check < end if start <= end else start <= check or check < end

def round_up(n, decimals=0):
    """
    Rounds a number up to the nearest specified number of decimal places.

    Parameters:
    - n (float): The number to round up.
    - decimals (int): The number of decimal places to round to.
    """
    _LOGGER = globals()['_LOGGER'].getChild("round_up")
    n = max(n, 0.0)
    multiplier = 10 ** decimals
    return float(math.ceil(n * multiplier) / multiplier)

def average(data):
    """
    Calculates the average of a list of numbers. Returns 0 if the list is empty or if an error occurs.

    Parameters:
    - data (list): The list of numbers to calculate the average of.
    """
    _LOGGER = globals()['_LOGGER'].getChild("average")
    if not isinstance(data, list):
        data = [data]
        
    try:
        return 0.0 if len(data) == 0 else sum(data) / len(data)
    except Exception as e:
        _LOGGER.error(f"data is not a list: {data} {e}")
        return 0.0
    

def get_specific_values(values, positive_only = False, negative_only = False):
    _LOGGER = globals()['_LOGGER'].getChild("get_specific_values")
    return_list = []
    for value in values:
        try:
            value = float(value)
        except:
            continue
        
        if (negative_only and value > 0.0) or (positive_only and value < 0.0):
            continue
        
        return_list.append(value)
        
    return [0.0] if return_list == [] else return_list

def get_closest_key(input_value, dictionary, return_key=False):
    """
    Finds the key in a dictionary closest to a given input value and returns the associated value.

    Parameters:
    - input_value (int): The value to find the closest key for.
    - dictionary (dict): The dictionary to search.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_closest_key")
    try:
        input_value = float(input_value)
        closest_key = list(dictionary.keys())[0]
        closest_diff = abs(float(closest_key) - input_value)

        for key in dictionary.keys():
            diff = abs(float(key) - input_value)
            if diff < closest_diff:
                closest_key = key
                closest_diff = diff
        
        if return_key:
            return closest_key
        return dictionary[closest_key]
    except Exception as e:
        _LOGGER.error(f"Cant get key {input_value} in {dictionary} {e}")
        return []

def keys_exists(element, *keys):
    """
    Checks if *keys (nested) exists in `element` (dict).

    Parameters:
    - element (dict): The dictionary to check.
    - keys (str): A sequence of keys representing the path to check for existence.
    """
    _LOGGER = globals()['_LOGGER'].getChild("keys_exists")
    if not isinstance(element, dict):
        raise AttributeError('keys_exists() expects dict as first argument.')
    if len(keys) == 0:
        raise AttributeError('keys_exists() expects at least two arguments, one given.')

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True

def has_key(d, path):
    """
    Checks if a nested key path, specified as a dot-separated string, exists within a dictionary.

    Parameters:
    - d (dict): The dictionary to check.
    - path (str): The dot-separated path of keys to check for existence.
    """
    _LOGGER = globals()['_LOGGER'].getChild("has_key")
    try:
        functools.reduce(lambda x, y: x[y], path.split("."), d)
        return True
    except KeyError:
        return False
    
def update_keys_recursive(obj, key_mapping):
    """
    Recursively update keys in an object (dictionary or list) that may contain nested dictionaries and lists,
    and return True if any updates were made, False otherwise.
    
    Parameters:
    - obj: The object to update, can be a dictionary or a list containing nested dictionaries.
    - key_mapping: Dict. A dictionary mapping old key names to new key names.
    
    Returns:
    - bool: True if any updates were made, False otherwise.
    """
    _LOGGER = globals()['_LOGGER'].getChild("update_keys_recursive")
    updated = False  # Flag to track if any updates are made

    if isinstance(obj, dict):
        for old_key, new_key in key_mapping.items():
            if old_key in obj:
                obj[new_key] = obj.pop(old_key)
                updated = True  # Set flag to True if a key is updated
        for value in obj.values():
            # Recursively update and check if nested dictionaries/lists are updated
            if update_keys_recursive(value, key_mapping):
                updated = True

    elif isinstance(obj, list):
        for item in obj:
            # Recursively update and check if items in the list are updated
            if update_keys_recursive(item, key_mapping):
                updated = True

    return updated

def compare_dicts_unique_to_dict1(dict1, dict2, path=""):
    """
    Compares two dictionaries and returns keys that are unique to the first dictionary, including nested structures.

    Parameters:
    - dict1 (dict): The first dictionary.
    - dict2 (dict): The second dictionary to compare against.
    - path (str): The current path, used internally for recursion.
    """
    _LOGGER = globals()['_LOGGER'].getChild("compare_dicts_unique_to_dict1")
    unique_to_dict1 = {}

    for key in dict1:
        if key not in dict2:
            unique_to_dict1[path + key] = dict1[key]
        elif isinstance(dict1[key], dict) and isinstance(dict2.get(key), dict):
            # Recursively compare nested dictionaries
            nested_unique = compare_dicts_unique_to_dict1(dict1[key], dict2.get(key, {}), path + key + ".")
            unique_to_dict1.update(nested_unique)
        elif isinstance(dict1[key], list) and isinstance(dict2.get(key), list):
            for idx, item in enumerate(dict1[key]):
                if isinstance(item, dict):
                    # Assuming dict2[key] is a list of dictionaries of the same length as dict1[key]
                    nested_unique = compare_dicts_unique_to_dict1(item, dict2[key][idx], path + key + f".{idx}.")
                    unique_to_dict1.update(nested_unique)

    return unique_to_dict1

def update_dict_with_new_keys(existing_config, new_config, unique_id_key='name', check_nested_keys=False):
    """
    Enhanced to handle lists of dictionaries, specifically for configurations like sensors.
    Assumes each dictionary in a list has a unique identifier specified by unique_id_key.

    Parameters:
    - existing_config (dict): The dictionary to be updated.
    - new_config (dict): The dictionary containing new keys and values to add or update in the existing dictionary.
    - unique_id_key (str): The key used to uniquely identify items in a list of dictionaries.

    Returns:
    - updated (bool): True if any updates were made to the existing dictionary, False otherwise.
    - existing_config (dict): The updated dictionary.
    """
    _LOGGER = globals()['_LOGGER'].getChild("update_dict_with_new_keys")
    updated = False
    for key, value in new_config.items():
        if key not in existing_config:
            existing_config[key] = value
            updated = True
        elif isinstance(value, dict):
            nested_updated, existing_config[key] = update_dict_with_new_keys(existing_config[key], value, unique_id_key)
            if check_nested_keys and key in existing_config and existing_config.get(key) != new_config.get(key):
                existing_config[key] = new_config[key]
                updated = True
            updated = updated or nested_updated
        elif isinstance(value, list):
            if not isinstance(existing_config[key], list):
                existing_config[key] = []
            list_updated = False
            for item in value:
                if isinstance(item, dict) and unique_id_key in item:
                    # Find and update the existing item with the same unique_id_key if it exists
                    found = False
                    for existing_item in existing_config[key]:
                        if isinstance(existing_item, dict) and existing_item.get(unique_id_key) == item[unique_id_key]:
                            found = True
                            nested_updated, _ = update_dict_with_new_keys(existing_item, item, unique_id_key)
                            list_updated = list_updated or nested_updated
                            break
                    if not found:
                        existing_config[key].append(item)
                        list_updated = True
            updated = updated or list_updated
    return updated, existing_config

def limit_dict_size(dct, size):
    """
    Limits the dictionary to the first X items based on insertion order.

    :param dct: The dictionary to be limited.
    :param size: The dictionary size.
    :return: A dictionary with a maximum of X key-value pairs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("limit_dict_size")
    # Convert dictionary items to a list, slice to keep the last 30 items, and convert back to dictionary
    return dict(list(dct.items())[:size])