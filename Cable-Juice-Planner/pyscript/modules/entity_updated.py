__version__ = "1.0.0"
from history import *
from mynotify import *
from mytime import *
from utils import *

import datetime
from dateutil import parser

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

entities = {}

def entities_updated(lst = None, trigger = 3, timeout = 60):
    """
    Tracks updates to specified entities and triggers a service reload if an entity is considered stuck based on 
    predefined conditions. It logs information about entities meeting restart conditions and sends notifications 
    for entities potentially stuck.

    Parameters:
    - lst (list|str): A list of entity IDs or a single entity ID to monitor for updates.
    - trigger (int): The number of update intervals without change after which an entity is considered stuck.
    - timeout (int): The time in minutes to wait before checking if an entity is stuck.

    Note: This function updates a global 'entities' dictionary to track state changes and timeouts.
    """
    _LOGGER = globals()['_LOGGER'].getChild("entities_updated")
    global entities

    entity_list = []

    if type(lst) == list:
        for entity_id in lst:
            if type(entity_id) == list:
                entity_list.extend(entity_id)
            else:
                entity_list.append(entity_id)
    else:
        entity_list.append(lst)
 
    for entity_id in entities.keys():
        if entities[entity_id]["last_state"] == get_state(entity_id, try_history=False):
            _LOGGER.info(f'entity_updated: {getTime()} >= {entities[entity_id]["timeout"]} {getTime() >= entities[entity_id]["timeout"]} and {entities[entity_id]["count"]} > {entities[entity_id]["trigger"]} {entities[entity_id]["count"] > entities[entity_id]["trigger"]}  {entity_id}')
            if getTime() >= entities[entity_id]["timeout"] and entities[entity_id]["count"] > entities[entity_id]["trigger"]:
                _LOGGER.warning(f"Restarting service for entity_id: {entity_id} maybe stuck last/current state {entities[entity_id]['last_state']}/{get_state(entity_id, try_history=False)}")
                if service.has_service("homeassistant", "reload_config_entry"):
                    service.call("homeassistant", "reload_config_entry", blocking=True,
                                        entity_id=entity_id)
                my_notify(f"Genstarter service til entity_id: {entity_id} sidder måske fast sidste/nuværence værdi {entities[entity_id]['last_state']}/{get_state(entity_id, try_history=False)}", title="Enhed sidder måske fast", admin_only = True)
                entities[entity_id]["count"] = 0
                entities[entity_id]["timeout"] = getTime() + datetime.timedelta(minutes=entities[entity_id]["interval"])
            else:
                entities[entity_id]["count"] += 1
        else:
            entities[entity_id]["count"] = 0
            entities[entity_id]["timeout"] = getTime() + datetime.timedelta(minutes=entities[entity_id]["interval"])
    
    if len(entities) == 0 and not entity_list:
        return
    elif entity_list:
        for entity_id in entity_list:
            if entity_id is None:
                continue
            entities[entity_id] = {
                "last_state": get_state(entity_id, try_history=False),
                "count": 0,
                "trigger": 0,
                "interval": timeout,
                "timeout": getTime() + datetime.timedelta(minutes=timeout)
            }
    _LOGGER.info(f"entity_updated: {entities}")
        
@time_trigger("startup")
@time_trigger(f"cron(0/10 * * * *)")
def cron_entity_updated(trigger_type=None, var_name=None, value=None):
    entities_updated()