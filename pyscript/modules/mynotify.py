'''
Add notify_entity_id to configuration.yaml
notify_entity_id: "notify.mobile_app_thomas_mobil"
'''
import datetime
import random as rand
import re

from filesystem import *
from mytime import *

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

NOTIFY_HISTORY = {}

def my_persistent_notification(message = None, title = "", persistent_notification_id = None):
    _LOGGER = globals()['_LOGGER'].getChild("my_persistent_notification")
    try:
        if service.has_service("notify", "persistent_notification"):
                if persistent_notification_id is None:
                    length_of_string = 6
                    sample_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                    persistent_notification_id = ''.join(rand.choices(sample_str, k = length_of_string))
                    
                pattern = "[^0-9a-zA-Z\s]+"
                persistent_notification_id = re.sub(pattern, "", persistent_notification_id)
                    
                service.call("notify", "persistent_notification", blocking=True,
                                    title=title,
                                    message=message,
                                    data={"notification_id": persistent_notification_id}
                                    )
        else:
            _LOGGER.warning(f"Notify service dont have notify.{entity_id} Message:'{message}' not send")
    except Exception as e:
        _LOGGER.error(f"Error in service call notify.persistent_notification: {e}")

def my_notify(message = None, title = "", data = {}, notify_list = [], admin_only = False, always = False, persistent_notification = False, persistent_notification_id = None):
    """
    Sends a notification message using the Home Assistant notification service. It supports sending
    notifications to a specific entity_ids if 'admin_only' is True and using 'notify_entity_id' from
    configuration.yaml. Messages can be prevented from being sent repeatedly within an hour unless
    'always' is True.

    Parameters:
    - message (str): The notification message to send.
    - title (str): The title of the notification.
    - admin_only (bool): If True, sends notification only to the 'notify_entity_id' specified in the configuration.
    - always (bool): If True, sends the notification even if it has been sent in the last hour.

    Note: If 'notify_entity_id' is not set or invalid, falls back to the default notify entity_ids.
    """
    _LOGGER = globals()['_LOGGER'].getChild("my_notify")
    global NOTIFY_HISTORY
    
    entity_ids = notify_list if notify_list else ["notify"]
        
    if admin_only:
        try:
            admin_entity_id = get_config("notify_entity_id")
            
            if admin_entity_id is None:
                raise("notify_entity_id is None")
            
            entity_ids = [admin_entity_id]
        except Exception as e:
            _LOGGER.error(f"Cant get notify_entity_id from configuration.yaml: {e}")
            entity_ids = notify_list if notify_list else ["notify"]

    if f"{title} {message}" in NOTIFY_HISTORY.values() and not always:
        _LOGGER.warning(f"Notify message not send, because its already been send in the last hour: '{title} {message}'")
    else:
        for entity_id in entity_ids:
            if "." in entity_id:
                entity_id = entity_id.split(".")[1]
            
            try:
                if service.has_service("notify", entity_id):
                        service.call("notify", entity_id, blocking=True,
                                            title=title,
                                            message=message,
                                            data=data)
                else:
                    _LOGGER.warning(f"Notify service dont have notify.{entity_id} Message:'{message}' not send")
            except Exception as e:
                _LOGGER.error(f"Error in service call notify.{entity_id}: {e}")
                
        if persistent_notification:
            my_persistent_notification(message = message, title = title, persistent_notification_id = persistent_notification_id)
                
        NOTIFY_HISTORY[getTime() + datetime.timedelta(minutes=60)] = f"{title} {message}"
        
def clear_old_history():
    """
    Clears old entries from the notification history that are older than an hour to prevent
    the history from indefinitely growing and to allow re-sending of notifications that
    have been previously sent more than an hour ago.
    """
    _LOGGER = globals()['_LOGGER'].getChild("clear_old_history")
    global NOTIFY_HISTORY
    clear_list = []
    for date in NOTIFY_HISTORY.keys():
        if date > getTime() + datetime.timedelta(minutes=60):
            clear_list.append(date)
            
    for item in clear_list:
        _LOGGER.info(f"Removing '{NOTIFY_HISTORY[date]}' from NOTIFY_HISTORY")
        del NOTIFY_HISTORY[item]
        
            
@time_trigger(f"cron(0 * * * *)")
def cron_clear_old_history(trigger_type=None, var_name=None, value=None):
    clear_old_history()