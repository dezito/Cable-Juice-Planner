"""
Home Assistant integration requirement:
    - Pyscript: Python Scripting for Home Assistant
        - Allow All Imports - Enabled
        - Access hass as a global variable - Enabled
    - Config: forecast.entity_ids.daily_service_entity_id = AccuWeather entity
    - Config: forecast.entity_ids.hourly_service_entity_id = OpenWeatherMap entity
    - Energi Data Service
    - Easee EV charger
    - Sun
"""

import datetime
from pprint import pformat

try:
    from benchmark import start_benchmark, end_benchmark, benchmark_decorator
    benchmark_loaded = True
except:
    benchmark_loaded = False

from filesystem import file_exists, create_yaml, load_yaml, save_yaml
from hass_manager import get_state, get_attr, set_state, set_attr, get_manufacturer, get_identifiers, get_integration, reload_integration
from history import get_values, get_average_value, get_max_value, get_min_value
from mynotify import my_notify
from mytime import getTime, getTimePlusDays, daysBetween, hoursBetween, minutesBetween, getMinute, getHour, getMonth, getYear, getTimeStartOfDay, getTimeEndOfDay, getDayOfWeekText, date_to_string, toDateTime, resetDatetime, reset_time_to_hour
from utils import in_between, round_up, average, get_specific_values, get_closest_key, update_keys_recursive, compare_dicts_unique_to_dict1, update_dict_with_new_keys, limit_dict_size

import homeassistant.helpers.sun as sun

from logging import getLogger
BASENAME = f"pyscript.{__name__}"
_LOGGER = getLogger(BASENAME)


INITIALIZATION_COMPLETE = False
TESTING = False
PREHEATING = False

EV_CONFIGURED = None
SOLAR_CONFIGURED = None
POWERWALL_CONFIGURED = None

USING_OFFLINE_PRICES = False

CHARGING_IS_BEGINNING = False
RESTARTING_CHARGER = False
RESTARTING_CHARGER_COUNT = 0
CURRENT_CHARGING_AMPS = [0, 0, 0]

CHARGING_LOSS_CAR_BEGIN_KWH = 0.0
CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL = 0.0
CHARGING_LOSS_CHARGER_BEGIN_KWH = 0.0
CHARGING_LOSS_CHARGING_COMPLETED = False

CHARGING_ALLOWED_AFTER_GOTO_TIME = -120 #Negative value in minutes

CHARGING_NO_RULE_COUNT = 0
ERROR_COUNT = 0

LAST_WAKE_UP_DATETIME = resetDatetime()
LAST_TRIP_CHANGE_DATETIME = getTime()

CONFIG = {}
SOLAR_PRODUCTION_AVAILABLE_DB = {}
KWH_AVG_PRICES_DB = {}
DRIVE_EFFICIENCY_DB = []
KM_KWH_EFFICIENCY_DB = []
CHARGING_HISTORY_DB = {}
CHEAP_GRID_CHARGE_HOURS_DICT = {}

SOLAR_SELL_TARIFF = {
    "energinets_network_tariff": 0.0030,
    "energinets_balance_tariff": 0.0024,
    "solar_production_seller_cut": 0.01
}

CHARGING_HISTORY_RUNNING = False
CHARGING_HISTORY_QUEUE = []
EV_SEND_COMMAND_QUEUE = []

CURRENT_CHARGING_SESSION = {}
WEATHER_CONDITION_DICT = {
    "sunny": 0,                # Maximum solar production
    "windy": 25,               # Minimal effect on solar production unless cloudy
    "windy-variant": 25,       # Similar to windy
    "partlycloudy": 50,        # Slightly reduced solar production
    "cloudy": 75,              # Moderately reduced solar production
    "rainy": 75,               # Moderate reduction in solar production
    "pouring": 75,             # Significant reduction in solar production
    "lightning": 75,           # Reduced solar production due to cloud coverage
    "lightning-rainy": 75,     # Significantly reduced solar production
    "snowy": 75,               # Snow can obstruct panels significantly
    "snowy-rainy": 75,         # Combined effect of snow and rain
    "clear-night": 100,        # No solar production
    "fog": 100,                # Severely reduced visibility and solar production
    "hail": 100,               # Potential zero production during hail
    "exceptional": 100         # Extreme weather conditions with no production
}

INTEGRATION_DAILY_LIMIT_BUFFER = 50
ENTITY_INTEGRATION_DICT = {
    "supported_integrations": {
        "kia_uvo": {"daily_limit": 200},
        "monta": {"daily_limit": 144000},
        "tesla": {"daily_limit": 200},
        "tessie": {"daily_limit": 500}
    },
    "entities": {},
    "commands_last_hour": {},
    "last_reload": {},
    "counter": {}
}

CHARGING_TYPES = {
    "error": {
        "priority": 1,
        "emoji": "☠️",
        "description": "Kritisk fejl, nød ladning"
    },
    "no_rule": {
        "priority": 2,
        "emoji": "⚠️",
        "description": "Lading uden grund"
    },
    "manual": {
        "priority": 3,
        "emoji": "🔌",
        "description": "Manuel ladning"
    },
    "low_battery": {
        "priority": 4,
        "emoji": "⛽",
        "description": "Tvangsladning under daglig batteri niveau"
    },
    "battery_health": {
        "priority": 5,
        "emoji": "🔋",
        "description": "Anbefalet fuld ladning"
    },
    "trip": {
        "priority": 6,
        "emoji": "🌍",
        "description": "Tur ladning / afgang"
    },
    "first_workday_preparation": {
        "priority": 7.0,
        "emoji": "1️⃣",
        "description": "Første arbejdsdag"
    },
    "second_workday_preparation": {
        "priority": 7.1,
        "emoji": "2️⃣",
        "description": "Anden arbejdsdag"
    },
    "third_workday_preparation": {
        "priority": 7.2,
        "emoji": "3️⃣",
        "description": "Tredje arbejdsdag"
    },
    "fourth_workday_preparation": {
        "priority": 7.3,
        "emoji": "4️⃣",
        "description": "Fjerde arbejdsdag"
    },
    "fifth_workday_preparation": {
        "priority": 7.4,
        "emoji": "5️⃣",
        "description": "Femte arbejdsdag"
    },
    "sixth_workday_preparation": {
        "priority": 7.5,
        "emoji": "6️⃣",
        "description": "Sjette arbejdsdag"
    },
    "seventh_workday_preparation": {
        "priority": 7.6,
        "emoji": "7️⃣",
        "description": "Syvende arbejdsdag"
    },
    "fill_up": {
        "priority": 8,
        "emoji": "💴",
        "description": "1., 4. & 7. dag opfyldning"
    },
    "under_min_avg_price": {
        "priority": 9.0,
        "emoji": "💵",
        "description": f"Under gennemsnit pris sidste 14 dage",
        "entity_name": f"{__name__}_charge_very_cheap_battery_level"
    },
    "half_min_avg_price": {
        "priority": 9.1,
        "emoji": "💶",
        "description": f"25% under gennemsnit pris sidste 14 dage",
        "entity_name": f"{__name__}_charge_ultra_cheap_battery_level"
    },
    "solar": {
        "priority": 10,
        "emoji": "☀️",
        "description": "Solcelle ladning / overproduktion"
    },
    "charging_loss": {
        "priority": 95,
        "emoji": "🤖",
        "description": "Kalkulering af ladetab"
    },
    "sunrise": {
        "priority": 96,
        "emoji": "🌅",
        "description": "Solopgang"
    },
    "sunset": {
        "priority": 97,
        "emoji": "🌇",
        "description": "Solnedgang"
    },
    "goto": {
        "priority": 98,
        "emoji": "🚗",
        "description": "Afgang"
    },
    "homecoming": {
        "priority": 99,
        "emoji": "🏠",
        "description": "Hjemkomst"
    },
    "charging_problem": {
        "priority": 100,
        "emoji": "❗",
        "description": "Ladning problemer"
    },
    "charging_error": {
        "priority": 101,
        "emoji": "❌",
        "description": "Ladning fejlede helt"
    }
}

ENTITIES_RENAMING = {
    f"{__name__}_allow_guest_charging_now": f"{__name__}_allow_manual_charging_now",
    f"{__name__}_allow_guest_charging_solar": f"{__name__}_allow_manual_charging_solar"
}

DEFAULT_CONFIG = {
    "charger": {
        "entity_ids": {
            "status_entity_id": "",
            "power_consumtion_entity_id": "",
            "kwh_meter_entity_id": "",
            "lifetime_kwh_meter_entity_id": "",
            "enabled_entity_id": "",
            "dynamic_circuit_limit": "",
            "co2_entity_id": "",
            "cable_connected_entity_id": "",
            "start_stop_charging_entity_id": ""
        },
        "power_voltage": 240.0,
        "charging_phases": 3.0,
        "charging_max_amp": 16.0,
        "charging_loss": 0.0,
    },
    "cron_interval": 5,
    "database": {
        "solar_available_db_data_to_save": 10,
        "kwh_avg_prices_db_data_to_save": 15,
        "drive_efficiency_db_data_to_save": 15,
        "km_kwh_efficiency_db_data_to_save": 15,
        "charging_history_db_data_to_save": 6
    },
    "ev_car": {
        "entity_ids": {
            "wake_up_entity_id": "",
            "climate_entity_id": "",
            "odometer_entity_id": "",
            "estimated_battery_range_entity_id": "",
            "usable_battery_level_entity_id": "",
            "charge_port_door_entity_id": "",
            "charge_cable_entity_id": "",
            "charge_switch_entity_id": "",
            "charging_limit_entity_id": "",
            "charging_amps_entity_id": "",
            "location_entity_id": "",
            "last_update_entity_id": ""
        },
        "battery_size": 75.0,
        "min_daily_battery_level": 30.0,
        "min_trip_battery_level": 25.0,
        "min_charge_limit_battery_level": 50.0,
        "max_recommended_charge_limit_battery_level": 90.0,
        "very_cheap_grid_charging_max_battery_level": 70.0,
        "ultra_cheap_grid_charging_max_battery_level": 90.0,
        "daily_drive_distance": 100.0,
    },
    "first_run": True,
    "forecast": {
        "entity_ids": {
            "hourly_service_entity_id": "",
            "daily_service_entity_id": "",
            "outdoor_temp_entity_id": ""
        }
    },
    "home": {
        "entity_ids": {
            "power_consumption_entity_id": "",
            "powerwall_watt_flow_entity_id": "",
            "ignore_consumption_from_entity_ids": []
        },
    },
    "notify_list": [],
    "prices": {
        "entity_ids": {
            "power_prices_entity_id": ""
        },
        "refund": 0.0
        
    },
    "solar": {
        "entity_ids": {
            "production_entity_id": ""
        },
        "solarpower_use_before_minutes": 60,
        "max_to_current_hour": True,
        "allow_grid_charging_above_solar_available": -100.0,
        "charging_single_phase_min_amp": 6.0,
        "charging_single_phase_max_amp": 16.0,
        "charging_three_phase_min_amp": 5.0,
        "production_price": 0.88
    },
    "testing_mode": False
}

CONFIG_KEYS_RENAMING = {
    "ignore_consumption_from_entity_id": "ignore_consumption_from_entity_ids"
}

DEFAULT_ENTITIES = {
   "input_button":{
       f"{__name__}_trip_reset":{
           "name":"Nulstil tur ladning",
           "icon":"mdi:restore"
      },
      f"{__name__}_enforce_planning":{
          "name":"Gennemtving planlægning",
          "icon":"mdi:calendar-refresh"
      },
      f"{__name__}_restart_script":{
          "name":"Genstart scriptet",
          "icon":"mdi:restart"
      }
   },
   "input_boolean":{
      f"{__name__}_debug_log":{
          "name":f"{__name__}.py debug log"
      },
      f"{__name__}_forced_charging_daily_battery_level":{
          "name":"Tvangsladning under daglig batteri niveau",
          "icon":"mdi:battery-charging-low"
      },
      f"{__name__}_allow_manual_charging_now":{
          "name":"Tillad manuel ladning nu"
      },
      f"{__name__}_allow_manual_charging_solar":{
          "name":"Tillad manuel ladning kun på sol"
      },
      f"{__name__}_fill_up":{
          "name":"Auto opladning til maks anbefalet"
      },
      f"{__name__}_days_to_charge":{
          "name":"Arbejde auto ladning"
      },
      f"{__name__}_trip_charging":{
          "name":"Tur ladning"
      },
      f"{__name__}_trip_preheat":{
          "name":"Tur ladning forvarm bilen"
      },
      f"{__name__}_workday_monday":{
          "name":"Mandag arbejdsdag"
      },
      f"{__name__}_workday_tuesday":{
          "name":"Tirsdag arbejdsdag"
      },
      f"{__name__}_workday_wednesday":{
          "name":"Onsdag arbejdsdag"
      },
      f"{__name__}_workday_thursday":{
          "name":"Torsdag arbejdsdag"
      },
      f"{__name__}_workday_friday":{
          "name":"Fredag arbejdsdag"
      },
      f"{__name__}_workday_saturday":{
          "name":"Lørdag arbejdsdag"
      },
      f"{__name__}_workday_sunday":{
          "name":"Søndag arbejdsdag"
      },
      f"{__name__}_preheat_monday":{
          "name":"Mandag forvarm bilen"
      },
      f"{__name__}_preheat_tuesday":{
          "name":"Tirsdag forvarm bilen"
      },
      f"{__name__}_preheat_wednesday":{
          "name":"Onsdag forvarm bilen"
      },
      f"{__name__}_preheat_thursday":{
          "name":"Torsdag forvarm bilen"
      },
      f"{__name__}_preheat_friday":{
          "name":"Fredag forvarm bilen"
      },
      f"{__name__}_preheat_saturday":{
          "name":"Lørdag forvarm bilen"
      },
      f"{__name__}_preheat_sunday":{
          "name":"Søndag forvarm bilen"
      },
      f"{__name__}_calculate_charging_loss":{
          "name":"Kalkulere ladetab",
          "icon": "mdi:power-plug-battery"
      }
   },
   "input_number":{
      f"{__name__}_co2_emitted":{
          "name":"CO₂ udledt",
          "min":0,
          "max":999999,
          "step":0.001,
          "icon":"mdi:molecule-co2",
          "unit_of_measurement":"kg",
          "mode": "box"
      },
      f"{__name__}_kwh_charged_by_solar":{
          "name":"kWh ladet af solcellerne",
          "min":0,
          "max":999999,
          "step":0.01,
          "icon":"mdi:white-balance-sunny",
          "unit_of_measurement":"kWh",
          "mode": "box"
      },
      f"{__name__}_solar_sell_fixed_price":{
          "name":"Solcelle fast salgspris",
          "min":-1,
          "max":2,
          "step":0.01,
          "icon":"mdi:cash-multiple",
          "unit_of_measurement":"DKK/kWh"
      },
      f"{__name__}_preheat_minutes_before":{
          "name":"Forvarm bilen X min før",
          "min":0,
          "max":60,
          "step":5,
          "unit_of_measurement":"min"
      },
      f"{__name__}_days_to_charge_range":{
          "name":"Daglig afstand",
          "min":0,
          "max":500,
          "step":5,
          "mode":"box",
          "unit_of_measurement":"km"
      },
      f"{__name__}_min_daily_battery_level":{
          "name":"Daglig hjemkomst batteri niveau",
          "min":10,
          "max":100,
          "step":5,
          "mode":"box",
          "unit_of_measurement":"%",
          "icon":"mdi:percent-outline"
      },
      f"{__name__}_min_trip_battery_level":{
          "name":"Tur hjemkomst batteri niveau",
          "min":10,
          "max":100,
          "step":5,
          "mode":"box",
          "unit_of_measurement":"%",
          "icon":"mdi:percent-outline"
      },
      f"{__name__}_min_charge_limit_battery_level":{
          "name":"Elbilens minimum ladingsprocent",
          "min":10,
          "max":100,
          "step":5,
          "mode":"box",
          "unit_of_measurement":"%",
          "icon":"mdi:percent-outline"
      },
      f"{__name__}_max_recommended_charge_limit_battery_level":{
          "name":"Elbilens maks anbefalet ladingsprocent",
          "min":10,
          "max":100,
          "step":5,
          "mode":"box",
          "unit_of_measurement":"%",
          "icon":"mdi:percent-outline"
      },
      f"{__name__}_very_cheap_grid_charging_max_battery_level":{
          "name":"Ladingsprocent ved billig strøm",
          "min":10,
          "max":100,
          "step":5,
          "mode":"box",
          "unit_of_measurement":"%",
          "icon":"mdi:sale"
      },
      f"{__name__}_ultra_cheap_grid_charging_max_battery_level":{
          "name":"Ladingsprocent ved meget billig strøm",
          "min":10,
          "max":100,
          "step":5,
          "mode":"box",
          "unit_of_measurement":"%",
          "icon":"mdi:sale-outline"
      },
      f"{__name__}_battery_level":{
          "name": "Virtuel elbil batteri niveau",
          "min": 0,
          "max": 100,
          "step": 1,
          "unit_of_measurement": "%",
          "icon": "mdi:battery-high",
          "mode": "box"
      },
      f"{__name__}_completed_battery_level":{
          "name": "Elbil lading færdig batteri niveau",
          "min": 0,
          "max": 100,
          "step": 1,
          "unit_of_measurement": "%",
          "icon": "mdi:battery-high",
          "mode": "box"
      },
      f"{__name__}_estimated_total_range":{
          "name": "Elbil max rækkevidde",
          "min": 0,
          "max": 1000,
          "step": 1,
          "unit_of_measurement": "km",
          "icon": "mdi:map-marker-distance",
          "mode": "box"
      },
      f"{__name__}_trip_charge_procent":{
          "name": "Tur ladning til",
          "min": 0,
          "max": 100,
          "step": 5,
          "unit_of_measurement": "%",
          "icon": "mdi:percent-outline"
      },
      f"{__name__}_trip_range_needed":{
          "name": "Tur km forbrug",
          "min": 0,
          "max": 1000,
          "step": 5,
          "unit_of_measurement": "km",
          "icon": "mdi:map-marker-distance"
      },
      f"{__name__}_full_charge_recommended":{
          "name":"Anbefalet fuld ladning hver",
          "min": 0,
          "max": 60,
          "step": 1,
          "unit_of_measurement": "dag(e)",
          "icon": "mdi:battery-heart"
      }
   },
   "input_datetime":{
      f"{__name__}_days_to_charge_monday":{
          "name":"Mandag afgang",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_days_to_charge_tuesday":{
          "name":"Tirsdag afgang",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_days_to_charge_wednesday":{
          "name":"Onsdag afgang",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_days_to_charge_thursday":{
          "name":"Torsdag afgang",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_days_to_charge_friday":{
          "name":"Fredag afgang",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_days_to_charge_saturday":{
          "name":"Lørdag afgang",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_days_to_charge_sunday":{
          "name":"Søndag afgang",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_monday_homecoming":{
          "name":"Mandag hjemkomst",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_tuesday_homecoming":{
          "name":"Tirsdag hjemkomst",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_wednesday_homecoming":{
          "name":"Onsdag hjemkomst",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_thursday_homecoming":{
          "name":"Torsdag hjemkomst",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_friday_homecoming":{
          "name":"Fredag hjemkomst",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_saturday_homecoming":{
          "name":"Lørdag hjemkomst",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_sunday_homecoming":{
          "name":"Søndag hjemkomst",
          "has_date":False,
          "has_time":True
      },
      f"{__name__}_trip_date_time":{
          "name":"Elbil Tur afgang",
          "has_date":True,
          "has_time":True
      },
      f"{__name__}_trip_homecoming_date_time":{
          "name":"Elbil Tur hjemkomst",
          "has_date":True,
          "has_time":True
      },
      f"{__name__}_last_full_charge":{
          "name":"Sidste fulde opladning",
          "has_date":True,
          "has_time":True
      },
   },
   "sensor":[
      {
          "platform":"template",
          "sensors":{
            f"{__name__}_solar_over_production_current_hour":{
               "friendly_name":"Solcelle produktion tilrådighed i nuværende time",
               "unit_of_measurement":"W",
               "value_template":"unavailable"
            },
            f"{__name__}_solar_charged_percentage":{
               "friendly_name":"Solcelle ladning",
               "unit_of_measurement":"%",
               "value_template":"unavailable"
            },
            f"{__name__}_drive_efficiency":{
               "friendly_name":"Kørsel effektivitet",
               "unit_of_measurement":"%",
               "value_template":"unavailable"
            },
            f"{__name__}_km_per_kwh":{
               "friendly_name":"km/kWh",
               "unit_of_measurement":"km/kWh",
               "value_template":"unavailable",
               "icon_template":"mdi:map-marker-distance"
            },
            f"{__name__}_estimated_range":{
               "friendly_name":"Estimerede rækkevidde",
               "unit_of_measurement":"km",
               "value_template":"unavailable",
               "icon_template":"mdi:map-marker-path"
            },
            f"{__name__}_drive_efficiency_last_battery_level":{
               "friendly_name":"Batteriniveau ved sidste ladning",
               "unit_of_measurement":"%",
               "value_template":"unavailable"
            },
            f"{__name__}_drive_efficiency_last_odometer":{
               "friendly_name":"Kilometerstand ved sidste ladning",
               "unit_of_measurement":"km",
               "value_template":"unavailable"
            },
            f"{__name__}_charge_very_cheap_battery_level":{
               "friendly_name":"",
               "value_template":"unavailable",
               "unit_of_measurement":"%"
            },
            f"{__name__}_charge_ultra_cheap_battery_level":{
               "friendly_name":"",
               "value_template":"unavailable",
               "unit_of_measurement":"%"
            },
            f"{__name__}_kwh_cost_price":{
               "friendly_name":"",
               "value_template":"unavailable",
               "unit_of_measurement":"DKK/kWh"
            },
            f"{__name__}_current_charging_rule":{
               "friendly_name":"Nuværende lade regel",
               "value_template":""
            },
            f"{__name__}_emoji_description":{
               "friendly_name":"Emoji forklaring",
               "value_template":"",
            },
            f"{__name__}_overview":{
               "friendly_name":"Oversigt",
               "value_template":""
            },
            f"{__name__}_charging_history":{
               "friendly_name":"Lade historik",
               "value_template":""
            }
         }
      }
   ]
}

COMMENT_DB_YAML = {
    "testing_mode": "In testing mode, no commands/service calls are sent to charger or ev",
    "first_run": "**Required** After editing the file set this to false",
    "cron_interval": "**Required** Interval between state check and function runs",
    "wake_up_entity_id": "Force wake up (Leave blank if using Hyundai-Kia-Connect, using wake up serive instead)",
    "climate_entity_id": "Used to preheat ev",
    "odometer_entity_id": "**Required**",
    "estimated_battery_range_entity_id": "**Required** Must precise battery range",
    "usable_battery_level_entity_id": "**Required** Must precise battery level",
    "charge_port_door_entity_id": "**Required**",
    "charge_cable_entity_id": "Used to determine if ev is connected to charger",
    "charge_switch_entity_id": "Start/stop charging on EV",
    "charging_limit_entity_id": "**Required** Setting charging battery limit on EV",
    "charging_amps_entity_id": "Setting charging amps on EV",
    "location_entity_id": "**Required**",
    "last_update_entity_id": "Used to determine sending wake up call",
    "battery_size": "**Required** Actual usable battery capacity, check with OBD2 unit for precise value",
    "min_daily_battery_level": "**Required** Also editable via WebGUI",
    "min_trip_battery_level": "**Required** Also editable via WebGUI",
    "min_charge_limit_battery_level": "**Required** Also editable via WebGUI",
    "max_recommended_charge_limit_battery_level": "**Required** Also editable via WebGUI",
    "very_cheap_grid_charging_max_battery_level": "**Required** Also editable via WebGUI",
    "ultra_cheap_grid_charging_max_battery_level": "**Required** Also editable via WebGUI",
    "daily_drive_distance": "**Required** Also editable via WebGUI",
    "status_entity_id": "**Required** Charger status",
    "power_consumtion_entity_id": "**Required** Charging power in Watt",
    "kwh_meter_entity_id": "**Required** Maybe use Riemann-sum integral-sensor (charger kwh meter is slow, as with Easee) else the chargers lifetime kwh meter",
    "lifetime_kwh_meter_entity_id": "**Required** Same as kwh_meter_entity_id, if you dont want the chargers lifetime kwh meter",
    "enabled_entity_id": "**Required** Turn Charger unit ON/OFF, NOT for start/stop charging",
    "dynamic_circuit_limit": "If not set, charger.entity_ids.start_stop_charging_entity_id must be set",
    "co2_entity_id": "Energi Data Service CO2 entity_id",
    "cable_connected_entity_id": "If EV dont have cable connected entity, use this instead to determine, if ev is connected to charger",
    "start_stop_charging_entity_id": "If using other integration than Easee to start stop charging, like Monta",
    "power_voltage": "**Required** Grid power voltage",
    "charging_phases": "**Required** Phases available for the ev",
    "charging_max_amp": "**Required** Maximum amps for the ev",
    "charging_loss": f"**Required** Can be auto calculated via WebGUI with input_boolean.{__name__}_calculate_charging_loss",
    "power_consumption_entity_id": "Home power consumption (Watt entity), not grid power consumption",
    "powerwall_watt_flow_entity_id": "Powerwall watt flow (Entity setup plus value for discharging, negative for charging)",
    "ignore_consumption_from_entity_ids": "List of power sensors to ignore",
    "notify_list": "List of users to send notifications",
    "production_entity_id": "Solar power production Watt",
    "solarpower_use_before_minutes": "Minutes back u can use solar overproduction available",
    "max_to_current_hour": "Must use solar overproduction available in current hour",
    "allow_grid_charging_above_solar_available": "Watt above(+)/under(-) overproduction available",
    "charging_single_phase_min_amp": "Minimum allowed amps the car can charge",
    "charging_single_phase_max_amp": "Maximum allowed amps the car can charge",
    "charging_three_phase_min_amp": "Minimum allowed amps the car can charge, uses charger.charging_phases config for max",
    "production_price": "Set to -1.0 if using raw hour sell price, also editable via WebGUI",
    "power_prices_entity_id": "**Required** Energi Data Service price entity_id",
    "hourly_service_entity_id": "**Required if using solar** hourly forecast entity_id",
    "daily_service_entity_id": "**Required if using solar** daily forecast entity_id",
    "outdoor_temp_entity_id": "Used to determine preheat or defrost when preheating the ev, for more precise temp than forecast",
    "solar_available_db_data_to_save": "Amount to save, per cloud coverage density",
    "kwh_avg_prices_db_data_to_save": "Amount to save",
    "drive_efficiency_db_data_to_save": "Amount to save",
    "km_kwh_efficiency_db_data_to_save": "Amount to save",
    "charging_history_db_data_to_save": "Save X month back",
    "refund": "Refund amount given by the state/country/nation/energy-provider"
}

def welcome():
    _LOGGER.info(f'''
-------------------------------------------------------------------
🚗Cable Juice Planner🔋🌞📅 (Script: {__name__}.py)
-------------------------------------------------------------------
''')

def restart_script():
    _LOGGER = globals()['_LOGGER'].getChild("restart_script")
    _LOGGER.info("Restarting script")
    set_charging_rule(f"📟Genstarter scriptet")
    if service.has_service("pyscript", "reload"):
        service.call("pyscript", "reload", blocking=True,
                            global_ctx=f"file.{__name__}")

def is_entity_configured(entity):
    _LOGGER = globals()['_LOGGER'].getChild("is_entity_configured")
    if entity is None or entity == "":
        return False
    return True
        
def is_powerwall_configured():
    global POWERWALL_CONFIGURED
    
    if POWERWALL_CONFIGURED is None:
        POWERWALL_CONFIGURED = True if CONFIG['home']['entity_ids']['powerwall_watt_flow_entity_id'] else False
        _LOGGER.info(f"Powerwall entity is {'' if POWERWALL_CONFIGURED else 'not '}configured")
    
    return POWERWALL_CONFIGURED

def is_solar_configured():
    global SOLAR_CONFIGURED
    
    if SOLAR_CONFIGURED is None:
        SOLAR_CONFIGURED = True if CONFIG['solar']['entity_ids']['production_entity_id'] else False
        _LOGGER.info(f"Solar entity is {'' if SOLAR_CONFIGURED else 'not '}configured")
    
    return SOLAR_CONFIGURED

def is_ev_configured():
    global EV_CONFIGURED
    if EV_CONFIGURED is None:
        if CONFIG['ev_car']['entity_ids']['odometer_entity_id'] and \
            CONFIG['ev_car']['entity_ids']['estimated_battery_range_entity_id'] and \
            CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id'] and \
            CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id'] and \
            CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'] and \
            CONFIG['ev_car']['entity_ids']['location_entity_id']:
            EV_CONFIGURED = True
        else:
            EV_CONFIGURED = False
        _LOGGER.info(f"Ev entities is {'' if EV_CONFIGURED else 'not '}configured")
    
    return EV_CONFIGURED

def save_changes(file, db):
    _LOGGER = globals()['_LOGGER'].getChild("save_changes")
    global COMMENT_DB_YAML
    db_disk = load_yaml(file)
    
    comment_db = COMMENT_DB_YAML if f"{__name__}_config" in file else None
    if db != db_disk or db == {}:
        try:
            _LOGGER.info(f"Saving {file} to disk")
            save_yaml(file, db, comment_db=comment_db)
        except Exception as e:
            _LOGGER.error(f"Cant save {file}: {e}")
            
def create_integration_dict():
    _LOGGER = globals()['_LOGGER'].getChild("create_integration_dict")
    global ENTITY_INTEGRATION_DICT, INTEGRATION_DAILY_LIMIT_BUFFER
    
    def hourly_limit(daily_limit):
        return max(1, int(daily_limit / 24))

    def add_to_dict(integration):
        daily_limit = hourly_limit(ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["daily_limit"])
        ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["hourly_limit"] = daily_limit
        ENTITY_INTEGRATION_DICT["commands_last_hour"][integration] = [(getTime(), "Startup")]
        ENTITY_INTEGRATION_DICT["last_reload"][integration] = getTime()
        ENTITY_INTEGRATION_DICT["counter"][integration] = 0
    
    for value in CONFIG.values():
        if isinstance(value, dict) and "entity_ids" in value:
            for entity in value["entity_ids"].values():
                if entity is None or entity == "":
                    continue
                
                if isinstance(entity, list):
                    for entity_2 in entity:
                        entity_id, integration = get_integration(entity_2)
                        
                        if integration is None or integration not in ENTITY_INTEGRATION_DICT["supported_integrations"]:
                            continue
                        
                        ENTITY_INTEGRATION_DICT["entities"][entity_id] = integration
                        add_to_dict(integration)
                else:
                    entity_id, integration = get_integration(entity)
                    
                    if integration is None or integration not in ENTITY_INTEGRATION_DICT["supported_integrations"]:
                        continue
                    
                    ENTITY_INTEGRATION_DICT["entities"][entity_id] = integration
                    add_to_dict(integration)
                    
    ENTITY_INTEGRATION_DICT["supported_integrations"] = {
        key: value
        for key, value in ENTITY_INTEGRATION_DICT["supported_integrations"].items()
        if "hourly_limit" in value
    }
    _LOGGER.info(f"Entity integration daily limit buffer: {INTEGRATION_DAILY_LIMIT_BUFFER}")
    _LOGGER.info(f"Entity integration dict:\n{pformat(ENTITY_INTEGRATION_DICT, width=200, compact=True)}")

def reload_entity_integration(entity_id):
    global ENTITY_INTEGRATION_DICT
    
    entity_id, integration = get_integration(entity_id)
    
    if integration is None:
        return
    
    if integration not in ENTITY_INTEGRATION_DICT["last_reload"] or minutesBetween(ENTITY_INTEGRATION_DICT["last_reload"][integration], getTime()) > 30:
        ENTITY_INTEGRATION_DICT["last_reload"][integration] = getTime()
        reload_integration(entity_id)
        
def reset_counter_entity_integration():
    _LOGGER = globals()['_LOGGER'].getChild("reset_counter_entity_integration")
    global ENTITY_INTEGRATION_DICT
    
    _LOGGER.info(f"ENTITY_INTEGRATION_DICT before reset:\n{pformat(ENTITY_INTEGRATION_DICT, width=200, compact=True)}")
    
    for integration in ENTITY_INTEGRATION_DICT["counter"].keys():
        ENTITY_INTEGRATION_DICT["counter"][integration] = 0
    

def allow_command_entity_integration(entity_id = None, command = "None", integration = None):#TODO Add check if same or similar command called in X time
    _LOGGER = globals()['_LOGGER'].getChild("allow_command_entity_integration")
    global ENTITY_INTEGRATION_DICT, INTEGRATION_DAILY_LIMIT_BUFFER
    
    if integration is None:
        _, integration = get_integration(entity_id)
    
    if integration is not None:
        now = getTime()
        try:
            ENTITY_INTEGRATION_DICT["commands_last_hour"][integration] = [dt for dt in ENTITY_INTEGRATION_DICT["commands_last_hour"][integration] if dt[0] >= now - datetime.timedelta(hours=1)]

            if integration in ENTITY_INTEGRATION_DICT["supported_integrations"]:
                charging_limit_list = []
                for item in ENTITY_INTEGRATION_DICT["commands_last_hour"][integration]:
                    if CONFIG["ev_car"]["entity_ids"]["charging_limit_entity_id"] in item[1]:
                        if CONFIG["ev_car"]["entity_ids"]["charging_limit_entity_id"] is None or CONFIG["ev_car"]["entity_ids"]["charging_limit_entity_id"] == "":
                            continue
                        charging_limit_list.append(float(item[1].split(": ")[1]))
                
                if charging_limit_list:
                    charging_limit_max = max(charging_limit_list)
                    if charging_limit_max == command:
                        _LOGGER.warning(f"Trying to set charging limit, to the same to often")
                        return
                    
                    if charging_limit_max > command:
                        _LOGGER.warning(f"Trying to set charging limit, to lower value to often, using max value")
                        command = charging_limit_max
                        
                        if float(get_state(CONFIG["ev_car"]["entity_ids"]["charging_limit_entity_id"], float_type=True)) == command:
                            _LOGGER.warning(f"Charging limit, already the same")
                            return
                
                extra_buffer = 0
                if "wake" in str(entity_id).lower():
                    extra_buffer = 3
                    
                daily_limit = ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["daily_limit"] - INTEGRATION_DAILY_LIMIT_BUFFER
                hourly_limit = ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["hourly_limit"] - extra_buffer
                
                _LOGGER.info(f"DEBUG {entity_id} {command} {integration} {len(ENTITY_INTEGRATION_DICT["commands_last_hour"][integration])} < {hourly_limit} = {len(ENTITY_INTEGRATION_DICT["commands_last_hour"][integration]) < hourly_limit} and {ENTITY_INTEGRATION_DICT['counter'][integration]} < {daily_limit} = {ENTITY_INTEGRATION_DICT['counter'][integration] < daily_limit} extra_buffer:{extra_buffer}")
                if len(ENTITY_INTEGRATION_DICT["commands_last_hour"][integration]) < hourly_limit and ENTITY_INTEGRATION_DICT["counter"][integration] < daily_limit:
                    ENTITY_INTEGRATION_DICT["commands_last_hour"][integration].append((now, f"{entity_id}: {command}"))
                    ENTITY_INTEGRATION_DICT["counter"][integration] += 1
                    return True
            else:
                return True
        except Exception as e:
            _LOGGER.error(f"allow_command_entity_integration(entity_id = {entity_id}, command = {command}, integration = {integration})\n{pformat(ENTITY_INTEGRATION_DICT, width=200, compact=True)}: {e}")
            return True
    else:
        _LOGGER.warning(f"integration was none allow_command_entity_integration(entity_id = {entity_id}, command = {command}, integration = {integration})")
        return True
    return False

def set_charging_rule(text=""):
    if RESTARTING_CHARGER_COUNT < 3:
        testing = "🧪" if TESTING else ""
        
        limit_string= ""
        integration_limited_hourly = []
        integration_limited_daily = []
        
        for integration in ENTITY_INTEGRATION_DICT["supported_integrations"]:
            if integration in ENTITY_INTEGRATION_DICT["commands_last_hour"]:
                if len(ENTITY_INTEGRATION_DICT["commands_last_hour"][integration]) >= ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["hourly_limit"]:
                    integration_limited_hourly.append(integration.capitalize())
                    
                if ENTITY_INTEGRATION_DICT["counter"][integration] >= ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["daily_limit"]:
                    integration_limited_daily.append(integration.capitalize())
        
        if integration_limited_hourly:
            limit_string += f"\n🚧Timegrænse nået {' & '.join(integration_limited_hourly)}"
        
        if integration_limited_daily:
            limit_string += f"\n🚧Dagliggrænse nået {' & '.join(integration_limited_daily)}"
        
        try:
            set_state(f"sensor.{__name__}_current_charging_rule", f"{testing}{text}{testing}{limit_string}")
        except Exception as e:
            _LOGGER.warning(f"Cant set sensor.{__name__}_current_charging_rule to '{text}'")

def init():
    _LOGGER = globals()['_LOGGER'].getChild("init")
    global CONFIG, DEFAULT_ENTITIES, INITIALIZATION_COMPLETE, TESTING

    def handle_yaml(file_path, default_content, key_renaming, comment_db, check_first_run=False, prompt_restart=False):
        """
        Handles the loading, updating, and saving of YAML configurations, and optionally prompts for a restart.
        """
        if not file_exists(file_path):
            save_yaml(file_path, default_content, comment_db)
            _LOGGER.error(f"File has been created: {file_path}")
            raise Exception(f"Edit it as needed. Please restart Home Assistant after making necessary changes.")

        content = load_yaml(file_path)
        _LOGGER.debug(f"Loaded content from {file_path}:\n{pformat(content, width=200, compact=True)}")

        if not content:
            raise Exception(f"Failed to load {file_path}")

        was_updated = False
        if key_renaming:
            was_updated = update_keys_recursive(content, key_renaming)
            if was_updated:
                save_yaml(file_path, content, comment_db)

        updated, content = update_dict_with_new_keys(content, default_content)
        if updated:
            if "first_run" in content and "config.yaml" in file_path:
                content['first_run'] = True
            save_yaml(file_path, content, comment_db)

        if was_updated or updated:
            msg = f"Config updated."
            if check_first_run:
                msg += " Set first_run to false and reload."
            msg += " Please restart Home Assistant to apply changes."
            raise Exception(msg)

        deprecated_keys = compare_dicts_unique_to_dict1(content, default_content)
        if deprecated_keys:
            _LOGGER.warning(f"{file_path} contains deprecated settings:")
            for key, value in deprecated_keys.items():
                _LOGGER.warning(f"\t{key}: {value}")
            _LOGGER.warning("Please remove them.")

        if prompt_restart and (was_updated or updated or deprecated_keys):
            raise Exception(f"Please restart Home Assistant to apply changes to {file_path}.")

        return content

    welcome()
    try:
        CONFIG = handle_yaml(f"{__name__}_config.yaml", DEFAULT_CONFIG, CONFIG_KEYS_RENAMING, COMMENT_DB_YAML, check_first_run=True, prompt_restart=False)
        TESTING = True if "test" in __name__ or ("testing_mode" in CONFIG and CONFIG['testing_mode']) else False
        set_charging_rule(f"📟Indlæser konfigurationen")
        if is_ev_configured():
            if f"{__name__}_battery_level" in DEFAULT_ENTITIES['input_number']:
                del DEFAULT_ENTITIES['input_number'][f'{__name__}_battery_level']
                
            if f"{__name__}_completed_battery_level" in DEFAULT_ENTITIES['input_number']:
                del DEFAULT_ENTITIES['input_number'][f'{__name__}_completed_battery_level']
                
            if f"{__name__}_estimated_total_range" in DEFAULT_ENTITIES['input_number']:
                del DEFAULT_ENTITIES['input_number'][f'{__name__}_estimated_total_range']
        else:
            for key in list(DEFAULT_ENTITIES['input_boolean'].keys()):
                if "preheat" in key:
                    if key in DEFAULT_ENTITIES['input_boolean']:
                        del DEFAULT_ENTITIES['input_boolean'][key]
                    
            for key in list(DEFAULT_ENTITIES['input_number'].keys()):
                if "preheat" in key:
                    if key in DEFAULT_ENTITIES['input_number']:
                        del DEFAULT_ENTITIES['input_number'][key]
                    
            for key in list(DEFAULT_ENTITIES['sensor'][0]['sensors'].keys()):
                if "drive_efficiency" in key:
                    if key in DEFAULT_ENTITIES['sensor'][0]['sensors']:
                        del DEFAULT_ENTITIES['sensor'][0]['sensors'][key]
                    
            if f"{__name__}_km_per_kwh" in DEFAULT_ENTITIES['sensor'][0]['sensors']:
                del DEFAULT_ENTITIES['sensor'][0]['sensors'][f'{__name__}_km_per_kwh']
        
        if not is_solar_configured():
            if f"{__name__}_kwh_charged_by_solar" in DEFAULT_ENTITIES['input_number']:
                del DEFAULT_ENTITIES['input_number'][f"{__name__}_kwh_charged_by_solar"]
                
            if f"{__name__}_solar_sell_fixed_price" in DEFAULT_ENTITIES['input_number']:
                del DEFAULT_ENTITIES['input_number'][f"{__name__}_solar_sell_fixed_price"]
                
            for key in list(DEFAULT_ENTITIES['sensor'][0]['sensors'].keys()):
                if "solar" in key:
                    if key in DEFAULT_ENTITIES['sensor'][0]['sensors']:
                        del DEFAULT_ENTITIES['sensor'][0]['sensors'][key]
        
        handle_yaml(f"packages/{__name__}.yaml", DEFAULT_ENTITIES, ENTITIES_RENAMING, None, prompt_restart=True)
        
        if CONFIG['first_run']:
            raise Exception("Edit config file and set first_run to false")
        
        is_powerwall_configured()
        
        create_integration_dict()
        
        INITIALIZATION_COMPLETE = True
    except Exception as e:
        _LOGGER.error(e)
        INITIALIZATION_COMPLETE = False
        set_charging_rule(f"⛔Lad script stoppet.\nTjek log for mere info:\n{e}")

set_charging_rule(f"📟Starter scriptet op")
init()

if INITIALIZATION_COMPLETE:
    SOLAR_CHARGING_TRIGGER_ON = abs(CONFIG['charger']['power_voltage'] * CONFIG['solar']['charging_single_phase_min_amp'])
    MAX_WATT_CHARGING = (CONFIG['charger']['power_voltage']  * CONFIG['charger']['charging_phases']) * CONFIG['charger']['charging_max_amp']
    MAX_KWH_CHARGING = MAX_WATT_CHARGING / 1000

def set_entity_friendlynames():
    _LOGGER = globals()['_LOGGER'].getChild("set_entity_friendlynames")
    for key, nested_dict in CHARGING_TYPES.items():
        if "entity_name" in nested_dict:
            _LOGGER.info(f"Setting sensor.{nested_dict['entity_name']}.friendly_name: {nested_dict['emoji']} {nested_dict['description']}")
            set_attr(f"sensor.{nested_dict['entity_name']}.friendly_name", f"{nested_dict['emoji']} {nested_dict['description']}")

def emoji_description():
    _LOGGER = globals()['_LOGGER'].getChild("emoji_description")
    emoji_sorted = {}
    for nested_dict in CHARGING_TYPES.values():
        emoji_sorted[float(nested_dict['priority'])] = nested_dict
    descriptions = ['## Emoji forklaring: ##']
    for key, nested_dict in sorted(emoji_sorted.items()):
        descriptions.append(f"* **{nested_dict['emoji']} {nested_dict['description']}**")
        
    _LOGGER.info(f"Setting sensor.{__name__}_emoji_description")
    set_state(f"sensor.{__name__}_emoji_description", f"Brug Markdown kort med dette i: {{{{ states.sensor.{__name__}_emoji_description.attributes.description }}}}")
    set_attr(f"sensor.{__name__}_emoji_description.description", "\n".join(descriptions))

def emoji_sorting(text):
    emoji_to_priority = {d['emoji']: float(d['priority']) for _, d in CHARGING_TYPES.items()}
    emoji_sorted = {}
    for emoji in text.split():
        if emoji in emoji_to_priority:
            emoji_sorted[emoji_to_priority[emoji]] = emoji
    
    emojis = [emoji for _, emoji in sorted(emoji_sorted.items())]
    return " ".join(emojis)

def emoji_parse(data):
    emojis = [CHARGING_TYPES[key]['emoji'] for key in data if data[key] is True and key in CHARGING_TYPES]
    return emoji_sorting(" ".join(emojis))

def emoji_text_format(text):
    words = text.split()
    result = []

    if len(words) > 3:
        for i in range(0, len(words), 3):
            # Join two adjacent words, if possible, else just take the single word left
            pair = ''.join(words[i:i+3])
            result.append(pair)
        return '<br>'.join(result)
    else:
        return ''.join(words)

def set_default_entity_states():
    set_state(f"sensor.{__name__}_overview", f"Brug Markdown kort med dette i: {{{{ states.sensor.{__name__}_overview.attributes.overview }}}}")
    set_attr(f"sensor.{__name__}_overview.overview", "<center>\n\n**Ingen oversigt endnu**\n\n</center>")

def weather_values():
    output = []
    for condition in WEATHER_CONDITION_DICT.values():
        if condition not in output:
            output.append(condition)
    return output
    
def get_list_values(data):
    float_list = []
    for item in data:
        if isinstance(item, float):
            float_list.append(item)
        elif isinstance(item, (list, tuple)):
            if isinstance(item[1], float):
                float_list.append(item[1])
    return float_list

def is_calculating_charging_loss():
    try:
        return True if get_state(f"input_boolean.{__name__}_calculate_charging_loss", float_type=False, error_state=False) == "on" else False
    except Exception as e:
        _LOGGER.warning(f": {e}")
        return False

def get_entity_daily_distance():
    try:
        return float(get_state(f"input_number.{__name__}_days_to_charge_range", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get daily distance, using config data {CONFIG['ev_car']['daily_drive_distance']}: {e}")
        return CONFIG['ev_car']['daily_drive_distance']

def get_min_daily_battery_level():
    try:
        return float(get_state(f"input_number.{__name__}_min_daily_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get daily battery level, using config data {CONFIG['ev_car']['min_daily_battery_level']}: {e}")
        return CONFIG['ev_car']['min_daily_battery_level']

def get_min_trip_battery_level():
    try:
        return float(get_state(f"input_number.{__name__}_min_trip_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get min trip battery level, using config data {CONFIG['ev_car']['min_trip_battery_level']}: {e}")
        return CONFIG['ev_car']['min_trip_battery_level']

def get_min_charge_limit_battery_level():
    try:
        return float(get_state(f"input_number.{__name__}_min_charge_limit_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get min charge limit battery level, using config data {CONFIG['ev_car']['min_charge_limit_battery_level']}: {e}")
        return CONFIG['ev_car']['min_charge_limit_battery_level']

def get_max_recommended_charge_limit_battery_level():
    try:
        return float(get_state(f"input_number.{__name__}_max_recommended_charge_limit_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get max recommended charge limit battery level, using config data {CONFIG['ev_car']['max_recommended_charge_limit_battery_level']}: {e}")
        return CONFIG['ev_car']['max_recommended_charge_limit_battery_level']

def get_very_cheap_grid_charging_max_battery_level():
    try:
        return float(get_state(f"input_number.{__name__}_very_cheap_grid_charging_max_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get very cheap grid charging max battery level, using config data {CONFIG['ev_car']['very_cheap_grid_charging_max_battery_level']}: {e}")
        return CONFIG['ev_car']['very_cheap_grid_charging_max_battery_level']

def get_ultra_cheap_grid_charging_max_battery_level():
    try:
        return float(get_state(f"input_number.{__name__}_ultra_cheap_grid_charging_max_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get ultra cheap grid charging max battery level, using config data {CONFIG['ev_car']['ultra_cheap_grid_charging_max_battery_level']}: {e}")
        return CONFIG['ev_car']['ultra_cheap_grid_charging_max_battery_level']

def get_completed_battery_level():
    try:
        if not is_ev_configured():
            return float(get_state(f"input_number.{__name__}_completed_battery_level", float_type=True))
        raise Exception("Not emulated ev")
    except Exception as e:
        _LOGGER.warning(f"Using default charge completed battery level 100.0: {e}")
        return 100.0

def get_estimated_total_range():
    estimated_total_range = 0.0
    try:
        estimated_total_range = float(get_state(f"input_number.{__name__}_estimated_total_range", float_type=True))
    except Exception as e:
        _LOGGER.error(f"input_number.{__name__}_estimated_total_range is not set to a total range: {e}")
        
    return estimated_total_range

def get_trip_date_time():
    trip_date_time = resetDatetime()
    try:
        trip_date_time = get_state(f"input_datetime.{__name__}_trip_date_time", error_state=resetDatetime())
    except Exception as e:
        _LOGGER.error(f"input_datetime.{__name__}_trip_date_time is not set to a dateTime: {e}")
        try:
            set_state(f"input_datetime.{__name__}_trip_date_time", resetDatetime())
            set_state(f"input_boolean.{__name__}_trip_charging", "off")
        except Exception as e:
            _LOGGER.error(f"Cant set input_datetime.{__name__}_trip_date_time to {resetDatetime()}: {e}")
            
    return trip_date_time

def get_trip_homecoming_date_time():
    trip_homecoming_date_time = resetDatetime()
    try:
        trip_homecoming_date_time = get_state(f"input_datetime.{__name__}_trip_homecoming_date_time", error_state=resetDatetime())
    except Exception as e:
        _LOGGER.error(f"input_datetime.{__name__}_trip_homecoming_date_time is not set to a dateTime: {e}")
        try:
            set_state(f"input_datetime.{__name__}_trip_homecoming_date_time", resetDatetime())
            set_state(f"input_boolean.{__name__}_trip_charging", "off")
        except Exception as e:
            _LOGGER.error(f"Cant set input_datetime.{__name__}_trip_homecoming_date_time to {resetDatetime()}: {e}")
            
    return trip_homecoming_date_time

def get_trip_range():
    trip_range = 0.0
    try:
        trip_range = float(get_state(f"input_number.{__name__}_trip_range_needed"))
    except Exception as e:
        _LOGGER.error(f"input_number.{__name__}_trip_range_needed is not set to a number: {e}")
        try:
            set_state(f"input_number.{__name__}_trip_range_needed", 0.0)
            set_state(f"input_boolean.{__name__}_trip_charging", "off")
        except Exception as e:
            _LOGGER.error(f"Cant set input_number.{__name__}_trip_range_needed to 0.0: {e}")
        
    return trip_range

def get_trip_target_level():
    trip_target_level = 0.0
    try:
        trip_target_level = float(get_state(f"input_number.{__name__}_trip_charge_procent"))
    except Exception as e:
        _LOGGER.error(f"input_number.{__name__}_trip_charge_procent is not set to a number: {e}")
        try:
            set_state(f"input_number.{__name__}_trip_charge_procent", 0.0)
            set_state(f"input_boolean.{__name__}_trip_charging", "off")
        except Exception as e:
            _LOGGER.error(f"Cant set input_number.{__name__}_trip_charge_procent to 0.0: {e}")
        
    return trip_target_level

def is_trip_planned():
    trip_planned = "off"
    try:
        trip_planned = get_state(f"input_boolean.{__name__}_trip_charging")
        if trip_planned != "on" and trip_planned != "off":
            raise Exception("State is not on/off")
    except Exception as e:
        _LOGGER.error(f"input_boolean.{__name__}_trip_charging is not set to a boolean: {e}")
        try:
            set_state(f"input_boolean.{__name__}_trip_charging", "off")
        except Exception as e:
            _LOGGER.error(f"Cant set input_boolean.{__name__}_trip_charging to off: {e}")
        
    return True if trip_planned == "on" else False

def manual_charging_enabled():
    if get_state(f"input_boolean.{__name__}_allow_manual_charging_now") == "on":
        return True

def manual_charging_solar_enabled():
    if get_state(f"input_boolean.{__name__}_allow_manual_charging_solar") == "on":
        return True

def get_solar_sell_price(set_entity_attr=False):
    _LOGGER = globals()['_LOGGER'].getChild("get_solar_sell_price")
    
    if not is_solar_configured(): return 0.0
    
    try:
        if CONFIG['prices']['entity_ids']['power_prices_entity_id'] not in state.names(domain="sensor"):
            raise Exception(f"{CONFIG['prices']['entity_ids']['power_prices_entity_id']} not loaded")
        
        power_prices_attr = get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id'])
        
        if "tariffs" not in power_prices_attr:
            raise Exception(f"tariffs not in {CONFIG['prices']['entity_ids']['power_prices_entity_id']}")
        
        price = get_state(CONFIG['prices']['entity_ids']['power_prices_entity_id'], float_type=True)
        attr = power_prices_attr["tariffs"]
        transmissions_nettarif = attr["additional_tariffs"]["transmissions_nettarif"]
        systemtarif = attr["additional_tariffs"]["systemtarif"]
        elafgift = attr["additional_tariffs"]["elafgift"]
        tariffs = attr["tariffs"][str(getHour())]
        
        tariff_sum = sum([transmissions_nettarif, systemtarif, elafgift, tariffs])
        
        raw_price = price - tariff_sum
        
        energinets_network_tariff = SOLAR_SELL_TARIFF["energinets_network_tariff"]
        energinets_balance_tariff = SOLAR_SELL_TARIFF["energinets_balance_tariff"]
        solar_production_seller_cut = SOLAR_SELL_TARIFF["solar_production_seller_cut"]
        
        sell_tariffs = sum((solar_production_seller_cut, energinets_network_tariff, energinets_balance_tariff, transmissions_nettarif, systemtarif))
        solar_sell_price = raw_price - sell_tariffs
        
        sell_price = float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price']))
        if sell_price == -1.0:
            if CONFIG['prices']['entity_ids']['power_prices_entity_id'] not in state.names(domain="sensor"):
                raise Exception(f"{CONFIG['prices']['entity_ids']['power_prices_entity_id']} not loaded")
            sell_price = round(solar_sell_price, 3)
        
        if set_entity_attr:
            for item in get_attr(f"sensor.{__name__}_kwh_cost_price"):
                state.delete(f"sensor.{__name__}_kwh_cost_price.{item}")
                
            set_attr(f"sensor.{__name__}_kwh_cost_price.price", f"{price:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.transmissions_nettarif", f"{transmissions_nettarif:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.systemtarif", f"{systemtarif:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.elafgift", f"{elafgift:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.tariffs", f"{tariffs:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.tariff_sum", f"{tariff_sum:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.raw_price", f"{raw_price:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.sell_tariffs_overview", "")
            set_attr(f"sensor.{__name__}_kwh_cost_price.transmissions_nettarif_", f"{transmissions_nettarif:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.systemtarif_", f"{systemtarif:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.energinets_network_tariff_", f"{energinets_network_tariff:.4f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.energinets_balance_tariff_", f"{energinets_balance_tariff:.4f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.solar_production_seller_cut_", f"{solar_production_seller_cut:.4f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.sell_tariffs", f"{sell_tariffs:.3f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.solar_sell_price", f"{solar_sell_price:.3f} kr/kWh")
            if sell_price >= 0.0:
                set_attr(f"sensor.{__name__}_kwh_cost_price.fixed_sell_price", f"{sell_price:.3f} kr/kWh")
    except Exception as e:
        sell_price = max(CONFIG['solar']['production_price'], 0.0)
        _LOGGER.error(f"Cant get solar sell price using {sell_price}: {e}")
        
    return sell_price

def get_refund():
    try:
        return abs(CONFIG['prices']['refund'])
    except Exception as e:
        _LOGGER.warning(f"Cant get refund, using default 0.0: {e}")
        return 0.0

def get_current_hour_price():
    try:
        return float(get_state(f"sensor.{__name__}_kwh_cost_price", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get current hour price, using default 0.0: {e}")
        return 0.0
    
def kwh_to_percentage(kwh, include_charging_loss=False):
    effective_kwh = kwh
    if include_charging_loss:
        effective_kwh = kwh / (1 + abs(CONFIG['charger']['charging_loss']))
    percentage = effective_kwh / CONFIG['ev_car']['battery_size'] * 100
    return percentage

def percentage_to_kwh(percentage, include_charging_loss=False):
    kwh = percentage * CONFIG['ev_car']['battery_size'] / 100
    if include_charging_loss:
        kwh = kwh * (1 + abs(CONFIG['charger']['charging_loss']))
    return kwh

def km_kwh_to_km_percentage(kwh):
    return percentage_to_kwh(kwh, include_charging_loss=False)

def km_percentage_to_km_kwh(percentage):
    return kwh_to_percentage(percentage, include_charging_loss=False)
    
def avg_distance_per_percentage():
    _LOGGER = globals()['_LOGGER'].getChild("avg_distance_per_percentage")
    output = 3.0
    
    if not is_ev_configured():
        try:
            output = round(get_estimated_total_range() / 100, 2)
        except Exception as e:
            _LOGGER.error(e)
    else:
        try:
            if KM_KWH_EFFICIENCY_DB == {}:
                raise Exception("No data yet")
            
            mean = round(average(get_list_values(KM_KWH_EFFICIENCY_DB)),2)
            if mean == 0.0:
                raise Exception(f"mean is invalid: {mean}")
            output = km_kwh_to_km_percentage(mean)
            _LOGGER.debug(f"mean_km/kwh:{mean} km_kwh_to_km_percentage({mean})={output}")
        except Exception as e:
            _LOGGER.warning(f"Using default value 3.0: {e}")
    return output

def calc_distance_to_battery_level(distance):
    return distance / avg_distance_per_percentage()

def calc_battery_level_to_distance(battery_level):
    return battery_level * avg_distance_per_percentage()

def is_entity_available(entity):
    _LOGGER = globals()['_LOGGER'].getChild("is_entity_available")
    try:
        if not is_entity_configured(entity):
            return
        
        entity_state = get_state(entity, error_state="unknown")
        if entity_state in ("unknown", "unavailable"):
            raise Exception(f"Entity state is {entity_state}")
        return True
    except Exception as e:
        _LOGGER.warning(f"Entity {entity} not available: {e}")
        
        reload_entity_integration(entity)
    
def wake_up_ev():
    _LOGGER = globals()['_LOGGER'].getChild("wake_up_ev")
    global LAST_WAKE_UP_DATETIME
    
    if not is_ev_configured(): return
    
    if minutesBetween(LAST_WAKE_UP_DATETIME, getTime()) <= 14:
        _LOGGER.info(f"Wake up call already called")
        return
    
    if is_entity_configured(CONFIG['ev_car']['entity_ids']['last_update_entity_id']):
        last_update = get_state(CONFIG['ev_car']['entity_ids']['last_update_entity_id'], error_state=resetDatetime())
        
        if minutesBetween(last_update, getTime()) <= 14:
            _LOGGER.info(f"Ev already updated, skipping wake up call")
            return

    LAST_WAKE_UP_DATETIME = getTime()
    
    if is_entity_configured(CONFIG['ev_car']['entity_ids']['wake_up_entity_id']):
        entity_id = CONFIG['ev_car']['entity_ids']['wake_up_entity_id']
        domain = entity_id.split(".")[0]
        
        if not allow_command_entity_integration(entity_id, "wake_up_ev()"):
            _LOGGER.warning(f"Limit reached, cant wake up ev")
            return
    
        _LOGGER.info("Waking up car")

        if domain == "button":
            button.press(entity_id=entity_id)
        elif domain == "input_button":
            input_button.press(entity_id=entity_id)
    else:
        integration = get_integration(CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id'])[1]
        
        if "kia_uvo" in integration and service.has_service(integration, "force_update"):
            if allow_command_entity_integration("Wake Up service","wake_up_ev()" , integration = integration):
                service.call(integration, "force_update", blocking=True)
            else:
                _LOGGER.warning(f"Limit reached, cant wake up ev")
    
def send_command(entity_id, command):#TODO Add queue and chargelimit last hour use max(commands)
    _LOGGER = globals()['_LOGGER'].getChild("send_command")
    
    if not is_entity_configured(entity_id): return
    
    if TESTING:
        _LOGGER.info(f"TESTING: Not sending command: {entity_id} {command}")
        return
    
    current_state = get_state(entity_id)
    try:
       current_state = float(current_state)
       command = float(command)
    except:
        pass
    
    if current_state != command:
        if not allow_command_entity_integration(entity_id, command):
            _LOGGER.warning(f"Limit reached, cant send command to ev {entity_id}: {command}")
            return
        
        _LOGGER.debug(f"Sending command: {entity_id} {command}")
        set_state(entity_id, command)
    else:
        _LOGGER.debug(f"Ignoring command {entity_id} state already: {command}")
        
def ev_send_command(entity_id, command):#TODO Add queue and chargelimit last hour use max(commands)
    _LOGGER = globals()['_LOGGER'].getChild("ev_send_command")
    
    if not is_ev_configured(): return
    
    if not is_entity_configured(entity_id): return
    
    if not ready_to_charge(): return
    
    if TESTING:
        _LOGGER.info(f"TESTING: Not sending command: {entity_id} {command}")
        return
    
    current_state = get_state(entity_id)
    try:
       current_state = float(current_state)
       command = float(command)
    except:
        pass
    
    if current_state != command:
        '''if entity_id == CONFIG['ev_car']['entity_ids']['charge_switch_entity_id'] and command == "on":
            wake_up_ev()'''
    
        if not allow_command_entity_integration(entity_id, command):
            _LOGGER.warning(f"Limit reached, cant send command to ev {entity_id}: {command}")
            return
        
        _LOGGER.debug(f"Sending command: {entity_id} {command}")
        set_state(entity_id, command)
    else:
        _LOGGER.debug(f"Ignoring command {entity_id} state already: {command}")

def battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("battery_level")
    try:
        if not is_ev_configured():
            return float(get_state(f"input_number.{__name__}_battery_level", float_type=True, error_state=0.0))
        
        if not is_entity_available(CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id']):
            return 0.0
        
        return float(get_state(CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id'], float_type=True, error_state=0.0))
    except Exception as e:
        if is_ev_configured():
            _LOGGER.error(f"battery_level(): {get_state(CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id'], try_history=False)}")
            _LOGGER.error(f"get_state(): {get_state(CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id'], float_type=True)}")
        _LOGGER.error(e)
        return 0.0

def battery_range():
    _LOGGER = globals()['_LOGGER'].getChild("battery_range")
    distance = 0.0
    
    if not is_ev_configured():
        distance = avg_distance_per_percentage() * battery_level()
    else:
        try:
            if not is_entity_available(CONFIG['ev_car']['entity_ids']['estimated_battery_range_entity_id']):
                return distance
            
            distance = float(get_state(CONFIG['ev_car']['entity_ids']['estimated_battery_range_entity_id'], float_type=True, error_state=0.0))
        except Exception as e:
            _LOGGER.error(f"battery_range(): {get_state(CONFIG['ev_car']['entity_ids']['estimated_battery_range_entity_id'], try_history=False)}")
            _LOGGER.error(f"get_state(): {get_state(CONFIG['ev_car']['entity_ids']['estimated_battery_range_entity_id'], float_type=True)}")
            _LOGGER.error(e)
    return distance
    
def is_battery_fully_charged(dont_set_date=False):
    if dont_set_date: return
    
    if battery_level() < 100.0: return
    
    set_state(f"input_datetime.{__name__}_last_full_charge", getTime())

def load_drive_efficiency():
    _LOGGER = globals()['_LOGGER'].getChild("load_drive_efficiency")
    global DRIVE_EFFICIENCY_DB
    
    if not is_ev_configured(): return
    
    try:
        create_yaml(f"{__name__}_drive_efficiency_db", db=DRIVE_EFFICIENCY_DB)
        DRIVE_EFFICIENCY_DB = load_yaml(f"{__name__}_drive_efficiency_db")
    except Exception as e:
        _LOGGER.error(f"Cant load {__name__}_drive_efficiency_db: {e}")
    
    if DRIVE_EFFICIENCY_DB == {} or not DRIVE_EFFICIENCY_DB:
        DRIVE_EFFICIENCY_DB = []
        save_drive_efficiency()
    
    set_state_drive_efficiency()
    
def save_drive_efficiency():
    global DRIVE_EFFICIENCY_DB
    
    if not is_ev_configured(): return
    
    if len(DRIVE_EFFICIENCY_DB) > 0:
        save_changes(f"{__name__}_drive_efficiency_db", DRIVE_EFFICIENCY_DB)
        
    set_state_drive_efficiency()
    
def set_state_drive_efficiency():
    if not is_ev_configured(): return
    
    try:
        drive_efficiency = get_list_values(DRIVE_EFFICIENCY_DB)
        set_state(f"sensor.{__name__}_drive_efficiency", drive_efficiency[0])
        set_attr(f"sensor.{__name__}_drive_efficiency.mean", float(average(drive_efficiency)))
        
        for item in get_attr(f"sensor.{__name__}_drive_efficiency"):
            if "dato" in item:
                state.delete(f"sensor.{__name__}_drive_efficiency.{item}")

        for i, item in enumerate(DRIVE_EFFICIENCY_DB):
            try:
                set_attr(f"sensor.{__name__}_drive_efficiency.dato_{item[0]}", round(item[1], 2))
            except:
                set_attr(f"sensor.{__name__}_drive_efficiency.dato_{i}", round(item, 2))
    except:
        pass

def load_km_kwh_efficiency():
    _LOGGER = globals()['_LOGGER'].getChild("load_km_kwh_efficiency")
    global KM_KWH_EFFICIENCY_DB
    
    if not is_ev_configured(): return
    
    try:
        create_yaml(f"{__name__}_km_kwh_efficiency_db", db=KM_KWH_EFFICIENCY_DB)
        KM_KWH_EFFICIENCY_DB = load_yaml(f"{__name__}_km_kwh_efficiency_db")
    except Exception as e:
        _LOGGER.error(f"Cant load {__name__}_km_kwh_efficiency_db: {e}")
    
    if KM_KWH_EFFICIENCY_DB == {} or not KM_KWH_EFFICIENCY_DB:
        KM_KWH_EFFICIENCY_DB = []
        save_km_kwh_efficiency()
    
    set_state_km_kwh_efficiency()
    
def save_km_kwh_efficiency():
    global KM_KWH_EFFICIENCY_DB
    
    if not is_ev_configured(): return
    
    if len(KM_KWH_EFFICIENCY_DB) > 0:
        save_changes(f"{__name__}_km_kwh_efficiency_db", KM_KWH_EFFICIENCY_DB)
        
    set_state_km_kwh_efficiency()
    
def set_state_km_kwh_efficiency():
    _LOGGER = globals()['_LOGGER'].getChild("set_state_km_kwh_efficiency")
    
    if not is_ev_configured(): return
    
    try:
        km_kwh_efficiency = get_list_values(KM_KWH_EFFICIENCY_DB)
        value = km_kwh_efficiency[0] if len(km_kwh_efficiency) > 0 else 3.0
        
        set_state(f"sensor.{__name__}_km_per_kwh", round(value, 2))
        km_kwh_mean = round(float(average(km_kwh_efficiency)), 2)
        
        if km_kwh_mean > 0.0:
            wh_km_mean = round(1000 / km_kwh_mean, 2)
            set_attr(f"sensor.{__name__}_km_per_kwh.mean", f"{km_kwh_mean:.2f} km/kWh - {wh_km_mean:.2f} Wh/km")
        
        for item in get_attr(f"sensor.{__name__}_km_per_kwh"):
            if "dato" in item:
                state.delete(f"sensor.{__name__}_km_per_kwh.{item}")

        for i, item in enumerate(KM_KWH_EFFICIENCY_DB):
            try:
                km_kwh = round(item[1], 2)
                wh_km = round(1000 / km_kwh, 2)
                set_attr(f"sensor.{__name__}_km_per_kwh.dato_{item[0]}", f"{km_kwh:.2f} km/kWh - {wh_km:.2f} Wh/km")
            except:
                km_kwh = round(item, 2)
                wh_km = round(1000 / km_kwh, 2)
                set_attr(f"sensor.{__name__}_km_per_kwh.dato_{i}", f"{km_kwh:.2f} km/kWh - {wh_km:.2f} Wh/km")
        set_estimated_range()
    except Exception as e:
        _LOGGER.error(f"{e}")
    
def set_estimated_range():
    try:
        range_per_percentage = km_kwh_to_km_percentage(float(average(get_list_values(KM_KWH_EFFICIENCY_DB))))
        range_at_battery_level = round(range_per_percentage * battery_level(), 2)
        range_total = round(range_per_percentage * 100.0, 2)
        
        set_attr(f"input_number.{__name__}_trip_range_needed.max", round(range_total + 100.0, 0)) #Must be above _estimated_range to update attr
        set_state(f"sensor.{__name__}_estimated_range", range_at_battery_level)
        set_attr(f"sensor.{__name__}_estimated_range.total", range_total)
    except Exception as e:
        _LOGGER.warning(f"Cant set estimated range: {e}")
            
def drive_efficiency(state = None):
    _LOGGER = globals()['_LOGGER'].getChild("drive_efficiency")
    global DRIVE_EFFICIENCY_DB, KM_KWH_EFFICIENCY_DB, PREHEATING
    
    def _save_car_stats():
        if is_ev_configured():
            set_state(f"sensor.{__name__}_drive_efficiency_last_odometer", float(get_state(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], float_type=True, error_state="unknown")))
        set_state(f"sensor.{__name__}_drive_efficiency_last_battery_level", battery_level())
        
    if len(DRIVE_EFFICIENCY_DB) == 0:
        load_drive_efficiency()
        
    if len(KM_KWH_EFFICIENCY_DB) == 0:
        load_km_kwh_efficiency()
    
    if state == "preheat":
        _save_car_stats()
        PREHEATING = True
    elif state == "preheat_cancel":
        PREHEATING = False
    
    if state in ("closed", "off"):
        if not PREHEATING:
            _save_car_stats()
            
        PREHEATING = False
    elif state in ("open", "on"):
        if not is_ev_configured():
            distancePerkWh = km_percentage_to_km_kwh(avg_distance_per_percentage())
            efficiency = 100.0
        else:
            if not is_entity_available(f"sensor.{__name__}_drive_efficiency_last_odometer"):
                _LOGGER.error(f"sensor.{__name__}_drive_efficiency_last_odometer is not available")
                return
            if not is_entity_available(f"sensor.{__name__}_drive_efficiency_last_battery_level"):
                _LOGGER.error(f"sensor.{__name__}_drive_efficiency_last_battery_level is not available")
                return
            if not is_entity_available(CONFIG['ev_car']['entity_ids']['odometer_entity_id']):
                _LOGGER.error(f"{CONFIG['ev_car']['entity_ids']['odometer_entity_id']} is not available")
                return
            
            current_odometer = float(get_state(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], float_type=True, try_history=True))
            last_current_odometer = float(get_state(f"sensor.{__name__}_drive_efficiency_last_odometer", float_type=True, error_state=current_odometer))
            
            last_battery_level = float(get_state(f"sensor.{__name__}_drive_efficiency_last_battery_level", float_type=True, error_state=battery_level()))
            
            usedBattery = last_battery_level - battery_level()
            kilometers = current_odometer - last_current_odometer
            usedkWh = percentage_to_kwh(usedBattery)
            distancePerkWh = 3.0
            if usedkWh != 0.0:
                distancePerkWh = kilometers / usedkWh
            else:
                _LOGGER.warning("Used kWh is 0.0 ignoring drive")
                return
            
            
            distancePerPercentage = kilometers / usedBattery
            cars_distance_per_percentage = round(battery_range() / battery_level(), 2)
            efficiency = abs(round((distancePerPercentage / cars_distance_per_percentage) * 100.0, 2))
            
            _LOGGER.info(f"distancePerPercentage {kilometers} / {usedBattery} = {distancePerPercentage}")
            _LOGGER.info(f"distancePerkWh {kilometers} / {usedkWh} = {distancePerkWh}")
            _LOGGER.info(f"cars_distance_per_percentage {battery_range()} / {battery_level()} = {round(battery_range() / battery_level(), 2)}")
            _LOGGER.info(f"efficiency {kilometers} / {usedBattery} = {kilometers / usedBattery}")
            
            _LOGGER.debug(f"battery_range(): {battery_range()} battery_level(): {battery_level()} usedBattery:{usedBattery} kilometers:{kilometers} usedkWh:{usedkWh} cars_distance_per_percentage:{cars_distance_per_percentage} distancePerkWh:{distancePerkWh} efficiency:{efficiency}%")
            if kilometers <= 10.0 or usedBattery <= 5.0:
                _LOGGER.warning(f"{kilometers}km <= 10.0 or {usedBattery} usedBattery <= 5.0, ignoring drive")
                return
            
            if efficiency > 150.0:
                _LOGGER.warning(f"usedBattery:{usedBattery} usedkWh:{usedkWh} kilometers:{kilometers} (start odometer:{get_state(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], float_type=True)} end odometer:{get_state(f"sensor.{__name__}_drive_efficiency_last_odometer", float_type=True)})")
                _LOGGER.warning(f"Efficiency is to high, ignoring it: {efficiency}%")
                return
        
        DRIVE_EFFICIENCY_DB.insert(0, [getTime(), efficiency])
        DRIVE_EFFICIENCY_DB = DRIVE_EFFICIENCY_DB[:CONFIG['database']['drive_efficiency_db_data_to_save']]
        save_drive_efficiency()
        
        KM_KWH_EFFICIENCY_DB.insert(0, [getTime(), distancePerkWh])
        KM_KWH_EFFICIENCY_DB = KM_KWH_EFFICIENCY_DB[:CONFIG['database']['km_kwh_efficiency_db_data_to_save']]
        save_km_kwh_efficiency()

def range_to_battery_level(extraRange = None, batteryBuffer = None):
    _LOGGER = globals()['_LOGGER'].getChild("range_to_battery_level")
    minRangeInBatteryLevel = get_min_charge_limit_battery_level()
    if extraRange is None:
        extraRange = get_entity_daily_distance()
    if batteryBuffer is None:
        batteryBuffer = get_min_daily_battery_level()

    try:
        minRangeInBatteryLevel = round_up(calc_distance_to_battery_level(extraRange)) + batteryBuffer
        _LOGGER.debug(f"extraRange:{extraRange} minRangeInBatteryLevel:{minRangeInBatteryLevel}")
    except Exception as e:
        _LOGGER.error(f"extraRange:{extraRange} batteryBuffer:{batteryBuffer} minRangeInBatteryLevel:{minRangeInBatteryLevel}: {e}")
    return min(minRangeInBatteryLevel, 100.0)

def kwh_needed_for_charging(targetLevel = None, battery = None):
    _LOGGER = globals()['_LOGGER'].getChild("kwh_needed_for_charging")
    if targetLevel is None:
        targetLevel = get_min_daily_battery_level()
    if battery is None:
        battery = battery_level()

    kwh = percentage_to_kwh(targetLevel - battery, include_charging_loss = True)
    _LOGGER.debug(f"targetLevel:{targetLevel} battery:{battery} kwh:{kwh} without loss kwh:{percentage_to_kwh(targetLevel - battery, include_charging_loss = True)}")
    return max(kwh, 0.0)

def verify_charge_limit(limit):
    _LOGGER = globals()['_LOGGER'].getChild("verify_charge_limit")
    try:
        if CONFIG['ev_car']['entity_ids']['charging_limit_entity_id']:
            if "kia_uvo" in get_integration(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'])[1]:
                limit = float(round_up((limit / 10)) * 10)
        
        limit = min(max(limit, get_min_charge_limit_battery_level()), 100.0)
    except Exception as e:
        _LOGGER.error(e)
        limit = get_min_charge_limit_battery_level()
    return limit

def reset_current_charging_session():
    global CURRENT_CHARGING_SESSION
    CURRENT_CHARGING_SESSION = {
        "type": None,
        "start": None,
        "start_charger_meter": 0.0,
        "emoji": "",
        "data": {}
    }
reset_current_charging_session()

def load_charging_history():
    _LOGGER = globals()['_LOGGER'].getChild("load_charging_history")
    global CHARGING_HISTORY_DB, CURRENT_CHARGING_SESSION
    
    try:
        create_yaml(f"{__name__}_charging_history_db", db=CHARGING_HISTORY_DB)
        CHARGING_HISTORY_DB = load_yaml(f"{__name__}_charging_history_db")
    except Exception as e:
        _LOGGER.error(f"Cant load {__name__}_charging_history_db: {e}")
    
    if CHARGING_HISTORY_DB == {} or not CHARGING_HISTORY_DB:
        CHARGING_HISTORY_DB = {}
        save_charging_history()
    
    if CHARGING_HISTORY_DB:
        last_item = sorted(CHARGING_HISTORY_DB.items(), key=lambda item: item[0], reverse=True)[0]
        if hoursBetween(getTime(), last_item[0]) == 0 and getHour(getTime()) == getHour(last_item[0]):
            try:
                CURRENT_CHARGING_SESSION = last_item[1]["charging_session"]
                CHARGING_HISTORY_DB[last_item[0]]["ended"] = ">"
                _LOGGER.info(f"Adding last charging session to CURRENT_CHARGING_SESSION:\n {pformat(CURRENT_CHARGING_SESSION, width=200, compact=True)}")
            except Exception as e:
                _LOGGER.error(f"Cant add last charging session to CURRENT_CHARGING_SESSION: {e}\n  ({last_item})")
                _LOGGER.error(f"Last item:\n {pformat(last_item, width=200, compact=True)}")
    
    set_state(f"sensor.{__name__}_charging_history", f"Brug Markdown kort med dette i: {{{{ states.sensor.{__name__}_charging_history.attributes.history }}}}")
    charging_history_combine_and_set()
    
def save_charging_history():
    _LOGGER = globals()['_LOGGER'].getChild("save_charging_history")
    global CHARGING_HISTORY_DB
    
    if CHARGING_HISTORY_DB:
        this_month = getYear(getTime()) * 12 + getMonth(getTime())
        
        try:
            for key in dict(sorted(CHARGING_HISTORY_DB.items(), key=lambda item: item[0], reverse=True)).keys():
                key_month = getYear(key) * 12 + getMonth(key)
                if this_month - key_month > CONFIG['database']['charging_history_db_data_to_save']:
                    _LOGGER.warning(f"{this_month} - {key_month} = {this_month - key_month} > {CONFIG['database']['charging_history_db_data_to_save']}")
                    _LOGGER.warning(f"Removing {key} from CHARGING_HISTORY_DB")
                    del CHARGING_HISTORY_DB[key]
                
            CHARGING_HISTORY_DB = dict(sorted(CHARGING_HISTORY_DB.items(), key=lambda item: item[0], reverse=True))
        
            save_changes(f"{__name__}_charging_history_db", CHARGING_HISTORY_DB)
        except Exception as e:
            _LOGGER.error(f"Cant save {__name__}_charging_history_db: {e}")
            pass
        
def charging_history_recalc_price():
    _LOGGER = globals()['_LOGGER'].getChild("charging_history_recalc_price")
    global CHARGING_HISTORY_DB
    
    if CHARGING_HISTORY_DB:
        now = getTime()
        
        sorted_keys = sorted(CHARGING_HISTORY_DB.keys(), reverse=True)
        start = sorted_keys[0]
        last_session = CHARGING_HISTORY_DB[start]
        remove_keys = [start]
                
        if hoursBetween(now, start) == 0 and getHour(now) == getHour(start):
            try:
                start_charger_meter = CHARGING_HISTORY_DB[start]["start_charger_meter"]
                ended = CHARGING_HISTORY_DB[start]["ended"]
                emoji = CHARGING_HISTORY_DB[start]["emoji"]
                emoji = CHARGING_HISTORY_DB[start]["emoji"]
                
                if ended == ">": return False
                
                for i in range(1, 20):
                    if hoursBetween(now, sorted_keys[i]) == 0 and getHour(now) == getHour(sorted_keys[i]):
                        start = sorted_keys[i]
                        
                        _LOGGER.info(f"Found another charging session in current hour {start}: {CHARGING_HISTORY_DB[start]}")
                        start_charger_meter = CHARGING_HISTORY_DB[start]['charging_session']['start_charger_meter']
                        
                        join_unique_emojis = lambda str1, str2: ' '.join(set(str1.split()).union(set(str2.split())))
                        emoji = join_unique_emojis(emoji, CHARGING_HISTORY_DB[sorted_keys[i]]["emoji"])
                        
                        remove_keys.append(start)
                    else:
                        break
                
                for key in remove_keys:
                    if key != start:
                        _LOGGER.info(f"Removing key {key} from CHARGING_HISTORY_DB")
                        del CHARGING_HISTORY_DB[key]
                
                end_charger_meter = float(get_state(CONFIG['charger']['entity_ids']['kwh_meter_entity_id'], float_type=True))
                added_kwh = end_charger_meter - start_charger_meter
                added_kwh_by_solar = calc_solar_kwh(getMinute(), added_kwh, solar_period_current_hour = True)
                added_percentage = kwh_to_percentage(added_kwh, include_charging_loss = True)
                price = calc_kwh_price(getMinute(), solar_period_current_hour = True)
                cost = added_kwh * price
                
                if added_kwh_by_solar > 0.0 or emoji_parse({'solar': True}) in emoji:
                    join_unique_emojis = lambda str1, str2: ' '.join(set(str1.split()).union(set(str2.split())))
                    emoji = join_unique_emojis(emoji, emoji_parse({'solar': True}))
                else:
                    return False

                CHARGING_HISTORY_DB[start]["kWh"] = round(added_kwh, 3)
                CHARGING_HISTORY_DB[start]["kWh_solar"] = round(added_kwh_by_solar, 3)
                CHARGING_HISTORY_DB[start]["percentage"] = round(added_percentage, 1)
                CHARGING_HISTORY_DB[start]["unit"] = round(price, 3)
                CHARGING_HISTORY_DB[start]["cost"] = round(cost, 3)
                CHARGING_HISTORY_DB[start]["emoji"] = emoji
                CHARGING_HISTORY_DB[start]["ended"] = ended
                CHARGING_HISTORY_DB[start]["start_charger_meter"] = start_charger_meter
                CHARGING_HISTORY_DB[start]["end_charger_meter"] = end_charger_meter
                
                _LOGGER.info(f"{last_session == CHARGING_HISTORY_DB[start]} {last_session} == {CHARGING_HISTORY_DB[start]}")
                if last_session != CHARGING_HISTORY_DB[start]:
                    _LOGGER.info(f"Last charging session to: {last_session}")
                    _LOGGER.info(f"Recalculated current hour charging sessions to: {CHARGING_HISTORY_DB[start]}")
                    _LOGGER.info(f"{pformat(CHARGING_HISTORY_DB[start], width=200, compact=True)}")
                    return True
            except Exception as e:
                _LOGGER.error(f"Cant calculate last charging session to CHARGING_HISTORY_DB({start}): {e}")
    return False

def charging_history_combine_and_set():
    _LOGGER = globals()['_LOGGER'].getChild("charging_history_combine_and_set")
    global CHARGING_HISTORY_DB
    
    history = []
    combined_db = {}
    
    if CHARGING_HISTORY_DB:
        total = {
            "cost": {"total": 0.0},
            "kwh": {"total": 0.0},
            "percentage": {"total": 0.0},
            "solar_kwh": {"total": 0.0}
        }
        
        details = False
        header = "| Tid |  | % | kWh | Pris |"
        align = "|:---:|:---|:---:|:---:|:---:|"
        
        history.append("<center>\n")
        history.append(header)
        history.append(align)
        
        length = 10
        sub_length = 50
        sub_details_count = 0
        
        max_history_length = 175
        max_history_length -= length
        
        append_counter = 0
        skip_counter = 0
        solar_in_months = False
        sorted_db = sorted(CHARGING_HISTORY_DB.items(), key=lambda item: item[0], reverse=True)
        sorted_db_length = len(sorted_db)
        
        now = getTime()
        
        for i, (when, d) in enumerate(sorted_db):
            if skip_counter == 0:
                if append_counter == length and not details:
                    details = True
                    history.extend([
                        "<details>",
                        "<summary><b>Se mere historik</b></summary>\n",
                        header,
                        align
                    ])
                elif append_counter > length and append_counter >= sub_length and append_counter % sub_length == 0 and (len(CHARGING_HISTORY_DB) - i) >= sub_length:
                    history.extend([
                        "\n",
                        "<details>",
                        "<summary><b>Se mere historik</b></summary>\n",
                        header,
                        align
                    ])
                    sub_details_count += 1
                    
                started = when
                charging_session = d["charging_session"] if "charging_session" in d else None
                ended = d['ended']
                emoji = d['emoji']
                percentage = d['percentage']
                kWh = d["kWh"]
                kWh_solar = d["kWh_solar"] if "kWh_solar" in d else 0.0
                cost = d['cost']
                unit = d['unit']
                start_charger_meter = None
                end_charger_meter = None
                
                if "start_charger_meter" in d and "end_charger_meter" in d:
                    start_charger_meter = d["start_charger_meter"]
                    end_charger_meter = d["end_charger_meter"]
                
                from_to = "-"
                
                combine_after = 2
                
                if i > combine_after and ended != ">":
                    charging_session = None
                    
                    for x in range(i+1, sorted_db_length+1):
                        if x+1 <= sorted_db_length:
                            next_when, next_d = sorted_db[x]
                            if daysBetween(when, now) > 40:
                                if daysBetween(when, next_when) == 0:
                                    join_unique_emojis = lambda str1, str2: ' '.join(set(str1.split()).union(set(str2.split())))
                                    emoji = join_unique_emojis(emoji, next_d['emoji'])
                                else:
                                    break
                            else:
                                if daysBetween(when, next_when) == 0 and hoursBetween(when, next_when) <= 1 and emoji == next_d['emoji']:
                                    pass
                                else:
                                    break
                                
                            started = next_when
                            percentage += next_d['percentage']
                            kWh += next_d["kWh"]
                            kWh_solar += next_d["kWh_solar"] if "kWh_solar" in d else 0.0
                            cost += next_d['cost']
                            if kWh > 0.0:
                                unit = cost / kWh
                            
                            if "start_charger_meter" in next_d:
                                start_charger_meter = next_d["start_charger_meter"]
                                
                            skip_counter += 1
                        else:
                            break
                
                emoji = emoji_sorting(emoji)
                
                combined_db[started] = {
                    "cost": cost,
                    "emoji": emoji,
                    "ended": ended,
                    "kWh": kWh,
                    "kWh_solar": kWh_solar,
                    "percentage": percentage,
                    "unit": unit
                }
                
                if start_charger_meter is not None and end_charger_meter is not None:
                    combined_db[started]["start_charger_meter"] = start_charger_meter
                    combined_db[started]["end_charger_meter"] = end_charger_meter
                
                if charging_session: combined_db[started]["charging_session"] = charging_session
                
                if append_counter <= max_history_length:
                    ended_hour = int(ended.split(":")[0]) if ended != ">" and len(ended) > 0 else getHour()
                    if getHour(started) != ended_hour:
                        from_to = "»"
                    
                    started = f"**{started.strftime('%d/%m %H:%M')}**" if started else ""
                    ended = f"**{ended}**" if ended else ">"
                    emoji = f"**{emoji_text_format(emoji)}**" if emoji else ""
                    percentage = f"**{get_closest_key(percentage, {1/4: "¼", 1/2: "½", 3/4: "¾"}) if 0.0 < percentage < 1.0 else int(percentage)}**" if isinstance(percentage, (float, int)) else "**0**"
                    kWh = f"**{kWh:.1f}**" if isinstance(kWh, (float, int)) else "**0.0**"
                    cost = f"**{cost:.2f}**" if isinstance(cost, (float, int)) else ""
                    unit = f"**{unit:.2f}**" if isinstance(unit, (float, int)) else ""
                    
                    history.append(f"| {started}{from_to}{ended} | {emoji} | {percentage} | {kWh} | {cost} ({unit}) |")
                append_counter += 1
            else:
                skip_counter = max(skip_counter - 1, 0)
                
            if append_counter > length and (len(CHARGING_HISTORY_DB) - i) == 1:
                history.extend(["</details>", "\n"] * (sub_details_count + 1))
            
            month = when.strftime('%Y %m %B')
            
            if month not in total['cost']:
                total['cost'][month] = 0.0
                total['kwh'][month] = 0.0
                total['percentage'][month] = 0.0
                total['solar_kwh'][month] = 0.0
                
            total['cost'][month] += d['cost']
            total['kwh'][month] += d["kWh"]
            total['percentage'][month] += d['percentage']
            
            if "kWh_solar" in d and d['kWh_solar'] > 0.0:
                total['solar_kwh'][month] += d['kWh_solar']
                total['solar_kwh']["total"] += d['kWh_solar']
                solar_in_months = True

            total['cost']["total"] += d['cost']
            total['kwh']["total"] += d["kWh"]
            total['percentage']["total"] += d['percentage']
                
        if details:
            solar_header = f"{emoji_parse({'solar': True})}kWh" if solar_in_months else ""
            history.extend([
                "</details>",
                "\n",
                f"| Måned | kWh | {solar_header} | Pris | Kr/kWh |",
                "|:---:|:---:|:---:|---:|:---:|"
            ])
            for month in sorted(total['cost'].keys()):
                if month == "total":
                    continue
                
                solar_kwh = ""
                solar_percentage = ""
                
                if total['solar_kwh'][month] > 0.0 and total['kwh'][month] > 0.0:
                    total_solar_percentage = round(total['solar_kwh'][month] / total['kwh'][month] * 100.0, 1)
                    
                    solar_kwh = round(total['solar_kwh'][month], 1)
                    solar_percentage = f" ({round(total_solar_percentage, 1)}%)"
                    
                unit_price = round(total['cost'][month] / total['kwh'][month],2) if total['kwh'][month] > 0.0 else 0.0
                
                history.append(f"| {month.split()[2]} {month.split()[0]} | {round(total['kwh'][month],1)} | {solar_kwh}{solar_percentage} | {round(total['cost'][month],2):.2f} | {unit_price:.2f} |")

        solar_string = ""
        if total['solar_kwh']["total"] > 0.0:
            total_solar_percentage = round(total['solar_kwh']["total"] / total['kwh']["total"] * 100.0, 1)
            solar_string = f" ({emoji_parse({'solar': True})}{total['solar_kwh']['total']:.1f}/{total_solar_percentage}%)"
            
        if total['kwh']["total"] > 0.0:
            history.append(f"\n**Ialt {round(total['kwh']["total"],1)}kWh {solar_string} {round(total['cost']["total"],2):.2f} kr ({round(total['cost']["total"] / total['kwh']["total"],2):.2f} kr)**")
            
        history.append("</center>")
        
    set_attr(f"sensor.{__name__}_charging_history.history", "\n".join(history) if history else "**Ingen lade historik**")
    
    CHARGING_HISTORY_DB = combined_db
    save_charging_history()
    
def charging_power_to_emulated_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("charging_power_to_emulated_battery_level")
    
    if is_ev_configured(): return
    
    global CURRENT_CHARGING_SESSION
    now = getTime()
    past = now - datetime.timedelta(minutes=CONFIG['cron_interval'])
    
    value_max = get_max_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0)
    value_min = get_min_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0)
    value_avg = get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0)
    _LOGGER.debug(f"charger_changed value_max:{value_max}")
    _LOGGER.debug(f"charger_changed value_min:{value_min}")
    _LOGGER.debug(f"charger_changed value_avg:{value_avg}")
    
    try:
        watt = float(value_max)
        _LOGGER.warning(f"charger_changed value:{watt}")
    except Exception as e:
        _LOGGER.error(f"charger_changed value:{value_max} {e}")
    
    if watt == 0.0:
        _LOGGER.warning(f"DEBUG CURRENT_CHARGING_SESSION:{CURRENT_CHARGING_SESSION} watt:{watt}")
    else:
        if CURRENT_CHARGING_SESSION['start']:
            current_charger_meter = float(get_state(CONFIG['charger']['entity_ids']['kwh_meter_entity_id'], float_type=True))
            added_kwh = round(current_charger_meter - CURRENT_CHARGING_SESSION['start_charger_meter'], 1)
                
            if "last_charger_meter" in CURRENT_CHARGING_SESSION:
                added_kwh = round(current_charger_meter - CURRENT_CHARGING_SESSION['last_charger_meter'], 1)
            
            CURRENT_CHARGING_SESSION['last_charger_meter'] = current_charger_meter
            added_percentage = round(kwh_to_percentage(added_kwh, include_charging_loss = True))
            current_battery_level = battery_level()
            new_battery_level = min(round(current_battery_level + added_percentage,0), get_completed_battery_level() - 1.0)
            _LOGGER.info(f"Adding {added_percentage}% to virtuel battery level from {current_battery_level}% to {new_battery_level}%")
            
            set_state(entity_id=f"input_number.{__name__}_battery_level", new_state=new_battery_level)

def charging_history(charging_data = None, charging_type = ""):
    _LOGGER = globals()['_LOGGER'].getChild("charging_history")
    global CHARGING_HISTORY_RUNNING, CHARGING_HISTORY_QUEUE
    
    CHARGING_HISTORY_QUEUE.append([charging_data, charging_type])
    
    if CHARGING_HISTORY_RUNNING:
        _LOGGER.warning(f"Queue running already CHARGING_HISTORY_QUEUE: {CHARGING_HISTORY_QUEUE}")
        return
    
    try:
        CHARGING_HISTORY_RUNNING = True
        
        while CHARGING_HISTORY_QUEUE:
            job = CHARGING_HISTORY_QUEUE.pop(0)
            _charging_history(charging_data = job[0], charging_type = job[1])
    except Exception as e:
        _LOGGER.error(f"Charging history queue failed  CHARGING_HISTORY_QUEUE: {CHARGING_HISTORY_QUEUE}")
        _LOGGER.error(f"{e}")
    finally:
        CHARGING_HISTORY_RUNNING = False

def _charging_history(charging_data = None, charging_type = ""):
    _LOGGER = globals()['_LOGGER'].getChild("_charging_history")
    global CHARGING_HISTORY_DB, CURRENT_CHARGING_SESSION
    
    def get_current_statistic(charging_ended = False):
        start = CURRENT_CHARGING_SESSION['start']
        charger_meter = float(get_state(CONFIG['charger']['entity_ids']['kwh_meter_entity_id'], float_type=True))
        added_kwh = round(charger_meter - CURRENT_CHARGING_SESSION['start_charger_meter'], 1)
        added_kwh_by_solar = calc_solar_kwh(minutesBetween(CURRENT_CHARGING_SESSION['start'], getTime(), error_value=getMinute()), added_kwh, solar_period_current_hour = False)
        added_percentage = round(kwh_to_percentage(added_kwh, include_charging_loss = True), 1)
        price = round(calc_kwh_price(minutesBetween(CURRENT_CHARGING_SESSION['start'], getTime(), error_value=getMinute()), solar_period_current_hour = True), 3)
        cost = round(added_kwh * price, 2)
        
        CHARGING_HISTORY_DB[start]["percentage"] = added_percentage
        CHARGING_HISTORY_DB[start]["kWh"] = added_kwh
        CHARGING_HISTORY_DB[start]["kWh_solar"] = added_kwh_by_solar
        CHARGING_HISTORY_DB[start]["cost"] = cost
        CHARGING_HISTORY_DB[start]["unit"] = price
        CHARGING_HISTORY_DB[start]["start_charger_meter"] = CURRENT_CHARGING_SESSION['start_charger_meter']
        CHARGING_HISTORY_DB[start]["end_charger_meter"] = charger_meter
        CHARGING_HISTORY_DB[start]["charging_session"] = CURRENT_CHARGING_SESSION
        
        if charging_ended:
            ended = f"{getTime().strftime('%H:%M')}"
            _LOGGER.warning(f"ended:{ended} added_percentage:{added_percentage} added_kwh:{added_kwh} cost:{cost} price:{price} charging_data:{charging_data} CURRENT_CHARGING_SESSION:{CURRENT_CHARGING_SESSION} emoji:{CURRENT_CHARGING_SESSION['emoji']}")
            CHARGING_HISTORY_DB[start]["ended"] = ended
        return [added_kwh, start]
    #timestamp: 31/03 14:00 charging_data: {'Price': 2.13, 'ChargingAmps': 16.0, 'Cost': 9.59, 'kWh': 4.5, 'battery_level': 6.0, 'trip': True, 'ChargeLevel': 50.0} emoji: 🌍
    update_entity = False
    
    if len(CHARGING_HISTORY_DB) == 0:
        load_charging_history()
    
    if CURRENT_CHARGING_SESSION['type'] is None and CURRENT_CHARGING_SESSION['start'] is None:
        for i, when in enumerate(sorted(CHARGING_HISTORY_DB.keys(), reverse=True)):
            if i > 10: break
            
            if CHARGING_HISTORY_DB[when]["ended"] == ">" or CHARGING_HISTORY_DB[when]["kWh"] == 0.0:
                _LOGGER.warning(f"Removing unfinished string: {CHARGING_HISTORY_DB[when]}")
                del CHARGING_HISTORY_DB[when]
                update_entity = True
                continue
    
    
    if charging_type != CURRENT_CHARGING_SESSION['type']:
        if CURRENT_CHARGING_SESSION['start']:
            added_kwh, when = get_current_statistic(True)
            charging_power_to_emulated_battery_level()
            
            #TODO calc_co2_emitted find a better place for this, chance of multiple run, when script reboot
            calc_co2_emitted(minutesBetween(CURRENT_CHARGING_SESSION['start'], getTime(), error_value=getMinute()), added_kwh = added_kwh)
            
            _LOGGER.debug(f"CURRENT_CHARGING_SESSION {CURRENT_CHARGING_SESSION['start']} {getTime()} {getMinute()} {minutesBetween(CURRENT_CHARGING_SESSION['start'], getTime(), error_value=getMinute())} calc_kwh_price(minutesBetween(CURRENT_CHARGING_SESSION['start'], getTime(), error_value=getMinute()), solar_period_current_hour = True) {calc_kwh_price(minutesBetween(CURRENT_CHARGING_SESSION['start'], getTime(), error_value=getMinute()), solar_period_current_hour = True)}")
            min_kwh = 0.1
            
            if added_kwh <= min_kwh and f"{emoji_parse({'charging_error': True})}" not in CURRENT_CHARGING_SESSION['emoji']:
                _LOGGER.warning(f"Removing unfinished string added_kwh:{added_kwh} <= min_kwh:{min_kwh}: {CHARGING_HISTORY_DB[when]}")
                del CHARGING_HISTORY_DB[when]
                
            update_entity = True
            
            reset_current_charging_session()
    
    if not CURRENT_CHARGING_SESSION['start'] and charging_data:
        start = getTime()
        CURRENT_CHARGING_SESSION['type'] = charging_type
        CURRENT_CHARGING_SESSION['start'] = start
        CURRENT_CHARGING_SESSION['start_charger_meter'] = float(get_state(CONFIG['charger']['entity_ids']['kwh_meter_entity_id'], float_type=True))
        
        if CHARGING_HISTORY_DB and len(CHARGING_HISTORY_DB) > 0:
            last_item = sorted(CHARGING_HISTORY_DB.items(), key=lambda item: item[0], reverse=True)[0]
            if "end_charger_meter" in last_item[1]:
                CURRENT_CHARGING_SESSION['start_charger_meter'] = last_item[1]["end_charger_meter"]
                _LOGGER.info(f"Using end charger meter from last session {CURRENT_CHARGING_SESSION['start_charger_meter']}")

        CURRENT_CHARGING_SESSION['emoji'] = f"{emoji_parse(charging_data)}"
        CURRENT_CHARGING_SESSION['data'] = charging_data
        _LOGGER.debug(f"start:{start} charging_data:{charging_data} CURRENT_CHARGING_SESSION:{CURRENT_CHARGING_SESSION} emoji:{CURRENT_CHARGING_SESSION['emoji']}")
        CHARGING_HISTORY_DB[start] = {
            "ended": ">",
            "emoji": CURRENT_CHARGING_SESSION['emoji'],
            "percentage": round(charging_data['battery_level'], 1),
            "kWh": round(charging_data['kWh'], 1),
            "cost": round(charging_data['Cost'], 2),
            "unit": round(charging_data['Price'], 2),
            "charging_session": CURRENT_CHARGING_SESSION,
            "start_charger_meter": CURRENT_CHARGING_SESSION['start_charger_meter'],
            "end_charger_meter": CURRENT_CHARGING_SESSION['start_charger_meter']
        }
        
        charging_power_to_emulated_battery_level()
        
        update_entity = True
    else:
        for i, when in enumerate(sorted(CHARGING_HISTORY_DB.keys(), reverse=True)):
            if i > 3: break
            
            if CHARGING_HISTORY_DB[when]["ended"] == ">" and (CHARGING_HISTORY_DB[when]["emoji"] == f"{emoji_parse({'solar': True})}" or CHARGING_HISTORY_DB[when]["emoji"] == f"{emoji_parse({'manual': True, 'solar': True})}" or CHARGING_HISTORY_DB[when]["emoji"] == f"{emoji_parse({'manual': True})}"):
                added_kwh, when = get_current_statistic()
                
                charging_power_to_emulated_battery_level()
                
                update_entity = True
                _LOGGER.warning(f"UPDATING CURRENT STRING {when}")
                break
    
    if getMinute() == 59:
        if charging_history_recalc_price():
            charging_power_to_emulated_battery_level()
            update_entity = True
        
    if update_entity:
        charging_history_combine_and_set()
        
def cheap_grid_charge_hours():
    _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours")
    global USING_OFFLINE_PRICES
    
    USING_OFFLINE_PRICES = False
    
    if CONFIG['prices']['entity_ids']['power_prices_entity_id'] not in state.names(domain="sensor"):
        _LOGGER.error(f"{CONFIG['prices']['entity_ids']['power_prices_entity_id']} not in entities")
        return

    today = getTimeStartOfDay()
    current_hour = reset_time_to_hour(getTime())
    now = getTime()
    
    chargeHours = {}
    totalCost = 0.0
    totalkWh = 0.0
        
    totalCost_alternative = 0.0
    totalkWh_alternative = 0.0
    
    solar_over_production = {}
    work_overview = {}
    charging_plan = {
        "workday_in_week": False
    }
    
    hourPrices = {}
    combinedHourPrices = {}
    try:
        if CONFIG['prices']['entity_ids']['power_prices_entity_id'] not in state.names(domain="sensor"):
            raise Exception(f"{CONFIG['prices']['entity_ids']['power_prices_entity_id']} not loaded")
            
        power_prices_attr = get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id'])
        
        if "raw_today" not in power_prices_attr:
            raise Exception(f"Real prices not in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes")
        
        for raw in power_prices_attr['raw_today']:
            hourPrices[raw['hour'].replace(tzinfo=None)] = round(raw['price'] - get_refund(), 2)


        if "forecast" not in power_prices_attr:
            raise Exception(f"Forecast not in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes")
        
        for raw in power_prices_attr['forecast']:
            combinedHourPrices[raw['hour'].replace(tzinfo=None)] = round(raw['price'] + (daysBetween(current_hour, raw['hour']) / 100) - get_refund(), 2)


        if "tomorrow_valid" in power_prices_attr:
            if power_prices_attr['tomorrow_valid']:
                if "raw_tomorrow" not in power_prices_attr:
                    raise Exception(f"Raw_tomorrow not in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes")
                
                for raw in power_prices_attr['raw_tomorrow']:
                    combinedHourPrices[raw['hour'].replace(tzinfo=None)] = round(raw['price'] - get_refund(), 2)
    except Exception as e:
            _LOGGER.warning(f"Cant get real prices, using database: {e}")
            
            USING_OFFLINE_PRICES = True
            for i in range(24):
                price = average(KWH_AVG_PRICES_DB['history'][i])
                for d in range(7):
                    timestamp = reset_time_to_hour(current_hour.replace(hour=i)) + datetime.timedelta(days=d)
                    timestamp = timestamp.replace(tzinfo=None)
                    if timestamp not in combinedHourPrices:
                        combinedHourPrices[timestamp] = round(price + (daysBetween(current_hour, timestamp) / 100), 2)
    
    combinedHourPrices.update(hourPrices)
    
    def available_for_charging_prediction(h, trip_datetime = None, trip_homecoming_datetime = None):
        _LOGGER = globals()['_LOGGER'].getChild("available_for_charging_prediction")
        working = False
        on_trip = False
        day = daysBetween(getTime(), h)
        
        try:
            if charging_plan[day]['workday']:
                working = in_between(h.hour, charging_plan[day]['work_goto'].hour, charging_plan[day]['homecoming'].hour)

            if trip_datetime:
                if in_between(h, trip_datetime, trip_homecoming_datetime):
                    on_trip = True
        except Exception as e:
            _LOGGER.error(e)
        
        return working, on_trip
        
    def kwh_available_in_hour(hour):
        _LOGGER = globals()['_LOGGER'].getChild("kwh_available_in_hour")
        hour_in_chargeHours = False
        kwhAvailable = False
        if hour in chargeHours:
            hour_in_chargeHours = True
            if chargeHours[hour]['kWh'] < (MAX_KWH_CHARGING - 1.0):
                kwhAvailable = True
        return [hour_in_chargeHours, kwhAvailable]

    def add_to_charge_hours(kwhNeeded, totalCost, totalkWh, hour, price, very_cheap_price, ultra_cheap_price, kwhAvailable, battery_level = None, max_recommended_battery_level = None, rules = []):
        _LOGGER = globals()['_LOGGER'].getChild("add_to_charge_hours")
        kwh = MAX_KWH_CHARGING
        battery_level_added = False
        
        if battery_level:
            if max_recommended_battery_level is None:
                max_recommended_battery_level = get_max_recommended_charge_limit_battery_level()
                
            battery_level_diff = round(max_recommended_battery_level - (battery_level + kwh_to_percentage(kwh, include_charging_loss = True)),2)
            kwh_diff = round(percentage_to_kwh(battery_level_diff, include_charging_loss = True),2)
            if (battery_level + kwh_to_percentage(kwh, include_charging_loss = True)) > max_recommended_battery_level:
                kwh -= abs(kwh_diff)
            
        if kwhAvailable == True and hour in chargeHours:
            kwh = kwh - chargeHours[hour]['kWh']
                
        if kwh > 0.5:
            if hour not in chargeHours:
                chargeHours[hour] = {
                    "Price": round(price, 2),
                    "ChargingAmps": CONFIG['charger']['charging_max_amp']
                }
            
            price = float(price)
            kwhNeeded = float(kwhNeeded)
            
            if (kwhNeeded - kwh) < 0.0:
                cost = kwhNeeded * price
                totalCost = totalCost + cost
                battery_level_added = kwh_to_percentage(kwhNeeded, include_charging_loss = True)
                kwh = kwhNeeded
                kwhNeeded = 0.0
            else:
                kwhNeeded = kwhNeeded - kwh
                cost = kwh * price
                totalCost = totalCost + cost
                battery_level_added = kwh_to_percentage(kwh, include_charging_loss = True)

            if kwhAvailable:
                calckWh = kwh
                chargeHours[hour]['Cost'] = round(chargeHours[hour]['Cost'] + cost, 2)
                chargeHours[hour]['kWh'] = round(chargeHours[hour]['kWh'] + calckWh, 2)
                calcProcent = round(kwh_to_percentage(calckWh, include_charging_loss = True), 2)
                chargeHours[hour]['battery_level'] = round(chargeHours[hour]['battery_level'] + calcProcent, 2)
                totalkWh = round(totalkWh + calckWh, 2)
            else:
                chargeHours[hour]['Cost'] = cost
                chargeHours[hour]['kWh'] = kwh
                chargeHours[hour]['battery_level'] = round(kwh_to_percentage(chargeHours[hour]['kWh'], include_charging_loss = True), 2)
                totalkWh = round(totalkWh + chargeHours[hour]['kWh'], 2)
                
            if ultra_cheap_price:
                rules.append("half_min_avg_price")
            elif very_cheap_price:
                rules.append("under_min_avg_price")
                
            if rules == []:
                rules.append("no_rule")
                
            for rule in rules:
                if rule not in chargeHours[hour]:
                    chargeHours[hour][rule] = True
                    
            _LOGGER.info(f"Adding {hour} {price} kr/kWh {chargeHours[hour]['battery_level']}% {chargeHours[hour]['kWh']}kWh with keys {rules}")

        return [kwhNeeded, totalCost, totalkWh, battery_level_added]

    def solar_prediction_available_until_next_workday(hour, work_day):
        days = daysBetween(hour, work_day)
        solar_prediction_available = 0.0
        if days > 0:
            for day in range(1,days+1):
                if charging_plan[day]['workday'] or charging_plan[day]['trip']:
                    break
                solar_prediction_available += charging_plan[day]['solar_prediction']
        return solar_prediction_available

    def cheap_price_check(price):
        _LOGGER = globals()['_LOGGER'].getChild("cheap_price_check")
        very_cheap_price = False
        ultra_cheap_price = False
        
        try:
            lowest_values = sorted(combinedHourPrices.values())[:CONFIG['database']['kwh_avg_prices_db_data_to_save']]
            average_price = round(average(lowest_values), 3)
            if round(price, 3) <= average_price:
                very_cheap_price = True
            if round(price, 3) <= (average_price * 0.75):
                ultra_cheap_price = True
        except Exception as e:
            _LOGGER.warning(f"Using local low prices to calc very/ultra cheap price: {e}")
            average_price = round(average(KWH_AVG_PRICES_DB['min']), 3)
            if round(price, 3) <= average_price:
                very_cheap_price = True
            if round(price, 3) <= (average_price * 0.75):
                ultra_cheap_price = True

        return [very_cheap_price, ultra_cheap_price]
    
    def future_charging(totalCost, totalkWh):
        _LOGGER = globals()['_LOGGER'].getChild("future_charging")
        nonlocal trip_date_time
        nonlocal trip_target_level
        nonlocal totalCost_alternative
        nonlocal totalkWh_alternative
        
        def what_battery_level(what_day, hour, price, day):
            battery_level_id = "battery_level_at_midnight"
            max_recommended_charge_limit_battery_level = get_max_recommended_charge_limit_battery_level()
            return_fail_list = [False, max_recommended_charge_limit_battery_level]
            
            total_trip_battery_level_needed = charging_plan[day]["trip_battery_level_needed"] + charging_plan[day]["trip_battery_level_above_max"]
            if charging_plan[day]["trip"] and in_between(day - what_day, 1, 0) and max_recommended_charge_limit_battery_level < total_trip_battery_level_needed:
                max_recommended_charge_limit_battery_level = total_trip_battery_level_needed
            
            what_day_battery_level_before_work = sum(charging_plan[what_day]['battery_level_before_work'])
            what_day_battery_level_after_work = max(sum(charging_plan[what_day]['battery_level_after_work']), sum(charging_plan[what_day]['battery_level_at_midnight']))
            after_what_day_battery_level_after_work = max(sum(charging_plan[min(what_day + 1, 7)]['battery_level_after_work']), sum(charging_plan[min(what_day + 1, 7)]['battery_level_at_midnight']))
            
            if what_day < 0:
                _LOGGER.warning(f"Error in combinedHourPrices: {hour} is before current time {getTime()} continue to next cheapest hour/price")
                return return_fail_list
            
            if price >= 0.0:
                if charging_plan[what_day]['workday']:
                    if hour < charging_plan[what_day]['work_goto']:
                        if what_day_battery_level_before_work >= max_recommended_charge_limit_battery_level:
                            _LOGGER.debug(f"Max battery level reached for day ({what_day}) before work {hour} {price}kr. {what_day_battery_level_before_work}% >= {max_recommended_charge_limit_battery_level}%")
                            return return_fail_list
                        battery_level_id = "battery_level_before_work"
                    else:
                        if what_day_battery_level_after_work >= max_recommended_charge_limit_battery_level:
                            _LOGGER.debug(f"Max battery level reached for day ({what_day}) at midnight {hour} {price}kr. {what_day_battery_level_after_work}% >= {max_recommended_charge_limit_battery_level}%")
                            return return_fail_list
                        if what_day + 1 < 7 and after_what_day_battery_level_after_work >= max_recommended_charge_limit_battery_level:
                            _LOGGER.debug(f"Max battery level reached for next day ({what_day + 1}) at midnight {hour} {price}kr. {what_day_battery_level_after_work}% >= {max_recommended_charge_limit_battery_level}%")
                            return return_fail_list
                else:
                    if what_day_battery_level_after_work >= max_recommended_charge_limit_battery_level:
                        _LOGGER.debug(f"Max battery level reached for day ({what_day}) at midnight {hour} {price}kr. {what_day_battery_level_after_work}% >= {max_recommended_charge_limit_battery_level}%")
                        return return_fail_list
                    if what_day + 1 < 7 and after_what_day_battery_level_after_work >= max_recommended_charge_limit_battery_level:
                        _LOGGER.debug(f"Max battery level reached for next day ({what_day + 1}) at midnight {hour} {price}kr. {after_what_day_battery_level_after_work}% >= {max_recommended_charge_limit_battery_level}%")
                        return return_fail_list
            return [battery_level_id, max_recommended_charge_limit_battery_level]
        
        def add_charging_session_to_day(hour, what_day, battery_level_id):
            charging_sessions_id = "battery_level_before_work" if battery_level_id == "battery_level_before_work" else "battery_level_after_work"
            
            if battery_level_id not in charging_plan[what_day]['charging_sessions']:
                charging_plan[what_day]['charging_sessions'][charging_sessions_id] = {}
            charging_plan[what_day]['charging_sessions'][charging_sessions_id][hour] = chargeHours[hour]
            return charging_sessions_id
                                
        def add_charging_to_days(day, what_day, charging_sessions_id, battery_level_added):
            for i in range(max(what_day - 1, 0), day + 1):
                if charging_sessions_id == "battery_level_before_work":
                    if i == max(what_day - 1, 0) and day > 0:
                        charging_plan[i]['battery_level_at_midnight'].append(battery_level_added)
                        
                    if  i >= what_day:
                        charging_plan[i]['battery_level_at_midnight'].append(battery_level_added)
                        charging_plan[i]['battery_level_after_work'].append(battery_level_added)
                        charging_plan[i]['battery_level_before_work'].append(battery_level_added)
                elif charging_sessions_id == "battery_level_after_work":
                    if i >= what_day:
                        charging_plan[i]['battery_level_at_midnight'].append(battery_level_added)
                        charging_plan[i]['battery_level_after_work'].append(battery_level_added)
                    
                    if i > what_day:
                        charging_plan[i]['battery_level_before_work'].append(battery_level_added)
        
        unused_solar_kwh = {}
        unused_solar_cost = {}
        solar_unit = get_solar_sell_price()
        
        current_battery_level = battery_level() - max(get_min_daily_battery_level(), get_min_trip_battery_level())
        if current_battery_level <= 0.0:
            current_battery_level = battery_level()
        battery_level_cost = 0.0
        battery_level_cost_kwh = 0.0
        battery_level_cost_percentage = 0.0
        battery_level_cost_solar_percentage = 0.0
        
        if CHARGING_HISTORY_DB:
            for key in dict(sorted(CHARGING_HISTORY_DB.items(), key=lambda item: item[0], reverse=True)).keys():
                if round(battery_level_cost_percentage) < round(current_battery_level):
                    if "cost" not in CHARGING_HISTORY_DB[key] or "kWh" not in CHARGING_HISTORY_DB[key] or "kWh_solar" not in CHARGING_HISTORY_DB[key] or "percentage" not in CHARGING_HISTORY_DB[key]:
                        continue
                    
                    cost = CHARGING_HISTORY_DB[key]["cost"]
                    kwh = CHARGING_HISTORY_DB[key]["kWh"]
                    percentage = CHARGING_HISTORY_DB[key]["percentage"]
                    solar_percentage = kwh_to_percentage(CHARGING_HISTORY_DB[key]["kWh_solar"], include_charging_loss=True)
                    
                    new_battery_level = percentage + battery_level_cost_percentage
                    if new_battery_level > current_battery_level and percentage > 0.0:
                        diff = (percentage - (new_battery_level - current_battery_level)) / percentage
                        cost = cost * diff
                        kwh = kwh * diff
                        percentage = percentage * diff
                        solar_percentage = solar_percentage * diff
                    battery_level_cost += cost
                    battery_level_cost_kwh += kwh
                    battery_level_cost_percentage += percentage
                    battery_level_cost_solar_percentage += solar_percentage
                else:
                    break
        
        battery_level_cost_per_kwh = None
        if battery_level_cost_kwh > 0.0:
            battery_level_cost_per_kwh = battery_level_cost / battery_level_cost_kwh
            
        fill_up_days = [1,4,7]
        kwh_needed_to_fill_up = kwh_needed_for_charging(get_max_recommended_charge_limit_battery_level())
        kwh_needed_to_fill_up_share = kwh_needed_to_fill_up / len(fill_up_days)
        
        for day in sorted([key for key in charging_plan.keys() if isinstance(key, int)]):
            day_before = max(day - 1, 0)
            day_after = min(day + 1, 7)
            last_charging = getTimeEndOfDay(getTimePlusDays(day))
                
            starting_battery_level = min(sum(charging_plan[day_before]['battery_level_at_midnight']), 100.0) if day > 0 else battery_level()
            
            if starting_battery_level < 0.0:
                correction_percentage = abs(starting_battery_level)
                starting_battery_level += correction_percentage
                _LOGGER.warning(f"Starting battery level under 0% ({round(correction_percentage * -1, 1)}%) adding {round(correction_percentage, 1)}%")
            charging_plan[day]['battery_level_before_work'].append(starting_battery_level)
            charging_plan[day]['battery_level_after_work'].append(starting_battery_level)
                
            if charging_plan[day]['trip']:
                work_battery_level_needed = 0.0
                
                if charging_plan[day]['workday']:
                    work_battery_level_needed -= charging_plan[day]['work_battery_level_needed']
                
                if charging_plan[day]['trip_goto'] >= charging_plan[day]['work_goto']:
                    charging_plan[day]['trip_kwh_needed'] = max(kwh_needed_for_charging(charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max'], sum(charging_plan[day]['battery_level_after_work']) + work_battery_level_needed), 0.0)
                else:
                    charging_plan[day]['trip_kwh_needed'] = max(kwh_needed_for_charging(charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max'], sum(charging_plan[day]['battery_level_before_work']) + work_battery_level_needed), 0.0)
   
            _LOGGER.debug(f"---------------------------------{day} {charging_plan[day]['day_text']} {charging_plan[day]['work_goto']} {day}---------------------------------")
            
            charging_plan[day]['battery_level_after_work'].append(charging_plan[day]['work_battery_level_needed'] * -1)
            
            charging_plan[day]['battery_level_at_midnight'].append(sum(charging_plan[day]['battery_level_after_work']))
            charging_plan[day]['battery_level_at_midnight'].append(charging_plan[day]['solar_prediction'])
            
            _LOGGER.debug(f"charging_plan[{day}]['battery_level_before_work'] {charging_plan[day]['battery_level_before_work']} {sum(charging_plan[day]['battery_level_before_work'])}")
            _LOGGER.debug(f"charging_plan[{day}]['battery_level_after_work'] {charging_plan[day]['battery_level_after_work']} {sum(charging_plan[day]['battery_level_after_work'])}")
            _LOGGER.debug(f"solar_prediction[{day}] {charging_plan[day]['solar_prediction']}%")
            _LOGGER.debug(f"charging_plan[{day}]['battery_level_at_midnight'] {charging_plan[day]['battery_level_at_midnight']} {sum(charging_plan[day]['battery_level_at_midnight'])}")
            
            very_cheap_kwh_needed_today = kwh_needed_for_charging(get_very_cheap_grid_charging_max_battery_level(), sum(charging_plan[day]['battery_level_at_midnight']))
            ultra_cheap_kwh_needed_today = kwh_needed_for_charging(get_ultra_cheap_grid_charging_max_battery_level(), sum(charging_plan[day]['battery_level_at_midnight']))
            _LOGGER.debug(f"{sum(charging_plan[day]['battery_level_at_midnight'])}% very_cheap_kwh_needed_today {very_cheap_kwh_needed_today} / ultra_cheap_kwh_needed_today {ultra_cheap_kwh_needed_today}")
            
            if charging_plan[day]['workday'] or charging_plan[day]['trip']:
                if charging_plan[day]['workday']:
                    last_charging = charging_plan[day]['work_last_charging']
                    
                if charging_plan[day]['trip']:
                    last_charging = min(charging_plan[day]['work_last_charging'], charging_plan[day]['trip_last_charging'])
                                    
                _LOGGER.debug(f"charging_plan[{day}]['work_goto'] {charging_plan[day]['work_goto']} / charging_plan[{day}]['trip_last_charging'] {charging_plan[day]['trip_last_charging']} / last_charging {last_charging}")
                
                kwh_needed_today = max(kwh_needed_for_charging(charging_plan[day]['work_battery_level_needed'] + get_min_daily_battery_level(), sum(charging_plan[day]['battery_level_before_work'])), 0.0)
                charging_plan[day]['work_kwh_needed'] = kwh_needed_today
                kwh_needed_today += charging_plan[day]['trip_kwh_needed']
                _LOGGER.debug(f"charging_plan[{day}]['work_battery_level_needed'] {charging_plan[day]['work_battery_level_needed']}")
                _LOGGER.debug(f"kwh_needed_today {kwh_needed_today}")
                
                
                #Workaround for cold weather
                if kwh_needed_today <= (CONFIG['ev_car']['battery_size'] / 100):
                    kwh_needed_today = 0.0
                
                for hour, price in sorted(combinedHourPrices.items(), key=lambda kv: (kv[1],kv[0])):
                    if hour <= last_charging and hour >= current_hour:
                        hour_in_chargeHours, kwhAvailable = kwh_available_in_hour(hour)
                        if hour_in_chargeHours and not kwhAvailable:
                            continue
                        
                        what_day = daysBetween(getTime(), hour)
                        battery_level_id, max_recommended_charge_limit_battery_level = what_battery_level(what_day, hour, price, day)
                        if not battery_level_id:
                            continue
                        
                        working, on_trip = available_for_charging_prediction(hour, trip_date_time, trip_homecoming_date_time)
                        if working or on_trip:
                            continue
                        
                        if len(chargeHours) > 0:
                            filteredDict = {k: v for k, v in chargeHours.items() if type(k) is datetime.datetime}
                            if len(filteredDict) > 0:
                                first_charging_session = sorted(filteredDict.keys())[0]
                                
                                try:
                                    if chargeHours[first_charging_session]['trip'] and hour < first_charging_session and (get_min_trip_battery_level() + charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max']) != 100:
                                        if what_day != 0 and not charging_plan[day]['workday']:
                                            continue
                                except:
                                    pass
                                
                        if kwh_needed_today > 0.0 and kwh_to_percentage(kwh_needed_today, include_charging_loss = True):
                            if sum(charging_plan[what_day][battery_level_id]) >= get_max_recommended_charge_limit_battery_level() - 1.0:
                                #Workaround for cold battery percentage: ex. 90% normal temp = 89% cold temp
                                continue
                            kwh_needed_today, totalCost, totalkWh, battery_level_added = add_to_charge_hours(kwh_needed_today, totalCost, totalkWh, hour, price, None, None, kwhAvailable, sum(charging_plan[what_day][battery_level_id]), max_recommended_charge_limit_battery_level, charging_plan[day]['rules'])
                            
                            if hour in chargeHours and battery_level_added:
                                if "trip" in charging_plan[day]['rules']:
                                    charging_plan[day]["trip_total_cost"] += chargeHours[hour]["Cost"]
                                
                                if filter(lambda x: 'workday_preparation' in x, charging_plan[day]['rules']):
                                    charging_plan[day]["work_total_cost"] += chargeHours[hour]["Cost"]
                                    
                                charging_sessions_id = add_charging_session_to_day(hour, what_day, battery_level_id)
                                add_charging_to_days(day, what_day, charging_sessions_id, battery_level_added)
                        else:
                            break
                
                try:
                    solar_kwh = 0.0
                    solar_percentage = 0.0
                    
                    if sum(unused_solar_kwh.values()) > 0.0:
                        total_solar_kwh = sum(unused_solar_kwh.values())
                        total_solar_price = sum(unused_solar_cost.values())
                        unused_solar_kwh.clear()
                        unused_solar_cost.clear()
                        
                        solar_percentage = kwh_to_percentage(total_solar_kwh, include_charging_loss=True)
                        if total_solar_kwh > 0.0:
                            solar_unit = total_solar_price / total_solar_kwh
                        
                    temp_events = []
                    for event_type in ['trip', 'workday']:
                        
                        if charging_plan[day][event_type]:
                            goto_key = 'trip_goto' if event_type == 'trip' else 'work_goto'
                            event_time = charging_plan[day][goto_key]
                            
                            if getTime() > event_time:
                                continue
                            
                            emoji = emoji_parse({'trip': True}) if event_type == 'trip' else charging_plan[day]['emoji']
                            battery_level_needed_key = 'trip_battery_level_needed' if event_type == 'trip' else 'work_battery_level_needed'
                            battery_level_needed = charging_plan[day][battery_level_needed_key] if battery_level_needed_key =="work_battery_level_needed" else charging_plan[day][battery_level_needed_key] + charging_plan[day]["trip_battery_level_above_max"]
                                                        
                            cost = charging_plan[day]["trip_total_cost" if event_type == "trip" else "work_total_cost"]
                            
                            solar_percentage = min(solar_percentage, battery_level_needed)
                            
                            if battery_level_cost_percentage > 0.0 and battery_level_cost_per_kwh is not None:
                                grid_battery_level_needed = battery_level_needed - solar_percentage
                                if grid_battery_level_needed > 0.0:
                                    amount = min(grid_battery_level_needed, battery_level_cost_percentage)
                                    grid_battery_level_cost = kwh_to_percentage(battery_level_cost_per_kwh, include_charging_loss=True) * amount
                                    cost += grid_battery_level_cost
                                    battery_level_cost_percentage -= amount
                                    
                                    solar_battery_level_cost = solar_unit * solar_percentage
                                    cost += solar_battery_level_cost
                                    
                                    if battery_level_cost_solar_percentage > 0.0:
                                        solar_amount = min(grid_battery_level_needed, battery_level_cost_solar_percentage)
                                        solar_percentage = min(solar_percentage + solar_amount, battery_level_needed)
                                        battery_level_cost_solar_percentage -= solar_amount
                                        
                                    solar_kwh = percentage_to_kwh(solar_percentage, include_charging_loss=True)
                                
                            if (battery_level_cost_percentage <= 0.0 and battery_level_cost_solar_percentage <= 0.0) or cost == 0.0:
                                if cost == 0.0:
                                    solar_percentage = battery_level_needed
                                
                                if solar_kwh == 0.0:
                                    solar_kwh = percentage_to_kwh(solar_percentage, include_charging_loss=True)
                                
                                solar_cost = solar_unit * solar_kwh
                                cost += solar_cost
                            
                            solar_label = f"{int(solar_percentage)}% {round(solar_kwh, 1)}kWh" if solar_kwh > 0.0 else ""
                            
                            solar_kwh = 0.0
                            solar_percentage = 0.0
                            
                            if charging_plan[day]['workday'] and charging_plan[day]['trip']:
                                total_trip_battery_level_needed = charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max']
                                
                                battery_level_sum = total_trip_battery_level_needed + charging_plan[day]['work_battery_level_needed']
                                if battery_level_sum > 0.0:
                                    if event_type == "trip":
                                        cost = (total_trip_battery_level_needed / battery_level_sum) * cost
                                    else:
                                        cost = (charging_plan[day]['work_battery_level_needed'] / battery_level_sum) * cost
                            
                            temp_events.append({
                                "time": event_time,
                                "data": {
                                    "emoji": emoji,
                                    "day": f"*{getDayOfWeekText(event_time, translate=True).capitalize()}*",
                                    "when": f"*{date_to_string(date = event_time, format = "%d/%m %H:%M")}*",
                                    "solar": solar_label,
                                    "battery_needed": battery_level_needed,
                                    "kwh_needed": percentage_to_kwh(battery_level_needed, include_charging_loss=True),
                                    "cost": cost
                                }
                            })

                    temp_events.sort(key=lambda x: x["time"])

                    for index, event in enumerate(temp_events[:-1]):  # Exclude the last item as it has no next item
                        current_event_date = event["time"].date()
                        next_event_date = temp_events[index + 1]["time"].date()
                        
                        if current_event_date == next_event_date:
                            temp_events[index + 1]["data"]["solar"] = ""
                            break
                            
                    for index, event in enumerate(temp_events):
                        work_overview_key = float(day) + (index / 10.0)
                        work_overview[work_overview_key] = event["data"]
                except Exception as e:
                    _LOGGER.warning(f"Cant create work overview for day {day}: {e}")
            
            unused_solar_kwh[getTimePlusDays(day).date()] = charging_plan[day]['solar_kwh_prediction']
            unused_solar_cost[getTimePlusDays(day).date()] = charging_plan[day]['solar_cost_prediction']
            
            try:
                days_need_between_recommended_full_charge = int(float(get_state(f"input_number.{__name__}_full_charge_recommended", error_state=0)))
                days_since_last_fully_charged = daysBetween(get_state(f"input_datetime.{__name__}_last_full_charge", try_history=True, error_state=resetDatetime()), getTime())
                need_recommended_full_charge = days_need_between_recommended_full_charge != 0 and days_since_last_fully_charged > days_need_between_recommended_full_charge and day == 1
                
                if need_recommended_full_charge:
                    _LOGGER.info(f"Days since last fully charged: {days_since_last_fully_charged}. Need full charge: {need_recommended_full_charge}")
                    
                fill_up = get_state(f"input_boolean.{__name__}_fill_up") == "on" and day in fill_up_days
                
                if fill_up or need_recommended_full_charge:#TODO Add minimum battery level rule
                    rules = []
                    kwh_needed_to_fill_up_day = kwh_needed_to_fill_up_share
                    
                    if need_recommended_full_charge:
                        kwh_needed_to_fill_up_day = max(kwh_needed_for_charging(100.0, battery_level() + charging_plan[day]['solar_prediction']), kwh_needed_to_fill_up_day)
                        _LOGGER.info(f"Needed for full charge: {round(kwh_needed_to_fill_up_day,1)}kWh")
                        rules.append("battery_health")
                    elif fill_up:
                        kwh_needed_to_fill_up_day = max(kwh_needed_for_charging(get_max_recommended_charge_limit_battery_level()), kwh_needed_to_fill_up_day)
                        rules.append("fill_up")
                        
                    if kwh_needed_to_fill_up_day > 0.0:
                        for hour, price in sorted(combinedHourPrices.items(), key=lambda kv: (kv[1],kv[0])):
                            hour_in_chargeHours, kwhAvailable = kwh_available_in_hour(hour)
                            if hour_in_chargeHours and not kwhAvailable:
                                continue
                            
                            what_day = daysBetween(getTime(), hour)
                            battery_level_id, max_recommended_charge_limit_battery_level = what_battery_level(what_day, hour, price, day)
                            if need_recommended_full_charge:
                                max_recommended_charge_limit_battery_level = 100.0 #Ignore solar over production
                                
                                if not is_ev_configured(): #Sets battery level to 0.0 at midnight
                                    battery_level_id = "battery_level_at_midnight"
                            else:
                                if not battery_level_id:
                                    continue

                            if hour <= last_charging and hour >= current_hour:
                                very_cheap_price, ultra_cheap_price = cheap_price_check(price)
                                if charging_plan['workday_in_week'] and not very_cheap_price and not ultra_cheap_price:
                                    continue
                            
                                if ultra_cheap_price:
                                    rules.append("half_min_avg_price")
                                elif very_cheap_price:
                                    rules.append("under_min_avg_price")
                                
                                if kwh_needed_to_fill_up_day <= 0.01:
                                    break
                                elif kwh_needed_to_fill_up_day > 0.0:
                                    kwh_needed_to_fill_up_day, totalCost, totalkWh, battery_level_added = add_to_charge_hours(kwh_needed_to_fill_up_day, totalCost, totalkWh, hour, price, None, None, kwhAvailable, sum(charging_plan[what_day][battery_level_id]), max_recommended_charge_limit_battery_level, rules)
                                    #_LOGGER.error(f"{hour}: {battery_level_added} {kwh_needed_to_fill_up_day}, {totalCost}, {totalkWh}, {hour}, {price}, {None}, {None}, {kwhAvailable}, {sum(charging_plan[what_day][battery_level_id])}, {max_recommended_charge_limit_battery_level}, {rules}")
                                    
                                    very_cheap_kwh_needed_today -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                    ultra_cheap_kwh_needed_today -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                
                                elif ultra_cheap_price and ultra_cheap_kwh_needed_today > 0.0:
                                    ultra_cheap_kwh_needed_today, totalCost, totalkWh, battery_level_added = add_to_charge_hours(ultra_cheap_kwh_needed_today, totalCost, totalkWh, hour, price, very_cheap_price, ultra_cheap_price, kwhAvailable, sum(charging_plan[what_day][battery_level_id]), max_recommended_charge_limit_battery_level, rules)
                                    very_cheap_kwh_needed_today -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                    kwh_needed_to_fill_up_day -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                    
                                elif very_cheap_price and very_cheap_kwh_needed_today > 0.0:
                                    very_cheap_kwh_needed_today, totalCost, totalkWh, battery_level_added = add_to_charge_hours(very_cheap_kwh_needed_today, totalCost, totalkWh, hour, price, very_cheap_price, ultra_cheap_price, kwhAvailable, sum(charging_plan[what_day][battery_level_id]), max_recommended_charge_limit_battery_level, rules)
                                    ultra_cheap_kwh_needed_today -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                    kwh_needed_to_fill_up_day -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                else:
                                    continue
                                
                                if hour in chargeHours and battery_level_added:
                                    charging_sessions_id = add_charging_session_to_day(hour, what_day, battery_level_id)
                                    add_charging_to_days(day, what_day, charging_sessions_id, battery_level_added)
                        kwh_needed_to_fill_up_day -= kwh_needed_to_fill_up_share
            except Exception as e:
                _LOGGER.warning(f"Cant create fill up or need recommended full charge for day {day}: {e}")
            
            try: #Alternative charging estimate
                diff_alternative = battery_level() - (
                    get_max_recommended_charge_limit_battery_level() - (
                        max(
                            charging_plan[day]['work_battery_level_needed'] + get_min_daily_battery_level(),
                            get_min_daily_battery_level()
                        ) if day != 0 else 0
                    )
                )
                extra_charge_alternative = True if diff_alternative < 0.0 else False
                
                if (day >= 0 and (charging_plan[day_after]['workday'] or charging_plan[day_after]["trip"])) or (day == 0 and extra_charge_alternative):
                    charger_status = get_state(CONFIG['charger']['entity_ids']['status_entity_id'], float_type=False, error_state="unavailable")
                    
                    homecoming_alternative = min([date for date in [charging_plan[day_before]['homecoming'], charging_plan[day_before]['trip_homecoming'], getTime() if day == 0 and charger_status in ["awaiting_authorization", "awaiting_start", "charging", "ready_to_charge", "completed"] else None] if date is not None])
                    last_charging_alternative = min([date for date in [charging_plan[day_after]['work_last_charging'], charging_plan[day_after]['trip_goto']] if date is not None])
                    used_battery_level_alternative = get_min_daily_battery_level() + charging_plan[day_after]['work_battery_level_needed']

                    if day == 0 and extra_charge_alternative:
                        diff = abs(diff_alternative)
                        used_battery_level_alternative += diff
                                    
                    if charging_plan[day_after]["trip"]:
                        diff_min_alternative = max(get_min_daily_battery_level() - get_min_trip_battery_level(), 0.0)
                        used_battery_level_alternative += charging_plan[day_after]['trip_battery_level_needed'] + charging_plan[day_after]['trip_battery_level_above_max'] + diff_min_alternative
                        
                    kwh_needed_today_alternative = kwh_needed_for_charging(used_battery_level_alternative - charging_plan[day_before]['solar_prediction'], get_min_daily_battery_level())
                    
                    for hour, price in sorted(combinedHourPrices.items(), key=lambda kv: (kv[1],kv[0])):
                        if hour <= last_charging_alternative and hour >= homecoming_alternative:
                            working, on_trip = available_for_charging_prediction(hour, trip_date_time, trip_homecoming_date_time)
                            if working or on_trip:
                                continue
                            
                            if kwh_needed_today_alternative > 0.0:
                                if (kwh_needed_today_alternative - MAX_KWH_CHARGING) < 0.0:
                                    cost = kwh_needed_today_alternative * price
                                    totalkWh_alternative += kwh_needed_today_alternative
                                    kwh_needed_today_alternative = 0.0
                                else:
                                    kwh_needed_today_alternative = kwh_needed_today_alternative - MAX_KWH_CHARGING
                                    cost = MAX_KWH_CHARGING * price
                                    totalkWh_alternative += MAX_KWH_CHARGING
                                totalCost_alternative += cost
                            else:
                                break
            except Exception as e:
                _LOGGER.warning(f"Cant create alternative charging estimate for day {day}: {e}")
            
            try:
                if charging_plan[day]['solar_prediction'] > 0.0:
                    date = date_to_string(date = charging_plan[day]['work_goto'], format = "%d/%m")
                    
                    location = sun.get_astral_location(hass)
                    sunrise = location[0].sunrise(charging_plan[day]['work_goto']).replace(tzinfo=None)
                    sunrise_text = f"{emoji_parse({'sunrise': True})}{date_to_string(date = sunrise, format = '%H:%M')}"
                    sunset = location[0].sunset(charging_plan[day]['homecoming']).replace(tzinfo=None)
                    sunset_text = f"{emoji_parse({'sunset': True})}{date_to_string(date = sunset, format = '%H:%M')}"
                    
                    timeperiod = []
                    if charging_plan[day]['trip_goto']:
                        if sunrise <= charging_plan[day]['trip_goto']:
                            timeperiod.append(f"{sunrise_text}-{emoji_parse({'trip': True})}{date_to_string(date = charging_plan[day]['trip_goto'], format = '%H:%M')}")
                            if sunset >= charging_plan[day]['trip_homecoming']:
                                timeperiod.append("<br>")
                        if sunset >= charging_plan[day]['trip_homecoming']:
                            timeperiod.append(f"{emoji_parse({'homecoming': True})}{date_to_string(date = charging_plan[day]['trip_homecoming'], format = '%H:%M')}-{sunset_text}")
                        
                    elif charging_plan[day]['work_goto'] == charging_plan[day]['homecoming'] and not charging_plan[day]['trip_goto']:
                        timeperiod.append(f"{sunrise_text}-{sunset_text}")
                    else:
                        if sunrise <= charging_plan[day]['work_goto']:
                            timeperiod.append(f"{sunrise_text}-{emoji_parse({'goto': True})}{date_to_string(date = charging_plan[day]['work_goto'], format = '%H:%M')}")
                            if sunset >= charging_plan[day]['homecoming']:
                                timeperiod.append("<br>")
                        if sunset >= charging_plan[day]['homecoming']:
                            timeperiod.append(f"{emoji_parse({'homecoming': True})}{date_to_string(date = charging_plan[day]['homecoming'], format = '%H:%M')}-{sunset_text}")
                        
                    solar_over_production[day] = {
                        "day": f"{getDayOfWeekText(charging_plan[day]['work_goto'], translate = True).capitalize()}",
                        "date": date,
                        "when": " ".join(timeperiod),
                        "emoji": emoji_parse({'solar': True}),
                        "percentage": charging_plan[day]['solar_prediction'],
                        "kWh": charging_plan[day]['solar_kwh_prediction']
                    }
            except Exception as e:
                _LOGGER.warning(f"Cant create solar over production prediction for day {day}: {e}")
                    
                
            if charging_plan[day]['trip']:
                total_trip_battery_level_needed = max((charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max'] - get_min_trip_battery_level()), 0.0) * -1
                charging_plan[day]['battery_level_at_midnight'].append(total_trip_battery_level_needed)
                
        return [totalCost, totalkWh]
    
    trip_planned = is_trip_planned()
    trip_date_time = get_trip_date_time() if get_trip_date_time() != resetDatetime() and trip_planned else None
    trip_homecoming_date_time = get_trip_homecoming_date_time() if get_trip_homecoming_date_time() != resetDatetime() and trip_planned else None
    trip_range = get_trip_range() if get_trip_range() != 0.0 and trip_planned else None
    trip_target_level = get_trip_target_level() if get_trip_target_level() != 0.0 and trip_planned else None
    
    solar_available_prediction_output = solar_available_prediction(trip_date_time, trip_homecoming_date_time)
    
    solar_kwh_prediction = solar_available_prediction_output[0]
    solar_price_prediction = solar_available_prediction_output[1]
    
    total_kwh_from_solar_available = solar_kwh_prediction['today']
    total_solar_price = [solar_price_prediction['today']]
    
    if is_solar_configured():
        attr_dict = {
            today.date(): f"{round(total_kwh_from_solar_available, 2)}% {round((total_kwh_from_solar_available * average(total_solar_price)), 2)}kr"
            }
        
        for date in [today + datetime.timedelta(days=1), today + datetime.timedelta(days=2), today + datetime.timedelta(days=3), today + datetime.timedelta(days=4)]:
            attr_dict[date.date()] = f"{round(kwh_to_percentage(solar_kwh_prediction[date], include_charging_loss = True), 2)}% {round((solar_kwh_prediction[date] * solar_price_prediction[date]), 2)}kr"
            total_kwh_from_solar_available += solar_kwh_prediction[date]
            total_solar_price.append(solar_price_prediction[date])
    
        attr_dict['Total'] = f"{round(kwh_to_percentage(total_kwh_from_solar_available, include_charging_loss = True), 2)}% {round(total_kwh_from_solar_available * average(total_solar_price), 2)}kr"
        set_attr(f"sensor.{__name__}_charge_very_cheap_battery_level.unused_solar_production_availability_prediction", attr_dict)
        set_attr(f"sensor.{__name__}_charge_ultra_cheap_battery_level.unused_solar_production_availability_prediction", attr_dict)
    
    ev_charge_very_cheap_battery_level = max(0, int(round(get_very_cheap_grid_charging_max_battery_level() - kwh_to_percentage(total_kwh_from_solar_available, include_charging_loss = True), 0)))
    ev_charge_ultra_cheap_battery_level = max(0, int(round(get_ultra_cheap_grid_charging_max_battery_level() - kwh_to_percentage(total_kwh_from_solar_available, include_charging_loss = True), 0)))
    
    set_state(f"sensor.{__name__}_charge_very_cheap_battery_level", f"{ev_charge_very_cheap_battery_level}%")
    set_state(f"sensor.{__name__}_charge_ultra_cheap_battery_level", f"{ev_charge_ultra_cheap_battery_level}%")
    
    workday_rules =["first_workday_preparation", "second_workday_preparation", "third_workday_preparation", "fourth_workday_preparation", "fifth_workday_preparation", "sixth_workday_preparation", "seventh_workday_preparation"]
    workday_labels =["Første arbejdsdag", "Anden arbejdsdag", "Tredje arbejdsdag", "Fjerde arbejdsdag", "Femte arbejdsdag", "Sjette arbejdsdag", "Syvende arbejdsdag"]
    workday_emoji = []
    
    for i, rule in enumerate(workday_rules):
        workday_labels[i] =  f"{emoji_parse({rule: True})} {workday_labels[i]}"
        workday_emoji.append(f"{emoji_parse({rule: True})}")
    
    for day in range(8):
        midnight_datetime = getTimeEndOfDay() + datetime.timedelta(days=day)
        day_text = getDayOfWeekText(midnight_datetime)
        
        charging_plan[day] = {
            "trip": False,
            "trip_goto": None,
            "trip_homecoming": None,
            "trip_last_charging": None,
            "trip_kwh_needed": 0.0,
            "trip_battery_level_needed": 0.0,
            "trip_battery_level_above_max": 0.0,
            "trip_total_cost": 0.0,
            "workday": False,
            "work_range_needed": 0.0,
            "work_battery_level_needed": 0.0,
            "work_kwh_needed": 0.0,
            "work_goto": midnight_datetime,
            "work_last_charging": midnight_datetime,
            "work_total_cost": 0.0,
            "homecoming": midnight_datetime,
            "total_needed_battery_level": 0.0,
            "day_text": day_text,
            "label": None,
            "emoji": "",
            "rules": [],
            "battery_level_before_work": [],
            "battery_level_after_work": [],
            "battery_level_at_midnight": [],
            "charging_sessions": {}
        }
        
        if get_state(f"input_boolean.{__name__}_workday_{day_text}") == "on" and get_state(f"input_boolean.{__name__}_days_to_charge") == "on":
            work_goto = midnight_datetime.replace(hour=get_state(f'input_datetime.{__name__}_days_to_charge_{day_text}').hour, minute=get_state(f'input_datetime.{__name__}_days_to_charge_{day_text}').minute, second=0)
                
            diff = minutesBetween(now, work_goto)
            if day == 0 and ready_to_charge() and in_between(diff, CHARGING_ALLOWED_AFTER_GOTO_TIME, 0):
                work_goto = work_goto + datetime.timedelta(hours=1)

            if (day == 0 and now < work_goto) or day > 0:
                
                charging_plan['workday_in_week'] = True
                charging_plan[day]['workday'] = True
                
                charging_plan[day]['work_goto'] = work_goto
                charging_plan[day]['homecoming'] = midnight_datetime.replace(hour=get_state(f'input_datetime.{__name__}_{day_text}_homecoming').hour, minute=get_state(f'input_datetime.{__name__}_{day_text}_homecoming').minute, second=0)
                
                hours_before = max(1, min(2, hoursBetween(now, charging_plan[day]['work_goto'])))
                charging_plan[day]['work_last_charging'] = reset_time_to_hour(work_goto) - datetime.timedelta(hours=hours_before)
                
                charging_plan[day]['work_range_needed'] = get_entity_daily_distance()
                charging_plan[day]['work_battery_level_needed'] = calc_distance_to_battery_level(charging_plan[day]['work_range_needed'])
            
                if len(workday_labels) > 0:
                    charging_plan[day]['label'] = workday_labels.pop(0)
                    charging_plan[day]['emoji'] = workday_emoji.pop(0)
                    charging_plan[day]['rules'].append(workday_rules.pop(0))
                    
        if is_trip_planned() and trip_date_time and day == daysBetween(getTime(), trip_date_time):
            charging_plan[day]['trip'] = True
            charging_plan[day]['trip_goto'] = trip_date_time
            charging_plan[day]['trip_homecoming'] = trip_homecoming_date_time
            
            diff = minutesBetween(now, charging_plan[day]['trip_goto'])
            if day == 0 and ready_to_charge() and in_between(diff, CHARGING_ALLOWED_AFTER_GOTO_TIME, 0):
                charging_plan[day]['trip_goto'] = charging_plan[day]['trip_goto'] + datetime.timedelta(hours=1)
                
            hours_before = max(1, min(2, hoursBetween(now, charging_plan[day]['trip_goto'])))
            
            charging_plan[day]['trip_last_charging'] = reset_time_to_hour(charging_plan[day]['trip_goto']) - datetime.timedelta(hours=hours_before)
            charging_plan[day]['rules'].append("trip")
            
            if trip_range:
                charging_plan[day]['trip_battery_level_needed'] = range_to_battery_level(trip_range, get_min_trip_battery_level())
                trip_target_level = charging_plan[day]['trip_battery_level_needed']
            elif trip_target_level:
                charging_plan[day]['trip_battery_level_needed'] = trip_target_level
                
            max_recommended_battery_level = max(get_max_recommended_charge_limit_battery_level(), battery_level())
            
            if charging_plan[day]['trip_battery_level_needed'] > max_recommended_battery_level and getTime() <= charging_plan[day]['trip_goto']:
                charging_plan[day]['trip_battery_level_above_max'] = charging_plan[day]['trip_battery_level_needed'] - max_recommended_battery_level
                charging_plan[day]['trip_battery_level_needed'] -= charging_plan[day]['trip_battery_level_above_max']
                trip_kwh_needed = percentage_to_kwh(charging_plan[day]['trip_battery_level_above_max'], include_charging_loss=True)
                charging_hours = int(round_up(trip_kwh_needed / MAX_KWH_CHARGING))
                
                last_charging = charging_plan[day]['trip_last_charging']
                
                if charging_plan[day]['workday'] and \
                ((charging_plan[day]['trip_last_charging'] < charging_plan[day]['homecoming'] and charging_plan[day]['trip_last_charging'] > charging_plan[day]['work_last_charging']) or \
                (getTime() > charging_plan[day]['work_last_charging'] and battery_level() < max_recommended_battery_level - 1)):
                    charging_plan[day]['trip_last_charging'] = max(charging_plan[day]['work_last_charging'], reset_time_to_hour(getTime()))
                    last_charging = charging_plan[day]['trip_last_charging']

                for i in range(charging_hours):
                    charging_hour = last_charging - datetime.timedelta(hours=i)
                    
                    try:
                        hour_in_chargeHours, kwhAvailable = kwh_available_in_hour(charging_hour)
                        very_cheap_price, ultra_cheap_price = cheap_price_check(combinedHourPrices[charging_hour])
                        
                        trip_kwh_needed, totalCost, totalkWh, battery_level_added = add_to_charge_hours(trip_kwh_needed, totalCost, totalkWh, charging_hour, combinedHourPrices[charging_hour], very_cheap_price, ultra_cheap_price, kwhAvailable, max_recommended_battery_level, trip_target_level, ['trip'])
                        charging_plan[day]['trip_kwh_needed'] += percentage_to_kwh(battery_level_added, include_charging_loss=False)
                        charging_plan[day]["trip_total_cost"] += chargeHours[charging_hour]["Cost"]
                        
                        if charging_plan[day]['trip_goto'] >= charging_plan[day]['work_goto']:
                            charging_plan[day]['battery_level_after_work'].append(battery_level_added)
                        else:
                            charging_plan[day]['battery_level_before_work'].append(battery_level_added)
                            charging_plan[day]['battery_level_after_work'].append(battery_level_added)
                    
                        charging_sessions_id = "battery_level_after_work" if charging_plan[day]['trip_goto'] >= charging_plan[day]['work_goto'] else "battery_level_before_work"
                        if charging_sessions_id not in charging_plan[day]['charging_sessions']:
                            charging_plan[day]['charging_sessions'][charging_sessions_id] = {}
                        charging_plan[day]['charging_sessions'][charging_sessions_id][charging_hour] = chargeHours[charging_hour]
                    except Exception as e:
                        _LOGGER.warning(f"Date not yet in database: {charging_hour} ({e})")
                
        charging_plan[day]['trip_battery_level_needed'] = max(charging_plan[day]['trip_battery_level_needed'], 0.0)
        
        charging_plan[day]['total_needed_battery_level'] = (charging_plan[day]['work_battery_level_needed'] + get_min_daily_battery_level()) if charging_plan[day]['workday'] else 0.0
        charging_plan[day]['total_needed_battery_level'] += charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max']
        charging_plan[day]['total_needed_battery_level'] = min(round_up(charging_plan[day]['total_needed_battery_level']), 100.0)
        
        total_solar_available = 0.0
        total_solar_available_price = []
        if day == 0 and (getTime() >= charging_plan[day]['homecoming'] or not charging_plan[day]['workday']):
            total_solar_available += solar_kwh_prediction['today']
            total_solar_available_price.append(solar_price_prediction['today'])
        elif 1 <= day <= 5 and (today + datetime.timedelta(days=day)) in solar_kwh_prediction:
            total_solar_available += solar_kwh_prediction[today + datetime.timedelta(days=day)]
            total_solar_available_price.append(solar_price_prediction[today + datetime.timedelta(days=day)])
        else:
            total_solar_available += solar_kwh_prediction['avg']
            total_solar_available_price.append(solar_price_prediction['avg'])
        
        charging_plan[day]['solar_prediction'] = round(kwh_to_percentage(total_solar_available, include_charging_loss = True), 2)
        charging_plan[day]['solar_kwh_prediction'] = round(total_solar_available, 2)
        charging_plan[day]['solar_cost_prediction'] = round((total_solar_available * average(total_solar_available_price)), 2)
        
        if not charging_plan[day]['rules']:
            charging_plan[day]['rules'].append("no_rule")

    totalCost, totalkWh = future_charging(totalCost, totalkWh)
    
    chargeHours['TotalCost'] = totalCost
    chargeHours['TotalkWh'] = totalkWh
    chargeHours['TotalProcent'] = round(kwh_to_percentage(totalkWh, include_charging_loss = True), 2)
    
    countExpensive = 0
    expensiveList = []
    
    for hour, price in sorted(hourPrices.items(), key=lambda kv: (kv[1],kv[0]), reverse=True):
        if countExpensive < 4:
            expensiveList.append(hour)
        else:
            break
        countExpensive += 1
        
    chargeHours['ExpensiveHours'] = expensiveList
    
    todays_max_battery_level = max(sum(charging_plan[0]["battery_level_before_work"]), sum(charging_plan[0]["battery_level_at_midnight"]), sum(charging_plan[0]["battery_level_after_work"]))
    tomorrow_max_battery_level = max(sum(charging_plan[1]["battery_level_before_work"]), sum(charging_plan[1]["battery_level_at_midnight"]), sum(charging_plan[1]["battery_level_after_work"]))
    chargeHours['MaxChargingLevelToday'] = round(max(todays_max_battery_level, tomorrow_max_battery_level, charging_plan[day]['total_needed_battery_level'], get_min_charge_limit_battery_level()), 2)
    '''_LOGGER.error(f"todays_max_battery_level:{todays_max_battery_level}")
    _LOGGER.error(f"tomorrow_max_battery_level:{tomorrow_max_battery_level}")
    _LOGGER.error(f"charging_plan[day]['total_needed_battery_level']:{charging_plan[day]['total_needed_battery_level']}")
    _LOGGER.error(f"get_min_charge_limit_battery_level:{get_min_charge_limit_battery_level()}")
    _LOGGER.error(f"chargeHours['MaxChargingLevelToday']:{chargeHours['MaxChargingLevelToday']}")'''

    for day in charging_plan.keys():
        if not isinstance(day, int): continue
        charging_plan[day]['battery_level_before_work_sum'] = sum(charging_plan[day]['battery_level_before_work'])
        charging_plan[day]['battery_level_after_work_sum'] = sum(charging_plan[day]['battery_level_after_work'])
        charging_plan[day]['battery_level_at_midnight_sum'] = sum(charging_plan[day]['battery_level_at_midnight'])
        
    _LOGGER.info(f"charging_plan:\n{pformat(charging_plan, width=200, compact=True)}")
    _LOGGER.info(f"chargeHours:\n{pformat(chargeHours, width=200, compact=True)}")
    
    overview = []
    
    try:
        charging_plan_list = {}
        
        for hour, value in sorted({k: v for k, v in chargeHours.items() if type(k) is datetime.datetime}.items(), key=lambda kv: (kv[0])):
            if type(hour) is datetime.datetime:
                charging_plan_list[hour] = {
                    "when": f"{hour.strftime('%d/%m %H:%M')}",
                    "type": f"{emoji_parse(chargeHours[hour])}",
                    "percentage": f"{int(round(chargeHours[hour]['battery_level'],0))}",
                    'kWh': f"{round(chargeHours[hour]['kWh'], 2):.2f}",
                    "cost": f"{round(chargeHours[hour]['Cost'], 2):.2f}",
                    "unit": f"{round(chargeHours[hour]['Price'], 2):.2f}"
                }
        
        overview.append("## Lade oversigt ##")
        overview.append("<center>\n")
        
        if charging_plan_list:
            
            if charging_plan_list:
                overview.append("|  | Tid | % | kWh | Kr/kWh | Pris |")
                overview.append("|---:|:---:|---:|---:|:---:|---:|")
                
                for d in charging_plan_list.values():
                    d['when'] = f"**{d['when']}**" if d['when'] else ""
                    d['type'] = f"**{d['type']}**" if d['type'] else ""
                    d['percentage'] = f"**{d['percentage']}**" if d['percentage'] else ""
                    d['kWh'] = f"**{d['kWh']}**" if d['kWh'] else ""
                    d['cost'] = f"**{d['cost']}**" if d['cost'] else ""
                    d['unit'] = f"**{d['unit']}**" if d['unit'] else ""
                    overview.append(f"| {d['type']} | {d['when']} | {d['percentage']} | {d['kWh']} | {d['unit']} | {d['cost']} |")
            
            if totalkWh > 0.0:
                overview.append(f"\n**Ialt {int(round(chargeHours['TotalProcent'],0))}% {chargeHours['TotalkWh']} kWh {chargeHours['TotalCost']:.2f} kr ({round(chargeHours['TotalCost'] / chargeHours['TotalkWh'],2)} kr)**")
            
            if USING_OFFLINE_PRICES:
                overview.append(f"\n**Bruger offline priser til nogle timepriser!!!**")
            
            if work_overview:
                overview.append("***")
        else:
            overview.append(f"**Ingen kommende ladning planlagt**")
            
            if work_overview and solar_over_production:
                overview.append("**Nok i solcelle overproduktion**")
            
        overview.append("</center>\n")
    except Exception as e:
        _LOGGER.error(f"Failed to create charging plan overview: {e}")
        _LOGGER.error(f"USING_OFFLINE_PRICES: {USING_OFFLINE_PRICES}")
        _LOGGER.error(f"charging_plan:\n{pformat(charging_plan, width=200, compact=True)}")
        _LOGGER.error(f"chargeHours:\n{pformat(chargeHours, width=200, compact=True)}")
    
    try:
        if work_overview:
            overview.append("## Afgangsplan ##")
            overview.append("<center>\n")
            
            work_overview_total_kwh = 0.0
            work_overview_total_cost = 0.0
            
            if work_overview:
                solar_header = f"{emoji_parse({'solar': True})}Sol" if is_solar_configured() else ""
                overview.append(f"|  | Dag | Behov | {solar_header} | Pris |")
                overview.append(f"|:---|:---:|:---:|:---:|:---:|")
                
                
                for d in work_overview.values():
                    work_overview_total_kwh += d['kwh_needed']
                    work_overview_total_cost += d['cost']
                    
                    d['emoji'] = f"**{emoji_text_format(d['emoji'])}**" if d['emoji'] else ""
                    d['day'] = f"**{d['day']}**" if d['day'] else ""
                    d['when'] = f"**{d['when']}**" if d['when'] else ""
                    d['solar'] = f"**{d['solar']}**" if d['solar'] and is_solar_configured() else ""
                    d['battery_needed'] = f"**{int(d['battery_needed'])}**" if d['battery_needed'] else ""
                    d['kwh_needed'] = f"**{round(d['kwh_needed'], 1)}**" if d['kwh_needed'] else ""
                    d['cost'] = f"**{d['cost']:.2f}**" if d['cost'] else ""
                    
                    overview.append(f"| {d['emoji']} | {d['day']}<br>{d['when']} | {d['battery_needed']}% {d['kwh_needed']}kWh | {d['solar']} | {d['cost']} |")
            else:
                overview.append(f"**Ingen kommende arbejdsdag**")
                
            if work_overview_total_kwh > 0.0 and totalkWh_alternative > 0.0:
                overview.append(f"\n**Ialt {round(work_overview_total_kwh, 1)}kWh {round(work_overview_total_cost, 2)}kr ({round(work_overview_total_cost / work_overview_total_kwh,2)} kr/kwh)**<br>Skøn ved daglig opladning {round((totalCost_alternative / totalkWh_alternative) * max(work_overview_total_kwh, totalkWh_alternative),2)}kr {round(totalCost_alternative / totalkWh_alternative,2)}kr/kwh")
            
            if solar_over_production:
                overview.append("***")
            overview.append("</center>\n")
    except Exception as e:
        _LOGGER.error(f"Failed to create work overview: {e}")
        _LOGGER.error(f"work_overview: {work_overview}")
        _LOGGER.error(f"charging_plan:\n{pformat(charging_plan, width=200, compact=True)}")
        _LOGGER.error(f"chargeHours:\n{pformat(chargeHours, width=200, compact=True)}")
    
    try:
        if solar_over_production:
            overview.append("## Solcelle over produktion ##")
            overview.append("<center>\n")
            
            if solar_over_production:
                overview.append("| Tid |  |  |  | % |  | kWh |")
                overview.append("|---|---:|:---|---:|---:|---|---:|")
                
                for d in solar_over_production.values():
                    d['day'] = f"**{d['day']}**" if d['day'] else ""
                    d['date'] = f"**{d['date']}**" if d['date'] else ""
                    d['when'] = f"**{d['when']}**" if d['when'] else ""
                    d['emoji'] = f"**{emoji_text_format(d['emoji'])}**" if d['emoji'] else ""
                    d['percentage'] = f"**{round(d['percentage'], 1)}**" if d['percentage'] else "**0**"
                    d['kWh'] = f"**{round(d['kWh'], 1)}**" if d['kWh'] else "**0.0**"
                    overview.append(f"| {d['day']} | {d['date']} | {d['when']} | {d['emoji']} | {d['percentage']} |  | {d['kWh']} |")
            else:
                overview.append(f"**Ingen kommende arbejdsdag**")
                
            overview.append("</center>\n")
    except Exception as e:
        _LOGGER.error(f"Failed to create solar over production overview: {e}")
        _LOGGER.error(f"solar_over_production: {solar_over_production}")
        _LOGGER.error(f"charging_plan:\n{pformat(charging_plan, width=200, compact=True)}")
        _LOGGER.error(f"chargeHours:\n{pformat(chargeHours, width=200, compact=True)}")
    
    
    if overview:
        overview.append("<center>\n")
        overview.append(f"##### Sidst planlagt {getTime()} #####")
        overview.append("</center>\n")
        
        set_attr(f"sensor.{__name__}_overview.overview", "\n".join(overview))
    else:
        set_attr(f"sensor.{__name__}_overview.overview", "Ingen data")
        
    return chargeHours

def calc_charging_amps(power = 0.0, report = False):
    _LOGGER = globals()['_LOGGER'].getChild("calc_charging_amps")
    power = float(power)
    power = power

    minWatt = SOLAR_CHARGING_TRIGGER_ON - 50
    powerDict = {
        minWatt: {
            "amp": 0.0,
            "phase": CONFIG['charger']['charging_phases'],
            "watt": 0.0
            }
        }
    for i in range(int(CONFIG['solar']['charging_single_phase_min_amp']),int(CONFIG['solar']['charging_single_phase_max_amp']) + 1):
        watt = float(i) * CONFIG['charger']['power_voltage']
        powerDict[watt] = {
            "amp": float(i),
            "phase": 1.0,
            "watt": watt
        }

    maxSinglePhaseWatt = max(powerDict.keys())

    for i in range(int(CONFIG['solar']['charging_three_phase_min_amp']),int(CONFIG['charger']['charging_max_amp']) + 1):
        watt = float(i) * (CONFIG['charger']['power_voltage']  * CONFIG['charger']['charging_phases'])
        if maxSinglePhaseWatt < watt:
            powerDict[watt] = {
                "amp": float(i),
                "phase": CONFIG['charger']['charging_phases'],
                "watt": watt
            }
    
    if report:
        if is_solar_configured():
            example_1 = 500 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            example_2 = 1500 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            example_3 = 3000 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            example_4 = 4000 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            example_5 = 5000 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            _LOGGER.info(f"Voltage above(+)/under(-) overproduction available: {CONFIG['solar']['allow_grid_charging_above_solar_available']}W examples:")
            _LOGGER.info(f"  1. overproduction 500W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_1}W {get_closest_key(example_1, powerDict)}")
            _LOGGER.info(f"  2. overproduction 1500W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_2}W {get_closest_key(example_2, powerDict)})")
            _LOGGER.info(f"  3. overproduction 3000W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_3}W {get_closest_key(example_3, powerDict)})")
            _LOGGER.info(f"  4. overproduction 4000W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_4}W {get_closest_key(example_4, powerDict)})")
            _LOGGER.info(f"  5. overproduction 5000W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_5}W {get_closest_key(example_5, powerDict)})")
            
        for key in sorted(powerDict):
            _LOGGER.info(f"{key}: {powerDict[key]}")
    output = get_closest_key(power, powerDict)
    return [output['phase'], output['amp'], output['watt']]

def set_charger_charging_amps(phase = None, amps = None, watt = 0.0):
    _LOGGER = globals()['_LOGGER'].getChild("set_charger_charging_amps")
    #Remember to add * before *calc_charging_amps(.......)..
    global CURRENT_CHARGING_AMPS
    
    if phase is None:
        phase = CONFIG['charger']['charging_phases']
    if amps is None:
        amps = CONFIG['charger']['charging_max_amp']
    
    successful = False
    phase_1 = 0
    phase_2 = 0
    phase_3 = 0
    
    if phase >= 1.0: phase_1 = int(amps)
    if phase >= 2.0: phase_2 = int(amps)
    if phase == 3.0: phase_3 = int(amps)
    
    if not is_entity_configured(CONFIG['charger']['entity_ids']['dynamic_circuit_limit']):
        CURRENT_CHARGING_AMPS = [phase_1, phase_2, phase_3]
        return
    
    watt = sum([phase_1, phase_2, phase_3]) * CONFIG['charger']['power_voltage']
        
    if TESTING:
        CURRENT_CHARGING_AMPS = [phase_1, phase_2, phase_3]
        _LOGGER.info(f"TESTING not setting chargers charging amps to {phase_1}/{phase_2}/{phase_3} watt:{watt}")
        return
    
    try:
        charger_id = get_attr(CONFIG['charger']['entity_ids']['status_entity_id'], "id", error_state=None)
        if not charger_id:
            raise Exception(f"No charger id found for {CONFIG['charger']['entity_ids']['status_entity_id']} return id: {str(charger_id)}")
        
        if service.has_service("easee", "set_circuit_dynamic_limit"):
            service.call("easee", "set_circuit_dynamic_limit", blocking=True,
                                charger_id=get_attr(CONFIG['charger']['entity_ids']['status_entity_id'], "id"),
                                current_p1=phase_1,
                                current_p2=phase_2,
                                current_p3=phase_3,
                                time_to_live=60)
        else:
            raise Exception("Easee integration dont has service set_circuit_dynamic_limit")
        
        if service.has_service("easee", "set_charger_dynamic_limit"):
            service.call("easee", "set_charger_dynamic_limit", blocking=True,
                                charger_id=get_attr(CONFIG['charger']['entity_ids']['status_entity_id'], "id"),
                                current=max(phase_1, phase_2, phase_3))
        else:
            raise Exception("Easee integration dont has service set_charger_dynamic_limit")
        successful = True
        
        _LOGGER.info(f"Setting chargers({charger_id}) charging amps to {phase_1}/{phase_2}/{phase_3} watt:{watt}")
    except Exception as e:
        _LOGGER.warning(f"Cant set dynamic amps on charger: {e}")
        _LOGGER.warning(f"Setting ev cars charging amps to {amps}")
        try:
            if not is_ev_configured():
                raise Exception(f"{e}")
            
            if not is_entity_available(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id']):
                raise Exception(f"Ev charging amps unavailable: {CONFIG['ev_car']['entity_ids']['charging_amps_entity_id']}")
            
            max_amps = float(get_attr(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id'], "max"))
            amps = min(amps, max_amps)
            if phase_2 == 0 and phase_3 == 0:
                amps = int(CONFIG['solar']['charging_single_phase_max_amp'])
            else:
                amps = int(CONFIG['charger']['charging_max_amp'])
                
            amps = min(amps, min([phase for phase in (phase_1, phase_2, phase_3) if phase > 0], default=0))
            successful = True
        
        except Exception as e_second:
            _LOGGER.error(f"Cant set charging amps: {e_second}")
    finally:
        try:
            if is_ev_configured() and is_entity_available(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id']):
                max_amps = float(get_attr(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id'], "max"))
                current_amps = float(get_state(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id']))
                if current_amps == 0.0:
                    _LOGGER.info(f"Ev charging amps was set to 0 amps, setting ev to max {max_amps}")
                    ev_send_command(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id'], max_amps)
        except Exception as e:
            _LOGGER.warning(f"Cant set ev charging amps to {CONFIG['charger']['charging_max_amp']}")
            
            
    if successful:
        CURRENT_CHARGING_AMPS = [phase_1, phase_2, phase_3]
    else:
        _LOGGER.warning(f"Cant set charger to phase:{phase} amps:{phase_1}/{phase_2}/{phase_3} watt:{watt}")

def power_from_ignored(from_time_stamp, to_time_stamp):
    _LOGGER = globals()['_LOGGER'].getChild("power_from_ignored")
    
    def average_since_sum(entity_id):
        if entity_id == "" or entity_id is None: return 0.0

        try:
            avg = float(get_average_value(entity_id, from_time_stamp, to_time_stamp, convert_to="W", error_state=0.0))
            return avg
        except Exception:
            return 0.0

    total = 0.0
    try:
        if CONFIG['home']['entity_ids']['ignore_consumption_from_entity_ids']:
            for entity_id in CONFIG['home']['entity_ids']['ignore_consumption_from_entity_ids']:
                total += average_since_sum(entity_id)
    except Exception as e:
        _LOGGER.warning(f"Cant get ignore values from {from_time_stamp} to {to_time_stamp}: {e}")
    return round(total, 2)

def power_from_powerwall(from_time_stamp, to_time_stamp):
    _LOGGER = globals()['_LOGGER'].getChild("power_from_powerwall")
    
    powerwall_charging = 0.0
    
    try:
        if is_powerwall_configured():
            powerwall_values = get_values(CONFIG['home']['entity_ids']['powerwall_watt_flow_entity_id'], from_time_stamp, to_time_stamp, float_type=True, convert_to="W", error_state=[0.0])
            powerwall_charging = abs(round(average(get_specific_values(powerwall_values, negative_only = True)), 0))
    except Exception as e:
        _LOGGER.warning(f"Cant get powerwall values from {from_time_stamp} to {to_time_stamp}: {e}")
        
    return powerwall_charging

def power_values(from_time_stamp, to_time_stamp):
    power_consumption = abs(round(float(get_average_value(CONFIG['home']['entity_ids']['power_consumption_entity_id'], from_time_stamp, to_time_stamp, convert_to="W", error_state=0.0)), 2))
    ignored_consumption = abs(power_from_ignored(from_time_stamp, to_time_stamp))
    powerwall_charging = power_from_powerwall(from_time_stamp, to_time_stamp)
    ev_used_consumption = abs(round(float(get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], from_time_stamp, to_time_stamp, convert_to="W", error_state=0.0)), 2))
    solar_production = abs(round(float(get_average_value(CONFIG['solar']['entity_ids']['production_entity_id'], from_time_stamp, to_time_stamp, convert_to="W", error_state=0.0)), 2))
    
    return {
        "power_consumption": power_consumption,
        "ignored_consumption": ignored_consumption,
        "powerwall_charging": powerwall_charging,
        "ev_used_consumption": ev_used_consumption,
        "solar_production": solar_production,
    }
    
def solar_production_available(period=None, withoutEV=False, timeFrom=0, timeTo=None):
    _LOGGER = globals()['_LOGGER'].getChild("solar_production_available")
    
    if not is_solar_configured(): return 0.0
    
    now = getTime()
    if timeTo is not None:
        # Range mode
        from_time_stamp = now - datetime.timedelta(minutes=timeFrom)
        to_time_stamp = now - datetime.timedelta(minutes=timeTo)
        period = minutesBetween(to_time_stamp, from_time_stamp, error_value=0)
    else:
        # Single period mode
        if period is None:
            period = CONFIG['solar']['solarpower_use_before_minutes']
        period = max(period, CONFIG['cron_interval'])
        to_time_stamp = now
        from_time_stamp = now - datetime.timedelta(minutes=period)

    values = power_values(from_time_stamp, to_time_stamp)
    power_consumption = values['power_consumption']
    ignored_consumption = values['ignored_consumption']
    powerwall_charging = values['powerwall_charging']
    ev_used_consumption = values['ev_used_consumption']
    solar_production = values['solar_production']

    power_consumption_without_ignored = round(power_consumption - ignored_consumption, 2)
    power_consumption_without_ignored_powerwall = round(power_consumption_without_ignored - powerwall_charging, 2)
    power_consumption_without_all_exclusion = max(round(power_consumption_without_ignored_powerwall - ev_used_consumption, 2), 0.0)

    if withoutEV:
        solar_production_available = round(solar_production - power_consumption_without_all_exclusion, 2)
    else:
        solar_production_available = round(solar_production - power_consumption_without_ignored_powerwall, 2)
    solar_production_available = max(solar_production_available, 0.0)

    '''if timeTo is not None:
        txt = "without" if withoutEV else "with"
        _LOGGER.info(f"sum period:{timeFrom}-{timeTo} {txt} EV, solar_production_available:{solar_production_available}")
    else:
        _LOGGER.info(f"period:{period}, withoutEV:{withoutEV}, solar_production_available:{solar_production_available}")'''

    if withoutEV:
        set_state(f"sensor.{__name__}_solar_over_production_current_hour", solar_production_available)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.from_the_last", f"{period} minutes")
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.power_consumption", power_consumption)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.ignored_consumption", ignored_consumption)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.powerwall_charging", powerwall_charging)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.ev_used_consumption", ev_used_consumption)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.solar_production", solar_production)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.power_consumption_without_ignored", power_consumption_without_ignored)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.power_consumption_without_ignored_powerwall", power_consumption_without_ignored_powerwall)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.power_consumption_without_all_exclusion", power_consumption_without_all_exclusion)
        set_attr(f"sensor.{__name__}_solar_over_production_current_hour.solar_production_available", solar_production_available)

    return solar_production_available

def max_solar_watts_available_remaining_hour():
    _LOGGER = globals()['_LOGGER'].getChild("max_solar_watts_available_remaining_hour")
    
    if not is_solar_configured():
        return {
            "period": f"No solar installed",
            "watt": 0.0
        }
    
    time_to = getMinute() if CONFIG['solar']['max_to_current_hour'] else CONFIG['solar']['solarpower_use_before_minutes'] - CONFIG['cron_interval']
    
    returnDict = {
        "predictedSolarPower": {
            "watt": max(solar_production_available(timeFrom = 0, timeTo = max(time_to, CONFIG['cron_interval']), withoutEV = True), 0.0)
        }
    }
    
    if time_to >= CONFIG['cron_interval']:
        returnDict['total'] = {
            "period": f"0-{time_to}",
            "watt": max(solar_production_available(timeFrom = 0, timeTo = time_to, withoutEV = False), 0.0)
        }
    else:
        returnDict['total'] = {
            "period": f"0-{time_to}",
            "watt": 0.0
        }

    solar_threadhold = CONFIG['charger']['power_voltage'] * CONFIG['solar']['charging_single_phase_min_amp'] / 5
    allowed_above_under_solar_available = CONFIG['solar']['allow_grid_charging_above_solar_available'] if returnDict['predictedSolarPower']['watt'] >= solar_threadhold else 0.0
    predictedSolarPower = returnDict['predictedSolarPower']['watt'] + allowed_above_under_solar_available
    
    multiple = 1 + round((getMinute() / 60 if CONFIG['solar']['max_to_current_hour'] else CONFIG['solar']['solarpower_use_before_minutes']) * 0.75, 2)
    extra_watt = max(((returnDict['total']['watt'] + allowed_above_under_solar_available) * multiple), 0.0)
    
    returnDict['output'] = {
        "period": f"predictedSolarPower:{predictedSolarPower} + {allowed_above_under_solar_available} + {returnDict['total']['period']}:{returnDict['total']['watt']} multiple:{multiple} extra_watt:{extra_watt} (min 0.0)",
        "watt": predictedSolarPower + extra_watt
    }
        
    _LOGGER.debug(f"max_solar_watts_available_remaining_hour returnDict:{returnDict}")
    _LOGGER.debug(f"max_solar_watts_available_remaining_hour output:{returnDict['output']}")

    return returnDict['output']

def inverter_available(error = ""):
    _LOGGER = globals()['_LOGGER'].getChild("inverter_available")
    
    if not is_solar_configured(): return False
        
    if is_entity_available(CONFIG['home']['entity_ids']['power_consumption_entity_id']): return True
    _LOGGER.error(f"Inverter not available ({CONFIG['home']['entity_ids']['power_consumption_entity_id']} = {get_state(CONFIG['home']['entity_ids']['power_consumption_entity_id'])}): {error}")
    return False

def get_forecast_dict():
    _LOGGER = globals()['_LOGGER'].getChild("get_forecast_dict")
    hourly_forecast= {}
    daily_forecast= {}
    return_dict = {
        "hourly": {},
        "daily": {}
    }
    
    try:
        if not service.has_service('weather', 'get_forecasts'):
            raise Exception("Forecast service not available: weather.get_forecasts")
        
        if CONFIG['forecast']['entity_ids']['hourly_service_entity_id']:
            hourly_forecast = service.call("weather", "get_forecasts", blocking=True,
                                    entity_id=CONFIG['forecast']['entity_ids']['hourly_service_entity_id'],
                                    type="hourly")
            
            if CONFIG['forecast']['entity_ids']['hourly_service_entity_id'] in hourly_forecast:
                return_dict["hourly"] = hourly_forecast[CONFIG['forecast']['entity_ids']['hourly_service_entity_id']]["forecast"]
            else:
                raise Exception(f"{CONFIG['forecast']['entity_ids']['hourly_service_entity_id']} not in return dict")
    except Exception as e:
        _LOGGER.error(f"Cant get hourly forecast dict: {e}")
        
    try:
        if not service.has_service('weather', 'get_forecasts'):
            raise Exception("Forecast service not available: weather.get_forecasts")
        
        if CONFIG['forecast']['entity_ids']['daily_service_entity_id']:
            daily_forecast = service.call("weather", "get_forecasts", blocking=True,
                                    entity_id=CONFIG['forecast']['entity_ids']['daily_service_entity_id'],
                                    type="daily")
            
            if CONFIG['forecast']['entity_ids']['daily_service_entity_id'] in daily_forecast:
                return_dict["daily"] = daily_forecast[CONFIG['forecast']['entity_ids']['daily_service_entity_id']]["forecast"]
            else:
                raise Exception(f"{CONFIG['forecast']['entity_ids']['daily_service_entity_id']} not in return dict")
    except Exception as e:
        _LOGGER.error(f"Cant get daily forecast dict: {e}")
        
    return return_dict

def get_forecast(forecast_dict = None, date = None):
    _LOGGER = globals()['_LOGGER'].getChild("get_forecast")
    if date is None:
        date = getTimeStartOfDay()
    
    forecast = None
    try:
        for data in forecast_dict["hourly"]:
            if data is None:
                continue
            
            date = date.replace(minute=0, second=0, tzinfo=None)
            forecastDate = toDateTime(data['datetime']).replace(minute=0, second=0, tzinfo=None)
            if date == forecastDate:
                forecast = data
                break
                
        if forecast is None:
            for data in forecast_dict["daily"]:
                if data is None:
                    continue
                
                date = date.replace(hour=0, minute=0, second=0, tzinfo=None)
                forecastDate = toDateTime(data['datetime']).replace(hour=0, minute=0, second=0, tzinfo=None)
                if date == forecastDate:
                    forecast = data
                    break
    except Exception as e:
        _LOGGER.error(f"Cant get forecast for date {date} {e}")
        
    _LOGGER.debug(f"{date}: {forecast}")
    return forecast
        
def load_solar_available_db():
    _LOGGER = globals()['_LOGGER'].getChild("load_solar_available_db")
    global SOLAR_PRODUCTION_AVAILABLE_DB
    
    if not is_solar_configured(): return
    
    try:
        create_yaml(f"{__name__}_solar_production_available_db", db=SOLAR_PRODUCTION_AVAILABLE_DB)
        SOLAR_PRODUCTION_AVAILABLE_DB = {int(outer_key): {int(inner_key): value for inner_key, value in inner_dict.items()} for outer_key, inner_dict in load_yaml(f"{__name__}_solar_production_available_db").items()}
    except Exception as e:
        _LOGGER.error(f"Cant load {__name__}_solar_production_available_db: {e}")
    
    if SOLAR_PRODUCTION_AVAILABLE_DB == {} or not SOLAR_PRODUCTION_AVAILABLE_DB:
        SOLAR_PRODUCTION_AVAILABLE_DB = {}
    
    for hour in range(24):
        if hour not in SOLAR_PRODUCTION_AVAILABLE_DB:
            SOLAR_PRODUCTION_AVAILABLE_DB[hour] = {}
        for value in weather_values():
            SOLAR_PRODUCTION_AVAILABLE_DB[hour].setdefault(value, [])
    save_solar_available_db()
    
def save_solar_available_db():
    _LOGGER = globals()['_LOGGER'].getChild("save_solar_available_db")
    global SOLAR_PRODUCTION_AVAILABLE_DB
    
    if not is_solar_configured(): return
    
    if len(SOLAR_PRODUCTION_AVAILABLE_DB) > 0:
        save_changes(f"{__name__}_solar_production_available_db", SOLAR_PRODUCTION_AVAILABLE_DB)
    
def solar_available_append_to_db(power):
    _LOGGER = globals()['_LOGGER'].getChild("solar_available_append_to_db")
    global SOLAR_PRODUCTION_AVAILABLE_DB
    
    if not is_solar_configured(): return
    
    if not inverter_available(f"solar_available_append_to_db({power})"):
        return
    
    if len(SOLAR_PRODUCTION_AVAILABLE_DB) == 0:
        load_solar_available_db()
    
    hour = getHour()
    cloudiness = None
    condition = None
    try:
        try:
            cloudiness = get_attr(CONFIG['forecast']['entity_ids']['hourly_service_entity_id'])["cloud_coverage"]
        except Exception as e_hourly:
            _LOGGER.warning(f"Cant get cloud coverage from hourly {CONFIG['forecast']['entity_ids']['hourly_service_entity_id']}: {e_hourly}")
            
            cloudiness = get_attr(CONFIG['forecast']['entity_ids']['daily_service_entity_id'])["cloud_coverage"]
    except Exception as e:
        _LOGGER.warning(f"Cant get cloud coverage from daily {CONFIG['forecast']['entity_ids']['daily_service_entity_id']}: {e}")
    finally:
        if cloudiness is not None:
            condition = get_closest_key(cloudiness, SOLAR_PRODUCTION_AVAILABLE_DB[hour], return_key=True)
        
    if condition is None:
        try:
            try:
                condition = WEATHER_CONDITION_DICT[get_state(CONFIG['forecast']['entity_ids']['hourly_service_entity_id'])]
            except:
                condition = WEATHER_CONDITION_DICT[get_state(CONFIG['forecast']['entity_ids']['daily_service_entity_id'])]
        except Exception as e:
            _LOGGER.error(f"Cant get states from hourly {CONFIG['forecast']['entity_ids']['daily_service_entity_id']} or daily {CONFIG['forecast']['entity_ids']['daily_service_entity_id']}: {e}")
            return
    
    SOLAR_PRODUCTION_AVAILABLE_DB[hour][condition].insert(0, [getTime(), power])
    _LOGGER.debug(f"inserting {power} SOLAR_PRODUCTION_AVAILABLE_DB[{hour}][{condition}] = {SOLAR_PRODUCTION_AVAILABLE_DB[hour][condition]}")
    
    SOLAR_PRODUCTION_AVAILABLE_DB[hour][condition] = SOLAR_PRODUCTION_AVAILABLE_DB[hour][condition][:CONFIG['database']['solar_available_db_data_to_save']]
    _LOGGER.debug(f"removing values over {CONFIG['database']['solar_available_db_data_to_save']} SOLAR_PRODUCTION_AVAILABLE_DB[{hour}][{condition}] = {SOLAR_PRODUCTION_AVAILABLE_DB[hour][condition]}")
    
    save_solar_available_db()

def solar_available_prediction(start_trip = None, end_trip=None):
    _LOGGER = globals()['_LOGGER'].getChild("solar_available_prediction")
    global SOLAR_PRODUCTION_AVAILABLE_DB, CHEAP_GRID_CHARGE_HOURS_DICT
    
    def get_power(cloudiness, hour):
        try:
            power_list = get_closest_key(cloudiness, SOLAR_PRODUCTION_AVAILABLE_DB[hour])
            power_one_down_list = []
            power_one_up_list = []
            if type(power_list) == list:
                if len(power_list) <= 6 or average(get_list_values(power_list)) <= 1000.0:
                    if cloudiness >= 25:
                        power_one_down_list = get_closest_key(cloudiness - 25, SOLAR_PRODUCTION_AVAILABLE_DB[hour])
                    if cloudiness <= 75:
                        power_one_up_list = get_closest_key(cloudiness + 25, SOLAR_PRODUCTION_AVAILABLE_DB[hour])
                
                power = list(filter(lambda value: value <= MAX_WATT_CHARGING, get_list_values(power_list)))
                power_one_down = list(filter(lambda value: value <= MAX_WATT_CHARGING, get_list_values(power_one_down_list)))
                power_one_up = list(filter(lambda value: value <= MAX_WATT_CHARGING, get_list_values(power_one_up_list)))
                
                _LOGGER.debug(f"{hour} {cloudiness} {power}={average(power)} {power_one_down}={average(power_one_down)} {power_one_up}={average(power_one_up)} ")
                
                avg_power = max(average(power + power + power + power_one_down + power_one_up), 0.0)
                avg_kwh = avg_power / 1000
                
                avg_sell_price = float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price'])) if is_solar_configured() else 0.0
                
                if avg_sell_price == -1.0:
                    avg_sell_price = average(KWH_AVG_PRICES_DB['history_sell'][hour])
                
                return avg_kwh, avg_sell_price
        except Exception as e:
            _LOGGER.warning(f"Cant get cloudiness: {cloudiness} hour: {hour}. {e}")
        return 0.0
    
    stop_prediction_before = 3
    days = 7
    today = getTimeStartOfDay()
    output = {
        "avg": 0,
        "today": 0
    }
    output_sell = {
        "avg": 0,
        "today": 0
    }
    
    if not is_solar_configured():
        return output, output_sell
    
    now = getTime()
    
    try:
        location = sun.get_astral_location(hass)
        sunrise = location[0].sunrise(now).replace(tzinfo=None).hour
        sunset = location[0].sunset(now).replace(tzinfo=None).hour
    except Exception as e:
        _LOGGER.error(f"Error: {e}")
        return output, output_sell
    

    forecast_dict = get_forecast_dict()
    
    trip_last_charging = None
    if start_trip:
        start_trip = reset_time_to_hour(start_trip)
        end_trip = reset_time_to_hour(end_trip)
        trip_last_charging = start_trip - datetime.timedelta(hours=stop_prediction_before)
        
    for day in range(days + 1):
        date = today + datetime.timedelta(days=day)
        output[date] = 0.0
        output_sell[date] = 0.0
        
        dayName = getDayOfWeekText(getTimePlusDays(day))
        total = []
        total_sell = []
        
        using_grid_price = True if float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price'])) == -1.0 else False
            
        expensive_hours = []
            
        if "ExpensiveHours" in CHEAP_GRID_CHARGE_HOURS_DICT:
            for hour in CHEAP_GRID_CHARGE_HOURS_DICT['ExpensiveHours']:
                expensive_hours.append(hour.hour)
            
        from_hour = sunrise if day > 0 else max(sunrise, getHour())
        to_hour = sunset
        
        work_last_charging = None
        end_work = None
        try:
            if get_state(f"input_boolean.{__name__}_workday_{dayName}") == "on":
                work_last_charging = date.replace(hour=get_state(f"input_datetime.{__name__}_days_to_charge_{dayName}").hour) - datetime.timedelta(hours=stop_prediction_before)
                end_work = date.replace(hour=get_state(f"input_datetime.{__name__}_{dayName}_homecoming").hour)
        except Exception as e:
            _LOGGER.warning(f"Cant get input_datetime.{__name__}_{dayName}_homecoming datetime, using from sunrise: {e}")
        
        if forecast_dict and inverter_available(f"Day {day} solar_available_prediction() = 0"):
            if from_hour <= to_hour:
                for hour in range(from_hour, to_hour + 1):
                    loop_datetime = date.replace(hour = hour)
                    forecast = get_forecast(forecast_dict, loop_datetime)
                    
                    if forecast is None:
                        continue
                    
                    if work_last_charging and in_between(loop_datetime, work_last_charging, end_work):
                        continue
                    
                    if trip_last_charging and in_between(loop_datetime, trip_last_charging, end_trip):
                        continue
                    
                    if hour in expensive_hours and using_grid_price:
                        continue
                        
                    cloudiness = forecast['cloud_coverage']
                    power_cost = get_power(cloudiness, hour)
                    total.append(power_cost[0])
                    total_sell.append(power_cost[1])
                        
            total = sum(total)
            total_sell = average(total_sell)
            
            if day == 0:
                output['today'] = total
                output_sell['today'] = total_sell
        else:
            if day == 0:
                output['today'] = sum(total)
                output_sell['today'] = average(total_sell)
            total = None
            total_sell = None

        output[date] = total
        output_sell[date] = total_sell
        
    avg = []
    avg_sell = []
    for key in output.keys():
        if key not in ("avg", "today") and output[key] is not None:
                avg.append(output[key])
    output['avg'] = average(avg)

    for key in output_sell.keys():
        if key not in ("avg", "today") and output_sell[key] is not None and output[key] != 0.0:
                avg_sell.append(output_sell[key])
    output_sell['avg'] = average(avg_sell)
    
    for date in output.keys():
        if output[date] is None:
            output[date] = output['avg']
            
    for date in output_sell.keys():
        if output_sell[date] is None:
            output_sell[date] = output_sell['avg']
            
    return output, output_sell

def trip_reset():
    set_state(f"input_number.{__name__}_trip_charge_procent", 0.0)
    set_state(f"input_number.{__name__}_trip_range_needed", 0.0)
    set_state(f"input_datetime.{__name__}_trip_date_time", resetDatetime())
    set_state(f"input_datetime.{__name__}_trip_homecoming_date_time", resetDatetime())
    set_state(f"input_boolean.{__name__}_trip_charging", "off")
    
    if is_ev_configured():
        set_state(f"input_boolean.{__name__}_trip_preheat", "off")

def trip_charging():
    _LOGGER = globals()['_LOGGER'].getChild("trip_charging")
    if get_trip_date_time() == resetDatetime(): return
    if get_trip_homecoming_date_time() == resetDatetime(): return
    
    charger_port = "open" if not is_ev_configured() else get_state(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id'], float_type=False, error_state="unknown")
        
    if is_trip_planned() and charger_port in ("open", "on"):
        _LOGGER.debug("trip_charging:True")
        return True
    
def trip_activate_reminder():
    _LOGGER = globals()['_LOGGER'].getChild("trip_activate_reminder")
    if not is_trip_planned() and (get_trip_range() > 0.0 or get_trip_target_level() > 0.0):
        minutes_since_change = minutesBetween(LAST_TRIP_CHANGE_DATETIME, getTime())

        reminder_times = [10, 60, 90, 360, 1440, 1440*2]
        
        trip_settings = f"Afgang: {get_trip_date_time()}\nHjemkomst: {get_trip_homecoming_date_time()}\n{f'Tur km forbrug: {get_trip_range()}km' if get_trip_range() > 0.0 else f'Tur ladning til: {get_trip_target_level()}km'}"
        
        for i in reminder_times:
            if in_between(minutes_since_change, i, i+5):
                my_notify(message = f"Tur ladning planlagt, men ikke aktiveret\n{trip_settings}", title = f"{__name__.capitalize()}", notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True, persistent_notification_id="trip_activation_needed")
 

def preheat_ev():#TODO Make it work on Tesla and Kia
    _LOGGER = globals()['_LOGGER'].getChild("preheat_ev")
    
    if TESTING:
        _LOGGER.info(f"TESTING not preheating car")
        return
    
    if not is_ev_configured() or get_state(f"input_boolean.{__name__}_days_to_charge") == "off":
        return
    
    try:
        preheat_min_before = float(get_state(f"input_number.{__name__}_preheat_minutes_before"))
        if preheat_min_before <= 0.0:
            return
    except Exception as e:
        _LOGGER.error(f"Cant preheat ev car input_number.{__name__}_preheat_minutes_before is {preheat_min_before}: {e}")
        return
    
    preheat = False
    
    now = getTime()
    next_drive = resetDatetime()
    
    trip_date_time = resetDatetime()
    try:
        trip_date_time = get_trip_date_time()
        if trip_date_time in ("unknown", "unavailable"):
            raise Exception(f"input_datetime.{__name__}_trip_date_time is unknown")
    except Exception as e:
        _LOGGER.error(e)
    
    next_work_time = resetDatetime()
    try:
        dayName = getDayOfWeekText(getTime())
        workday = get_state(f"input_boolean.{__name__}_workday_{dayName}")
        work_time = get_state(f"input_datetime.{__name__}_days_to_charge_{dayName}")
        if workday == "on" and work_time not in ("unknown", "unavailable"):
            next_work_time = getTime().replace(hour=work_time.hour, minute=work_time.minute, second=0, microsecond=0)
    except Exception as e:
        _LOGGER.error(e)
    
    next_work_time_diff = abs(now - next_work_time)
    trip_date_time_diff = abs(now - trip_date_time)
    min_diff = min(next_work_time_diff, trip_date_time_diff)
    
    if min_diff == next_work_time_diff:
        next_drive = next_work_time
    else:
        next_drive = trip_date_time
        
    _LOGGER.debug(f"preheat {minutesBetween(now, next_drive, error_value=-1)} {preheat_min_before} {0 < minutesBetween(now, next_drive, error_value=-1) <= preheat_min_before}")
    
    if 0 < minutesBetween(now, next_drive, error_value=-1) <= preheat_min_before:
        if next_drive == trip_date_time:
            if get_state(f"input_boolean.{__name__}_trip_preheat") == "on":
                preheat = True
        else:
            day_name = getDayOfWeekText(next_drive)
            if get_state(f"input_boolean.{__name__}_preheat_{day_name}") == "on":
                preheat = True
                
    _LOGGER.debug(f"preheat {preheat} {get_state(CONFIG['ev_car']['entity_ids']['climate_entity_id'], error_state='unknown')} {service.has_service('climate', 'turn_on')}")
    
    integration = get_integration(CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id'])[1]
    
    if preheat and get_state(CONFIG['ev_car']['entity_ids']['climate_entity_id'], error_state="unknown") == "off" and service.has_service("climate", "turn_on"):
        outdoor_temp = 0.0
        forecast_temp = 0.0
        
        try:
            if CONFIG['forecast']['entity_ids']['outdoor_temp_entity_id']:
                outdoor_temp = float(get_state(CONFIG['forecast']['entity_ids']['outdoor_temp_entity_id'], float_type=True, error_state=0.0))
        except Exception as e:
            _LOGGER.error(f"Cant get outdoor temp from entity {CONFIG['forecast']['entity_ids']['outdoor_temp_entity_id']}: {e}")
            
        try:
            try:
                forecast_temp = float(get_attr(CONFIG['forecast']['entity_ids']['hourly_service_entity_id'], "temperature"))
            except:
                forecast_temp = float(get_attr(CONFIG['forecast']['entity_ids']['daily_service_entity_id'], "temperature"))
        except Exception as e:
            _LOGGER.error(f"Cant get forecast temp from entity {CONFIG['forecast']['entity_ids']['daily_service_entity_id']}['temperature']: {e}")
            
        heating_type = "Forvarmer"
        
        if outdoor_temp <= -1.0 or forecast_temp <= -1.0:
            if not allow_command_entity_integration("Tesla Climate service Defrost", "preheat()", integration = integration): return
            
            service.call("climate", "set_preset_mode", preset_mode="Defrost", blocking=True, entity_id=CONFIG['ev_car']['entity_ids']['climate_entity_id'])
            heating_type = "Optøer"
        else:
            if not allow_command_entity_integration("Tesla Climate service Preheat", "preheat()", integration = integration): return
            
            service.call("climate", "turn_on", blocking=True, entity_id=CONFIG['ev_car']['entity_ids']['climate_entity_id'])
        drive_efficiency("preheat")
        
        _LOGGER.info("Preheating ev car")
        my_notify(message = f"{heating_type} bilen til kl. {next_drive.strftime('%H:%M')}", title = f"{__name__.capitalize()}", notify_list = CONFIG['notify_list'], admin_only = False, always = False)
    elif get_state(CONFIG['ev_car']['entity_ids']['climate_entity_id'], error_state="unknown") == "heat_cool" and service.has_service("climate", "turn_off"):
        if ready_to_charge():
            if minutesBetween(next_drive, now, error_value=(preheat_min_before * 3) + 1) > (preheat_min_before * 3) and minutesBetween(next_drive, now, error_value=(preheat_min_before * 3) + 11) <= (preheat_min_before * 3) + 10:
                if not allow_command_entity_integration("Tesla Climate service Turn off", "preheat()", integration = integration): return
            
                service.call("climate", "turn_off", blocking=True, entity_id=CONFIG['ev_car']['entity_ids']['climate_entity_id'])
                drive_efficiency("preheat_cancel")
                
                _LOGGER.info("Car not moved stopping preheating ev car")
                my_notify(message = f"Forvarmning af bilen stoppet, pga ingen kørsel kl. {next_drive.strftime('%H:%M')}", title = f"{__name__.capitalize()}", notify_list = CONFIG['notify_list'], admin_only = False, always = False)

def ready_to_charge():
    _LOGGER = globals()['_LOGGER'].getChild("ready_to_charge")
    
    def entity_unavailable(entity_id):
        if is_entity_configured(entity_id) and not is_entity_available(entity_id):
            set_charging_rule(f"⛔{get_integration(entity_id).capitalize()} integrationen er nede\nGenstarter integrationen")
            my_notify(message = f"{get_integration(entity_id).capitalize()} integrationen er nede\nGenstarter integrationen", title = f"{__name__.capitalize()}", notify_list = CONFIG['notify_list'], admin_only = False, always = True)
            return True
        
    if entity_unavailable(CONFIG['charger']['entity_ids']['status_entity_id']) or entity_unavailable(CONFIG['charger']['entity_ids']['enabled_entity_id']):
        return
    
    charger_status = get_state(CONFIG['charger']['entity_ids']['status_entity_id'], float_type=False, error_state="connected")
    charger_enabled = get_state(CONFIG['charger']['entity_ids']['enabled_entity_id'], float_type=False, error_state="off")
    
    if charger_enabled != "on":
        _LOGGER.warning(f"Charger was off, turning it on")
        send_command(CONFIG['charger']['entity_ids']['enabled_entity_id'], "on")
        
    
    if entity_unavailable(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']):
        return
    
    ev_charger_port = "open" if not is_ev_configured() else get_state(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id'], float_type=False, error_state="open")
    
    if charger_status == "disconnected":
        _LOGGER.info("Charger cable disconnected")
        set_charging_rule(f"Lader kabel frakoblet")
        
        if not is_ev_configured() and float(get_state(f"input_number.{__name__}_battery_level", float_type=True, error_state=0.0)) != 0.0:
            _LOGGER.info("Reseting battery level to 0.0")
            set_state(entity_id=f"input_number.{__name__}_battery_level", new_state=0.0)
        return
    elif manual_charging_enabled() or manual_charging_solar_enabled():
        return True
    elif charger_status in ("awaiting_authorization", "awaiting_start") and ev_charger_port in ("closed", "off"):
        _LOGGER.info("Charger cable connected, but car not updated")
        set_charging_rule(f"⛔Lader kabel forbundet, men bilen ikke opdateret")
        wake_up_ev()
        return
    else:
        if is_ev_configured():
            if entity_unavailable(CONFIG['ev_car']['entity_ids']['location_entity_id']) or entity_unavailable(CONFIG['charger']['entity_ids']['cable_connected_entity_id']) or entity_unavailable(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']):
                return
            
            currentLocation = get_state(CONFIG['ev_car']['entity_ids']['location_entity_id'], float_type=False, try_history=True, error_state="home")
            
            charger_connector = get_state(CONFIG['charger']['entity_ids']['cable_connected_entity_id'], float_type=False, error_state="on") if is_entity_configured(CONFIG['charger']['entity_ids']['cable_connected_entity_id']) else "not_configured"
            ev_charger_connector = get_state(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id'], float_type=False, error_state="on") if is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']) else "not_configured"
            
            if ev_charger_connector == "on" or charger_connector == "on":
                if currentLocation != "home":
                    _LOGGER.info("To long away from home")
                    set_charging_rule(f"⛔Ladekabel forbundet, men bilen ikke hjemme")
                    return
            
            if ev_charger_port not in ("open", "on"):
                _LOGGER.info("Chargeport not open")
                set_charging_rule(f"⛔Bilens ladeport ikke åben")
                return
            
            if charger_connector != "on" and ev_charger_connector != "on":
                _LOGGER.info("Charger cable is Disconnected")
                set_charging_rule(f"⛔Ladekabel ikke forbundet til bilen")
                return
            
    return True

def start_charging():
    send_command(CONFIG['charger']['entity_ids']['enabled_entity_id'], "on")
    send_command(CONFIG['charger']['entity_ids']['start_stop_charging_entity_id'], "on")
    ev_send_command(CONFIG['ev_car']['entity_ids']['charge_switch_entity_id'], "on")

def is_charging():
    _LOGGER = globals()['_LOGGER'].getChild("is_charging")
    global CHARGING_IS_BEGINNING, RESTARTING_CHARGER, RESTARTING_CHARGER_COUNT, CURRENT_CHARGING_SESSION, CHARGING_HISTORY_DB
    
    def reset():
        global CHARGING_IS_BEGINNING, RESTARTING_CHARGER, RESTARTING_CHARGER_COUNT
        
        if RESTARTING_CHARGER_COUNT > 0 or (charger_enabled != "on"):
            send_command(CONFIG['charger']['entity_ids']['enabled_entity_id'], "on")
            ev_send_command(CONFIG['ev_car']['entity_ids']['charge_switch_entity_id'], "on")
            
        CHARGING_IS_BEGINNING = False
        RESTARTING_CHARGER = False
        RESTARTING_CHARGER_COUNT = 0
    
    if TESTING:
        _LOGGER.warning(f"Not checking if is charging TESTMODE")
        return
        
    charger_enabled = get_state(CONFIG['charger']['entity_ids']['enabled_entity_id'], float_type=False, error_state="off")
    charger_status = get_state(CONFIG['charger']['entity_ids']['status_entity_id'], float_type=False, error_state="unavailable")
        
    data = {
        "ttl": 0,
        "priority": "high",
        "channel": "alarm_stream"
    } if RESTARTING_CHARGER_COUNT == 3 else {}
    
    emoji_charging_problem = f"{emoji_parse({'charging_problem': True})}"
    emoji_charging_error = f"{emoji_parse({'charging_error': True})}"
    
    if charger_status in ("charging", "completed"):
        if RESTARTING_CHARGER_COUNT > 0:
            _LOGGER.info("Ev is charging as it should again")
            
            if CURRENT_CHARGING_SESSION['start']:
                when = CURRENT_CHARGING_SESSION['start']
                
                if 1 < RESTARTING_CHARGER_COUNT < 3:
                    if emoji_charging_error not in CHARGING_HISTORY_DB[when]["emoji"]:
                        CHARGING_HISTORY_DB[when]["emoji"] = CHARGING_HISTORY_DB[when]["emoji"].replace(emoji_charging_error, emoji_charging_problem)
                        charging_history_combine_and_set()
            
            my_notify(message = f"Elbilen lader, som den skal igen", title = f"{__name__.capitalize()} Elbilen lader", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True)
        reset()
        
        if charger_status in ("charging"):
            return True
        else:
            return
        
    if not ready_to_charge() or not CURRENT_CHARGING_SESSION['start']:
        reset()
        return
    
    when = CURRENT_CHARGING_SESSION['start']
    if RESTARTING_CHARGER_COUNT == 0 and minutesBetween(getTime(), when, error_value=CONFIG['cron_interval'] + 5) <= CONFIG['cron_interval'] * 2:
        return
    
    if is_entity_available(CONFIG['charger']['entity_ids']['dynamic_circuit_limit']):
        error_dict = {
            "state_dynamicCircuitCurrentP1": CONFIG['charger']['charging_max_amp'],
            "state_dynamicCircuitCurrentP2": CONFIG['charger']['charging_max_amp'],
            "state_dynamicCircuitCurrentP3": CONFIG['charger']['charging_max_amp']
        }
        charger_dynamic_circuit_limit = get_attr(CONFIG['charger']['entity_ids']['dynamic_circuit_limit'], error_state=error_dict)
        p1 = int(charger_dynamic_circuit_limit["state_dynamicCircuitCurrentP1"])
        p2 = int(charger_dynamic_circuit_limit["state_dynamicCircuitCurrentP2"])
        p3 = int(charger_dynamic_circuit_limit["state_dynamicCircuitCurrentP3"])
        dynamic_circuit_limit = sum([p1, p2, p3])
        current_charging_amps = sum(CURRENT_CHARGING_AMPS)
    else:
        dynamic_circuit_limit = sum(CURRENT_CHARGING_AMPS)
        current_charging_amps = sum(CURRENT_CHARGING_AMPS)
    
    try:
        if RESTARTING_CHARGER:
            set_charging_rule(f"⛔Fejl i ladning af elbilen\nStarter ladningen op igen {RESTARTING_CHARGER_COUNT}. forsøg")
            _LOGGER.warning(f"Starting charging (attempts {RESTARTING_CHARGER_COUNT}): Starting charging again")
            my_notify(message = f"Starter ladningen igen, {RESTARTING_CHARGER_COUNT} forsøg", title = f"{__name__.capitalize()} Elbilen lader ikke", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True)
            
            start_charging()
            RESTARTING_CHARGER = False
        elif charger_status in ("unknown", "unavailable"):
            set_charging_rule(f"⛔Fejl i ladning af elbilen\nLader ikke tilgængelig")
            raise Exception(f"Charger is unavailable, entity id: {CONFIG['charger']['entity_ids']['status_entity_id']}")
        elif charger_status == "error":
            set_charging_rule(f"⛔Fejl i ladning af elbilen\nKritisk fejl på lader, tjek integration eller Easee app")
            raise Exception(f"Charger critical error, check Easee app or Home Assistant")
        elif charger_status in ("awaiting_start", "awaiting_authorization", "ready_to_charge"):
            if current_charging_amps == 0:
                if CHARGING_IS_BEGINNING or RESTARTING_CHARGER or RESTARTING_CHARGER_COUNT or charger_enabled != "on":
                    reset()
            elif RESTARTING_CHARGER_COUNT == 3:
                set_charging_rule(f"⛔Fejl i ladning af elbilen")
                raise Exception(f"Charging has not started even after restarting multiple times")
            elif RESTARTING_CHARGER_COUNT < 3:
                if current_charging_amps != dynamic_circuit_limit:
                    set_charging_rule(f"⛔Fejl i ladning af elbilen\nDynamisk begrænsning ikke sat")
                    raise Exception(f"Chargers dynamic circuit limit not set")
                else:
                    if CHARGING_IS_BEGINNING:
                        set_charging_rule(f"⛔Fejl i ladning af elbilen\nGenstarter lader")
                        raise Exception("Ev is not charging, restarting charger")
                    CHARGING_IS_BEGINNING = True
    except Exception as e:
        _LOGGER.warning(f"Charging has not started as expected: {e}")
        
        if 1 < RESTARTING_CHARGER_COUNT < 3:
            if emoji_charging_problem not in CHARGING_HISTORY_DB[when]["emoji"]:
                CHARGING_HISTORY_DB[when]["emoji"] = CHARGING_HISTORY_DB[when]["emoji"] + f" {emoji_charging_problem}"
                charging_history_combine_and_set()
        elif RESTARTING_CHARGER_COUNT == 3:
            if emoji_charging_problem in CHARGING_HISTORY_DB[when]["emoji"]:
                CHARGING_HISTORY_DB[when]["emoji"] = CHARGING_HISTORY_DB[when]["emoji"].replace(emoji_charging_problem, emoji_charging_error)
                charging_history_combine_and_set()
                    
        restarting = ""
        
        if not RESTARTING_CHARGER:
            RESTARTING_CHARGER = True
            RESTARTING_CHARGER_COUNT += 1
            
            if RESTARTING_CHARGER_COUNT == 1 and is_entity_configured(CONFIG['charger']['entity_ids']['start_stop_charging_entity_id']):
                _LOGGER.warning(f"Restarting charger control integration (attempts {RESTARTING_CHARGER_COUNT}): Stopping charger control integration for now")
                restarting = f"\nGenstarter ladeoperatør, {RESTARTING_CHARGER_COUNT} forsøg"
                send_command(CONFIG['charger']['entity_ids']['start_stop_charging_entity_id'], "off")
            else:
                _LOGGER.warning(f"Restarting charger (attempts {RESTARTING_CHARGER_COUNT}): Stopping charger for now")
                restarting = f"\nGenstarter laderen, {RESTARTING_CHARGER_COUNT} forsøg"
                send_command(CONFIG['charger']['entity_ids']['enabled_entity_id'], "off")
        my_notify(message = f"Elbilen lader ikke som den skal:\n{e}{restarting}", title = f"{__name__.capitalize()} Elbilen lader ikke", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True)
            
    _LOGGER.debug(f"DEBUG: CHARGING_IS_BEGINNING:{CHARGING_IS_BEGINNING} RESTARTING_CHARGER:{RESTARTING_CHARGER} RESTARTING_CHARGER_COUNT:{RESTARTING_CHARGER_COUNT}")
    _LOGGER.debug(f"DEBUG: charger_enabled:{charger_enabled} charger_status:{charger_status} current_charging_amps:{current_charging_amps} dynamic_circuit_limit:{dynamic_circuit_limit} dynamic_circuit_limit:{dynamic_circuit_limit} dynamic_circuit_limit:{dynamic_circuit_limit}")

def charging_without_rule():
    _LOGGER = globals()['_LOGGER'].getChild("charging_without_rule")
    global CHARGING_NO_RULE_COUNT
    if getMinute() < 5: return False
    
    minutes = max(5, int(round_up(CONFIG['cron_interval'] / 2)))
    
    now = getTime()
    past = now - datetime.timedelta(minutes=minutes)
    
    entity_id = CONFIG['charger']['entity_ids']['power_consumtion_entity_id']
    
    power = get_state(entity_id, float_type=True, error_state=0.0)
    power_avg = round(abs(float(get_average_value(entity_id, past, now, convert_to="W", error_state=0.0))), 3)
    
    if power != 0.0 or (power > 100.0 and power_avg > 100.0):
        if CHARGING_NO_RULE_COUNT > 2:
            if not CURRENT_CHARGING_SESSION['start']:
                charging_history({'Price': get_current_hour_price(), 'Cost': 0.0, 'kWh': 0.0, 'battery_level': 0.0, 'no_rule': True}, "no_rule")
            set_charging_rule(f"{emoji_parse({'no_rule': True})}Lader uden grund")
            _LOGGER.warning("Charging without rule")
            return True
        CHARGING_NO_RULE_COUNT += 1
    else:
        CHARGING_NO_RULE_COUNT = 0
    return False

def charge_if_needed():
    _LOGGER = globals()['_LOGGER'].getChild("charge_if_needed")
    global CHEAP_GRID_CHARGE_HOURS_DICT
    
    try:
        trip_date_time = get_trip_date_time() if get_trip_date_time() != resetDatetime() else resetDatetime()
        trip_planned = is_trip_planned()
        
        CHEAP_GRID_CHARGE_HOURS_DICT = cheap_grid_charge_hours()
        
        if trip_planned:
            if trip_date_time != resetDatetime() and minutesBetween(getTime(), trip_date_time, error_value=0) < CHARGING_ALLOWED_AFTER_GOTO_TIME:
                _LOGGER.info(f"Trip date {trip_date_time} exceeded by an hour. Reseting trip settings")
                trip_reset()
                CHEAP_GRID_CHARGE_HOURS_DICT = cheap_grid_charge_hours()
                
        solar_available = max_solar_watts_available_remaining_hour()
        solar_period = solar_available['period']
        solar_watt = solar_available['watt']
        solar_amps = calc_charging_amps(solar_watt)[:-1]
        
        currentHour = getTime().replace(hour=getHour(), minute=0, second=0, tzinfo=None)
        current_price = get_current_hour_price()
        
        charging_limit = min(range_to_battery_level(), get_max_recommended_charge_limit_battery_level())
        amps = [3.0, 0.0]
        
        if currentHour in CHEAP_GRID_CHARGE_HOURS_DICT:
            if solar_amps[1] > 0.0:
                CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]['solar'] = True
                
            if trip_planned:
                solar_amps[1] = 0.0
            
        _LOGGER.info(f"Solar Production Available Remaining Hour: {solar_available}")
        
        if solar_amps[1] != 0.0:
            alsoCheapPower = ""
            charging_limit = get_max_recommended_charge_limit_battery_level()
            solar_using_grid_price = False
            
            if is_solar_configured():
                solar_using_grid_price = True if float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price'])) == -1.0 else False
        
            if currentHour in CHEAP_GRID_CHARGE_HOURS_DICT:
                if "half_min_avg_price" in CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]:
                    amps = [CONFIG['charger']['charging_phases'], int(CONFIG['charger']['charging_max_amp'])]
                    charging_limit = charging_limit if charging_limit > get_ultra_cheap_grid_charging_max_battery_level() else get_ultra_cheap_grid_charging_max_battery_level()
                    alsoCheapPower = " + Ultra cheap power"
                elif "under_min_avg_price" in CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]:
                    amps = [CONFIG['charger']['charging_phases'], int(CONFIG['charger']['charging_max_amp'])]
                    charging_limit = charging_limit if charging_limit > get_very_cheap_grid_charging_max_battery_level() else get_very_cheap_grid_charging_max_battery_level()
                    alsoCheapPower = " + Cheap power"
                else:
                    amps = [CONFIG['charger']['charging_phases'], int(CONFIG['charger']['charging_max_amp'])]
                    charging_limit = round_up(battery_level() + CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]['battery_level'])
                    alsoCheapPower = " + Grid Charging not enough solar production"
                charging_limit = min(charging_limit, get_max_recommended_charge_limit_battery_level())
            elif solar_using_grid_price and currentHour in CHEAP_GRID_CHARGE_HOURS_DICT['ExpensiveHours']:
                _LOGGER.info(f"Ignoring solar overproduction, because of expensive hour")
                solar_amps[1] = 0.0
                
        if is_calculating_charging_loss():
            completed_battery_level = float(get_state(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'], float_type=True, error_state=100.0)) if is_ev_configured() else get_completed_battery_level()
            _LOGGER.info(f"Calculating charging loss {completed_battery_level}%")
            
            if completed_battery_level < get_max_recommended_charge_limit_battery_level():
                completed_battery_level = get_max_recommended_charge_limit_battery_level()
                charging_limit = get_max_recommended_charge_limit_battery_level()
                
            set_charging_rule(f"{emoji_parse({'charging_loss': True})}Klakulere ladetab {completed_battery_level}%")
            amps = [CONFIG['charger']['charging_phases'], CONFIG['charger']['charging_max_amp']]
            
            battery = round(completed_battery_level - battery_level(), 1)
            kwh = round(percentage_to_kwh(battery, include_charging_loss = True))
            cost = round(current_price * kwh, 2)
            charging_history({'Price': current_price, 'Cost': cost, 'kWh': kwh, 'battery_level': battery, 'charging_loss': True, 'solar': True if solar_watt > 0.0 else False}, "charging_loss")
        elif manual_charging_enabled() or manual_charging_solar_enabled():
            charging_limit = get_max_recommended_charge_limit_battery_level()
            if not manual_charging_solar_enabled():
                _LOGGER.info("Manual charging")
                amps = [CONFIG['charger']['charging_phases'], CONFIG['charger']['charging_max_amp']]
                set_charging_rule(f"{emoji_parse({'manual': True})}Manuel ladning tilladt {int(amps[0])}x{int(amps[1])}A")
            else:
                _LOGGER.info(f"Manual charging solar only")
                amps = solar_amps
                solar_charging = f" {int(amps[0])}x{int(amps[1])}A" if solar_amps[1] != 0.0 else ""
                set_charging_rule(f"{emoji_parse({'manual': True, "solar": True})}Manuel ladning tilladt, kun sol {solar_charging}")
                
            if amps[1] > 0.0:
                charging_history({'Price': get_solar_sell_price() if solar_amps[1] != 0.0 else current_price, 'Cost': 0.0, 'kWh': 0.0, 'battery_level': 0.0, 'manual': True, 'solar': True if solar_amps[1] != 0.0 else False}, "manual")
            else:
                charging_history(None, "")
        elif ready_to_charge():
            if get_state(f"input_boolean.{__name__}_forced_charging_daily_battery_level", error_state="on") == "on" and battery_level() < get_min_daily_battery_level() and battery_level() != 0.0:
                if currentHour not in CHEAP_GRID_CHARGE_HOURS_DICT['ExpensiveHours']:
                    set_charging_rule(f"{emoji_parse({'low_battery': True})}Lader ikke, pga. for dyr strøm")
                    _LOGGER.info(f"Battery under <{get_min_daily_battery_level()}%, but power is expensive: {date_to_string(CHEAP_GRID_CHARGE_HOURS_DICT['ExpensiveHours'], format = '%H:%M')}")
                else:
                    battery = round(get_min_daily_battery_level() - battery_level(), 1)
                    kwh = round(percentage_to_kwh(battery, include_charging_loss = True))
                    cost = round(current_price * kwh, 2)
                    charging_history({'Price': current_price, 'Cost': cost, 'kWh': kwh, 'battery_level': battery, 'low_battery': True, 'solar': True if solar_watt > 0.0 else False}, "low_battery")
                    charging_limit = get_min_daily_battery_level()
                    amps = [CONFIG['charger']['charging_phases'], int(CONFIG['charger']['charging_max_amp'])]
                    set_charging_rule(f"{emoji_parse({'low_battery': True})}Lader pga. batteriniveauet <{get_min_daily_battery_level()}%")
                    _LOGGER.info(f"Charging because of under <{get_min_daily_battery_level()}%")
            elif currentHour in CHEAP_GRID_CHARGE_HOURS_DICT:
                CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]['solar'] = True if solar_watt > 0.0 else False
                charging_history(CHEAP_GRID_CHARGE_HOURS_DICT[currentHour], "planned")
                
                battery_level_plus_charge = battery_level() + CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]['battery_level']
                max_level_today = CHEAP_GRID_CHARGE_HOURS_DICT['MaxChargingLevelToday']
                charging_limit = min(round_up(max(battery_level_plus_charge, max_level_today, range_to_battery_level())), 100.0)
                amps = [CONFIG['charger']['charging_phases'], CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]['ChargingAmps']]
                '''_LOGGER.error(f"battery_level_plus_charge:{battery_level_plus_charge}")
                _LOGGER.error(f"max_level_today:{max_level_today}")
                _LOGGER.error(f"range_to_battery_level():{range_to_battery_level()}")
                _LOGGER.error(f"charging_limit:{charging_limit}")'''
                emoji = emoji_parse(CHEAP_GRID_CHARGE_HOURS_DICT[currentHour])

                set_charging_rule(f"Lader op til {emoji}")
                _LOGGER.info(f"Charging because of {emoji} {CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]['Price']}kr. {int(CONFIG['charger']['charging_phases'])}x{CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]['ChargingAmps']}amps ({MAX_KWH_CHARGING}kWh)")
            elif solar_amps[1] != 0.0 and battery_level() < (get_max_recommended_charge_limit_battery_level() - 1.0):
                if currentHour in CHEAP_GRID_CHARGE_HOURS_DICT:
                    CHEAP_GRID_CHARGE_HOURS_DICT[currentHour]['solar'] = True
                    charging_history(CHEAP_GRID_CHARGE_HOURS_DICT[currentHour], "planned")
                else:
                    charging_history({'Price': get_solar_sell_price(), 'Cost': 0.0, 'kWh': 0.0, 'battery_level': 0.0, 'solar': True}, "solar")
                amps = solar_amps
                set_charging_rule(f"{emoji_parse({'solar': True})}Solcelle lader {int(amps[0])}x{int(amps[1])}A")
                _LOGGER.info(f"EV solar charging at max {amps}{alsoCheapPower}")
                _LOGGER.debug(f"solar_watt:{solar_watt} solar_period:{solar_period}")
            else:
                if not charging_without_rule():
                    charging_history(None, "")
                    set_charging_rule(f"Lader ikke")
                    _LOGGER.info("No rules for charging")
        else:
            if not charging_without_rule():
                charging_history(None, "")
                _LOGGER.info("EV not ready to charge")
        
        if get_state(f"input_boolean.{__name__}_fill_up") == "on":
            charging_limit = max(charging_limit, get_max_recommended_charge_limit_battery_level())
            
        ev_send_command(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'], verify_charge_limit(charging_limit))
        
        if amps[1] > 0.0:
            start_charging()
        else:
            send_command(CONFIG['charger']['entity_ids']['start_stop_charging_entity_id'], "off")
            
        set_charger_charging_amps(*amps)
    except Exception as e:
        global ERROR_COUNT
        
        _LOGGER.error(f"Error running charge_if_needed(), setting charger and car to max: {e}")
        
        if ERROR_COUNT == 3:
            _LOGGER.error(f"Restarting script to maybe fix error!!!")
            
            restart_script()
        else:
            _LOGGER.error(f"Trying to restart script to fix error in {ERROR_COUNT}/3")
            
        ERROR_COUNT += 1
        
        ev_send_command(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'], verify_charge_limit(get_max_recommended_charge_limit_battery_level()))
        start_charging()
        
        charging_history({'Price': 0.0, 'Cost': 0.0, 'kWh': 0.0, 'battery_level': 0.0, 'error': True}, "error")
        set_charging_rule(f"{emoji_parse({'error': True})}Fejl: Script deaktiveret, lader maks!!!")
        
        amps = [3.0, CONFIG['charger']['charging_max_amp']]
        set_charger_charging_amps(*amps)

def set_charging_price(price):
    _LOGGER = globals()['_LOGGER'].getChild("set_charging_price")
    
    if TESTING:
        _LOGGER.info(f"TESTING not setting easee charging cost")
        return
    
    try:
        if service.has_service("easee", "set_charging_cost"):
            service.call("easee", "set_charging_cost", blocking=True,
                                charger_id=get_attr(CONFIG['charger']['entity_ids']['status_entity_id'], "id"),
                                cost_per_kwh=price,
                                vat=25,
                                currency_id="DKK")
        else:
            raise Exception(f"Easee service dont have set_charging_cost, cant set price to {price}")
    except Exception as e:
        _LOGGER.error(f"Cant set charging cost in Easee: {e}")

def kwh_charged_by_solar():
    _LOGGER = globals()['_LOGGER'].getChild("kwh_charged_by_solar")
    
    if not is_solar_configured(): return
        
    now = getTime()
    past = now - datetime.timedelta(minutes=60)
    
    ev_watt = round(abs(float(get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0))), 3)
    solar_watt = round(max(solar_production_available(period = 60, withoutEV = True), 0.0), 3)
    
    if not ev_watt:
        return
    
    solar_watt = min(solar_watt, ev_watt)
    
    ev_solar_kwh = round(solar_watt / 1000, 3)
    try:
        solar_kwh = get_state(entity_id=f"input_number.{__name__}_kwh_charged_by_solar", float_type=True, try_history=True, error_state=None)
        if solar_kwh is not None:
            solar_kwh = round(float(solar_kwh) + ev_solar_kwh, 2)
            set_state(entity_id=f"input_number.{__name__}_kwh_charged_by_solar", new_state=solar_kwh)
        else:
            raise Exception(f"Cant get state for input_number.{__name__}_kwh_charged_by_solar")
    except Exception as e:
        _LOGGER.error(e)
    
def solar_charged_percentage():
    _LOGGER = globals()['_LOGGER'].getChild("solar_percentage")
    
    if not is_solar_configured(): return
    
    total_ev_kwh = float(get_state(CONFIG['charger']['entity_ids']['lifetime_kwh_meter_entity_id'], float_type=True, try_history=True, error_state=None))
    total_solar_ev_kwh = float(get_state(f"input_number.{__name__}_kwh_charged_by_solar", float_type=True, try_history=True, error_state=None))
    
    try:
        set_state(f"sensor.{__name__}_solar_charged_percentage", round(((total_solar_ev_kwh / total_ev_kwh) * 100.0), 1))
    except Exception as e:
        _LOGGER.error(f"Cant set sensor.{__name__}_solar_charged_percentage total_solar_ev_kwh={total_solar_ev_kwh} total_ev_kwh={total_ev_kwh}: {e}")
    
def calc_co2_emitted(period = None, added_kwh = None):
    _LOGGER = globals()['_LOGGER'].getChild("calc_co2_emitted")
    
    if added_kwh is None:
        return 0.0
    
    if CONFIG['charger']['entity_ids']['co2_entity_id'] not in state.names(domain="sensor"): return
    
    minutes = getMinute() if period is None else period
    
    now = getTime()
    past = now - datetime.timedelta(minutes=minutes)
    
    ev_kwh = round(abs(float(get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0))) / 1000.0, 3)
    solar_kwh_available = round(max(solar_production_available(period = minutes, withoutEV = True), 0.0) / 1000.0, 3)
       
    ev_solar_kwh = round(solar_kwh_available, 3)
    ev_grid_kwh =  round(max(ev_kwh - (solar_kwh_available), 0.0), 3)
    
    grid_co2_emitted = 0.0
    grid_co2_kwh = float(get_state(entity_id=CONFIG['charger']['entity_ids']['co2_entity_id'], float_type=True, error_state=0.0))
    try:
        solar_co2_emitted =((ev_solar_kwh / ev_kwh) * (10 / 1000.0)) #Solar co2 50g * 3years = 0.15 / 15years life = 0.01 = 10g/kWh
        grid_co2_emitted = ((ev_grid_kwh / ev_kwh) * (grid_co2_kwh / 1000.0))
        grid_co2_emitted = round((solar_co2_emitted + grid_co2_emitted) * added_kwh, 3)
    except:
        pass
    
    co2_emitted = get_state(entity_id=f"input_number.{__name__}_co2_emitted", float_type=True, try_history=True, error_state=None)
    if co2_emitted is not None and grid_co2_emitted > 0.0:
        co2_emitted = round(float(co2_emitted) + grid_co2_emitted, 3)
        
        _LOGGER.info(f"Setting sensor.{__name__}_co2_emitted to {co2_emitted} increased by {grid_co2_emitted}")
        set_state(entity_id=f"input_number.{__name__}_co2_emitted", new_state=co2_emitted)
        return co2_emitted
    return 0.0

def calc_kwh_price(period = 60, update_entities = False, solar_period_current_hour = False):
    _LOGGER = globals()['_LOGGER'].getChild("calc_kwh_price")
    minutes = getMinute() if solar_period_current_hour else period
    minutes = 60 if not in_between(getMinute(), 1, 58) else minutes
    
    now = getTime()
    past = now - datetime.timedelta(minutes=minutes)
    
    ev_watt = round(abs(float(get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0))), 3)
    solar_watt_available = round(max(solar_production_available(period = minutes, withoutEV = True), 0.0), 3)
    
    min_watt = (SOLAR_CHARGING_TRIGGER_ON if is_solar_configured() else MAX_WATT_CHARGING) / 2 if in_between(getMinute(), 1, 58) else 0.0
        
    if ev_watt < min_watt:
        _LOGGER.debug("Calculating ev cost, when ev not charging. For display only")
        ev_watt = SOLAR_CHARGING_TRIGGER_ON if is_solar_configured() else MAX_WATT_CHARGING
    else:
        solar_watt_available = round(min(solar_watt_available, ev_watt), 3)
    
    ev_solar_watt = round(solar_watt_available, 3)
    ev_grid_watt =  round(max(ev_watt - solar_watt_available, 0.0), 3)
    
    solar_kwh_price = get_solar_sell_price(set_entity_attr=update_entities)
    
    ev_solar_share = 0.0
    ev_solar_price_kwh = 0.0
    try:
        ev_solar_share = min(round(ev_solar_watt / ev_watt, 2), 100.0)
        ev_solar_price_kwh = round(ev_solar_share * solar_kwh_price, 5)
    except:
        pass
    _LOGGER.info(f"ev_watt {ev_watt}")
    _LOGGER.info(f"solar_watt_available {solar_watt_available} minutes:{minutes}")
    _LOGGER.info(f"solar_kwh_price: {solar_kwh_price}kr")
    _LOGGER.info(f"ev_solar_price_kwh: ({ev_solar_watt}/{ev_watt}={int(ev_solar_share*100)}%)*{solar_kwh_price} = {ev_solar_price_kwh}")
    
    grid_kwh_price = float(get_state(CONFIG['prices']['entity_ids']['power_prices_entity_id'], float_type=True)) - get_refund()
    
    ev_grid_share = 0.0
    ev_grid_price_kwh = 0.0
    try:
        ev_grid_share = min(round(ev_grid_watt/ev_watt, 2), 100.0)
        ev_grid_price_kwh = round(ev_grid_share * grid_kwh_price, 5)
    except:
        pass
    _LOGGER.warning(f"grid_kwh_price: {grid_kwh_price}kr")
    _LOGGER.warning(f"ev_grid_price_kwh: ({ev_grid_watt}/{ev_watt}={int(ev_grid_share*100)}%)*{grid_kwh_price} = {ev_grid_price_kwh}")
    
    ev_total_price_kwh = round(ev_solar_price_kwh + ev_grid_price_kwh, 3)
    _LOGGER.warning(f"ev_total_price_kwh: round({ev_solar_price_kwh} + {ev_grid_price_kwh}, 3) = {ev_total_price_kwh}")
    
    if update_entities:
        _LOGGER.info(f"Setting sensor.{__name__}_kwh_cost_price to {ev_total_price_kwh}")
        set_state(f"sensor.{__name__}_kwh_cost_price", ev_total_price_kwh)
        
        if not is_solar_configured():
            for item in get_attr(f"sensor.{__name__}_kwh_cost_price"):
                state.delete(f"sensor.{__name__}_kwh_cost_price.{item}")
                
            raw_price = get_state(CONFIG['prices']['entity_ids']['power_prices_entity_id'], float_type=True)
            refund = get_refund()
            price = raw_price - refund
            set_attr(f"sensor.{__name__}_kwh_cost_price.raw_price", f"{raw_price:.2f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.refund", f"{refund:.2f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.price", f"{price:.2f} kr/kWh")
        else:
            set_attr(f"sensor.{__name__}_kwh_cost_price.solar_grid_ratio", "")
            set_attr(f"sensor.{__name__}_kwh_cost_price.solar_share", f"{ev_solar_share*100:.0f}%")
            set_attr(f"sensor.{__name__}_kwh_cost_price.solar_kwh_price", f"{solar_kwh_price:.2f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.grid_share", f"{ev_grid_share*100:.0f}%")
            set_attr(f"sensor.{__name__}_kwh_cost_price.grid_kwh_price", f"{grid_kwh_price:.2f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.ev_kwh_price", f"{ev_total_price_kwh:.2f} kr/kWh")
            
        set_charging_price(ev_total_price_kwh)

    return ev_total_price_kwh

def calc_solar_kwh(period = 60, ev_kwh = None, solar_period_current_hour = False):
    _LOGGER = globals()['_LOGGER'].getChild("calc_solar_kwh")
    
    if not is_solar_configured(): return 0.0
    
    minutes = getMinute() if solar_period_current_hour else period
    
    if ev_kwh is None:
        now = getTime()
        past = now - datetime.timedelta(minutes=minutes)
        
        ev_kwh = round(abs(float(get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="kW", error_state=0.0))), 3)
        
    solar_kwh_available = round(max(solar_production_available(period = minutes, withoutEV = True), 0.0) / 1000, 3)
    
    _LOGGER.debug(f"minutes:{minutes} ev_kwh:{ev_kwh} solar_kwh_available:{solar_kwh_available} return:{round(min(solar_kwh_available, ev_kwh), 3)}")
    
    return round(min(solar_kwh_available, ev_kwh), 3)

def load_kwh_prices():
    _LOGGER = globals()['_LOGGER'].getChild("load_kwh_prices")
    global KWH_AVG_PRICES_DB
    force_save = False
    
    try:
        create_yaml(f"{__name__}_kwh_avg_prices_db", db=KWH_AVG_PRICES_DB)
        KWH_AVG_PRICES_DB = load_yaml(f"{__name__}_kwh_avg_prices_db")
    except Exception as e:
        _LOGGER.error(f"Cant load {__name__}_kwh_avg_prices_db: {e}")
    
    if KWH_AVG_PRICES_DB == {} or not KWH_AVG_PRICES_DB:
        KWH_AVG_PRICES_DB = {}
    
    if "max" not in KWH_AVG_PRICES_DB:
        KWH_AVG_PRICES_DB['max'] = []
        KWH_AVG_PRICES_DB['mean'] = []
        KWH_AVG_PRICES_DB['min'] = []
        force_save = True
        
    if "history" not in KWH_AVG_PRICES_DB:
        KWH_AVG_PRICES_DB['history'] = {}
        force_save = True
        for i in range(24):
            KWH_AVG_PRICES_DB['history'][i] = []
        
    if "history_sell" not in KWH_AVG_PRICES_DB:
        KWH_AVG_PRICES_DB['history_sell'] = {}
        force_save = True
        for i in range(24):
            KWH_AVG_PRICES_DB['history_sell'][i] = []
    
    if force_save:
        append_kwh_prices()
        save_kwh_prices()
    
    set_low_mean_price()
    
def save_kwh_prices():
    global KWH_AVG_PRICES_DB
    
    if len(KWH_AVG_PRICES_DB) > 0:
        save_changes(f"{__name__}_kwh_avg_prices_db", KWH_AVG_PRICES_DB)

def append_kwh_prices():
    _LOGGER = globals()['_LOGGER'].getChild("append_kwh_prices")
    global KWH_AVG_PRICES_DB
    
    if len(KWH_AVG_PRICES_DB) == 0:
        load_kwh_prices()
    
    if CONFIG['prices']['entity_ids']['power_prices_entity_id'] in state.names(domain="sensor"):
        if "today" in get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id']):
            today = get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id'], "today")
            _LOGGER.info(today)
            
            max_price = max(today) - get_refund()
            mean_price = round(average(today), 3) - get_refund()
            min_price = min(today) - get_refund()
            
            max_length = CONFIG['database']['kwh_avg_prices_db_data_to_save']
            
            KWH_AVG_PRICES_DB['max'].insert(0, max_price)
            KWH_AVG_PRICES_DB['mean'].insert(0, mean_price)
            KWH_AVG_PRICES_DB['min'].insert(0, min_price)
            KWH_AVG_PRICES_DB['max'] = KWH_AVG_PRICES_DB['max'][:max_length]
            KWH_AVG_PRICES_DB['mean'] = KWH_AVG_PRICES_DB['mean'][:max_length]
            KWH_AVG_PRICES_DB['min'] = KWH_AVG_PRICES_DB['min'][:max_length]

            power_prices_attr = get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id'])
            
            transmissions_nettarif = 0.0
            systemtarif = 0.0
            elafgift = 0.0
            
            if "tariffs" in power_prices_attr:
                attr = power_prices_attr["tariffs"]
                transmissions_nettarif = attr["additional_tariffs"]["transmissions_nettarif"]
                systemtarif = attr["additional_tariffs"]["systemtarif"]
                elafgift = attr["additional_tariffs"]["elafgift"]
                
            
            for i in range(24):
                KWH_AVG_PRICES_DB['history'][i].insert(0, today[i] - get_refund())
                KWH_AVG_PRICES_DB['history'][i] = KWH_AVG_PRICES_DB['history'][i][:max_length]
                
                if is_solar_configured():
                    tariffs = 0.0
                    
                    if "tariffs" in power_prices_attr:
                        tariffs = attr["tariffs"][str(i)]
                        
                    tariff_sum = sum([transmissions_nettarif, systemtarif, elafgift, tariffs])
                    raw_price = today[i] - tariff_sum - get_refund()

                    energinets_network_tariff = SOLAR_SELL_TARIFF["energinets_network_tariff"]
                    energinets_balance_tariff = SOLAR_SELL_TARIFF["energinets_balance_tariff"]
                    solar_production_seller_cut = SOLAR_SELL_TARIFF["solar_production_seller_cut"]
                    
                    sell_tariffs = sum((solar_production_seller_cut, energinets_network_tariff, energinets_balance_tariff, transmissions_nettarif, systemtarif))
                    sell_price = raw_price - sell_tariffs
                        
                    sell_price = round(sell_price, 3)
                    KWH_AVG_PRICES_DB['history_sell'][i].insert(0, sell_price)
                    KWH_AVG_PRICES_DB['history_sell'][i] = KWH_AVG_PRICES_DB['history_sell'][i][:max_length]
                
            save_kwh_prices()
            
            set_low_mean_price()

def set_low_mean_price():
    average_price = round(average(KWH_AVG_PRICES_DB['min']), 3)
    set_attr(f"sensor.{__name__}_charge_very_cheap_battery_level.low_mean_price", round(average_price, 2))
    set_attr(f"sensor.{__name__}_charge_ultra_cheap_battery_level.low_mean_price", round((average_price * 0.75), 2))

def notify_set_battery_level():
    if is_ev_configured(): return
    
    if battery_level() == 0.0:
        data = {
            "actions": [
                {
                    "action": "URI",
                    "title": "Sæt batteri niveau",
                    "uri": f"entityId:input_number.{__name__}_battery_level"
                }
            ]
        }
        my_notify(message = f"Husk at sætte batteri niveauet på elbilen i Home Assistant", title = f"{__name__.capitalize()} Elbilen batteri niveau", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True)

def notify_battery_under_daily_battery_level():
    if battery_level() < get_min_daily_battery_level() and battery_level() != 0.0:
        data = {
            "actions": [
                {
                    "action": "URI",
                    "title": "Aktivere for at starte tvangsladningen",
                    "uri": f"entityId:input_boolean.{__name__}_forced_charging_daily_battery_level"
                }
            ]
        }
        my_notify(message = f"Skal elbilen tvangslades til minimum daglig batteri niveau\nLader ikke i de 3 dyreste timer", title = f"{__name__.capitalize()} Elbilen batteri niveau under daglig batteri niveau", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True)

if INITIALIZATION_COMPLETE:
    @time_trigger("startup")
    def startup(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("startup")
        _LOGGER.info(f"{BASENAME} started")
        set_charging_rule(f"📟Sætter entities op")
        set_entity_friendlynames()
        emoji_description()
        set_default_entity_states()
        
        set_charging_rule(f"📟Indlæser databaserne")
        
        load_solar_available_db()
        load_kwh_prices()
        load_drive_efficiency()
        load_km_kwh_efficiency()
        
        if benchmark_loaded: start_benchmark("load_charging_history")
        load_charging_history()
        if benchmark_loaded: end_benchmark("load_charging_history")
        
        solar_charged_percentage()
        is_battery_fully_charged(dont_set_date=True)
        set_estimated_range()
        
        _LOGGER.info(f"EV solar charging max to {get_max_recommended_charge_limit_battery_level()}%")
        _LOGGER.info(f"EV solar charging 1phase min amps {CONFIG['solar']['charging_three_phase_min_amp'] } ({CONFIG['solar']['charging_three_phase_min_amp']  * CONFIG['charger']['power_voltage'] } Watts)")
        _LOGGER.info(f"EV solar charging 3phase max amps {CONFIG['charger']['charging_max_amp']} ({(CONFIG['charger']['charging_max_amp'] * CONFIG['charger']['charging_phases']) * CONFIG['charger']['power_voltage'] } Watts)")
        _LOGGER.info(f"EV solar charging trigger ON {SOLAR_CHARGING_TRIGGER_ON} Watts")
        _LOGGER.info(f"EV grid charging min to {get_min_daily_battery_level()}%")
        _LOGGER.info(f"EV every cheap grid charging max to {get_very_cheap_grid_charging_max_battery_level()}%")
        _LOGGER.info(f"EV grid charging max amps {CONFIG['charger']['charging_max_amp'] } ({CONFIG['charger']['charging_max_amp']  * (CONFIG['charger']['power_voltage']  * CONFIG['charger']['charging_phases'])} Watts)")
        _LOGGER.info(f"battery_range: {battery_range()}")
        _LOGGER.info(f"battery_level: {battery_level()}")
        distance_per_percent = avg_distance_per_percentage()
        _LOGGER.info(f"avg_distance_per_percentage: {distance_per_percent}")
        _LOGGER.info(f"HA estimated range: {battery_level() * distance_per_percent}")
        _LOGGER.info(f"range_to_battery_level: {range_to_battery_level()}")
        _LOGGER.info(f"kwh_needed_for_charging: {kwh_needed_for_charging()}")
        _LOGGER.info(f"calc_charging_amps: {calc_charging_amps(0.0, report = True)}")

        calc_kwh_price(getMinute(), update_entities = True)
        
        set_charging_rule(f"📟Beregner ladeplan")
        if benchmark_loaded: start_benchmark("charge_if_needed")
        charge_if_needed()
        if benchmark_loaded: end_benchmark("charge_if_needed")
        
        preheat_ev()
        
    @state_trigger(f"input_boolean.{__name__}_fill_up")
    @state_trigger(f"input_boolean.{__name__}_days_to_charge")
    def charging_rule(trigger_type=None, var_name=None, value=None, old_value=None):
        if value == "on":
            if var_name == f"input_boolean.{__name__}_fill_up":
                if get_state(f"input_boolean.{__name__}_days_to_charge") == "on":
                    set_state(f"input_boolean.{__name__}_days_to_charge", "off")
            elif var_name == f"input_boolean.{__name__}_days_to_charge":
                if get_state(f"input_boolean.{__name__}_fill_up") == "on":
                    set_state(f"input_boolean.{__name__}_fill_up", "off")
                
    @time_trigger(f"cron(0/{CONFIG['cron_interval']} * * * *)")
    @state_trigger(f"input_button.{__name__}_enforce_planning")
    @state_trigger(f"input_boolean.{__name__}_allow_manual_charging_now")
    @state_trigger(f"input_boolean.{__name__}_allow_manual_charging_solar")
    @state_trigger(f"input_boolean.{__name__}_calculate_charging_loss")
    def triggers_charge_if_needed(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("triggers_charge_if_needed")
        if trigger_type == "time":
            calc_kwh_price(getMinute(), update_entities = True)
            
        if is_charging():
            wake_up_ev()
            
        charge_if_needed()
            
        is_battery_fully_charged()
        set_estimated_range()

    @state_trigger(f"input_boolean.{__name__}_trip_charging == 'on' or input_boolean.{__name__}_trip_charging == 'off'")
    @state_trigger(f"input_number.{__name__}_trip_charge_procent")
    @state_trigger(f"input_number.{__name__}_trip_range_needed")
    @state_trigger(f"input_datetime.{__name__}_trip_date_time")
    @state_trigger(f"input_datetime.{__name__}_trip_homecoming_date_time")
    @state_trigger(f"input_button.{__name__}_trip_reset")
    def state_trigger_ev_trips(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("state_trigger_ev_trips")
        global LAST_TRIP_CHANGE_DATETIME
        
        if var_name == f"input_boolean.{__name__}_trip_charging":
            if value == "on":
                if ready_to_charge():
                    startCharging = False
                    if get_trip_target_level() != 0.0:
                        startCharging = True
                        charging_limit = get_trip_target_level()
                        _LOGGER.debug(f"Setting new trip charging BATTERY_LEVEL to {charging_limit}")
                    if get_trip_range() != 0.0:
                        startCharging = True
                        charging_limit = range_to_battery_level(get_trip_range(), get_min_trip_battery_level())
                        _LOGGER.debug(f"Setting new trip range to {get_trip_range()}")

                    if startCharging:
                        ev_send_command(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'], verify_charge_limit(charging_limit))
                        
                        if get_trip_date_time() == resetDatetime():
                            set_charger_charging_amps(CONFIG['charger']['charging_phases'], CONFIG['charger']['charging_max_amp'])
                                
                            start_charging()
                            _LOGGER.info("Begin to charge now")
                        else:
                            _LOGGER.info(f"Schedule charging to trip at {get_trip_date_time()}")
                            charge_if_needed()
            else:
                charge_if_needed()
                
        elif var_name == f"input_number.{__name__}_trip_charge_procent":
            if value in ("unknown", "unavailable"): return
            if get_trip_target_level() != 0.0:
                set_state(f"input_number.{__name__}_trip_range_needed", 0.0)
            if is_trip_planned():
                _LOGGER.debug(f"Setting new trip charging BATTERY_LEVEL to {value}")
                
        elif var_name == f"input_number.{__name__}_trip_range_needed":
            if value in ("unknown", "unavailable"): return
            if get_trip_range() != 0.0:
                set_state(f"input_number.{__name__}_trip_charge_procent", 0.0)
            if is_trip_planned():
                _LOGGER.debug(f"Setting new trip range to {value}")
                
        elif var_name == f"input_datetime.{__name__}_trip_date_time":
            if value in ("unknown", "unavailable"): return
            value = toDateTime(value)
            
            if value != resetDatetime() and (get_trip_homecoming_date_time() == resetDatetime() or get_trip_homecoming_date_time() < value):
                set_state(f"input_datetime.{__name__}_trip_homecoming_date_time", getTimeEndOfDay(value))
                
        elif var_name == f"input_datetime.{__name__}_trip_homecoming_date_time":
            if value in ("unknown", "unavailable"): return
            value = toDateTime(value)
            
            if value != resetDatetime() and (get_trip_date_time() == resetDatetime() or get_trip_date_time() > value):
                set_state(f"input_datetime.{__name__}_trip_date_time", value - datetime.timedelta(hours=1))
                    
        elif var_name == f"input_button.{__name__}_trip_reset":
            trip_reset()
            
        LAST_TRIP_CHANGE_DATETIME = getTime()
            
    @state_trigger(f"{CONFIG['charger']['entity_ids']['power_consumtion_entity_id']}")
    def state_trigger_charger_power(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("state_trigger_charger_power")
        global CURRENT_CHARGING_SESSION
        
        try:
            if float(old_value) > 0.0 and float(value) == 0.0 and CURRENT_CHARGING_SESSION['type'] == "no_rule":
                if not charging_without_rule():
                    charging_history(None, "")
                    set_charging_rule(f"Lader ikke")
        except:
            pass
    
    @state_trigger(f"{CONFIG['charger']['entity_ids']['status_entity_id']}")
    def state_trigger_charger_port(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("state_trigger_charger_port")
        if "disconnected" in old_value:
            notify_set_battery_level()
            wake_up_ev()
            charge_if_needed()
        elif "disconnected" in value:
            wake_up_ev()
            set_state(f"input_boolean.{__name__}_allow_manual_charging_now", "off")
            set_state(f"input_boolean.{__name__}_allow_manual_charging_solar", "off")
            set_state(f"input_boolean.{__name__}_forced_charging_daily_battery_level", "off")
        elif "charging" in old_value and "complete" in value:
            if not is_ev_configured():
                charging_history(None, "")
                set_state(entity_id=f"input_number.{__name__}_battery_level", new_state=get_completed_battery_level())
         
    if is_entity_configured(CONFIG['charger']['entity_ids']['cable_connected_entity_id']):
        @state_trigger(f"{CONFIG['charger']['entity_ids']['cable_connected_entity_id']}")
        def state_trigger_charger_cable_connected(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("state_trigger_charger_cable_connected")
            wake_up_ev()
            
    if is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']):
        @state_trigger(f"{CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']}")
        def state_trigger_ev_charge_cable(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("state_trigger_ev_charge_cable")
            wake_up_ev()

    if is_ev_configured():
        @time_trigger(f"cron(0/5 * * * *)")
        def cron_five_every_minute(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("cron_five_every_minute")
            global ENTITY_INTEGRATION_DICT
            preheat_ev()
            _LOGGER.warning(f"DEBUG ENTITY_INTEGRATION_DICT:\n{pformat(ENTITY_INTEGRATION_DICT, width=200, compact=True)}")
            
        @state_trigger(f"{CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']}")
        def state_trigger_ev_charger_port(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("state_trigger_ev_charger_port")
            drive_efficiency(str(value))
            notify_battery_under_daily_battery_level()
    else:
        @state_trigger(f"input_number.{__name__}_battery_level")
        def emulated_battery_level_changed(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("emulated_battery_level_changed")
            if float(old_value) == 0.0 and float(value) < get_min_daily_battery_level():
                notify_battery_under_daily_battery_level()
            
    @time_trigger("startup")
    @time_trigger(f"cron(0/5 * * * *)")
    def trip_cron_five_every_minute(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("trip_cron_five_every_minute")
        trip_activate_reminder()
        
    @time_trigger(f"cron(59 * * * *)")
    def cron_hour_end(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("cron_hour_end")
        solar_available_append_to_db(solar_production_available(period = 60, withoutEV = True))
        charging_history(None, "")
        kwh_charged_by_solar()
        solar_charged_percentage()
        
    @time_trigger(f"cron(0 0 * * *)")
    def cron_new_day(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("cron_new_day")
        reset_counter_entity_integration()
        
    @time_trigger(f"cron(0 1 * * *)")
    def cron_append_kwh_prices(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("cron_append_kwh_prices")
        append_kwh_prices()

    @state_trigger(f"input_boolean.{__name__}_calculate_charging_loss")#TODO Add phase and amp levels measurements
    @state_trigger(f"{CONFIG['charger']['entity_ids']['status_entity_id']}")
    @state_trigger(f"{CONFIG['charger']['entity_ids']['kwh_meter_entity_id']}")
    def calculate_charging_loss(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("calculate_charging_loss")
        
        global CONFIG, CHARGING_LOSS_CAR_BEGIN_KWH, CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL, CHARGING_LOSS_CHARGER_BEGIN_KWH, CHARGING_LOSS_CHARGING_COMPLETED

        try:
            battery_size = CONFIG['ev_car']['battery_size']
            charger_current_kwh = float(get_state(CONFIG['charger']['entity_ids']['kwh_meter_entity_id'], float_type=True, try_history=True, error_state=None))
            completed_battery_level = float(get_state(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'], float_type=True, error_state=100.0)) if is_ev_configured() else get_completed_battery_level()
            completed_battery_size = battery_size * (completed_battery_level / 100.0)
            
            if var_name == f"input_boolean.{__name__}_calculate_charging_loss":
                if value != "on":
                    CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL = 0.0
                    CHARGING_LOSS_CAR_BEGIN_KWH = 0.0
                    CHARGING_LOSS_CHARGER_BEGIN_KWH = 0.0
                    CHARGING_LOSS_CHARGING_COMPLETED = False
                    return
                    
                if battery_level() == 0.0:
                    raise Exception("Battery level is 0.0, make sure battery level is set or car is connected")
                
                CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL = battery_level()
                CHARGING_LOSS_CAR_BEGIN_KWH = battery_size * (CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL / 100.0)
                CHARGING_LOSS_CHARGER_BEGIN_KWH = charger_current_kwh
                
            if not is_calculating_charging_loss(): return
            
            _LOGGER.warning(f"completed_battery_level: {completed_battery_level}")
            _LOGGER.warning(f"completed_battery_size: {completed_battery_size}")
            _LOGGER.warning(f"CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL: {CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL}")
            _LOGGER.warning(f"CHARGING_LOSS_CAR_BEGIN_KWH: {CHARGING_LOSS_CAR_BEGIN_KWH}")
            _LOGGER.warning(f"CHARGING_LOSS_CHARGER_BEGIN_KWH: {CHARGING_LOSS_CHARGER_BEGIN_KWH}")
            
            if var_name == f"input_boolean.{__name__}_calculate_charging_loss":
                return
            elif var_name == f"{CONFIG['charger']['entity_ids']['status_entity_id']}":
                if value in ["completed", "awaiting_start", "awaiting_authorization"] and "charging" in old_value:
                    CHARGING_LOSS_CHARGING_COMPLETED = True
            elif var_name == f"{CONFIG['charger']['entity_ids']['kwh_meter_entity_id']}":
                    if CHARGING_LOSS_CHARGING_COMPLETED:
                        added_kwh = charger_current_kwh - CHARGING_LOSS_CHARGER_BEGIN_KWH
                        charging_loss = round((completed_battery_size - CHARGING_LOSS_CAR_BEGIN_KWH) / added_kwh - 1, 4)
                        
                        if charging_loss >= 0.0:
                            raise Exception(f"Charging loss was not negative {charging_loss * 100.0}%, set charging limit in car and let charging complete")
                        
                        CONFIG['charger']['charging_loss'] = charging_loss
                        save_changes(f"{__name__}_config", CONFIG)
                        
                        set_state(f"input_boolean.{__name__}_calculate_charging_loss", "off")
                        my_notify(message = f"Ladetab er kalkuleret til {round(charging_loss * 100)}%", title = f"{__name__.capitalize()} Ladetab kalkuleret", notify_list = CONFIG['notify_list'], admin_only = False, always = True)
            else:
                raise Exception(f"Unknown error: trigger_type={trigger_type}, var_name={var_name}, value={value}, old_value={old_value}")
        except Exception as e:
            CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL = 0.0
            CHARGING_LOSS_CAR_BEGIN_KWH = 0.0
            CHARGING_LOSS_CHARGER_BEGIN_KWH = 0.0
            CHARGING_LOSS_CHARGING_COMPLETED = False
            _LOGGER.error(f"Failed to calculate charging loss: {e}")
            my_notify(message = f"Fejlede i kalkulation af ladetab:\n{e}", title = f"{__name__.capitalize()} Fejl", notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True)
            
    '''@time_trigger("startup")
    @state_trigger(f"input_boolean.{__name__}_debug_log")
    def ev_debug():
        logger.set_level(**{"custom_components.pyscript.file.my_script": "debug"})
        _LOGGER = globals()['_LOGGER'].getChild("ev_debug")
        log_level = "INFO"
        if get_state(f"input_boolean.{__name__}_debug_log") == "on":
            log_level = "DEBUG"
        data = '{pyscript.ev: ' + log_level +'}'
        _LOGGER.info(data)
        
        if service.has_service("logger", "set_level"):
            service.call("logger", "set_level", blocking=True,
                                pyscript.ev=log_level)
        _LOGGER.info(f"Setting pyscript.ev loglevel to {log_level}")'''

    @time_trigger("shutdown")
    def shutdown(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("shutdown")
        global CONFIG
        set_charging_rule(f"📟Scriptet lukket ned")
        charging_history(None, "")
        reset_counter_entity_integration()
        
        try:
            CONFIG = load_yaml(f"{__name__}_config")
            CONFIG['ev_car']['daily_drive_distance'] = get_entity_daily_distance()
            CONFIG['ev_car']['min_daily_battery_level'] = get_min_daily_battery_level()
            CONFIG['ev_car']['min_trip_battery_level'] = get_min_trip_battery_level()
            CONFIG['ev_car']['min_charge_limit_battery_level'] = get_min_charge_limit_battery_level()
            CONFIG['ev_car']['max_recommended_charge_limit_battery_level'] = get_max_recommended_charge_limit_battery_level()
            CONFIG['ev_car']['very_cheap_grid_charging_max_battery_level'] = get_very_cheap_grid_charging_max_battery_level()
            CONFIG['ev_car']['ultra_cheap_grid_charging_max_battery_level'] = get_ultra_cheap_grid_charging_max_battery_level()
            
            if is_solar_configured():
                CONFIG['solar']['production_price'] = float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price']))
            
            save_changes(f"{__name__}_config", CONFIG)
        except Exception as e:
            _LOGGER.error(f"Cant save config from Home assistant to config: {e}")
            

@state_trigger(f"input_button.{__name__}_restart_script")
def restart(trigger_type=None, var_name=None, value=None, old_value=None):
    _LOGGER = globals()['_LOGGER'].getChild("restart")
    restart_script()