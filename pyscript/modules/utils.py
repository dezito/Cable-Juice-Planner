__version__ = "1.0.0"
import datetime
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

def calculate_ema(data, span=5):
    """
    Calculates the Exponential Moving Average (EMA) of a list of numbers.
    """
    ema_values = []
    alpha = 2 / (span + 1)
    ema = data[0]
    for value in data:
        ema = (value * alpha) + (ema * (1 - alpha))
        ema_values.append(ema)
    return ema_values[-1]

def calculate_trend(data):
    """
    Calculates the trend of a list of numbers.
    """
    x = list(range(len(data)))
    n = len(x)

    sum_x = 0
    sum_y = 0
    sum_x_squared = 0
    sum_xy = 0

    for i in x:
        sum_x += i
        sum_x_squared += i ** 2

    for i, j in zip(x, data):
        sum_y += j
        sum_xy += i * j

    denominator = (n * sum_x_squared - sum_x ** 2)
    if denominator == 0:
        return data[-1]

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    return intercept + slope * len(data)

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

def get_dict_value_with_path(d, path):
    """
    Retrieves the value from a dictionary based on a given path.
    Parameters:
        d (dict): The dictionary to retrieve the value from.
        path (str): The path to the value in dot notation.
    Returns:
        The value from the dictionary at the specified path.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_dict_value_with_path")
    
    keys = path.split('.')
    for key in keys:
        if key.isdigit():
            key = int(key)
            d = d[key]
        elif key in d:
            d = d[key]
        else:
            return
    return d

def set_dict_value_with_path(d, path, value):
    """
    Sets the value of a nested dictionary given a path.
    Args:
        d (dict): The dictionary to modify.
        path (str): The path to the value, using dot notation.
        value: The value to set.
    Returns:
        dict: The modified dictionary.
    Example:
        >>> d = {'a': {'b': {'c': 1}}}
        >>> set_dict_value_with_path(d, 'a.b.c', 2)
        {'a': {'b': {'c': 2}}}
    """
    _LOGGER = globals()['_LOGGER'].getChild("set_dict_value_with_path")
    
    keys = path.split('.')
    current = d
    for i, key in enumerate(keys):
        if key.isdigit():
            key = int(key)
            if i == len(keys) - 1:
                current[key] = value
            else:
                if key >= len(current):
                    current.extend([{}] * (key + 1 - len(current)))
                if not isinstance(current[key], (dict, list)):
                    current[key] = {}
                current = current[key]
        else:
            if i == len(keys) - 1:
                current[key] = value
            else:
                if key not in current or not isinstance(current[key], (dict, list)):
                    current[key] = {} if not keys[i + 1].isdigit() else []
                current = current[key]
    return d

def delete_dict_key_with_path(d, path):
    """
    Deletes a key from a nested dictionary based on the given path.
    Args:
        d (dict): The nested dictionary.
        path (str): The path to the key in dot notation.
    Returns:
        dict: The modified dictionary with the key removed.
    Example:
        >>> d = {'a': {'b': {'c': 1}}}
        >>> path = 'a.b.c'
        >>> delete_dict_key_with_path(d, path)
        {'a': {'b': {}}}
    """
    _LOGGER = globals()['_LOGGER'].getChild("delete_dict_key_with_path")
    
    keys = path.split('.')
    current = d

    for i, key in enumerate(keys[:-1]):  # Iterate up to the second last key
        if key.isdigit():
            key = int(key)
            if isinstance(current, list) and 0 <= key < len(current):
                current = current[key]
            else:
                return d
        elif isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return d

    last_key = keys[-1]
    if isinstance(current, dict) and last_key in current:
        del current[last_key]
    elif isinstance(current, list) and last_key.isdigit():
        last_key = int(last_key)
        if 0 <= last_key < len(current):
            del current[last_key]

    return d

def rename_dict_keys(d, keys_renaming, remove_old_keys=False):
    """
    Renames keys in a dictionary based on a given mapping.
    Args:
        d (dict): The dictionary to modify.
        keys_renaming (dict): A dictionary mapping old keys to new keys.
        remove_old_keys (bool, optional): Whether to remove the old keys from the dictionary. Defaults to False.
    Returns:
        dict: The modified dictionary with renamed keys.
    """
    _LOGGER = globals()['_LOGGER'].getChild("rename_dict_keys")
    
    for old_path, new_path in keys_renaming.items():
        old_value = get_dict_value_with_path(d, old_path)
        if old_value is not None:
            d = set_dict_value_with_path(d, new_path, old_value)
            if remove_old_keys:
                d = delete_dict_key_with_path(d, old_path)
    return d

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

def update_dict_with_new_keys(existing_config, default_config):
    changed = False

    def recursive_add(saved, default):
        """ Rekursiv funktion til at tilføje manglende keys uden at ændre eksisterende værdier. """
        nonlocal changed

        if isinstance(default, dict):
            if not isinstance(saved, dict):
                saved = {}
            for key, value in default.items():
                if key not in saved:
                    saved[key] = value
                    changed = True
                else:
                    saved[key] = recursive_add(saved[key], value)

        elif isinstance(default, list):
            if not isinstance(saved, list):
                saved = []
            
            default_dicts = [item for item in default if isinstance(item, dict)]
            saved_dicts = [item for item in saved if isinstance(item, dict)]

            for default_item in default_dicts:
                platform = default_item.get("platform")
                found = False

                for saved_item in saved_dicts:
                    if saved_item.get("platform") == platform:
                        recursive_add(saved_item, default_item)
                        found = True
                        break

                if not found:
                    saved.append(default_item)
                    changed = True

            for default_item in default:
                if not isinstance(default_item, dict) and default_item not in saved:
                    saved.append(default_item)
                    changed = True

        return saved

    updated_config = recursive_add(existing_config, default_config)

    return changed, updated_config

def limit_dict_size(dct, size):
    """
    Limits the dictionary to the last X items based on insertion order.

    :param dct: The dictionary to be limited.
    :param size: The dictionary size.
    :return: A dictionary with a maximum of X key-value pairs, keeping the newest.
    """
    _LOGGER = globals()['_LOGGER'].getChild("limit_dict_size")
    
    # Konverter dictionary til en liste, behold kun de nyeste X elementer, og lav det tilbage til en dictionary
    return dict(list(dct.items())[-size:])

def contains_any(first, second):
    """
    Checks if at least one element from 'first' exists in 'second'.
    Uses set operations for efficiency.
    """
    # Convert both inputs to sets
    first_set = set(first) if not isinstance(first, str) else {first}
    second_set = set(second) if not isinstance(second, str) else {second}

    # Check if there's any intersection
    return bool(first_set & second_set)


def check_next_24_hours_diff(dict1, dict2):
    now = datetime.datetime.now()
    end_time = now + datetime.timedelta(hours=24)

    keys1 = {key for key in dict1 if isinstance(key, datetime.datetime) and now <= key < end_time}
    keys2 = {key for key in dict2 if isinstance(key, datetime.datetime) and now <= key < end_time}

    only_in_dict1 = keys1 - keys2
    only_in_dict2 = keys2 - keys1

    if not only_in_dict1 and not only_in_dict2:
        return {}

    return {
        'only_in_dict1': list(only_in_dict1),
        'only_in_dict2': list(only_in_dict2)
    }