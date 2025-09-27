__version__ = "1.0.1"
import aiofiles
import asyncio
import json
import yaml
import re
import textwrap
import sys, os, os.path, tempfile

from typing import Optional, Dict, Any

_FILE_LOCKS: Dict[str, asyncio.Lock] = {}

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

CONFIG_FOLDER = os.getcwd()

def _get_lock(path: str) -> asyncio.Lock:
    lock = _FILE_LOCKS.get(path)
    if lock is None:
        lock = asyncio.Lock()
        _FILE_LOCKS[path] = lock
    return lock

def _atomic_write_text(path: str, text: str, mode: int = 0o666) -> None:
    """
    Atomically write text to a file:
    - Write to a temporary file
    - Flush + fsync
    - Replace the original file in one operation
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="._tmp_", suffix=".yaml", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)  # atomic swap
        os.chmod(path, mode) # set file mode
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

def get_config_folder():
    """
    Returns the current working directory asynchronously. This directory is used as the base for loading and saving configuration files.
    """
    return CONFIG_FOLDER

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
        if "." not in filename:
            filename = f"{filename}.{ext_type}"
            return filename
        
        ext = filename.split(".")[-1]
        
        if ext != ext_type:
            filename = f"{filename}.{ext_type}"
    except Exception as e:
        _LOGGER.error(f"Error adding extension {ext_type} to filename {filename}: {e}")
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

async def load_json(filename: Optional[str] = None, retries: int = 10, sleep_seconds: float = 1.0) -> Dict[str, Any]:
    """
    Loads a JSON file and returns its content asynchronously.

    Parameters:
    - filename (str): The name of the JSON file to load.
    - retries (int): Number of retries if file is temporarily locked.
    - sleep_seconds (float): Delay between retries.

    Returns:
    - dict: The JSON content, or {} on error.
    """
    _LOGGER = globals()['_LOGGER'].getChild("load_json")
    filename = add_config_folder_path(_add_ext(filename, "json"))

    if not file_exists(filename):
        _LOGGER.error(f"Filename does not exist {filename}")
        return {}

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            async with aiofiles.open(filename, "r", encoding="utf-8") as f:
                content = await f.read()

            if not content.strip():
                return {}

            return json.loads(content)

        except (PermissionError, OSError) as e:
            last_exc = e
            _LOGGER.warning(f"Retry {attempt}/{retries}: file {filename} locked ({e}); sleeping {sleep_seconds}s")
            await asyncio.sleep(sleep_seconds)
        except json.JSONDecodeError as e:
            _LOGGER.error(f"JSON parse error in {filename}: {e}")
            return {}
        except Exception as e:
            _LOGGER.error(f"Can't read {filename} file: {e}")
            return {}

    _LOGGER.error(f"Can't read {filename} after {retries} retries: {last_exc}")
    return {}

async def create_json(filename=None, db=None):
    filename = add_config_folder_path(_add_ext(filename, 'yaml'))
    if not file_exists(filename):
        save_json(filename, db)
        return True
    return False

async def save_json(filename: Optional[str] = None, db: Optional[Dict[str, Any]] = None) -> bool:
    """
    Saves a dictionary to a JSON file asynchronously (atomically, without comment injection).

    Parameters:
    - filename (str): The JSON file to save.
    - db (dict): The dictionary to save into the file.

    Returns:
    - bool: True if successful, False otherwise.
    """
    _LOGGER = globals()['_LOGGER'].getChild("save_json")
    try:
        if db is None or not isinstance(db, dict):
            raise ValueError("db must be a dict")

        path = add_config_folder_path(_add_ext(filename, "json"))
        text = json.dumps(db, sort_keys=True, indent=4)

        # Run atomic write in thread to avoid blocking event loop
        await asyncio.to_thread(_atomic_write_text, path, text)
        return True
    except Exception as error:
        _LOGGER.error(f"Can't write {filename} file: {error}")
        return False

def _inject_comments(lines: list[str], comment_db: Dict[str, str], max_width: int) -> list[str]:
    """
    Insert comments after key lines based on dot-paths found in comment_db.
    Works fully in memory (no file I/O).
    """
    new_lines: list[str] = []
    parents: list[str] = []
    key_re = re.compile(r"^(\s*)([^:\n]+):")

    for line in lines:
        stripped = line.strip()
        # Keep empty lines or existing comments unchanged
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        m = key_re.match(line)
        if not m:
            new_lines.append(line)
            continue

        indent_spaces, raw_key = m.groups()
        indent = len(indent_spaces)
        level = indent // 2  # yaml.safe_dump uses 2 spaces by default

        # Normalize key (strip quotes if present)
        key = raw_key.strip().strip("'\"")
        parents = parents[:level] + [key]
        full_key = ".".join(parents)

        # Write the original line without trailing inline comments
        clean_line = re.sub(r"\s+#.*$", "", line).rstrip("\n")
        new_lines.append(clean_line + "\n")

        # Add comment lines if available
        comment = comment_db.get(full_key)
        if comment:
            wrap_width = max(20, max_width - indent - 4)
            wrapped = textwrap.wrap(comment, width=wrap_width, break_long_words=False)
            extra_indent = indent + 2
            for w in wrapped:
                new_lines.append(f"{' ' * extra_indent}# {w}\n")

    return new_lines

async def create_yaml(filename=None, db=None):
    filename = add_config_folder_path(_add_ext(filename, 'yaml'))
    if not file_exists(filename):
        save_yaml(filename, db)
        return True
    return False

async def load_yaml(filename: Optional[str] = None, retries: int = 10, sleep_seconds: float = 1.0) -> Dict[str, Any]:
    """
    Loads a YAML file and returns its content asynchronously.
    Lines starting with '!include' and '!secret' are ignored.

    Parameters:
    - filename (str): The YAML file to load.
    - retries (int): Number of retries if file is temporarily locked.
    - sleep_seconds (float): Delay between retries.

    Returns:
    - dict: The YAML content, or {} on error.
    """
    _LOGGER = globals()['_LOGGER'].getChild("load_yaml")
    filename = add_config_folder_path(_add_ext(filename, 'yaml'))

    if not file_exists(filename):
        _LOGGER.error(f"Filename does not exist {filename}")
        return {}

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            async with aiofiles.open(filename, "r", encoding="utf-8") as f:
                lines = await f.readlines()

            yaml_string = ""
            for line in lines:
                # ignore only if line starts with !include / !secret
                if line.strip().startswith(("!include", "!secret")):
                    continue
                yaml_string += line

            return yaml.safe_load(yaml_string) or {}

        except (PermissionError, OSError) as e:
            last_exc = e
            _LOGGER.warning(f"Retry {attempt}/{retries}: file {filename} locked ({e})")
            await asyncio.sleep(sleep_seconds)
        except yaml.YAMLError as e:
            _LOGGER.error(f"YAML parse error in {filename}: {e}")
            return {}
        except Exception as e:
            _LOGGER.error(f"Can't read {filename} file: {e}")
            return {}

    _LOGGER.error(f"Can't read {filename} after {retries} retries: {last_exc}")
    return {}

async def save_yaml(
    filename: Optional[str] = None,
    db: Optional[Dict[str, Any]] = None,
    comment_db: Optional[Dict[str, str]] = None,
    max_width: int = 120,
):
    """
    Save a dictionary as YAML safely and atomically, with optional inline comments.
    
    Features:
    - Full content is built in memory
    - Atomic write (temp file + replace)
    - Per-file async lock to avoid concurrent writes
    - Protects against asyncio cancellation mid-write
    - Optionally injects comments from comment_db after keys
    
    Returns:
        True if successful, False on error.
    """
    _LOGGER = globals()['_LOGGER'].getChild("save_yaml")
    try:
        if db is None:
            raise ValueError("db must not be None")
        if not isinstance(db, dict):
            raise TypeError("db must be a dict")
        if comment_db is not None and not isinstance(comment_db, dict):
            raise TypeError("comment_db must be a dict or None")

        path = add_config_folder_path(_add_ext(filename, "yaml"))

        # --- Serialize YAML in memory ---
        try:
            text = yaml.safe_dump(
                db,
                sort_keys=True,
                allow_unicode=True,
                default_flow_style=False,
                indent=2,
            )
        except Exception as e:
            raise RuntimeError(f"YAML serialization failed: {e}") from e

        if not text.strip():
            raise RuntimeError("Refusing to write empty YAML content")

        # --- Inject comments in memory ---
        if comment_db:
            lines = text.splitlines(keepends=True)
            new_lines = _inject_comments(lines, comment_db, max_width)
            text = "".join(new_lines)

        # --- explicit lock/unlock with finally ---
        lock = _get_lock(path)
        acquired = False
        try:
            await lock.acquire()
            acquired = True
            await asyncio.shield(asyncio.to_thread(_atomic_write_text, path, text))
            return True
        except Exception as error:
            if _LOGGER:
                _LOGGER.error(f"Can't write YAML file: {error}")
            return False
        finally:
            if acquired:
                lock.release()

        return True

    except asyncio.CancelledError:
        if _LOGGER:
            _LOGGER.warning("save_yaml was cancelled; file left unchanged (atomic write).")
        raise
    except Exception as error:
        if _LOGGER:
            _LOGGER.error(f"Can't write YAML file: {error}")
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

@time_trigger("shutdown")
def shutdown(trigger_type=None, var_name=None, value=None, old_value=None):
    _LOGGER = globals()['_LOGGER'].getChild("shutdown")
    for key, lock in _FILE_LOCKS.items():
        if lock.locked():
            _LOGGER.warning(f"File lock for {key} is still held at shutdown")
            lock.release()