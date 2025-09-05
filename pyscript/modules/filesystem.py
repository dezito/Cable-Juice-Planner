__version__ = "1.0.1"
import aiofiles
import asyncio
import json
import yaml
import re
import textwrap
import sys, os, os.path

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

CONFIG_FOLDER = os.getcwd()

def get_config_folder():
    """
    Returns the current working directory asynchronously. This directory is used as the base for loading and saving configuration files.
    """
    return os.getcwd()

def add_config_folder_path(file_path):
    if CONFIG_FOLDER not in file_path:
        file_path = f"{CONFIG_FOLDER}/{file_path}"
    return file_path

def _add_ext(filename, ext_type = ""):
    """
    Ensures the filename has the specified extension. If the filename does not end async with the given extension, it appends it.

    Parameters:
    - filename (str): The name of the file.
    - ext_type (str): The extension to ensure on the filename, default is an empty string.
    
    Returns:
    - str: The filename async with the ensured extension.
    """
    try:
        ext = filename.split(".")[-1]
        if ext != ext_type:
            filename = f"{filename}.{ext_type}"
    except:
        filename = f"{filename}.{ext_type}"
    return filename
   
async def file_exists(filename=None):
    """
    Checks if a file exists at the specified path asynchronously.

    Parameters:
    - filename (str): The path to the file to check.

    Returns:
    - bool: True if the file exists, False otherwise.
    """
    _LOGGER = globals()['_LOGGER'].getChild("file_exists")
    filename = add_config_folder_path(filename)
    
    try:
        file_exists = os.path.exists(filename)
        return file_exists
    except Exception as error:
        _LOGGER.error(f"Error checking if {filename} exists: {error}")
        return False
    
async def get_file_modification_time(filename=None):
    """
    Gets the last modification time of a file asynchronously.

    Parameters:
    - filename (str): The path to the file.

    Returns:
    - float: The last modification time as a timestamp, or None if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_file_modification_time")
    filename = add_config_folder_path(filename)
    
    if file_exists(filename):
        try:
            mod_time = os.path.getmtime(filename)
            return mod_time
        except Exception as error:
            _LOGGER.error(f"Error getting modification time for {filename}: {error}")
            return None

async def load_json(filename=None):
    """
    Loads a JSON file and returns its content asynchronously.

    Parameters:
    - filename (str): The name of the JSON file to load.

    Returns:
    - dict: The content of the JSON file or an empty dictionary if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("load_json")
    filename = add_config_folder_path(_add_ext(filename, 'json'))
    
    if file_exists(filename):
        try:
            async with aiofiles.open(filename, 'r', encoding="utf-8") as f:
                content = f.read()
                return json.loads(content)
        except Exception as error:
            _LOGGER.error(f"Can't read {filename} file: {error}")
    else:
        _LOGGER.error(f"Filename does not exist {filename}")
    return {}
        

async def save_json(filename=None, db=None):
    """
    Saves a dictionary to a JSON file asynchronously.

    Parameters:
    - filename (str): The name of the JSON file to save.
    - db (dict): The dictionary to save into the file.

    Returns:
    - bool: True if the file was successfully written, False if an error occurred.
    """
    _LOGGER = globals()['_LOGGER'].getChild("save_json")
    filename = add_config_folder_path(_add_ext(filename, 'json'))
    
    try:
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            f.write(json.dumps(db, sort_keys=True, indent=4))
        return True
    except Exception as error:
        _LOGGER.error(f"Can't write {filename} file: {error}")
    return False

async def create_yaml(filename=None, db=None):
    filename = add_config_folder_path(_add_ext(filename, 'yaml'))
    if not file_exists(filename):
        save_yaml(filename, db)
        return True
    return False

async def load_yaml(filename=None):
    """
    Loads a YAML file and returns its content asynchronously. Lines containing '!include' and '!secret' are ignored for security reasons.

    Parameters:
    - filename (str): The name of the YAML file to load.

    Returns:
    - dict: The content of the YAML file or an empty dictionary if an error occurs.
    """
    _LOGGER = globals()['_LOGGER'].getChild("load_yaml")
    filename = add_config_folder_path(_add_ext(filename, 'yaml'))
    if file_exists(filename):
        try:
            async with aiofiles.open(filename, 'r', encoding="utf-8") as f:
                data = f.readlines()
                
            yaml_string = ""
            for line in data:
                if line not in ("!include","!secret"):
                    yaml_string += f"{line}"
                    
            return yaml.safe_load(yaml_string)
        except Exception as error:
            _LOGGER.error(f"Can't read {filename} file: {error}")
    else:
        _LOGGER.error(f"Filename does not exist {filename}")
    return {}

async def save_yaml(filename=None, db=None, comment_db=None, max_width=120):
    _LOGGER = globals().get('_LOGGER')
    
    filename = add_config_folder_path(_add_ext(filename, 'yaml'))

    try:
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            await f.write(yaml.dump(db, sort_keys=True, allow_unicode=True))

        if comment_db is None:
            return True

        async with aiofiles.open(filename, 'r', encoding='utf-8') as file:
            lines = await file.readlines()

        new_lines = []
        parents = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                continue

            indent = len(line) - len(line.lstrip())
            level = indent // 2

            match = re.match(r"^\s*([^\s:#]+):", line)
            if not match:
                new_lines.append(line)
                continue

            key = match.group(1)
            parents = parents[:level] + [key]
            full_key = ".".join(parents)
            comment = comment_db.get(full_key)
            if comment:
                wrapped_comment = textwrap.wrap(comment, width=max_width - indent - 4)
                comment_lines = [f"{' ' * indent}# {line}" for line in wrapped_comment]
                
                extra_indent = indent + 2
                comment_lines = [f"{' ' * extra_indent}# {line}" for line in wrapped_comment]

                line = re.sub(r" *#.*", "", line).rstrip("\n")
                new_lines.append(f"{line}\n")
                new_lines.extend([f"{c}\n" for c in comment_lines])
            else:
                new_lines.append(line)

        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            await file.writelines(new_lines)

        return True

    except Exception as error:
        _LOGGER.error(f"Can't write {filename} file: {error}")
        return False

async def get_yaml_entities(filename=None):
    """
    Parses a YAML file for entities and returns a list of entity IDs asynchronously.

    Parameters:
    - filename (str): The name of the YAML file to parse.

    Returns:
    - list: A list of entity IDs parsed from the YAML file.
    """
    output = []
    yaml_db = load_yaml(filename)
    for domain, entity_id in yaml_db.items():
        if isinstance(entity_id, dict):
            for name in entity_id.keys():
                output.append(f"{domain}.{name}")
        else:
            for template_type in entity_id:
                for template_domain in template_type.keys():
                    if template_domain != "platform":
                        for template_entity_id in template_type[template_domain]:
                            output.append(f"{domain}.{template_entity_id}")
    return output

async def get_config(key):
    """
    Fetches a specific key's value from the configuration.yaml file asynchronously.

    Parameters:
    - key (str): The key to fetch from the configuration file.

    Returns:
    - The value associated with the key or None if the key is not found.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_config")
    try:
        config = load_yaml("configuration.yaml")
        return config.get(key)
    except Exception as e:
        config = load_yaml("configuration.yaml")
        _LOGGER.error(f"{e}: {config}")
        return None

async def get_secret(key):
    """
    Fetches a specific key's value from the secrets.yaml file asynchronously.

    Parameters:
    - key (str): The key to fetch from the secrets file.

    Returns:
    - The value associated async with the key or None if the key is not found.
    """
    _LOGGER = globals()['_LOGGER'].getChild("get_secret")
    try:
        config = load_yaml("secrets.yaml")
        return config.get(key)
    except Exception as e:
        _LOGGER.error(f"Cant get secret with key {key}: {e}")