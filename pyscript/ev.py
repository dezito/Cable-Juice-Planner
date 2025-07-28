import asyncio
import datetime
import random
import string
import subprocess
from itertools import chain
from typing import Optional
from pprint import pformat

try:
    from benchmark import (
        start_benchmark,
        end_benchmark,
        benchmark_decorator)
    benchmark_loaded = True
except:
    benchmark_loaded = False

from filesystem import (
    get_config_folder,
    file_exists,
    get_file_modification_time,
    create_yaml,
    load_yaml,
    save_yaml)
from hass_manager import (
    get_state,
    get_attr,
    set_state,
    set_attr,
    get_manufacturer,
    get_identifiers,
    get_integration,
    reload_integration)
from history import (
    get_values,
    get_average_value,
    get_max_value,
    get_min_value)
from mynotify import (
    my_notify,
    my_persistent_notification)
from mytime import (
    getTime,
    getTimePlusDays,
    daysBetween,
    hoursBetween,
    minutesBetween,
    getMinute,
    getHour,
    getMonth,
    getYear,
    getMonthFirstDay,
    getTimeStartOfDay,
    getTimeEndOfDay,
    getDayOfWeek,
    getDayOfWeekText,
    date_to_string,
    toDateTime,
    resetDatetime,
    reset_time_to_hour,
    is_day,
    add_months)
from utils import (
    in_between,
    round_up,
    average,
    calculate_ema,
    calculate_trend,
    reverse_list,
    get_specific_values,
    get_closest_key,
    get_dict_value_with_path,
    delete_dict_key_with_path,
    rename_dict_keys,
    compare_dicts_unique_to_dict1,
    update_dict_with_new_keys,
    limit_dict_size,
    contains_any,
    check_next_24_hours_diff)

import homeassistant.helpers.sun as sun

from logging import getLogger
TITLE = f"Cable Juice Planner ({__name__}.py)"
BASENAME = f"pyscript.{__name__}"
_LOGGER = getLogger(BASENAME)

INITIALIZATION_COMPLETE = False
TESTING = False
PREHEATING = False

CHARGER_CONFIGURED = None
SOLAR_CONFIGURED = None
POWERWALL_CONFIGURED = None
EV_CONFIGURED = None

USING_OFFLINE_PRICES = False
LAST_SUCCESSFUL_GRID_PRICES = {}

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

POWERWALL_CHARGING_TEXT = ""

SOLAR_PRODUCTION_TRIGGER = 100.0  # Minimum solar production in Watt to consider solar available
POWERWALL_CHARGING_TRIGGER = 500.0  # Minimum Powerwall charging in Watt to consider Powerwall charging
POWERWALL_DISCHARGING_TRIGGER = 500.0 # Minimum Powerwall discharging in Watt to consider Powerwall discharging

LAST_WAKE_UP_DATETIME = resetDatetime()
LAST_TRIP_CHANGE_DATETIME = getTime()

ENTITY_UNAVAILABLE_STATES = ("unavailable", "unknown")
CHARGER_READY_STATUS = ("on", "connect", "connected", "ready", "ready_to_charge", "awaiting_authorization", "awaiting_start")
CHARGER_NOT_READY_STATUS = ("off", "disconnect", "disconnected")
CHARGER_COMPLETED_STATUS = ("completed", "finished")
CHARGER_CHARGING_STATUS = ("charging",)
EV_PLUGGED_STATES = ("on", "open", "plugged", "connect", "connected", "plugged_waiting_for_charge", "manual")
EV_UNPLUGGED_STATES = ("off", "closed", "unplugged", "disconnect", "disconnected")

INSTANCE_ID = random.randint(0, 10000)
TASKS = {}
TASKS_REMOVE = []
SHUTTING_DOWN = False

CONFIG = {}
CONFIG_LAST_MODIFIED = None

POWER_VALUES_DB = {}
POWER_VALUES_DB_VERSION = 1.0

SOLAR_PRODUCTION_AVAILABLE_DB = {}
SOLAR_PRODUCTION_AVAILABLE_DB_VERSION = 2.0

KWH_AVG_PRICES_DB = {}
KWH_AVG_PRICES_DB_VERSION = 2.0

DRIVE_EFFICIENCY_DB = []
KM_KWH_EFFICIENCY_DB = []

CHARGING_HISTORY_ENDING_BYTE_SIZE = None
CHARGING_HISTORY_DB = {}
OVERVIEW_HISTORY = {}

BATTERY_LEVEL_EXPENSES = {}
CHARGING_PLAN = {}
CHARGE_HOURS = {}
LAST_DRIVE_EFFICIENCY_DATA = {}

LOCAL_ENERGY_PREDICTION_DB = {
    "solar_prediction": {},
}
LOCAL_ENERGY_PRICES = {
    "solar_kwh_price": {},
    "powerwall_kwh_price": {},
}

COLOR_THRESHOLDS = [
    ("price1", "#0064FF"),
    ("price2", "#0096FF"),
    ("price3", "#00B496"),
    ("price4", "#00FA50"),
    ("price5", "#00FF32"),
    ("price6", "#00FF00"),
    ("price7", "#FFFF00"),
    ("price8", "#FFA500"),
    ("price9", "#FF5000"),
    ("price10", "#C81919"),
    ("price11", "#C800C8"),
]

SOLAR_SELL_TARIFF = {
    "energinets_network_tariff": 0.0030,
    "energinets_balance_tariff": 0.0024,
    "solar_production_seller_cut": 0.01
}

CHARGING_HISTORY_RUNNING = False
CHARGING_HISTORY_QUEUE = []
EV_SEND_COMMAND_QUEUE = []

INTEGRATION_OFFLINE_TIMESTAMP = {}

CURRENT_CHARGING_SESSION = {}
WEATHER_CONDITION_DICT = {
    "sunny": 100,                # Maksimal solproduktion, ideelle forhold
    "windy": 80,                 # Minimal effekt på solproduktion
    "windy-variant": 80,         # Ligner windy, mindre effekt på produktionen
    "partlycloudy": 60,          # Moderat reduceret solproduktion
    "cloudy": 40,                # Betydelig reduceret solproduktion
    "rainy": 40,                 # Betydelig reduceret produktion på grund af regn og skyer
    "pouring": 20,               # Kraftig regn, stor reduktion i produktion
    "lightning": 20,             # Stor reduktion pga. skydække og storm
    "lightning-rainy": 20,       # Kraftig storm og regn, signifikant reduceret produktion
    "snowy": 20,                 # Sne, reducerer solproduktionen markant
    "snowy-rainy": 20,           # Kombination af sne og regn, meget lav produktion
    "clear-night": 0,            # Ingen produktion om natten
    "fog": 20,                   # Tåge, meget lav produktion pga. nedsat sollys
    "hail": 0,                   # Ingen produktion under hagl
    "exceptional": 0             # Ekstreme forhold, ingen produktion
}

INTEGRATION_DAILY_LIMIT_BUFFER = 50
ENTITY_INTEGRATION_DICT = {
    "supported_integrations": {
        "cupra_we_connect": {"daily_limit": 500},
        "kia_uvo": {"daily_limit": 200},
        "monta": {"daily_limit": 144000},
        "tesla": {"daily_limit": 200},
        "tessie": {"daily_limit": 500}
    },
    "entities": {},
    "commands_last_hour": {},
    "commands_history": {},
    "last_reload": {},
    "counter": {}
}

CHARGING_TYPES = {
    "error": {
        "priority": 1,
        "emoji": "☠️",
        "description": "Kritisk fejl, nødladning"
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
        "emoji": "📈",
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
    "eighth_workday_preparation": {
        "priority": 7.7,
        "emoji": "8️⃣",
        "description": "Ottende arbejdsdag"
    },
    "fill_up": {
        "priority": 8,
        "emoji": "📈",
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
    "grid_charging": {
        "priority": 10,
        "emoji": "⚡",
        "description": "Ladning fra elnettet"
    },
    "solar": {
        "priority": 11,
        "emoji": "☀️",
        "description": "Solcelle ladning / overproduktion"
    },
    "powerwall": {
        "priority": 11.1,
        "emoji": "🛢️",
        "description": "Ladning fra Powerwall"
    },
    "powerwall_avg_symbol": {
        "priority": 11.2,
        "emoji": "x̄",
        "description": "Gennemsnitlig ladning af Powerwall"
    },
    "battery_stored": {
        "priority": 12,
        "emoji": "🔋",
        "description": "Forbrug fra batteri"
    },
    "charging_loss": {
        "priority": 95,
        "emoji": "🤖",
        "description": "Ladetab beregning"
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
    "battery_usage": {
        "priority": 100,
        "emoji": "📉",
        "description": "Afgang & hjemkomst batteri niveau"
    },
    "charging_problem": {
        "priority": 999,
        "emoji": "❗",
        "description": "Ladning problemer"
    },
    "charging_error": {
        "priority": 1000,
        "emoji": "❌",
        "description": "Ladning fejlede helt"
    }
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
        "charging_loss": -0.05,
    },
    "cron_interval": 5,
    "database": {
        "power_values_db_data_to_save": 15,
        "solar_available_db_data_to_save": 10,
        "kwh_avg_prices_db_data_to_save": 15,
        "drive_efficiency_db_data_to_save": 15,
        "km_kwh_efficiency_db_data_to_save": 15,
        "charging_history_db_data_to_save": 12
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
        "typical_daily_distance_non_working_day": 50.0,
        "workday_distance_needed_monday": 50.0,
        "workday_distance_needed_tuesday": 50.0,
        "workday_distance_needed_wednesday": 50.0,
        "workday_distance_needed_thursday": 50.0,
        "workday_distance_needed_friday": 50.0,
        "workday_distance_needed_saturday": 50.0,
        "workday_distance_needed_sunday": 50.0,
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
            "powerwall_battery_level_entity_id": "",
            "ignore_consumption_from_entity_ids": []
        },
        "power_consumption_entity_id_include_powerwall_charging": False,
        "power_consumption_entity_id_include_powerwall_discharging": False,
        "invert_powerwall_watt_flow_entity_id": False
    },
    "notification": {
        "update_available": True,
        "efficiency_on_cable_plug_in": True,
        "preheating": True,
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
            "production_entity_id": "",
            "forecast_entity_id": ""
        },
        "solarpower_use_before_minutes": 60,
        "max_to_current_hour": True,
        "allow_grid_charging_above_solar_available": -100.0,
        "charging_single_phase_min_amp": 6.0,
        "charging_single_phase_max_amp": 16.0,
        "charging_three_phase_min_amp": 5.0,
        "production_price": -1.00,
        "ev_charge_after_powerwall_battery_level": 0.0,
        "powerwall_battery_size": 10.0,
        "inverter_discharging_power_limit": 5000.0,
        "powerwall_charging_power_limit": 5000.0,
        "powerwall_discharging_power": 5000.0,
        "enable_selling_during_expensive_hours": True
    },
    "testing_mode": False
}

CONFIG_KEYS_RENAMING = {# Old path: New path (seperated by ".")
    "home.ignore_consumption_from_entity_id": "home.ignore_consumption_from_entity_ids",
    "ev_car.daily_drive_distance": "ev_car.typical_daily_distance_non_working_day"
}

COMMENT_DB_YAML = {
    "first_run": "**Required** After editing the file set this to false",
    "cron_interval": "**Required** Interval between state check and function runs",
    "testing_mode": "In testing mode, no commands/service calls are sent to charger or ev",
    "charger.entity_ids.status_entity_id": f"**Required** Charger status (Supported states: {tuple(chain(CHARGER_READY_STATUS, CHARGER_CHARGING_STATUS, CHARGER_COMPLETED_STATUS))})",
    "charger.entity_ids.power_consumtion_entity_id": "**Required** Charging power in Watt",
    "charger.entity_ids.kwh_meter_entity_id": "**Required** Maybe use Riemann-sum integral-sensor (charger kwh meter is slow, as with Easee) else the chargers lifetime kwh meter",
    "charger.entity_ids.lifetime_kwh_meter_entity_id": "**Required** Same as kwh_meter_entity_id, if you dont want the chargers lifetime kwh meter",
    "charger.entity_ids.enabled_entity_id": "Turn Charger unit ON/OFF, NOT for start/stop charging",
    "charger.entity_ids.dynamic_circuit_limit": "If not set, charger.entity_ids.start_stop_charging_entity_id must be set",
    "charger.entity_ids.co2_entity_id": "Energi Data Service CO2 entity_id",
    "charger.entity_ids.cable_connected_entity_id": f"If EV dont have cable connected entity, use this instead to determine, if ev is connected to charger (Supported states: {tuple(chain(CHARGER_READY_STATUS, CHARGER_CHARGING_STATUS, CHARGER_COMPLETED_STATUS))})",
    "charger.entity_ids.start_stop_charging_entity_id": "If using other integration than Easee to start stop charging, like Monta",
    "charger.power_voltage": "**Required** Grid power voltage",
    "charger.charging_phases": "**Required** Phases available for the ev",
    "charger.charging_max_amp": "**Required** Maximum amps for the ev",
    "charger.charging_loss": f"**Required** Can be auto calculated via WebGUI with input_boolean.{__name__}_calculate_charging_loss",
    "database.power_values_db_data_to_save": "Days back to save power values",
    "database.solar_available_db_data_to_save": "Amount to save, per cloud coverage density",
    "database.kwh_avg_prices_db_data_to_save": "Amount to save",
    "database.drive_efficiency_db_data_to_save": "Amount to save",
    "database.km_kwh_efficiency_db_data_to_save": "Amount to save",
    "database.charging_history_db_data_to_save": "Save X month back",
    "ev_car": "EV car configuration",
    "ev_car.entity_ids": "Entity IDs used by the EV car",
    "ev_car.entity_ids.wake_up_entity_id": "Force wake up (Leave blank if using Hyundai-Kia-Connect, using wake up serive instead)",
    "ev_car.entity_ids.climate_entity_id": "Used to preheat ev",
    "ev_car.entity_ids.odometer_entity_id": "**Required**",
    "ev_car.entity_ids.estimated_battery_range_entity_id": "**Required** Must precise battery range",
    "ev_car.entity_ids.usable_battery_level_entity_id": "**Required** Must precise battery level",
    "ev_car.entity_ids.charge_port_door_entity_id": f"Used to determine if ev charge port is open/closed (Supported states: {tuple(chain(EV_PLUGGED_STATES, EV_UNPLUGGED_STATES))})",
    "ev_car.entity_ids.charge_cable_entity_id": f"Used to determine if ev is connected to charger (Supported states: {tuple(chain(EV_PLUGGED_STATES, EV_UNPLUGGED_STATES))})",
    "ev_car.entity_ids.charge_switch_entity_id": "Start/stop charging on EV",
    "ev_car.entity_ids.charging_limit_entity_id": "Setting charging battery limit on EV",
    "ev_car.entity_ids.charging_amps_entity_id": "Setting charging amps on EV",
    "ev_car.entity_ids.location_entity_id": "If not configured, uses charger.entity_ids.status_entity_id status to determine if ev is home or away",
    "ev_car.entity_ids.last_update_entity_id": "Used to determine sending wake up call",
    "ev_car.battery_size": "**Required** Actual usable battery capacity, check with OBD2 unit for precise value",
    "ev_car.min_daily_battery_level": "**Required** Also editable via WebGUI",
    "ev_car.min_trip_battery_level": "**Required** Also editable via WebGUI",
    "ev_car.min_charge_limit_battery_level": "**Required** Also editable via WebGUI",
    "ev_car.max_recommended_charge_limit_battery_level": "**Required** Also editable via WebGUI",
    "ev_car.very_cheap_grid_charging_max_battery_level": "**Required** Also editable via WebGUI",
    "ev_car.ultra_cheap_grid_charging_max_battery_level": "**Required** Also editable via WebGUI",
    "ev_car.typical_daily_distance_non_working_day": "**Required** Also editable via WebGUI",
    "forecast.entity_ids.hourly_service_entity_id": "**Required if using solar** hourly forecast entity_id",
    "forecast.entity_ids.daily_service_entity_id": "**Required if using solar** daily forecast entity_id",
    "forecast.entity_ids.outdoor_temp_entity_id": "Used to determine preheat or defrost when preheating the ev, for more precise temp than forecast",
    "home.entity_ids.power_consumption_entity_id": "Home power consumption (Watt entity), not grid power consumption",
    "home.entity_ids.powerwall_watt_flow_entity_id": "Powerwall watt flow (Tip: Disable powerwall discharging when ev charging) (Entity setup plus value for discharging, negative for charging)",
    "home.entity_ids.powerwall_battery_level_entity_id": "Used to determine when to charge ev on solar with ev_charge_after_powerwall_battery_level",
    "home.entity_ids.ignore_consumption_from_entity_ids": "List of power sensors to ignore",
    "home.power_consumption_entity_id_include_powerwall_charging": "Home power consumption include powerwall charging (Watt entity)",
    "home.power_consumption_entity_id_include_powerwall_discharging": "Home power consumption include powerwall discharging (Watt entity)",
    "home.invert_powerwall_watt_flow_entity_id": "Invert powerwall watt flow entity_id (Entity setup plus value for charging, negative for discharging)",
    "notification.efficiency_on_cable_plug_in": "Notification of last drive efficiency on cable plug in",
    "notification.update_available": "Notification of new version available at midnight and on script start",
    "notification.preheating": "Notification of preheating start/stop",
    "notify_list": "List of users to send notifications",
    "prices.entity_ids.power_prices_entity_id": "**Required** Energi Data Service price entity_id",
    "prices.refund": "Refund amount given by the state/country/nation/energy-provider",
    "solar.entity_ids.production_entity_id": "Solar power production Watt",
    "solar.entity_ids.forecast_entity_id": "Solar power forecast Watt (Supported integration: Solcast PV Forecast)",
    "solar.solarpower_use_before_minutes": "Minutes back you can use solar overproduction available (Solar charging can exceed available power to use all excess energy)",
    "solar.max_to_current_hour": "Must use solar overproduction available in current hour (Solar charging can exceed available power to use all excess energy)",
    "solar.allow_grid_charging_above_solar_available": "Watt above(+)/under(-) overproduction available",
    "solar.charging_single_phase_min_amp": "Minimum allowed amps the car can charge, to disable single phase charging set to 0",
    "solar.charging_single_phase_max_amp": "Maximum allowed amps the car can charge, to disable single phase charging set to 0",
    "solar.charging_three_phase_min_amp": "Minimum allowed amps the car can charge, uses charger.charging_phases config for max",
    "solar.production_price": "Set to -1.0 if using raw hour sell price, also editable via WebGUI",
    "solar.ev_charge_after_powerwall_battery_level": f"Solar charge ev after powerwall battery level, editable via input_number.{__name__}_ev_charge_after_powerwall_battery_level entity also. Set to 0.0 to disable. **Requires** powerwall_battery_level_entity_id",
    "solar.powerwall_battery_size": "Powerwall battery size (kWh)",
    "solar.inverter_discharging_power_limit": "Inverter discharging power limit (Watt)",
    "solar.powerwall_charging_power_limit": "Powerwall charging power limit (Watt)",
    "solar.powerwall_discharging_power": f"Powerwall discharging power (Watt), used to charge ev from powerwall, when powerwall battery level is above ev_charge_after_powerwall_battery_level and input_boolean.{__name__}_powerwall_discharge_above_needed is on",
    "solar.enable_selling_during_expensive_hours": f"Enable selling solar power during expensive hours, if not enabled, solar power will be used for charging the ev. input_number.{__name__}_solar_sell_fixed_price must be set to -1.0, to use the hourly sell price.",
}

DEFAULT_ENTITIES = {
    "homeassistant": {
        "customize": {
            f"input_button.{__name__}_trip_reset": {"description": "Nulstil tur ladning"},
            f"input_button.{__name__}_enforce_planning": {"description": "Udregn planlægning igen"},
            f"input_button.{__name__}_restart_script": {"description": "Genstart scriptet"},
            f"input_boolean.{__name__}_debug_log": {"description": f"{__name__}.py debug log"},
            f"input_boolean.{__name__}_forced_charging_daily_battery_level": {"description": "Tvangsladning til under daglig batteri niveau"},
            f"input_boolean.{__name__}_allow_manual_charging_now": {"description": "Tillad manuel ladning nu"},
            f"input_boolean.{__name__}_allow_manual_charging_solar": {"description": "Tillad manuel ladning kun på sol"},
            f"input_boolean.{__name__}_solar_charging": {"description": "Aktiveres ved solcelleoverproduktion. Oplader med overskudsenergi tilpasset husets forbrug. Planlægger optimal opladning ud fra estimeret ugentlig overproduktion."},
            f"input_boolean.{__name__}_fill_up": {"description": "Kan aktiveres ved ferie og ignorerer arbejdsplan. Fordeler opladning over ugen baseret på behov. Planlægger efter laveste priser og maks. anbefalet batteriniveau."},
            f"input_boolean.{__name__}_workplan_charging": {"description": "Aktiveres ved arbejde indenfor en uge. Planlægger daglig opladning baseret på arbejdsdage, afgangstid og afstand. Oplader økonomisk og sikrer tilstrækkeligt niveau ved hjemkomst."},
            f"input_boolean.{__name__}_trip_preheat": {"description": "Aktiveres ved tur ladning. Forvarmer bilen før afgang, hvis forvarmning er nødvendig."},
            f"input_boolean.{__name__}_workday_monday": {"description": "Sætter om mandag er arbejdsdag"},
            f"input_boolean.{__name__}_workday_tuesday": {"description": "Sætter om tirsdag er arbejdsdag"},
            f"input_boolean.{__name__}_workday_wednesday": {"description": "Sætter om onsdag er arbejdsdag"},
            f"input_boolean.{__name__}_workday_thursday": {"description": "Sætter om torsdag er arbejdsdag"},
            f"input_boolean.{__name__}_workday_friday": {"description": "Sætter om fredag er arbejdsdag"},
            f"input_boolean.{__name__}_workday_saturday": {"description": "Sætter om lørdag er arbejdsdag"},
            f"input_boolean.{__name__}_workday_sunday": {"description": "Sætter om søndag er arbejdsdag"},
            f"input_boolean.{__name__}_preheat_monday": {"description": "Forvarm bilen om mandagen"},
            f"input_boolean.{__name__}_preheat_tuesday": {"description": "Forvarm bilen om tirsdagen"},
            f"input_boolean.{__name__}_preheat_wednesday": {"description": "Forvarm bilen om onsdagen"},
            f"input_boolean.{__name__}_preheat_thursday": {"description": "Forvarm bilen om torsdagen"},
            f"input_boolean.{__name__}_preheat_friday": {"description": "Forvarm bilen om fredagen"},
            f"input_boolean.{__name__}_preheat_saturday": {"description": "Forvarm bilen om lørdagen"},
            f"input_boolean.{__name__}_preheat_sunday": {"description": "Forvarm bilen om søndagen"},
            f"input_boolean.{__name__}_calculate_charging_loss": {"description": "For præcis ladetabsberegning: Aflad bilen, indstil ønsket maks. ladegrænse, og aktiver beregning. Resultat gemmes automatisk, og notifikation sendes ved fuld opladning."},
            f"input_boolean.{__name__}_powerwall_discharge_above_needed": {"description": f"Aflader Powerwall over det nødvendige niveau for at oplade elbilen, når den er tilsluttet. Kræver aktivering af input_boolean.{__name__}_solar_charging."},
            f"input_number.{__name__}_co2_emitted": {"description": "CO₂ udledt i kg, baseret på Energi Data Service CO₂ faktor"},
            f"input_number.{__name__}_kwh_charged_by_solar": {"description": "kWh opladet af solcellerne"},
            f"input_number.{__name__}_solar_sell_fixed_price": {"description": "Fast salgspris for solceller, bruges til at beregne solcelleoverskud, sæt til -1.0 for at bruge timepris"},
            f"input_number.{__name__}_preheat_minutes_before": {"description": "Forvarm bilen X minutter før afgang, hvis forvarmning er aktiveret"},
            f"input_number.{__name__}_typical_daily_distance": {"description": f"Typisk daglig afstand i km, bruges til at planlægge opladning. Kræver aktivering af input_boolean.{__name__}_fill_up."},
            f"input_number.{__name__}_workday_distance_needed_monday": {"description": "Afstand i km, der skal oplades for mandag arbejdsdag"},
            f"input_number.{__name__}_workday_distance_needed_tuesday": {"description": "Afstand i km, der skal oplades for tirsdag arbejdsdag"},
            f"input_number.{__name__}_workday_distance_needed_wednesday": {"description": "Afstand i km, der skal oplades for onsdag arbejdsdag"},
            f"input_number.{__name__}_workday_distance_needed_thursday": {"description": "Afstand i km, der skal oplades for torsdag arbejdsdag"},
            f"input_number.{__name__}_workday_distance_needed_friday": {"description": "Afstand i km, der skal oplades for fredag arbejdsdag"},
            f"input_number.{__name__}_workday_distance_needed_saturday": {"description": "Afstand i km, der skal oplades for lørdag arbejdsdag"},
            f"input_number.{__name__}_workday_distance_needed_sunday": {"description": "Afstand i km, der skal oplades for søndag arbejdsdag"},
            f"input_number.{__name__}_min_daily_battery_level": {"description": "Minimum daglig batteriniveau i procent, ved hjemkomst"},
            f"input_number.{__name__}_min_trip_battery_level": {"description": "Minimum tur batteriniveau i procent, ved hjemkomst"},
            f"input_number.{__name__}_min_charge_limit_battery_level": {"description": "Minimum batteriniveau i procent, bilen kan sættes til i opladningstilstand"},
            f"input_number.{__name__}_max_recommended_charge_limit_battery_level": {"description": "Maks. anbefalet batteriniveau i procent, bilen lades til dagligt"},
            f"input_number.{__name__}_very_cheap_grid_charging_max_battery_level": {"description": f"Ved meget billig strøm, lades bilen til dette niveau i procent. Kræver aktivering af input_boolean.{__name__}_fill_up."},
            f"input_number.{__name__}_ultra_cheap_grid_charging_max_battery_level": {"description": f"Ved ekstremt billig strøm, lades bilen til dette niveau i procent. Kræver aktivering af input_boolean.{__name__}_fill_up."},
            f"input_number.{__name__}_battery_level": {"description": "Ved ingen bilintegration, bruges denne til at sætte batteriniveauet i procent"},
            f"input_number.{__name__}_completed_battery_level": {"description": f"Ved ingen bilintegration, sættes dette til det fuldt opladede batteriniveau bilen viser, når den melder opladning færdig. input_number.{__name__}_battery_level opdateres automatisk til dette."},
            f"input_number.{__name__}_estimated_total_range": {"description": "Ved ingen bilintegration, bruges denne til at sætte det estimerede totale rækkevidde i km"},
            f"input_number.{__name__}_trip_charge_procent": {"description": f"Bruges ved turladning til at angive ønsket batteriniveau ved afgang, bilen lades til denne værdi + input_number.{__name__}_min_trip_battery_level (f.eks. 50% + 30% = 80%)"},
            f"input_number.{__name__}_trip_range_needed": {"description": f"Bruges ved turladning til at angive det ønskede rækkevidde i km, der skal oplades til ved afgang, km omregnes automatisk til batteriniveau og bilen lades til dette niveau + input_number.{__name__}_min_trip_battery_level (f.eks. 50% + 30% = 80%)"},
            f"input_number.{__name__}_full_charge_recommended": {"description": "Anbefalet fuld opladning minimum hver X dage, for at undgå batteri skader. Bilen lades til 100%. Sæt til 0 for at deaktivere."},
            f"input_number.{__name__}_ev_charge_after_powerwall_battery_level": {"description": f"Oplader elbilen fra Powerwall, når Powerwall batteriniveau er over dette niveau i procent. Sæt til 0.0 for at deaktivere. Kræver aktivering af input_boolean.{__name__}_solar_charging."},
            f"input_datetime.{__name__}_workday_departure_monday": {"description": "Afgangstidspunkt for mandag arbejdsdag, bruges til at planlægge opladning og forvarmning"},
            f"input_datetime.{__name__}_workday_departure_tuesday": {"description": "Afgangstidspunkt for tirsdag arbejdsdag, bruges til at planlægge opladning og forvarmning"},
            f"input_datetime.{__name__}_workday_departure_wednesday": {"description": "Afgangstidspunkt for onsdag arbejdsdag, bruges til at planlægge opladning og forvarmning"},
            f"input_datetime.{__name__}_workday_departure_thursday": {"description": "Afgangstidspunkt for torsdag arbejdsdag, bruges til at planlægge opladning og forvarmning"},
            f"input_datetime.{__name__}_workday_departure_friday": {"description": "Afgangstidspunkt for fredag arbejdsdag, bruges til at planlægge opladning og forvarmning"},
            f"input_datetime.{__name__}_workday_departure_saturday": {"description": "Afgangstidspunkt for lørdag arbejdsdag, bruges til at planlægge opladning og forvarmning"},
            f"input_datetime.{__name__}_workday_departure_sunday": {"description": "Afgangstidspunkt for søndag arbejdsdag, bruges til at planlægge opladning og forvarmning"},
            f"input_datetime.{__name__}_workday_homecoming_monday": {"description": "Hjemkomsttidspunkt for mandag arbejdsdag, bruges til at planlægge opladning"},
            f"input_datetime.{__name__}_workday_homecoming_tuesday": {"description": "Hjemkomsttidspunkt for tirsdag arbejdsdag, bruges til at planlægge opladning"},
            f"input_datetime.{__name__}_workday_homecoming_wednesday": {"description": "Hjemkomsttidspunkt for onsdag arbejdsdag, bruges til at planlægge opladning"},
            f"input_datetime.{__name__}_workday_homecoming_thursday": {"description": "Hjemkomsttidspunkt for torsdag arbejdsdag, bruges til at planlægge opladning"},
            f"input_datetime.{__name__}_workday_homecoming_friday": {"description": "Hjemkomsttidspunkt for fredag arbejdsdag, bruges til at planlægge opladning"},
            f"input_datetime.{__name__}_workday_homecoming_saturday": {"description": "Hjemkomsttidspunkt for lørdag arbejdsdag, bruges til at planlægge opladning"},
            f"input_datetime.{__name__}_workday_homecoming_sunday": {"description": "Hjemkomsttidspunkt for søndag arbejdsdag, bruges til at planlægge opladning"},
            f"input_datetime.{__name__}_trip_date_time": {"description": "Dato og tidspunkt for tur afgang, bruges til at planlægge opladning og forvarmning"},
            f"input_datetime.{__name__}_trip_homecoming_date_time": {"description": "Dato og tidspunkt for tur hjemkomst, bruges til at planlægge opladning"},
            f"input_datetime.{__name__}_last_full_charge": {"description": "Dato og tidspunkt for sidste fuld opladning"},
        },
    },
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
            "name":f"{__name__}.py debug log",
            "icon":"mdi:math-log"
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
        f"{__name__}_solar_charging":{
            "name":"Solcelleoverskud til opladning",
            "icon": "mdi:brain"
        },
        f"{__name__}_fill_up":{
            "name":"Optimal ugeopladning (uden Arbejdsplan)",
            "icon": "mdi:brain"
        },
        f"{__name__}_workplan_charging":{
            "name":"Arbejdsplan opladning",
            "icon": "mdi:brain"
        },
        f"{__name__}_trip_preheat":{
            "name":"Tur ladning forvarm bilen",
            "icon": "mdi:heat-wave"
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
            "name":"Mandag forvarm bilen",
            "icon": "mdi:heat-wave"
        },
        f"{__name__}_preheat_tuesday":{
            "name":"Tirsdag forvarm bilen",
            "icon": "mdi:heat-wave"
        },
        f"{__name__}_preheat_wednesday":{
            "name":"Onsdag forvarm bilen",
            "icon": "mdi:heat-wave"
        },
        f"{__name__}_preheat_thursday":{
            "name":"Torsdag forvarm bilen",
            "icon": "mdi:heat-wave"
        },
        f"{__name__}_preheat_friday":{
            "name":"Fredag forvarm bilen",
            "icon": "mdi:heat-wave"
        },
        f"{__name__}_preheat_saturday":{
            "name":"Lørdag forvarm bilen",
            "icon": "mdi:heat-wave"
        },
        f"{__name__}_preheat_sunday":{
            "name":"Søndag forvarm bilen",
            "icon": "mdi:heat-wave"
        },
        f"{__name__}_calculate_charging_loss":{
            "name":"Beregn ladetab",
            "icon": "mdi:battery-sync"
        },
        f"{__name__}_powerwall_discharge_above_needed":{
            "name":"Powerwall afladning over behov til elbil",
            "icon": "mdi:power-plug-battery"
        },
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
            "unit_of_measurement":"kr/kWh"
        },
        f"{__name__}_preheat_minutes_before":{
            "name":"Forvarm bilen X min før",
            "min":0,
            "max":60,
            "step":5,
            "unit_of_measurement":"min"
        },
        f"{__name__}_typical_daily_distance":{
            "name":"Typisk daglig afstand (Fridag)",
            "min":0,
            "max":500,
            "step":5,
            "mode":"box",
            "icon":"mdi:transit-connection-variant",
            "unit_of_measurement":"km"
        },
        f"{__name__}_workday_distance_needed_monday":{
            "name":"Mandagsafstand i alt",
            "min":0,
            "max":500,
            "step":5,
            "mode":"box",
            "icon":"mdi:transit-connection-variant",
            "unit_of_measurement":"km"
        },
        f"{__name__}_workday_distance_needed_tuesday":{
            "name":"Tirsdagsafstand i alt",
            "min":0,
            "max":500,
            "step":5,
            "mode":"box",
            "icon":"mdi:transit-connection-variant",
            "unit_of_measurement":"km"
        },
        f"{__name__}_workday_distance_needed_wednesday":{
            "name":"Onsdagsafstand i alt",
            "min":0,
            "max":500,
            "step":5,
            "mode":"box",
            "icon":"mdi:transit-connection-variant",
            "unit_of_measurement":"km"
        },
        f"{__name__}_workday_distance_needed_thursday":{
            "name":"Torsdagsafstand i alt",
            "min":0,
            "max":500,
            "step":5,
            "mode":"box",
            "icon":"mdi:transit-connection-variant",
            "unit_of_measurement":"km"
        },
        f"{__name__}_workday_distance_needed_friday":{
            "name":"Fredagsafstand i alt",
            "min":0,
            "max":500,
            "step":5,
            "mode":"box",
            "icon":"mdi:transit-connection-variant",
            "unit_of_measurement":"km"
        },
        f"{__name__}_workday_distance_needed_saturday":{
            "name":"Lørdagsafstand i alt",
            "min":0,
            "max":500,
            "step":5,
            "mode":"box",
            "icon":"mdi:transit-connection-variant",
            "unit_of_measurement":"km"
        },
        f"{__name__}_workday_distance_needed_sunday":{
            "name":"Søndagsafstand i alt",
            "min":0,
            "max":500,
            "step":5,
            "mode":"box",
            "icon":"mdi:transit-connection-variant",
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
            "name": "Virtuel elbil max rækkevidde",
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
        },
        f"{__name__}_ev_charge_after_powerwall_battery_level":{
            "name":"Oplad elbil efter Powerwall minimum batteriniveau",
            "min": 0,
            "max": 100,
            "step": 1,
            "unit_of_measurement": "%",
            "icon": "mdi:percent-outline"
        },
    },
    "input_datetime":{
        f"{__name__}_workday_departure_monday":{
            "name":"Mandag afgang",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-start"
        },
        f"{__name__}_workday_departure_tuesday":{
            "name":"Tirsdag afgang",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-start"
        },
        f"{__name__}_workday_departure_wednesday":{
            "name":"Onsdag afgang",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-start"
        },
        f"{__name__}_workday_departure_thursday":{
            "name":"Torsdag afgang",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-start"
        },
        f"{__name__}_workday_departure_friday":{
            "name":"Fredag afgang",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-start"
        },
        f"{__name__}_workday_departure_saturday":{
            "name":"Lørdag afgang",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-start"
        },
        f"{__name__}_workday_departure_sunday":{
            "name":"Søndag afgang",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-start"
        },
        f"{__name__}_workday_homecoming_monday":{
            "name":"Mandag hjemkomst",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-end"
        },
        f"{__name__}_workday_homecoming_tuesday":{
            "name":"Tirsdag hjemkomst",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-end"
        },
        f"{__name__}_workday_homecoming_wednesday":{
            "name":"Onsdag hjemkomst",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-end"
        },
        f"{__name__}_workday_homecoming_thursday":{
            "name":"Torsdag hjemkomst",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-end"
        },
        f"{__name__}_workday_homecoming_friday":{
            "name":"Fredag hjemkomst",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-end"
        },
        f"{__name__}_workday_homecoming_saturday":{
            "name":"Lørdag hjemkomst",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-end"
        },
        f"{__name__}_workday_homecoming_sunday":{
            "name":"Søndag hjemkomst",
            "has_date":False,
            "has_time":True,
            "icon": "mdi:clock-end"
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
    "sensor":[{
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
                "unit_of_measurement":"kr/kWh"
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
    }]
}

ENTITIES_RENAMING = {# Old path: New path (seperated by ".")
    f"input_number.{__name__}_days_to_charge_range": f"input_number.{__name__}_typical_daily_distance",
    f"input_boolean.{__name__}_days_to_charge": f"input_boolean.{__name__}_workplan_charging",
    f"input_datetime.{__name__}_days_to_charge_monday": f"input_datetime.{__name__}_workday_departure_monday",
    f"input_datetime.{__name__}_days_to_charge_tuesday": f"input_datetime.{__name__}_workday_departure_tuesday",
    f"input_datetime.{__name__}_days_to_charge_wednesday": f"input_datetime.{__name__}_workday_departure_wednesday",
    f"input_datetime.{__name__}_days_to_charge_thursday": f"input_datetime.{__name__}_workday_departure_thursday",
    f"input_datetime.{__name__}_days_to_charge_friday": f"input_datetime.{__name__}_workday_departure_friday",
    f"input_datetime.{__name__}_days_to_charge_saturday": f"input_datetime.{__name__}_workday_departure_saturday",
    f"input_datetime.{__name__}_days_to_charge_sunday": f"input_datetime.{__name__}_workday_departure_sunday",
    f"input_datetime.{__name__}_monday_homecoming": f"input_datetime.{__name__}_workday_homecoming_monday",
    f"input_datetime.{__name__}_tuesday_homecoming": f"input_datetime.{__name__}_workday_homecoming_tuesday",
    f"input_datetime.{__name__}_wednesday_homecoming": f"input_datetime.{__name__}_workday_homecoming_wednesday",
    f"input_datetime.{__name__}_thursday_homecoming": f"input_datetime.{__name__}_workday_homecoming_thursday",
    f"input_datetime.{__name__}_friday_homecoming": f"input_datetime.{__name__}_workday_homecoming_friday",
    f"input_datetime.{__name__}_saturday_homecoming": f"input_datetime.{__name__}_workday_homecoming_saturday",
    f"input_datetime.{__name__}_sunday_homecoming": f"input_datetime.{__name__}_workday_homecoming_sunday",
}

def welcome():
    _LOGGER = globals()['_LOGGER'].getChild("welcome")
    return f'''
-------------------------------------------------------------------
🚗Cable Juice Planner🔋🌞📅 (Script: {__name__}.py)
-------------------------------------------------------------------
'''

def task_wait_until(task_name, timeout=3.0, wait_period=1.0):
    global TASKS
    _LOGGER = globals()['_LOGGER'].getChild("task_wait_until")
    
    try:
        if task_name not in TASKS:
            return True
        
        if not isinstance(TASKS[task_name], asyncio.Task):
            return True
        
        if TASKS[task_name].done():
            return True
        
        period = 0
        while task_name in TASKS and (not TASKS[task_name].done() or not TASKS[task_name].cancelled()):
            task.wait_until(timeout=wait_period)
            period += wait_period
            if period >= timeout:
                break
        
        if TASKS[task_name].done():
            return True
        else:
            return False
    except Exception as e:
        _LOGGER.error(f"Error while waiting for task {task_name} (INSTANCE_ID: {INSTANCE_ID}): {e}")
        
    return False
    
def task_cancel(task_name, task_remove=True, timeout=3.0, wait_period=0.2):
    global TASKS
    _LOGGER = globals()['_LOGGER'].getChild("task_cancel")
    
    try:
        if task_name not in TASKS:
            return True
        
        if not isinstance(TASKS[task_name], asyncio.Task):
            if task_remove:
                del TASKS[task_name]
            return True
        
        if "save" in task_name and "saving" in task_name and not TASKS[task_name].done():
            _LOGGER.warning(f"Waiting 3 seconds for task {task_name} (saving task) to finish before killing it (INSTANCE_ID: {INSTANCE_ID})")
            task_wait_until(task_name, timeout=3.0, wait_period=0.2)
            
        if not task_wait_until(task_name, timeout=1, wait_period=0.2):
            TASKS[task_name].cancel()
        
        if task_wait_until(task_name, timeout=timeout, wait_period=wait_period):
            if task_remove:
                del TASKS[task_name]
            return True
        else:
            _LOGGER.error(f"Task {task_name} is still not done after waiting, ignoring it (INSTANCE_ID: {INSTANCE_ID})")
            return False
    except Exception as e:
        _LOGGER.error(f"Error while killing task {task_name}: {e} {TASKS[task_name]} (INSTANCE_ID: {INSTANCE_ID})")
        
def task_shutdown():
    task.unique("task_shutdown")
    global TASKS, SHUTTING_DOWN
    
    SHUTTING_DOWN = True
    
    tasks_done_list = []
    for task_name, task_id in TASKS.items():
        if task_cancel(task_name, task_remove=False):
            tasks_done_list.append(task_name)
    
    for task_name in tasks_done_list:
        try:
            del TASKS[task_name]
        except KeyError:
            _LOGGER.error(f"Error deleting task {task_name} from TASKS (INSTANCE_ID: {INSTANCE_ID})")
    
    if len(TASKS) > 0:
        _LOGGER.error(f"Some tasks were not killed:\n{pformat(TASKS, indent=4, width=200)} (INSTANCE_ID: {INSTANCE_ID})")
        _LOGGER.error("Please report this issue to the developer.")
        my_persistent_notification(
            title=f"⚠️ {__name__} - Task Kill Error",
            message=f"Some tasks were not killed from instance {INSTANCE_ID}:\n{pformat(TASKS, indent=4, width=80)}\n\nPlease report this issue to the developer with the above information\nat https://github.com/dezito/Cable-Juice-Planner/issues",
            persistent_notification_id=f"{__name__}_task_shutdown_error_{INSTANCE_ID}"
        )
        
    TASKS = None

def calculate_price_levels(prices):
    """ Beregner de forskellige prisniveauer baseret på lowest, mean og highest price. """
    lowest_price = min(prices)
    highest_price = max(prices)
    mean_price = sum(prices) / len(prices)
    step_under = (mean_price - lowest_price) / 5
    step_over = (highest_price - mean_price) / 5

    return {
        "price1": lowest_price,
        "price2": mean_price - step_under * 4,
        "price3": mean_price - step_under * 3,
        "price4": mean_price - step_under * 2,
        "price5": mean_price - step_under * 1,
        "price6": mean_price,
        "price7": mean_price + step_over * 1,
        "price8": mean_price + step_over * 2,
        "price9": mean_price + step_over * 3,
        "price10": mean_price + step_over * 4,
        "price11": highest_price,
    }

def get_color(price, price_levels):
    """ Finder den passende farve for en given pris. """
    for key, color in reversed(COLOR_THRESHOLDS):  # Starter fra højeste pris
        if price >= price_levels[key]:
            return color
    return "#FFFFFF"  # Default farve hvis ingen matcher

def get_hours_plan():
    output = []
    
    if "prices" in LAST_SUCCESSFUL_GRID_PRICES:
        prices = LAST_SUCCESSFUL_GRID_PRICES["prices"]
        if not prices:
            return output

        # Beregn prisniveauer én gang
        price_levels = calculate_price_levels(prices.values())

        # Organiser data
        data = {}
        now = getTime().replace(minute=0, second=0, microsecond=0)
        date_objects = set()
        not_home_color = "#666666"
        
        for timestamp, price in prices.items():
            date_obj = timestamp.date()  # Gem dato som et `datetime.date` objekt
            date_objects.add(date_obj)  # Tilføj til sorteringssættet
            date_str = f"{timestamp.strftime('%a')}<br>{timestamp.strftime('%-d/%-m')}"  # Format: 31/1/24
            time_str = timestamp.strftime("%H:%M")  # Format: 06:00
            color = get_color(price, price_levels)

            if time_str not in data:
                data[time_str] = {}

            text_format_start, text_format_end = "**", "**"
            color_start, color_end = "", ""
            emojis = ""
            not_home_start_emoji, not_home_end_emoji = "", ""

            day = daysBetween(now, timestamp)
            if day in CHARGING_PLAN:
                if timestamp < now:
                    text_format_start, text_format_end = "", ""
                    color = not_home_color
                    price = ""
                    
                if CHARGING_PLAN[day]["trip"]:
                    trip_start = reset_time_to_hour(CHARGING_PLAN[day]["trip_goto"])
                    trip_end = reset_time_to_hour(CHARGING_PLAN[day]["trip_homecoming"])
                    if in_between(timestamp, trip_start, trip_end + datetime.timedelta(seconds=1)):
                        text_format_start, text_format_end = "~~", "~~"
                        color = not_home_color
                        if timestamp == trip_start:
                            not_home_start_emoji += emoji_parse({'trip': True})
                        elif timestamp == trip_end:
                            not_home_end_emoji += emoji_parse({'trip': True})
                        
                if CHARGING_PLAN[day]["workday"]:
                    workday_start = reset_time_to_hour(CHARGING_PLAN[day]["work_goto"])
                    workday_end = reset_time_to_hour(CHARGING_PLAN[day]["work_homecoming"])
                    if in_between(timestamp, workday_start, workday_end + datetime.timedelta(seconds=1)):
                        text_format_start, text_format_end = "~~", "~~"
                        color = not_home_color
                        if timestamp == workday_start:
                            not_home_start_emoji += CHARGING_PLAN[day]["emoji"]
                        elif timestamp == workday_end:
                            not_home_end_emoji += CHARGING_PLAN[day]["emoji"]
                
            emojis = emoji_parse(CHARGE_HOURS.get(timestamp, ""))
            
            color_start, color_end = (f'<font color="{color}">', "</font>") if color else ("", "")
            
            emojis = f"<br>{emoji_text_format(emojis, group_size=2)}" if emojis else ""
            
            not_home_start_emoji = f"{not_home_start_emoji}⤵️<br>" if not_home_start_emoji else ""
            not_home_end_emoji = f"<br>{not_home_end_emoji}⤴️" if not_home_end_emoji else ""
                
            data[time_str][date_str] = f'{not_home_start_emoji}{color_start}{text_format_start}{price}{text_format_end}{color_end}{emojis}{not_home_end_emoji}'

        # Sorter datoer som `datetime.date` og konverter tilbage til str
        sorted_dates = [f"{d.strftime('%a')}<br>{d.strftime('%-d/%-m')}" for d in sorted(date_objects)]
        sorted_hours = sorted({t.strftime("%H:%M") for t in prices})

        prices_output = []
        prices_output.append("### Strøm priser ###")
        
        # Opret tabel-header
        prices_output.append("| " + " | ".join([""] + sorted_dates) + " |")
        prices_output.append("|" + "|".join([":---:"] * (len(sorted_dates) + 1)) + "|")

        # Tilføj rækker med farvede priser
        for hour in sorted_hours:
            row = [f"**{hour}**"] + [data[hour].get(date, "") for date in sorted_dates]
            prices_output.append("| " + " | ".join(row) + " |")

        output.append("\n".join(prices_output))
    return output

def append_overview_output(title = None, timestamp = None):
    task.unique("append_overview_output")
    global OVERVIEW_HISTORY
    
    if timestamp is None:
        timestamp = getTime().strftime("%Y-%m-%d %H:%M")
    
    key = f"{timestamp} {title}"
    
    if key in OVERVIEW_HISTORY:
        return
    
    OVERVIEW_HISTORY[key] = [get_attr(f"sensor.{__name__}_overview", "overview", error_state=f"Cant get sensor.{__name__}_overview.overview")]
    
    OVERVIEW_HISTORY = limit_dict_size(OVERVIEW_HISTORY, 10)
    
def get_debug_info_sections():
    return {
        "Status and Initialization": {
            "table": {
                "INITIALIZATION_COMPLETE": INITIALIZATION_COMPLETE,
                "PREHEATING": PREHEATING,
            },
            "details": None,
        },
        "Configuration": {
            "table": {
                "CHARGER_CONFIGURED": CHARGER_CONFIGURED,
                "SOLAR_CONFIGURED": SOLAR_CONFIGURED,
                "POWERWALL_CONFIGURED": POWERWALL_CONFIGURED,
                "EV_CONFIGURED": EV_CONFIGURED,
                "CONFIG_LAST_MODIFIED": CONFIG_LAST_MODIFIED,
            },
            "details": {"CONFIG": CONFIG},
        },
        "Entities Integration Limits, Counters & Command history": {
            "table": None,
            "details": {"ENTITY_INTEGRATION_DICT": ENTITY_INTEGRATION_DICT},
        },
        "Charging Plan": {
            "table": {
                "CURRENT_CHARGING_AMPS": CURRENT_CHARGING_AMPS,
                "USING_OFFLINE_PRICES": USING_OFFLINE_PRICES,
            },
            "details": {
                "BATTERY_LEVEL_EXPENSES": BATTERY_LEVEL_EXPENSES,
                "CHARGING_PLAN": CHARGING_PLAN,
                "CHARGE_HOURS": CHARGE_HOURS,
                "LAST_SUCCESSFUL_GRID_PRICES": LAST_SUCCESSFUL_GRID_PRICES,
            },
        },
        "Solar and Powerwall": {
            "table": None,
            "details": {
                "LOCAL_ENERGY_PRICES": LOCAL_ENERGY_PRICES,
                "LOCAL_ENERGY_PREDICTION_DB": LOCAL_ENERGY_PREDICTION_DB,
            }
        },
        "Charging Loss": {
            "table": {
                "CHARGING_LOSS_CAR_BEGIN_KWH": CHARGING_LOSS_CAR_BEGIN_KWH,
                "CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL": CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL,
                "CHARGING_LOSS_CHARGER_BEGIN_KWH": CHARGING_LOSS_CHARGER_BEGIN_KWH,
                "CHARGING_LOSS_CHARGING_COMPLETED": CHARGING_LOSS_CHARGING_COMPLETED,
            },
            "details": None,
        },
        "Errors and Counters": {
            "table": {
                "CHARGING_IS_BEGINNING": CHARGING_IS_BEGINNING,
                "CHARGING_NO_RULE_COUNT": CHARGING_NO_RULE_COUNT,
                "ERROR_COUNT": ERROR_COUNT,
                "RESTARTING_CHARGER": RESTARTING_CHARGER,
                "RESTARTING_CHARGER_COUNT": RESTARTING_CHARGER_COUNT,
            },
            "details": None,
        },
        "Timestamps and Sessions": {
            "table": {
                "LAST_WAKE_UP_DATETIME": LAST_WAKE_UP_DATETIME,
                "LAST_TRIP_CHANGE_DATETIME": LAST_TRIP_CHANGE_DATETIME,
                "INTEGRATION_OFFLINE_TIMESTAMP": INTEGRATION_OFFLINE_TIMESTAMP,
            },
            "details": {"CURRENT_CHARGING_SESSION": CURRENT_CHARGING_SESSION},
        },
        "Task Management": {
            "table": {
                "INSTANCE_ID": INSTANCE_ID,
                "TASKS_COUNT": len(TASKS) if TASKS else 0,
            },
            "details": {
                "TASKS": TASKS,
            },
        },
    }

def run_git_command_sync(cmd):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if result.returncode != 0:
            raise RuntimeError(f"Git failed: {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        result.kill()
        raise TimeoutError("Git command timed out after 15 seconds")
    except RuntimeError as e:
        raise RuntimeError(f"Git command failed: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {e}")

async def run_git_command(cmd):
    """Run a git command synchronously and safely with timeout and error handling."""
    try:
        length = 8
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        
        task_name = f'run_git_command_{random_string}'
        TASKS[task_name] = task.create(run_git_command_sync, cmd)
        done, pending = task.wait({TASKS[task_name]})
        result = TASKS[task_name].result()
        
        task_cancel(task_name, task_remove=True, timeout=5.0, wait_period=0.2)
        
        return result
    except TimeoutError as e:
        raise TimeoutError(e)
    except RuntimeError as e:
        raise RuntimeError(e)
    except Exception as e:
        raise RuntimeError(e)

@service(f"pyscript.{__name__}_check_master_updates")
def check_master_updates(trigger_type=None, trigger_id=None, **kwargs):
    task.unique("check_master_updates")
    _LOGGER = globals()['_LOGGER'].getChild("check_master_updates")
    global TASKS
    
    config_path = get_config_folder()
    repo_path = f"{config_path}/Cable-Juice-Planner"
    branch = kwargs.get("branch", "master")
    
    result = {"has_updates": False, "commits_behind": 0}

    try:
        _LOGGER.info(f"Checking for updates in {repo_path}")

        run_git_command(["git", "-C", repo_path, "config", "--global", "--add", "safe.directory", repo_path])
        run_git_command(["git", "-C", repo_path, "fetch", "origin", branch])

        TASKS['check_master_updates_local_head'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "rev-parse", "HEAD"])
        TASKS['check_master_updates_remote_head'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "rev-parse", f"origin/{branch}"])
        done, pending = task.wait({TASKS['check_master_updates_local_head'], TASKS['check_master_updates_remote_head']})
        
        local_head = TASKS['check_master_updates_local_head'].result()
        remote_head = TASKS['check_master_updates_remote_head'].result()
        
        if local_head == remote_head:
            _LOGGER.info("No updates available.")
            my_persistent_notification(
                "✅ Ingen opdateringer tilgængelige",
                title=f"{TITLE} Opdateringstjek",
                persistent_notification_id=f"{__name__}_check_master_updates"
            )
            return

        TASKS['check_master_updates_total_commits_behind'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "rev-list", "--count", f"HEAD..origin/{branch}"])
        TASKS['check_master_updates_merge_commits'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "log", "--oneline", "--grep=Merge pull request", f"HEAD..origin/{branch}"])
        TASKS['check_master_updates_commit_log_lines'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "log", "--pretty=format:%s", "--grep=Merge pull request", "--invert-grep", f"HEAD..origin/{branch}"])
        done, pending = task.wait({TASKS['check_master_updates_total_commits_behind'], TASKS['check_master_updates_merge_commits'], TASKS['check_master_updates_commit_log_lines']})
        
        total_commits_behind = int(TASKS['check_master_updates_total_commits_behind'].result() or "0")
        
        merge_commits = TASKS['check_master_updates_merge_commits'].result()
        merge_commit_count = len(merge_commits.split("\n")) if merge_commits.strip() else 0
        
        real_commits_behind = max(0, total_commits_behind - merge_commit_count)

        commit_log_lines = str(TASKS['check_master_updates_commit_log_lines'].result()).split("\n")
        commit_log_md = "\n".join([f"- {line.lstrip('- ')}" for line in commit_log_lines if line.strip()]) if commit_log_lines else "✅ Ingen ændringer fundet."
        
        result = {"has_updates": real_commits_behind > 0, "commits_behind": real_commits_behind, "commit_log": commit_log_md}

    except Exception as e:
        result = {"has_updates": False, "commits_behind": 0, "error": str(e)}
    finally:
        task_list = ["check_master_updates_local_head", "check_master_updates_remote_head",
                 "check_master_updates_total_commits_behind", "check_master_updates_merge_commits",
                 "check_master_updates_commit_log_lines"
                 ]
        for task_name in task_list:
            task_cancel(task_name, task_remove=True, timeout=5.0)

    _LOGGER.info(f"Check {branch} updates: {result}")

    if result["has_updates"]:
        _LOGGER.info(f"New version available: {result['commits_behind']} commits behind")
        my_persistent_notification(
            f"**Ny version tilgængelig**\n\n"
            f"📌 **{result['commits_behind']} commit{'s' if result['commits_behind'] > 1 else ''} bagud**\n\n"
            f"**Ændringer:**\n{result['commit_log']}",
            title=f"{TITLE} Opdatering tilgængelig",
            persistent_notification_id=f"{__name__}_check_master_updates"
        )
    elif "error" in result:
        _LOGGER.error(f"Could not check for updates: {result['error']}")
        my_persistent_notification(
            f"⚠️ Kan ikke tjekke efter opdateringer: {result['error']}",
            title=f"{TITLE} Fejl",
            persistent_notification_id=f"{__name__}_check_master_updates"
        )
    elif trigger_type == "service":
        _LOGGER.info("No updates available")
        my_persistent_notification(
            "✅ Ingen opdateringer tilgængelige",
            title=f"{TITLE} Opdateringstjek",
            persistent_notification_id=f"{__name__}_check_master_updates"
        )


@service(f"pyscript.{__name__}_update_repo")
def update_repo(trigger_type=None, trigger_id=None, **kwargs):
    task.unique("update_repo")
    _LOGGER = globals()['_LOGGER'].getChild("update_repo")
    global TASKS

    config_path = get_config_folder()
    repo_path = f"{config_path}/Cable-Juice-Planner"
    branch = kwargs.get("branch", "master")

    try:
        _LOGGER.info(f"Pulling latest changes for {repo_path} (branch: {branch})")

        run_git_command(["git", "-C", repo_path, "fetch", "--all"])

        TASKS['check_master_updates_local_head'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "rev-parse", "HEAD"])
        TASKS['check_master_updates_remote_head'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "rev-parse", f"origin/{branch}"])
        done, pending = task.wait({TASKS['check_master_updates_local_head'], TASKS['check_master_updates_remote_head']})
        
        local_head = TASKS['check_master_updates_local_head'].result()
        remote_head = TASKS['check_master_updates_remote_head'].result()
        
        if local_head == remote_head:
            _LOGGER.info("No updates available.")
            my_persistent_notification(
                "✅ Ingen opdateringer tilgængelige",
                title=f"{TITLE} Opdateringstjek",
                persistent_notification_id=f"{__name__}_update_repo"
            )
            return

        TASKS['check_master_updates_total_commits_behind'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "rev-list", "--count", f"{local_head}..{remote_head}"])
        TASKS['check_master_updates_merge_commits'] = task.create(run_git_command_sync, ["git", "-C", repo_path, "log", "--oneline", "--grep=Merge pull request", f"{local_head}..{remote_head}"])
        done, pending = task.wait({TASKS['check_master_updates_total_commits_behind'], TASKS['check_master_updates_merge_commits']})
        
        total_commits_behind = int(TASKS['check_master_updates_total_commits_behind'].result() or "0")

        merge_commits = TASKS['check_master_updates_merge_commits'].result()
        merge_commit_count = len(merge_commits.split("\n")) if merge_commits.strip() else 0

        real_commits_behind = max(0, total_commits_behind - merge_commit_count)

        run_git_command(["git", "-C", repo_path, "reset", "--hard", f"origin/{branch}"])
        run_git_command(["git", "-C", repo_path, "pull", "--force", "origin", branch])

        commit_log_lines = run_git_command(
            ["git", "-C", repo_path, "log", "--pretty=format:%s", "--grep=Merge pull request", "--invert-grep", f"{local_head}..{remote_head}"]
        ).split("\n")

        commit_log_md = "\n".join([f"- {line.lstrip('- ')}" for line in commit_log_lines if line.strip()]) if commit_log_lines else "✅ Ingen specifikke ændringer fundet."

        _LOGGER.info("Repository updated successfully.")
        my_persistent_notification(
            f"🚀 Opdatering gennemført!\n\n📌 **{real_commits_behind} commit{'s' if real_commits_behind > 1 else ''} bagud**\n\n"
            f"**Ændringer hentet fra GitHub:**\n{commit_log_md}",
            title=f"{TITLE} Opdatering fuldført",
            persistent_notification_id=f"{__name__}_update_repo"
        )

        task.wait_until(timeout=5)
        restart_script()

    except Exception as e:
        _LOGGER.error(f"Update failed: {str(e)}")
        my_persistent_notification(
            f"⚠️ Opdateringsfejl: {str(e)}",
            title=f"{TITLE} Fejl under opdatering",
            persistent_notification_id=f"{__name__}_update_repo"
        )
    finally:
        task_list = ["check_master_updates_local_head", "check_master_updates_remote_head",
                     "check_master_updates_total_commits_behind", "check_master_updates_merge_commits"]
        for task_name in task_list:
            task_cancel(task_name, task_remove=True, timeout=5.0)

@service(f"pyscript.{__name__}_debug_info")
def debug_info(trigger_type=None, trigger_id=None, **kwargs):
    task.unique("debug_info")
    _LOGGER = globals()['_LOGGER'].getChild("debug_info")
    debug_info = []

    # Generate debug info from structured data
    for section, content in get_debug_info_sections().items():
        debug_info.append(f"<center>\n\n### {section}\n</center>\n")
        if content["table"]:
            debug_info.append("| Variable | Value |")
            debug_info.append("|---:|:---|")
            for key, value in content["table"].items():
                debug_info.append(f"| {key}: | {value} |")
                
        if content["table"] and content["details"]:
            debug_info.append("<br>\n") # Insert an extra line between the table and the dictionary
        
        if content["details"]:
            for detail_key, detail_value in content["details"].items():
                debug_info.append("<details>")
                debug_info.append(f"<summary>{detail_key}: Show dictionary</summary>\n")
                debug_info.append(f"```\n{pformat(detail_value)}\n```")
                debug_info.append("</details>\n")
                if len(content["details"]) > 1:
                    debug_info.append("<br>\n") # Insert an extra line between the dictionaries
        debug_info.append("---")
    
    if OVERVIEW_HISTORY:
        debug_info.append(f"<center>\n\n### Overview History\n</center>\n")
        for title, overview in sorted(OVERVIEW_HISTORY.items(), reverse=True):
            debug_info.append("<details>")
            debug_info.append(f"<summary>{title}: Show snapshot</summary>\n")
            debug_info.extend(overview)
            debug_info.append("</details>\n")

    # Join the debug_info list into a single string
    debug_info_output = "\n".join(debug_info)

    #_LOGGER.info(f"Debug Info: \n{get_debug_info_sections()}")
    my_persistent_notification(debug_info_output, title = f"{TITLE} debug info", persistent_notification_id = f"{__name__}_debug_info")

def save_error_to_file(error_message, caller_function_name = None):
    _LOGGER = globals()['_LOGGER'].getChild("save_error_to_file")
    # Convert get_debug_info_sections() to ensure compatibility with YAML
    def convert_tuples_to_lists(obj):
        if isinstance(obj, tuple):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: convert_tuples_to_lists(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_tuples_to_lists(item) for item in obj]
        else:
            return obj
        
    def remove_anchors(data):
        if isinstance(data, list):
            return [remove_anchors(item) for item in data]
        elif isinstance(data, dict):
            return {key: remove_anchors(value) for key, value in data.items()}
        else:
            return data
    
    filename = f"{__name__}_error_log.yaml"
    
    try:
        TASKS['save_error_to_file_error_log'] = task.create(load_yaml, filename)
        done, pending = task.wait({TASKS['save_error_to_file_error_log']})
        error_log = TASKS['save_error_to_file_error_log'].result()
        
        if not error_log:
            error_log = dict()
    
        TASKS["convert_tuples_to_lists"] = task.create(convert_tuples_to_lists, get_debug_info_sections().copy())
        done, pending = task.wait({TASKS["convert_tuples_to_lists"]})
        
        debug_dict = {
            "caller_function_name": caller_function_name,
            "error_message": error_message,
            "live_image": TASKS["convert_tuples_to_lists"].result(),
        }
        if error_log:
            error_log = limit_dict_size(error_log, 30)
            for timestamp in sorted(list(error_log.keys()), reverse=True):
                _LOGGER.info(f"Checking timestamp: {timestamp}")
                continue
                if minutesBetween(timestamp, getTime()) < 60:
                    _LOGGER.warning("Ignoring error log, as there is already an error logged within the last hour")
                    return
                break
                
        TASKS["remove_anchors"] = task.create(remove_anchors, debug_dict)
        done, pending = task.wait({TASKS["remove_anchors"]})
        error_log[getTime()] = TASKS["remove_anchors"].result()
        
        save_changes(filename, error_log)
    except Exception as e:
        _LOGGER.error(f"Error saving error to file error_message: {error_message} caller_function_name: {caller_function_name}: {e}")
    finally:
        for task_name in ["save_error_to_file_error_log", "convert_tuples_to_lists", "remove_anchors"]:
            task_cancel(task_name, task_remove=True, timeout=5.0)
    
def is_charger_configured(cfg = None):
    _LOGGER = globals()['_LOGGER'].getChild("is_charger_configured")
    global CHARGER_CONFIGURED
    
    def check_criteria(cfg):
        if (cfg['charger']['entity_ids']['kwh_meter_entity_id'] and
            cfg['charger']['entity_ids']['lifetime_kwh_meter_entity_id'] and
            cfg['charger']['entity_ids']['power_consumtion_entity_id'] and
            cfg['charger']['entity_ids']['status_entity_id']):
            return True
        return False
    
    if cfg is not None:
        return check_criteria(cfg)
    
    if CHARGER_CONFIGURED is None:
        CHARGER_CONFIGURED = check_criteria(CONFIG)
        _LOGGER.info(f"Charger entity is {'' if CHARGER_CONFIGURED else 'not '}configured")
            
    return CHARGER_CONFIGURED

def is_solar_configured(cfg = None):
    _LOGGER = globals()['_LOGGER'].getChild("is_solar_configured")
    global SOLAR_CONFIGURED
    
    def check_criteria(cfg):
        return True if cfg['solar']['entity_ids']['production_entity_id'] else False
    
    if cfg is not None:
        return check_criteria(cfg)
    
    if SOLAR_CONFIGURED is None:
        SOLAR_CONFIGURED = check_criteria(CONFIG)
        _LOGGER.info(f"Solar entity is {'' if SOLAR_CONFIGURED else 'not '}configured")
    
    return SOLAR_CONFIGURED
        
def is_powerwall_configured(cfg = None):
    _LOGGER = globals()['_LOGGER'].getChild("is_powerwall_configured")
    global POWERWALL_CONFIGURED
    
    def check_criteria(cfg):
        return True if cfg['home']['entity_ids']['powerwall_watt_flow_entity_id'] else False
    
    if cfg is not None:
        return check_criteria(cfg)
    
    if POWERWALL_CONFIGURED is None:
        POWERWALL_CONFIGURED = check_criteria(CONFIG)
        _LOGGER.info(f"Powerwall entity is {'' if POWERWALL_CONFIGURED else 'not '}configured")
    
    return POWERWALL_CONFIGURED

def is_ev_configured(cfg = None):
    _LOGGER = globals()['_LOGGER'].getChild("is_ev_configured")
    global EV_CONFIGURED
    
    def check_criteria(cfg):
        if (cfg['ev_car']['entity_ids']['odometer_entity_id'] and
            cfg['ev_car']['entity_ids']['estimated_battery_range_entity_id'] and
            cfg['ev_car']['entity_ids']['usable_battery_level_entity_id']):
            return True
        return False
    
    if cfg is not None:
        return check_criteria(cfg)
    
    if EV_CONFIGURED is None:
        EV_CONFIGURED = check_criteria(CONFIG)
        _LOGGER.info(f"Ev entities is {'' if EV_CONFIGURED else 'not '}configured")
    
    return EV_CONFIGURED

def is_entity_configured(entity):
    _LOGGER = globals()['_LOGGER'].getChild("is_entity_configured")
    if entity is None or entity == "":
        return False
    return True

def is_entity_available(entity):
    _LOGGER = globals()['_LOGGER'].getChild("is_entity_available")
    global INTEGRATION_OFFLINE_TIMESTAMP
    
    if not is_entity_configured(entity):
        return
    
    integration = get_integration(entity)
    
    try:
        entity_state = str(get_state(entity, try_history=True, error_state="unknown"))
        if entity_state in ENTITY_UNAVAILABLE_STATES:
            raise Exception(f"Entity state is {entity_state}")
        
        if integration is not None:
            if integration in INTEGRATION_OFFLINE_TIMESTAMP:
                del INTEGRATION_OFFLINE_TIMESTAMP[integration]
                _LOGGER.warning(f"Removing {integration} from offline timestamp")
                
        return True
    except Exception as e:
        _LOGGER.warning(f"Entity {entity} not available: {e}")
        
        if integration is not None:
            if integration not in INTEGRATION_OFFLINE_TIMESTAMP:
                INTEGRATION_OFFLINE_TIMESTAMP[integration] = getTime()
                _LOGGER.warning(f"Adding {integration} to offline timestamp")
                
            if minutesBetween(INTEGRATION_OFFLINE_TIMESTAMP[integration], getTime()) > 30:
                _LOGGER.warning(f"Reloading {integration} integration")
                my_persistent_notification(message = f"⛔Entity \"{entity}\" ikke tilgængelig siden {INTEGRATION_OFFLINE_TIMESTAMP[integration]}\nGenstarter {integration}", title = f"{TITLE} Entity ikke tilgængelig", persistent_notification_id = f"{__name__}_{entity}_reload_entity_integration")
                reload_entity_integration(entity)

def is_powerwall_charging(charge_watt = 0.0):
    _LOGGER = globals()['_LOGGER'].getChild("is_powerwall_charging")
    if not isinstance(charge_watt, (int, float)):
        _LOGGER.error(f"Invalid discharge_watt value: {charge_watt}")
        return False
    return True if charge_watt > POWERWALL_CHARGING_TRIGGER else False

def is_powerwall_discharging(discharge_watt = 0.0):
    _LOGGER = globals()['_LOGGER'].getChild("is_powerwall_discharging")
    if not isinstance(discharge_watt, (int, float)):
        _LOGGER.error(f"Invalid discharge_watt value: {discharge_watt}")
        return False
    return True if discharge_watt > POWERWALL_DISCHARGING_TRIGGER else False

def is_solar_production_available(watt = 0.0):
    _LOGGER = globals()['_LOGGER'].getChild("is_solar_production_available")
    if not isinstance(watt, (int, float)):
        _LOGGER.error(f"Invalid watt value: {watt}")
        return False
    return True if watt > SOLAR_PRODUCTION_TRIGGER else False
    
def get_all_unavailable_entities():
    _LOGGER = globals()['_LOGGER'].getChild("get_all_unavailable_entities")
    
    entities = []
    for value in CONFIG.values():
        if not isinstance(value, dict) or "entity_ids" not in value:
            continue
        
        entity_ids = []
        
        for entity in value["entity_ids"].values():
            if isinstance(entity, list):
                entity_ids.extend(entity)
            else:
                entity_ids.append(entity)
                
        for entity in entity_ids:
            if not is_entity_configured(entity):
                continue
            
            if not is_entity_available(entity):
                entities.append(entity)
    return entities

def save_changes(file, db):
    _LOGGER = globals()['_LOGGER'].getChild("save_changes")
    global COMMENT_DB_YAML
    
    db = db.copy() if isinstance(db, dict) else db
    
    if db == {} or db == [] or db is None:
        _LOGGER.error(f"Database is empty or None for {file}, not saving changes.")
    
    try:
        TASKS[f'save_changes_db_disk_{file}'] = task.create(load_yaml, file)
        done, pending = task.wait({TASKS[f'save_changes_db_disk_{file}']})
        db_disk = TASKS[f'save_changes_db_disk_{file}'].result()
    except Exception as e:
        _LOGGER.error(f"Error loading {file} from disk: {e}")
        db_disk = {}
    finally:
        task_cancel(f'save_changes_db_disk_{file}', task_remove=True, timeout=5.0)
    
    if "version" in db_disk:
        del db_disk["version"]
    
    comment_db = COMMENT_DB_YAML.copy() if f"{__name__}_config" in file else None
    if db != db_disk:
        try:
            _LOGGER.info(f"Saving {file} to disk")
            TASKS[f'save_changes_save_yaml_{file}'] = task.create(save_yaml, file, db, comment_db=comment_db)
            done, pending = task.wait({TASKS[f'save_changes_save_yaml_{file}']})
        except Exception as e:
            _LOGGER.error(f"Cant save {file}: {e}")
            my_persistent_notification(f"Kan ikke gemme {file} til disk", f"{TITLE} notification", persistent_notification_id = f"{__name__}_{file}_save_changes_error")
        finally:
            task_cancel(f'save_changes_save_yaml_{file}', task_remove=True, timeout=5.0)
        
def create_integration_dict():
    _LOGGER = globals()['_LOGGER'].getChild("create_integration_dict")
    global ENTITY_INTEGRATION_DICT, INTEGRATION_DAILY_LIMIT_BUFFER
    
    def integration_lookup(entity_id):
        integration = get_integration(entity_id)
        
        if integration is None or integration not in ENTITY_INTEGRATION_DICT["supported_integrations"]:
            return entity_id, None
        
        return entity_id, integration
    
    def hourly_limit(daily_limit):
        return max(1, int(daily_limit / 24)) + 5

    def add_to_dict(integration):
        ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["hourly_limit"] = hourly_limit(ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["daily_limit"])
        ENTITY_INTEGRATION_DICT["commands_last_hour"][integration] = [(getTime(), "Startup")]
        ENTITY_INTEGRATION_DICT["commands_history"][integration] = [(getTime(), "Startup")]
        ENTITY_INTEGRATION_DICT["last_reload"][integration] = getTime()
        ENTITY_INTEGRATION_DICT["counter"][integration] = 0
    
    local_task_names = []
    
    for value in CONFIG.values():
        if isinstance(value, dict) and "entity_ids" in value:
            for entity_id in value["entity_ids"].values():
                if entity_id is None or entity_id == "":
                    continue
                
                if isinstance(entity_id, list):
                    for entity_id_2 in entity_id:
                        task_name = f"create_integration_dict_integration_lookup_{entity_id_2}"
                        TASKS[task_name] = task.create(integration_lookup, entity_id_2)
                        local_task_names.append(task_name)
                else:
                    task_name = f"create_integration_dict_integration_lookup_{entity_id}"
                    TASKS[task_name] = task.create(integration_lookup, entity_id)
                    local_task_names.append(task_name)
    
    done, pending = task.wait(set([TASKS[task_name] for task_name in local_task_names]))
    
    for task_name in local_task_names:
        if task_name in TASKS:
            entity_id, integration = TASKS[task_name].result()
            
            task_cancel(task_name, task_remove=True)
            
            if integration is None:
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
    _LOGGER = globals()['_LOGGER'].getChild("reload_entity_integration")
    global ENTITY_INTEGRATION_DICT
    
    integration = get_integration(entity_id)
    
    if integration is None:
        return
    
    if integration not in ENTITY_INTEGRATION_DICT["last_reload"] or minutesBetween(ENTITY_INTEGRATION_DICT["last_reload"][integration], getTime()) > 30:
        ENTITY_INTEGRATION_DICT["last_reload"][integration] = getTime()
        
        _LOGGER.warning(f"Reloading integration {integration} for entity {entity_id}")
        TASKS[f'reload_entity_integration_{entity_id}'] = task.create(reload_integration, entity_id)
        task_cancel(f'reload_entity_integration_{entity_id}', task_remove=True, timeout=5.0)
        
def reset_counter_entity_integration():
    _LOGGER = globals()['_LOGGER'].getChild("reset_counter_entity_integration")
    global ENTITY_INTEGRATION_DICT
    
    _LOGGER.info(f"ENTITY_INTEGRATION_DICT before reset:\n{pformat(ENTITY_INTEGRATION_DICT, width=200, compact=True)}")
    
    for integration in ENTITY_INTEGRATION_DICT["counter"].keys():
        ENTITY_INTEGRATION_DICT["counter"][integration] = 0
        
def commands_history_clean_entity_integration():
    global ENTITY_INTEGRATION_DICT
    
    now = getTime()
    for integration in ENTITY_INTEGRATION_DICT["commands_history"].keys():
        ENTITY_INTEGRATION_DICT["commands_history"][integration] = [dt for dt in ENTITY_INTEGRATION_DICT["commands_history"][integration] if dt[0] >= now - datetime.timedelta(days=1)]
    
def allow_command_entity_integration(entity_id=None, command="None", integration=None, check_only=False):
    _LOGGER = globals()['_LOGGER'].getChild("allow_command_entity_integration")
    global ENTITY_INTEGRATION_DICT, INTEGRATION_DAILY_LIMIT_BUFFER

    allowed = False
    now = getTime()

    if integration is None:
        integration = get_integration(entity_id)

    if integration is None and entity_id.split(".")[0] in ("input_number", "input_select", "input_boolean", "input_text", "input_datetime"):
        integration = entity_id.split(".")[0]

    if integration is None:
        _LOGGER.warning(f"integration was none allow_command_entity_integration(entity_id = {entity_id}, command = {command}, integration = {integration})")
        return False

    try:
        ENTITY_INTEGRATION_DICT["commands_last_hour"][integration] = [
            dt for dt in ENTITY_INTEGRATION_DICT["commands_last_hour"][integration]
            if dt[0] >= now - datetime.timedelta(hours=1)
        ]

        if integration in ENTITY_INTEGRATION_DICT["supported_integrations"]:
            extra_buffer = 3 if "wake" in str(entity_id).lower() else 0

            daily_limit = ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["daily_limit"] - INTEGRATION_DAILY_LIMIT_BUFFER
            hourly_limit = ENTITY_INTEGRATION_DICT["supported_integrations"][integration]["hourly_limit"] - extra_buffer

            if (
                len(ENTITY_INTEGRATION_DICT["commands_last_hour"][integration]) < hourly_limit
                and ENTITY_INTEGRATION_DICT["counter"][integration] < daily_limit
                and ENTITY_INTEGRATION_DICT["commands_last_hour"][integration] != command
            ):
                allowed = True
                if not check_only:
                    ENTITY_INTEGRATION_DICT["commands_last_hour"][integration].append((now, f"{entity_id}: {command}"))
                    ENTITY_INTEGRATION_DICT["counter"][integration] += 1
        else:
            allowed = True

    except Exception as e:
        _LOGGER.error(
            f"allow_command_entity_integration(entity_id = {entity_id}, command = {command}, integration = {integration})\n"
            f"{pformat(ENTITY_INTEGRATION_DICT, width=200, compact=True)}: {e}"
        )
        allowed = True

    if allowed and not check_only:
        ENTITY_INTEGRATION_DICT["commands_history"][integration].append((now, f"{entity_id}: {command}"))

    return allowed

def set_charging_rule(text=""):
    _LOGGER = globals()['_LOGGER'].getChild("set_charging_rule")
    global POWERWALL_CHARGING_TEXT, RESTARTING_CHARGER_COUNT, TESTING
    
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
        
        powerwall_sting = f"\n🚧{POWERWALL_CHARGING_TEXT}" if POWERWALL_CHARGING_TEXT else ""
        
        text = "\n".join([f"{testing}{line.strip()}{testing}" for line in text.split("\n") if line.strip()])
        try:
            set_state(f"sensor.{__name__}_current_charging_rule", f"{text}{limit_string}{powerwall_sting}")
        except Exception as e:
            _LOGGER.warning(f"Cant set sensor.{__name__}_current_charging_rule to '{text}': {e}")
            
def restart_script():
    _LOGGER = globals()['_LOGGER'].getChild("restart_script")
    
    task_shutdown()
    
    _LOGGER.info("Restarting script")
    set_charging_rule(f"📟Genstarter scriptet")
    if service.has_service("pyscript", "reload"):
        service.call("pyscript", "reload", blocking=True, global_ctx=f"file.{__name__}")

def notify_critical_change(cfg = {}, filename = None):
    _LOGGER = globals()['_LOGGER'].getChild("notify_critical_change")
    
    def check_nested_keys_exist(cfg, dotted_keys):
        missing_keys = []
        for dotted_key in dotted_keys:
            keys = dotted_key.split(".")
            current = cfg
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    missing_keys.append(dotted_key)
                    break
        return missing_keys
    
    def keys_description(keys):
        description = []
        
        for key in keys:
            description.append(f"**{key}**\n{COMMENT_DB_YAML.get(key, '')}\n\n")
        return description
    
    if filename == f"{__name__}_config.yaml":
        powerwall_update_new_keys = [
            "home.power_consumption_entity_id_include_powerwall_charging",
            "solar.powerwall_battery_size",
            "solar.inverter_discharging_power_limit",
            "solar.powerwall_discharging_power",
        ]
        powerwall_update_missing_keys = check_nested_keys_exist(cfg, powerwall_update_new_keys)
        
        if is_powerwall_configured(cfg) and powerwall_update_missing_keys:
            _LOGGER.warning(f"Powerwall configuration update required: {powerwall_update_missing_keys}")
                
            my_persistent_notification(
                message = f"## Vigtigt\n\n"
                        f"Der er sket en kritisk ændring i konfigurationen, som kræver opdatering af din {__name__}_config.yaml fil.\n\n"
                        f"### Nye konfigurations nøgler:\n - {'- '.join(keys_description(powerwall_update_missing_keys))}\n\n"
                        f"**Handling:**\n"
                        f"Opdater venligst din konfiguration i {__name__}_config.yaml filen.\n",
                title = f"{TITLE} Kritisk ændring i konfiguration",
                persistent_notification_id = f"{__name__}_notify_critical_change_powerwall_update_required"
            )
            
    if filename == f"packages/{__name__}.yaml":
        powerwall_update_new_entities = [
            f"input_boolean.{__name__}_powerwall_discharge_above_needed",
            f"input_number.{__name__}_ev_charge_after_powerwall_battery_level",
        ]
        powerwall_update_missing_entities = check_nested_keys_exist(cfg, powerwall_update_new_entities)
        
        if is_powerwall_configured(CONFIG) and powerwall_update_missing_entities:
            _LOGGER.warning(f"Powerwall entities update required: {powerwall_update_missing_entities}")
            
            my_persistent_notification(
                message = f"## Vigtigt\n\n"
                        f"Nye entiteter er blevet tilføjet\n"
                        f"Læs mere om dem i entitiens beskrivelse.\n\n"
                        f"### Nye entiteter:\n - {'- '.join(keys_description(powerwall_update_missing_entities))}\n\n"
                        f"**Handling:**\n"
                        f"Tilføj venligst de nye entiteter til dine Betjeningspaneler sider.\n",
                title = f"{TITLE} Kritisk ændring i entiteter",
                persistent_notification_id = f"{__name__}_notify_critical_change_powerwall_entities_update_required"
            )

def init():
    _LOGGER = globals()['_LOGGER'].getChild("init")
    global CONFIG, CONFIG_LAST_MODIFIED, DEFAULT_ENTITIES, INITIALIZATION_COMPLETE, COMMENT_DB_YAML, TESTING

    def handle_yaml(file_path, default_content, key_renaming, comment_db, check_nested_keys=False, check_first_run=False, prompt_restart=False):
        """
        Handles the loading, updating, and saving of YAML configurations, and optionally prompts for a restart.
        """
        if not file_exists(file_path):
            TASKS[f'init_not_exists_save_yaml_{file_path}'] = task.create(save_yaml, file_path, default_content, comment_db)
            done, pending = task.wait({TASKS[f'init_not_exists_save_yaml_{file_path}']})
    
            _LOGGER.error(f"File has been created: {file_path}")
            if "config.yaml" in file_path:
                my_persistent_notification(message = f"Oprettet konfigurations fil: {file_path}\nTilføj entities efter behov & genstart Home Assistant", title = f"{TITLE} ", persistent_notification_id = f"{file_path}_created")
            else:
                my_persistent_notification(message = f"Oprettet yaml fil: {file_path}\nGenstart Home Assistant", title = f"{TITLE} ", persistent_notification_id = f"{file_path}_created")
            
            raise Exception(f"Edit it as needed. Please restart Home Assistant after making necessary changes.")
        
        TASKS[f'init_load_yaml_{file_path}'] = task.create(load_yaml, file_path)
        done, pending = task.wait({TASKS[f'init_load_yaml_{file_path}']})
        content = TASKS[f'init_load_yaml_{file_path}'].result()
        
        _LOGGER.debug(f"Loaded content from {file_path}:\n{pformat(content, width=200, compact=True)}")

        if not content:
            raise Exception(f"Failed to load {file_path}")

        notify_critical_change(cfg = content, filename = file_path)

        updated, content = update_dict_with_new_keys(content, default_content)
            
        if content == {}:
            raise Exception(f"{file_path} is empty after updating keys, removing file")
        
        if (updated or file_path == f"{__name__}_config.yaml"):
            TASKS[f'init_updated_save_yaml_{file_path}'] = task.create(save_yaml, file_path, content, comment_db)
            done, pending = task.wait({TASKS[f'init_updated_save_yaml_{file_path}']})
            
        if key_renaming:
            old_content = content.copy()
            is_config_file = True if "config.yaml" in file_path else False
            
            keys_renamed = []
            keys_renamed_log = []
            all_entities = state.names() if not is_config_file else []
            
            content = rename_dict_keys(content, key_renaming, remove_old_keys=False)
            
            for old_path, new_path in key_renaming.items():
                if is_config_file:
                    if get_dict_value_with_path(content, old_path) is None:
                        continue
                    
                    content = delete_dict_key_with_path(content, old_path)
                    keys_renamed.append(f"{old_path} -> {new_path}")
                    keys_renamed_log.append(f"Renamed {old_path} to {new_path}")
                else:
                    old_entity_id = ".".join(old_path.split(".")[-2:])
                    new_entity_id = ".".join(new_path.split(".")[-2:])
                    if old_entity_id in all_entities and new_entity_id not in all_entities:
                        old_entity_id_state = get_state(old_entity_id)
                        old_entity_id_attr = get_attr(old_entity_id)
                        
                        if new_entity_id in all_entities:
                            if not is_entity_available(new_entity_id):
                                set_state(new_entity_id, old_entity_id_state)
                                
                            new_entity_id_state = get_state(new_entity_id)
                            if old_entity_id_state == new_entity_id_state or (is_entity_available(new_entity_id) and "restored" in old_entity_id_attr and old_entity_id_attr["restored"] == True):
                                content = delete_dict_key_with_path(content, old_path)
                                keys_renamed.append(f"{old_path} ({old_entity_id_state}) (Slettet) -> {new_path} ({new_entity_id_state})")
                                keys_renamed_log.append(f"Renamed {old_path} ({old_entity_id_state}) (Removed) to {new_path} ({new_entity_id_state})")
                            else:
                                keys_renamed.append(f"{old_path} ({old_entity_id_state}) -> {new_path} ({new_entity_id_state})")
                                keys_renamed_log.append(f"Renamed {old_path} ({old_entity_id_state}) to {new_path} ({new_entity_id_state})")
                        else:
                            keys_renamed.append(f"{old_path} ({old_entity_id_state}) -> {new_path} (Oprettet)")
                            keys_renamed_log.append(f"Renamed {old_path} ({old_entity_id_state}) to {new_path} (Created)")
                            
            if content == {}:
                raise Exception(f"{file_path} is empty after renaming keys, removing file")
                
            if old_content != content:
                for log_string in keys_renamed_log:
                    _LOGGER.info(log_string)
                
                config_entity_title = f"nøgler i {__name__}_config.yaml" if "config.yaml" in file_path else "entitetsnavne"
                my_persistent_notification(message = f"{'\n'.join(keys_renamed)}", title = f"{TITLE} Kritisk ændring af {config_entity_title}", persistent_notification_id = f"{file_path}_renaming_keys")
                
                TASKS[f'init_key_moved_save_yaml_{file_path}'] = task.create(save_yaml, file_path, content, comment_db)
                done, pending = task.wait({TASKS[f'init_key_moved_save_yaml_{file_path}']})
        
        deprecated_keys = compare_dicts_unique_to_dict1(content, default_content)
        if deprecated_keys:
            _LOGGER.warning(f"{file_path} contains deprecated settings:")
            for key, value in deprecated_keys.items():
                _LOGGER.warning(f"\t{key}: {value}")
            _LOGGER.warning("Please remove them.")
            my_persistent_notification(message = f"Forældet nøgler i {file_path}\n Fjern disse nøgler:\n{'\n'.join(deprecated_keys.keys())}", title = f"{TITLE} Forældet nøgler", persistent_notification_id = file_path)
            
                
        if updated:
            msg = f"{'Config' if "config.yaml" in file_path else 'Entities package'} updated."
            
            if check_first_run:
                msg += " Set first_run to false and reload."
            msg += " Please restart Home Assistant to apply changes."
            
            if ("first_run" in content and content['first_run']) or "config.yaml" not in file_path:
                raise Exception(msg)

        if prompt_restart and updated:
            raise Exception(f"Please restart Home Assistant to apply changes to {file_path}.")

        return content
    
    _LOGGER.info(welcome())
    try:
        CONFIG = handle_yaml(f"{__name__}_config.yaml", DEFAULT_CONFIG.copy(), CONFIG_KEYS_RENAMING.copy(), COMMENT_DB_YAML.copy(), check_first_run=True, prompt_restart=False)
        CONFIG_LAST_MODIFIED = get_file_modification_time(f"{__name__}_config.yaml")

        TESTING = True if "test" in __name__ or ("testing_mode" in CONFIG and CONFIG['testing_mode']) else False
        
        set_charging_rule(f"📟Indlæser konfigurationen")
        
        if is_ev_configured():
            for key in [f"{__name__}_battery_level", f"{__name__}_completed_battery_level", f"{__name__}_estimated_total_range"]:
                DEFAULT_ENTITIES['input_number'].pop(key, None)
        else:
            for entity_type in ['input_boolean', 'input_number']:
                DEFAULT_ENTITIES[entity_type] = {
                    key: value for key, value in DEFAULT_ENTITIES[entity_type].items() if "preheat" not in key
                }

            DEFAULT_ENTITIES['sensor'][0]['sensors'] = {
                key: value for key, value in DEFAULT_ENTITIES['sensor'][0]['sensors'].items() if "drive_efficiency" not in key or "drive_efficiency_last_battery_level" in key
            }
                    
            if f"{__name__}_km_per_kwh" in DEFAULT_ENTITIES['sensor'][0]['sensors']:
                del DEFAULT_ENTITIES['sensor'][0]['sensors'][f'{__name__}_km_per_kwh']
        
        if not is_solar_configured():
            keys_to_remove = [
                f"{__name__}_solar_charging",
                f"{__name__}_kwh_charged_by_solar",
                f"{__name__}_solar_sell_fixed_price"
            ]

            for key in keys_to_remove:
                DEFAULT_ENTITIES.get('input_boolean', {}).pop(key, None)
                DEFAULT_ENTITIES.get('input_number', {}).pop(key, None)

            if 'sensor' in DEFAULT_ENTITIES and isinstance(DEFAULT_ENTITIES['sensor'], list) and DEFAULT_ENTITIES['sensor']:
                DEFAULT_ENTITIES['sensor'][0]['sensors'] = {
                    key: value for key, value in DEFAULT_ENTITIES['sensor'][0]['sensors'].items() if "solar" not in key
                }
        
        if not is_powerwall_configured() and not CONFIG['home']['entity_ids']['powerwall_battery_level_entity_id']:
            keys_to_remove = [
                f"{__name__}_powerwall_discharge_above_needed",
                f"{__name__}_ev_charge_after_powerwall_battery_level"
            ]

            for key in keys_to_remove:
                DEFAULT_ENTITIES.get('input_boolean', {}).pop(key, None)
                DEFAULT_ENTITIES.get('input_number', {}).pop(key, None)
        
        handle_yaml(f"packages/{__name__}.yaml", DEFAULT_ENTITIES.copy(), ENTITIES_RENAMING.copy(), None, check_nested_keys=True, prompt_restart=True)

        if CONFIG['first_run']:
            raise Exception("Edit config file and set first_run to false")
        
        if not is_charger_configured():
            raise Exception("Required charger entities not configured, if no charger integration, use similar ev car entities")
        
        CONFIG['solar']['charging_single_phase_max_amp'] = min(CONFIG['solar']['charging_single_phase_max_amp'], CONFIG['charger']['charging_max_amp'])
        CONFIG['solar']['charging_single_phase_min_amp'] = min(CONFIG['solar']['charging_single_phase_min_amp'], CONFIG['charger']['charging_max_amp'])
        CONFIG['solar']['charging_three_phase_min_amp'] = min(CONFIG['solar']['charging_three_phase_min_amp'], CONFIG['charger']['charging_max_amp'])
        
        is_powerwall_configured()
        
        create_integration_dict()
        
        INITIALIZATION_COMPLETE = True
    except Exception as e:
        _LOGGER.error(e)
        INITIALIZATION_COMPLETE = False
        set_charging_rule(f"⛔Lad script stoppet.\nTjek log for mere info:\n{e}")
        my_persistent_notification(message = f"Lad script stoppet.\nTjek log for mere info:\n{e}", title = f"{TITLE} Stop", persistent_notification_id = f"{__name__}_init")
    finally:
        for task_name in list(TASKS.keys()):
            if task_name.startswith("init_"):
                task_cancel(task_name, task_remove=True)

@service(f"pyscript.{__name__}_all_entities")
def get_all_entities(trigger_type=None, trigger_id=None, **kwargs):
    _LOGGER = globals()['_LOGGER'].getChild("get_all_entities")
    global DEFAULT_ENTITIES
    entities = []
    yaml_card = ["type: vertical-stack\n", "cards:\n"]
    
    for domain_name, sub_dict in DEFAULT_ENTITIES.items():
        if "homeassistant" in domain_name:
            continue
        
        if domain_name == "sensor":
            yaml_card.append(f"  - type: entities\n    title: 📊 Sensorer\n    state_color: true\n    entities:\n")
            for sensor_dict in sub_dict:
                for entity_name in sensor_dict["sensors"].keys():
                    yaml_card.append(f"    - {domain_name}.{entity_name}\n")
                    entities.append(f"{domain_name}.{entity_name}")
        else:
            yaml_card.append(f"  - type: entities\n    title: 📦 {domain_name.capitalize()}\n    state_color: true\n    entities:\n")
            for entity_name in sub_dict.keys():
                yaml_card.append(f"    - {domain_name}.{entity_name}\n")
                entities.append(f"{domain_name}.{entity_name}")
    
    yaml_card.append("  - type: markdown\n    content: >-\n")
    for entity in entities:
        description = DEFAULT_ENTITIES.get("homeassistant", {}).get('customize', {}).get(entity, {}).get('description', '')
        description = f"<br>{description}<br><br>" if description else ""
        yaml_card.append(f"      - <b>`{entity}`</b>{description}\n")
        
    notify_message = [f"## Alle entities:\n\n"]
    for entity in entities:
        description = DEFAULT_ENTITIES.get("homeassistant", {}).get('customize', {}).get(entity, {}).get('description', '')
        description = f"\n{description}\n" if description else ""
        notify_message.append(f"- <b>`{entity}`</b>{description}\n")
        
    my_persistent_notification(
        message = "\n".join(notify_message),
        title = f"{TITLE} Alle entities",
        persistent_notification_id = f"{__name__}_get_all_entities_notification"
    )
        
    if trigger_type == "service":
        return
    
    _LOGGER.info(f"Entities:\n{"".join(yaml_card)}")
    
    return entities

set_charging_rule(f"📟Starter scriptet op")
init()

if TESTING:
    LAST_DRIVE_EFFICIENCY_DATA = {
        "timestamp": getTime(),
        "distance": 100.0,
        "usedkWh": 20.0,
        "usedBattery": 30.0,
        "cost": 15.0,
        "efficiency": 90.0,
        "distancePerkWh": 5.0,
        "wh_km": 175.0
    }

if INITIALIZATION_COMPLETE:
    solar_min_amp = CONFIG['solar']['charging_single_phase_min_amp'] if float(CONFIG['charger']['charging_phases']) > 1.0 else CONFIG['solar']['charging_three_phase_min_amp'] * 3.0
    SOLAR_CHARGING_TRIGGER_ON = abs(CONFIG['charger']['power_voltage'] * solar_min_amp)
    MAX_WATT_CHARGING = (CONFIG['charger']['power_voltage'] * CONFIG['charger']['charging_phases']) * CONFIG['charger']['charging_max_amp']
    MAX_KWH_CHARGING = MAX_WATT_CHARGING / 1000

def set_entity_friendlynames():
    _LOGGER = globals()['_LOGGER'].getChild("set_entity_friendlynames")
    for key, nested_dict in CHARGING_TYPES.items():
        if "entity_name" in nested_dict:
            _LOGGER.info(f"Setting sensor.{nested_dict['entity_name']}.friendly_name: {nested_dict['emoji']} {nested_dict['description']}")
            set_attr(f"sensor.{nested_dict['entity_name']}.friendly_name", f"{nested_dict['emoji']} {nested_dict['description']}")

def emoji_description():
    _LOGGER = globals()['_LOGGER'].getChild("emoji_description")

    emoji_sorted = sorted(CHARGING_TYPES.values(), key=lambda x: float(x.get('priority', 0)))

    descriptions = ["## Emoji forklaring: ##"] + [
        f"* **{entry.get('emoji', '❓')} {entry.get('description', 'Ingen beskrivelse')}**"
        for entry in emoji_sorted
    ]

    _LOGGER.info(f"Setting sensor.{__name__}_emoji_description")

    set_state(
        f"sensor.{__name__}_emoji_description",
        f"Brug Markdown kort med dette i: {{{{ states.sensor.{__name__}_emoji_description.attributes.description }}}}"
    )
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

def join_unique_emojis(str1: str, str2: str) -> str:
    if str1 and str2:
        emojis1 = set(str1.split())
        emojis2 = set(str2.split())
        unique_emojis = emojis1.union(emojis2)
        return ' '.join(unique_emojis)
    return str1 or str2

def emoji_text_format(text, group_size=3):
    words = text.split()
    
    if len(words) <= group_size:
        return ''.join(words)

    grouped_text = [''.join(words[i:i+group_size]) for i in range(0, len(words), group_size)]
    
    return '<br>'.join(grouped_text)

def set_default_entity_states():
    _LOGGER = globals()['_LOGGER'].getChild("set_default_entity_states")
    set_state(f"sensor.{__name__}_overview", f"Brug Markdown kort med dette i: {{{{ states.sensor.{__name__}_overview.attributes.overview }}}}")
    set_attr(f"sensor.{__name__}_overview.overview", "<center>\n\n**Ingen oversigt endnu**\n\n</center>")
    
    entity_dict = {
        f"input_number.{__name__}_typical_daily_distance": CONFIG['ev_car']['typical_daily_distance_non_working_day'],
        f"input_number.{__name__}_workday_distance_needed_monday": CONFIG['ev_car']['workday_distance_needed_monday'],
        f"input_number.{__name__}_workday_distance_needed_tuesday": CONFIG['ev_car']['workday_distance_needed_tuesday'],
        f"input_number.{__name__}_workday_distance_needed_wednesday": CONFIG['ev_car']['workday_distance_needed_wednesday'],
        f"input_number.{__name__}_workday_distance_needed_thursday": CONFIG['ev_car']['workday_distance_needed_thursday'],
        f"input_number.{__name__}_workday_distance_needed_friday": CONFIG['ev_car']['workday_distance_needed_friday'],
        f"input_number.{__name__}_workday_distance_needed_saturday": CONFIG['ev_car']['workday_distance_needed_saturday'],
        f"input_number.{__name__}_workday_distance_needed_sunday": CONFIG['ev_car']['workday_distance_needed_sunday'],
        f"input_number.{__name__}_min_daily_battery_level": CONFIG['ev_car']['min_daily_battery_level'],
        f"input_number.{__name__}_min_trip_battery_level": CONFIG['ev_car']['min_trip_battery_level'],
        f"input_number.{__name__}_min_charge_limit_battery_level": CONFIG['ev_car']['min_charge_limit_battery_level'],
        f"input_number.{__name__}_max_recommended_charge_limit_battery_level": CONFIG['ev_car']['max_recommended_charge_limit_battery_level'],
        f"input_number.{__name__}_very_cheap_grid_charging_max_battery_level": CONFIG['ev_car']['very_cheap_grid_charging_max_battery_level'],
        f"input_number.{__name__}_ultra_cheap_grid_charging_max_battery_level": CONFIG['ev_car']['ultra_cheap_grid_charging_max_battery_level'],
        f"input_number.{__name__}_ev_charge_after_powerwall_battery_level": CONFIG['solar']['ev_charge_after_powerwall_battery_level'],
        f"input_number.{__name__}_solar_sell_fixed_price": CONFIG['solar']['production_price']
    }
    
    for entity_id, value in entity_dict.items():
        try:
            if not is_entity_configured(entity_id):
                continue
            
            if not is_powerwall_configured() and "powerwall" in entity_id:
                continue
            
            if not is_solar_configured() and "solar" in entity_id:
                continue
            
            if not is_entity_available(entity_id):
                raise Exception(f"Entity {entity_id} not available cant set state")

            if str(get_state(entity_id, float_type=False, error_state=None)) in ENTITY_UNAVAILABLE_STATES:
                _LOGGER.info(f"Setting {entity_id} to {value}")

            set_state(entity_id, value)
        except Exception as e:
            _LOGGER.error(f"Error setting {entity_id} to {value}: {e}")

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
    _LOGGER = globals()['_LOGGER'].getChild("is_calculating_charging_loss")
    try:
        return True if get_state(f"input_boolean.{__name__}_calculate_charging_loss", float_type=False, error_state=False) == "on" else False
    except Exception as e:
        _LOGGER.warning(f": {e}")
        return False
    
def get_vin_cupra_born(entity_id):
    vin = False
    if get_identifiers(entity_id):
        vin = get_identifiers(entity_id)[0][1].replace("vw","")
    return vin

def get_entity_daily_distance(day_text = None, date = None):
    _LOGGER = globals()['_LOGGER'].getChild("get_entity_daily_distance")
    try:
        if day_text is None and date is None:
            distance = float(get_state(f"input_number.{__name__}_typical_daily_distance", float_type=True))
        else:
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day_text = day_text if day_text in days else getDayOfWeekText(getTime() if date is None else date, translate=False)
                
            workday = get_state(f"input_boolean.{__name__}_workday_{day_text}", error_state="off")
            distance = float(get_state(f"input_number.{__name__}_workday_distance_needed_{day_text}", float_type=True, error_state=0.0))
            
            if distance == 0.0 or workday == "off":
                distance = float(get_state(f"input_number.{__name__}_typical_daily_distance", float_type=True))

        if is_ev_configured():
            estimated_range_attr = get_attr(f"sensor.{__name__}_estimated_range")
            if "total" in estimated_range_attr and float(estimated_range_attr["total"]) > 0.0:
                estimated_range_per_percent = float(estimated_range_attr["total"]) / 100
                daily_available_battery_level = get_max_recommended_charge_limit_battery_level() - get_min_daily_battery_level()
                daily_available_range = daily_available_battery_level * estimated_range_per_percent
                distance = min(daily_available_range, distance)
        return distance
    except Exception as e:
        _LOGGER.warning(f"Cant get daily distance, using config data {CONFIG['ev_car']['typical_daily_distance_non_working_day']}: {e}")
        return CONFIG['ev_car']['typical_daily_distance_non_working_day']

def get_min_daily_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_min_daily_battery_level")
    try:
        return float(get_state(f"input_number.{__name__}_min_daily_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get daily battery level, using config data {CONFIG['ev_car']['min_daily_battery_level']}: {e}")
        return CONFIG['ev_car']['min_daily_battery_level']

def get_min_trip_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_min_trip_battery_level")
    try:
        return float(get_state(f"input_number.{__name__}_min_trip_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get min trip battery level, using config data {CONFIG['ev_car']['min_trip_battery_level']}: {e}")
        return CONFIG['ev_car']['min_trip_battery_level']

def get_min_charge_limit_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_min_charge_limit_battery_level")
    try:
        return float(get_state(f"input_number.{__name__}_min_charge_limit_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get min charge limit battery level, using config data {CONFIG['ev_car']['min_charge_limit_battery_level']}: {e}")
        return CONFIG['ev_car']['min_charge_limit_battery_level']

def get_max_recommended_charge_limit_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_max_recommended_charge_limit_battery_level")
    try:
        return float(get_state(f"input_number.{__name__}_max_recommended_charge_limit_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get max recommended charge limit battery level, using config data {CONFIG['ev_car']['max_recommended_charge_limit_battery_level']}: {e}")
        return CONFIG['ev_car']['max_recommended_charge_limit_battery_level']

def get_very_cheap_grid_charging_max_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_very_cheap_grid_charging_max_battery_level")
    try:
        return float(get_state(f"input_number.{__name__}_very_cheap_grid_charging_max_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get very cheap grid charging max battery level, using config data {CONFIG['ev_car']['very_cheap_grid_charging_max_battery_level']}: {e}")
        return CONFIG['ev_car']['very_cheap_grid_charging_max_battery_level']

def get_ultra_cheap_grid_charging_max_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_ultra_cheap_grid_charging_max_battery_level")
    try:
        return float(get_state(f"input_number.{__name__}_ultra_cheap_grid_charging_max_battery_level", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get ultra cheap grid charging max battery level, using config data {CONFIG['ev_car']['ultra_cheap_grid_charging_max_battery_level']}: {e}")
        return CONFIG['ev_car']['ultra_cheap_grid_charging_max_battery_level']

def get_powerwall_discharge_above_needed():
    _LOGGER = globals()['_LOGGER'].getChild("get_powerwall_discharge_above_needed")
    if not is_powerwall_configured():
        return False
    
    try:
        state = get_state(f"input_boolean.{__name__}_powerwall_discharge_above_needed", float_type=False, error_state="off")
        return True if state == "on" else False
    except Exception as e:
        _LOGGER.warning(f"Cant get powerwall discharge above needed state from input_boolean.{__name__}_powerwall_discharge_above_needed entity: {e}")

def get_powerwall_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_powerwall_battery_level")
    if not is_powerwall_configured():
        return 100.0
    
    try:
        return float(get_state(CONFIG["home"]["entity_ids"]["powerwall_battery_level_entity_id"], float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get powerwall battery level from {CONFIG['home']['entity_ids']['powerwall_battery_level_entity_id']}, using default value 100.0: {e}")
        return 100.0

def get_ev_charge_after_powerwall_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_ev_charge_after_powerwall_battery_level")
    if not is_powerwall_configured():
        return 100.0
    
    try:
        return float(get_state(f"input_number.{__name__}_ev_charge_after_powerwall_battery_level", float_type=True))
    except Exception as e:
        try:
            _LOGGER.warning(f"Cant get ev charge after powerwall battery level, using config data {CONFIG['solar']['ev_charge_after_powerwall_battery_level']}: {e}")
            return float(CONFIG['solar']['ev_charge_after_powerwall_battery_level'])
        except Exception as e:
            _LOGGER.error(f"Failed to get ev charge after powerwall battery level from config: {e}")
            return 100.0

def get_completed_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_completed_battery_level")
    try:
        if not is_ev_configured():
            return float(get_state(f"input_number.{__name__}_completed_battery_level", float_type=True))
        return 100.0
    except Exception as e:
        _LOGGER.warning(f"Using default charge completed battery level 100.0: {e}")
        return 100.0

def get_estimated_total_range():
    _LOGGER = globals()['_LOGGER'].getChild("get_estimated_total_range")
    estimated_total_range = 0.0
    try:
        estimated_total_range = float(get_state(f"input_number.{__name__}_estimated_total_range", float_type=True))
    except Exception as e:
        _LOGGER.error(f"input_number.{__name__}_estimated_total_range is not set to a total range: {e}")
        
    return estimated_total_range

def get_trip_date_time():
    _LOGGER = globals()['_LOGGER'].getChild("get_trip_date_time")
    trip_date_time = resetDatetime()
    try:
        trip_date_time = get_state(f"input_datetime.{__name__}_trip_date_time", error_state=resetDatetime())
    except Exception as e:
        _LOGGER.error(f"input_datetime.{__name__}_trip_date_time is not set to a dateTime: {e}")
        try:
            set_state(f"input_datetime.{__name__}_trip_date_time", resetDatetime())
        except Exception as e:
            _LOGGER.error(f"Cant set input_datetime.{__name__}_trip_date_time to {resetDatetime()}: {e}")
            
    return trip_date_time

def get_trip_homecoming_date_time():
    _LOGGER = globals()['_LOGGER'].getChild("get_trip_homecoming_date_time")
    trip_homecoming_date_time = resetDatetime()
    try:
        trip_homecoming_date_time = get_state(f"input_datetime.{__name__}_trip_homecoming_date_time", error_state=resetDatetime())
    except Exception as e:
        _LOGGER.error(f"input_datetime.{__name__}_trip_homecoming_date_time is not set to a dateTime: {e}")
        try:
            set_state(f"input_datetime.{__name__}_trip_homecoming_date_time", resetDatetime())
        except Exception as e:
            _LOGGER.error(f"Cant set input_datetime.{__name__}_trip_homecoming_date_time to {resetDatetime()}: {e}")
            
    return trip_homecoming_date_time

def get_trip_range():
    _LOGGER = globals()['_LOGGER'].getChild("get_trip_range")
    trip_range = 0.0
    try:
        trip_range = float(get_state(f"input_number.{__name__}_trip_range_needed"))
    except Exception as e:
        _LOGGER.error(f"input_number.{__name__}_trip_range_needed is not set to a number: {e}")
        try:
            set_state(f"input_number.{__name__}_trip_range_needed", 0.0)
        except Exception as e:
            _LOGGER.error(f"Cant set input_number.{__name__}_trip_range_needed to 0.0: {e}")
        
    return trip_range

def get_trip_target_level():
    _LOGGER = globals()['_LOGGER'].getChild("get_trip_target_level")
    trip_target_level = 0.0
    try:
        trip_target_level = float(get_state(f"input_number.{__name__}_trip_charge_procent"))
    except Exception as e:
        _LOGGER.error(f"input_number.{__name__}_trip_charge_procent is not set to a number: {e}")
        try:
            set_state(f"input_number.{__name__}_trip_charge_procent", 0.0)
        except Exception as e:
            _LOGGER.error(f"Cant set input_number.{__name__}_trip_charge_procent to 0.0: {e}")
        
    return trip_target_level

def is_trip_planned():
    if (not is_entity_available(f"input_number.{__name__}_trip_charge_procent") or
        not is_entity_available(f"input_number.{__name__}_trip_range_needed") or
        not is_entity_available(f"input_datetime.{__name__}_trip_date_time") or
        not is_entity_available(f"input_datetime.{__name__}_trip_homecoming_date_time")):
            return False
        
    if get_trip_range() == 0.0 and get_trip_target_level() == 0.0:
            return False
        
    if get_trip_date_time() == resetDatetime() or get_trip_homecoming_date_time() == resetDatetime():
            return False
    return True

def fill_up_charging_enabled():
    if get_state(f"input_boolean.{__name__}_fill_up") == "on":
        return True

def workplan_charging_enabled():
    if get_state(f"input_boolean.{__name__}_workplan_charging") == "on":
        return True

def solar_charging_enabled():
    if is_solar_configured() and get_state(f"input_boolean.{__name__}_solar_charging") == "on":
        return True

def manual_charging_enabled():
    if get_state(f"input_boolean.{__name__}_allow_manual_charging_now") == "on":
        return True

def manual_charging_solar_enabled():
    if get_state(f"input_boolean.{__name__}_allow_manual_charging_solar") == "on":
        return True
    
def get_tariffs(hour, day_of_week):
    _LOGGER = globals()['_LOGGER'].getChild("tariffs")
    try:
        if CONFIG['prices']['entity_ids']['power_prices_entity_id'] not in state.names(domain="sensor"):
            raise Exception(f"{CONFIG['prices']['entity_ids']['power_prices_entity_id']} not loaded")
        
        power_prices_attr = get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id'])
        
        if "tariffs" not in power_prices_attr:
            raise Exception(f"tariffs not in {CONFIG['prices']['entity_ids']['power_prices_entity_id']}")
        
        attr = power_prices_attr["tariffs"]
        transmissions_nettarif = attr["additional_tariffs"]["transmissions_nettarif"]
        systemtarif = attr["additional_tariffs"]["systemtarif"]
        elafgift = attr["additional_tariffs"]["elafgift"]
        tariffs = attr["tariffs"][str(hour)]
        tariff_sum = sum([transmissions_nettarif, systemtarif, elafgift, tariffs])
        
        return {
            "transmissions_nettarif": transmissions_nettarif,
            "systemtarif": systemtarif,
            "elafgift": elafgift,
            "tariffs": tariffs,
            "tariff_sum": tariff_sum
        }
        
    except Exception as e:
        _LOGGER.error(f"get_raw_price(hour = {hour}, day_of_week = {day_of_week}): {e}")
        return {
                "transmissions_nettarif": 0.0,
                "systemtarif": 0.0,
                "elafgift": 0.0,
                "tariffs": 0.0,
                "tariff_sum": 0.0
            }

def get_solar_sell_price(set_entity_attr=False, get_avg_offline_sell_price=False):
    _LOGGER = globals()['_LOGGER'].getChild("get_solar_sell_price")
    
    if not is_solar_configured(): return 0.0
    
    day_of_week = getDayOfWeek()
    try:
        sell_price = float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price']))
        entity_price = sell_price
        
        if get_avg_offline_sell_price:
            if sell_price != -1.0:
                return sell_price
            
            location = sun.get_astral_location(hass)
            sunrise = location[0].sunrise(getTime()).replace(tzinfo=None).hour
            sunset = location[0].sunset(getTime()).replace(tzinfo=None).hour
            sell_price_list = []
            
            for hour in range(sunrise, sunset):
                sell_price_list.append(average(KWH_AVG_PRICES_DB['history_sell'][hour][day_of_week]))
                
            return average(sell_price_list)
        
        if CONFIG['prices']['entity_ids']['power_prices_entity_id'] not in state.names(domain="sensor"):
            raise Exception(f"{CONFIG['prices']['entity_ids']['power_prices_entity_id']} not loaded")
        
        price = get_state(CONFIG['prices']['entity_ids']['power_prices_entity_id'], float_type=True)
        
        tariff_dict = get_tariffs(getHour(), day_of_week)
        transmissions_nettarif = tariff_dict["transmissions_nettarif"]
        systemtarif = tariff_dict["systemtarif"]
        elafgift = tariff_dict["elafgift"]
        tariffs = tariff_dict["tariffs"]
        
        tariff_sum = tariff_dict["tariff_sum"]
        raw_price = price - tariff_sum
        
        energinets_network_tariff = SOLAR_SELL_TARIFF["energinets_network_tariff"]
        energinets_balance_tariff = SOLAR_SELL_TARIFF["energinets_balance_tariff"]
        solar_production_seller_cut = SOLAR_SELL_TARIFF["solar_production_seller_cut"]
        
        sell_tariffs = sum((solar_production_seller_cut, energinets_network_tariff, energinets_balance_tariff, transmissions_nettarif, systemtarif))
        solar_sell_price = raw_price - sell_tariffs
        
        if sell_price == -1.0:
            sell_price = round(solar_sell_price, 3)
        
        if set_entity_attr:
            attr_list = ["price", "transmissions_nettarif", "systemtarif", "elafgift", "tariffs", "tariff_sum", "raw_price", "sell_tariffs_overview", "transmissions_nettarif_", "systemtarif_", "energinets_network_tariff_", "energinets_balance_tariff_", "solar_production_seller_cut_", "sell_tariffs", "solar_sell_price", "fixed_sell_price"]
            entity_attr = get_attr(f"sensor.{__name__}_kwh_cost_price")
            for item in attr_list:
                if item in entity_attr:
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
            LOCAL_ENERGY_PRICES['solar_kwh_price'] = {
                "price": price,
                "transmissions_nettarif": transmissions_nettarif,
                "systemtarif": systemtarif,
                "elafgift": elafgift,
                "tariffs": tariffs,
                "tariff_sum": tariff_sum,
                "raw_price": raw_price,
                "sell_tariffs_overview": "",
                "transmissions_nettarif_": transmissions_nettarif,
                "systemtarif_": systemtarif,
                "energinets_network_tariff_": energinets_network_tariff,
                "energinets_balance_tariff_": energinets_balance_tariff,
                "solar_production_seller_cut_": solar_production_seller_cut,
                "sell_tariffs": sell_tariffs,
                "solar_sell_price": solar_sell_price,
            }
            if entity_price >= 0.0:
                set_attr(f"sensor.{__name__}_kwh_cost_price.fixed_sell_price", f"{sell_price:.3f} kr/kWh")
                LOCAL_ENERGY_PRICES['solar_kwh_price']['fixed_sell_price'] = sell_price
    except Exception as e:
        sell_price = None
        using_text = "default"
        try:
            sell_price = float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price']))
            if sell_price == -1.0:
                sell_price = average(KWH_AVG_PRICES_DB['history_sell'][getHour()][day_of_week])
                using_text = "database average"
        except Exception as e:
            pass
        
        if sell_price is None:
            sell_price = max(CONFIG['solar']['production_price'], 0.0)
            
        _LOGGER.error(f"Cant get solar sell price using {using_text} {sell_price}: {e}")
        
    return sell_price

def get_refund():
    _LOGGER = globals()['_LOGGER'].getChild("get_refund")
    try:
        return abs(CONFIG['prices']['refund'])
    except Exception as e:
        _LOGGER.warning(f"Cant get refund, using default 0.0: {e}")
        return 0.0

def get_current_hour_price():
    _LOGGER = globals()['_LOGGER'].getChild("get_current_hour_price")
    try:
        return float(get_state(f"sensor.{__name__}_kwh_cost_price", float_type=True))
    except Exception as e:
        _LOGGER.warning(f"Cant get current hour price, using default 0.0: {e}")
        return 0.0

def get_powerwall_kwh_price(kwh = None):
    _LOGGER = globals()['_LOGGER'].getChild("get_powerwall_kwh_price")
    global POWER_VALUES_DB, KWH_AVG_PRICES_DB, LOCAL_ENERGY_PRICES
    
    if not is_powerwall_configured():
        return 0.0
    
    def is_valid(data: dict, keys: list) -> bool:
        for key in keys:
            if key not in data or not isinstance(data[key], list) or len(data[key]) == 0:
                return False
        return True
    
    if kwh is None:
        kwh = CONFIG['solar']['powerwall_battery_size']
    
    if kwh <= 0.0:
        return get_solar_sell_price()

    def get_data_timestamp(data, timestamp):
        for item in data:
            if reset_time_to_hour(item[0]) == timestamp:
                return item[1]
        return 0.0

    timestamp = getTime()
    
    powerwall_kwh = []
    powerwall_total_cost = []
    kwh_price_list = []
    
    try:
        for i in range(CONFIG['database']['power_values_db_data_to_save']):
            for hour in range(1, 24):
                loop_timestamp = reset_time_to_hour(timestamp) - datetime.timedelta(hours=hour)
                
                data = POWER_VALUES_DB.setdefault(loop_timestamp.hour, {})
                
                if not is_valid(data, ["power_consumption_without_all_exclusion", "powerwall_charging_consumption", "powerwall_discharging_consumption", "solar_production"]):
                    continue
                
                power_consumption_without_all_exclusion_data = data["power_consumption_without_all_exclusion"]
                powerwall_charging_consumption_data = data["powerwall_charging_consumption"]
                solar_production_data = data["solar_production"]
                
                power_consumption_without_all_exclusion = get_data_timestamp(power_consumption_without_all_exclusion_data, loop_timestamp) / 1000.0
                powerwall_charging_consumption = get_data_timestamp(powerwall_charging_consumption_data, loop_timestamp) / 1000.0
                solar_production = get_data_timestamp(solar_production_data, loop_timestamp) / 1000.0
                
                if None in (power_consumption_without_all_exclusion,
                            powerwall_charging_consumption,
                            solar_production):
                    continue
                
                solar_available_production = max(solar_production - power_consumption_without_all_exclusion, 0.0)
                if powerwall_charging_consumption > 0.0  and sum(powerwall_kwh) < kwh:
                    kwh_price = KWH_AVG_PRICES_DB['history_sell'][hour][getDayOfWeek(loop_timestamp)][i] if solar_available_production > 0 else KWH_AVG_PRICES_DB['history'][hour][getDayOfWeek(loop_timestamp)][i]
                    kwh_price_list.append(kwh_price)
                    powerwall_kwh.append(powerwall_charging_consumption)
                    powerwall_total_cost.append(powerwall_charging_consumption * kwh_price)
    except Exception as e:
        _LOGGER.error(f"Error getting powerwall kWh price: {e}")
        return get_solar_sell_price()
    
    if powerwall_kwh:
        LOCAL_ENERGY_PRICES['powerwall_kwh_price'] = {
            "powerwall_kwh": powerwall_kwh,
            "powerwall_total_cost": powerwall_total_cost,
            "kwh_price_list": kwh_price_list,
            "kr_per_kwh": sum(powerwall_total_cost) / sum(powerwall_kwh) if sum(powerwall_kwh) > 0.0 else 0.0
        }
        
    powerwall_kwh = sum(powerwall_kwh)
    powerwall_total_cost = sum(powerwall_total_cost)
    
    return powerwall_total_cost / powerwall_kwh if powerwall_kwh > 0.0 else 0.0

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
    
def distance_per_percentage():
    _LOGGER = globals()['_LOGGER'].getChild("distance_per_percentage")
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
            ema = round(calculate_ema(reverse_list(get_list_values(KM_KWH_EFFICIENCY_DB))),2)
            #ema = round(average(get_list_values(KM_KWH_EFFICIENCY_DB)),2)
            if ema == 0.0:
                raise Exception(f"ema is invalid: {ema}")
            output = km_kwh_to_km_percentage(ema)
            _LOGGER.debug(f"ema_km/kwh:{ema} km_kwh_to_km_percentage({ema})={output}")
        except Exception as e:
            _LOGGER.warning(f"Using default value 3.0: {e}")
    return output

def calc_distance_to_battery_level(distance):
    return distance / distance_per_percentage()

def calc_battery_level_to_distance(battery_level):
    return battery_level * distance_per_percentage()

def ev_power_connected():
    if not is_ev_configured():
        return True
    
    if not is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']) and not is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']):
        return True
    
    return get_state(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']) in EV_PLUGGED_STATES or get_state(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']) in EV_PLUGGED_STATES
    
def wake_up_ev():
    _LOGGER = globals()['_LOGGER'].getChild("wake_up_ev")
    global LAST_WAKE_UP_DATETIME
    
    if not is_ev_configured(): return
    
    if minutesBetween(LAST_WAKE_UP_DATETIME, getTime()) <= 14:
        _LOGGER.info(f"Wake up call already called")
        return
    
    if is_entity_available(CONFIG['ev_car']['entity_ids']['last_update_entity_id']):
        last_update = get_state(CONFIG['ev_car']['entity_ids']['last_update_entity_id'], error_state=resetDatetime())
        
        if minutesBetween(last_update, getTime()) <= 14:
            _LOGGER.info(f"Ev already updated, skipping wake up call")
            return

    LAST_WAKE_UP_DATETIME = getTime()
    
    if is_entity_configured(CONFIG['ev_car']['entity_ids']['wake_up_entity_id']):
        entity_id = CONFIG['ev_car']['entity_ids']['wake_up_entity_id']
        domain = entity_id.split(".")[0]
        
        if not allow_command_entity_integration(entity_id, "wake_up_ev()", check_only=True):
            _LOGGER.warning(f"Limit reached, cant wake up ev")
            return

        allow_command_entity_integration(entity_id, "wake_up_ev()")
        
        _LOGGER.info("Waking up car")

        if domain == "button":
            button.press(entity_id=entity_id)
        elif domain == "input_button":
            input_button.press(entity_id=entity_id)
    else:
        integration = get_integration(CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id'])
        
        if integration == "kia_uvo" and service.has_service(integration, "force_update"):
            if allow_command_entity_integration("Wake Up service","wake_up_ev()", integration = integration, check_only=True):
                allow_command_entity_integration("Wake Up service","wake_up_ev()", integration = integration)
                service.call(integration, "force_update", blocking=True)
            else:
                _LOGGER.warning(f"Limit reached, cant wake up ev")
    
def send_command(entity_id, command, force = False):
    _LOGGER = globals()['_LOGGER'].getChild("send_command")
    
    if not is_entity_available(entity_id): return
    
    if TESTING:
        _LOGGER.info(f"TESTING: Not sending command: {entity_id} {command}")
        return
    
    current_state = get_state(entity_id)
    try:
       current_state = float(current_state)
       command = float(command)
    except:
        pass
    
    if current_state != command or force:
        if not allow_command_entity_integration(entity_id, command, check_only=True) and not force:
            _LOGGER.warning(f"Limit reached, cant send command to ev {entity_id}: {command}")
            return
        
        allow_command_entity_integration(entity_id, command)
        
        _LOGGER.debug(f"Sending command: {entity_id} {command}")
        set_state(entity_id, command)
    else:
        _LOGGER.debug(f"Ignoring command {entity_id} state already: {command}")
        
def ev_send_command(entity_id, command, force = False): #TODO Add start/stop service for EVs
    _LOGGER = globals()['_LOGGER'].getChild("ev_send_command")
    
    if not is_ev_configured(): return
    
    if not is_entity_available(entity_id): return
    
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

    if entity_id == CONFIG["ev_car"]["entity_ids"]["charging_limit_entity_id"] and is_entity_configured(entity_id):
        integration = get_integration(entity_id)
        
        if integration is None and entity_id.split(".")[0] in ("input_number", "input_select", "input_boolean", "input_text", "input_datetime"):
            integration = entity_id.split(".")[0]
        
        if integration is not None and integration in ENTITY_INTEGRATION_DICT["supported_integrations"]:
            charging_limit_list = []
            for item in ENTITY_INTEGRATION_DICT["commands_last_hour"][integration]:
                if CONFIG["ev_car"]["entity_ids"]["charging_limit_entity_id"] in item[1]:
                    charging_limit_list.append(float(item[1].split(": ")[1]))
            
            if charging_limit_list:
                charging_limit_max = max(charging_limit_list)
                
                if charging_limit_max > command:
                    _LOGGER.warning(f"Trying to set charging limit, to lower value to often, using max value")
                    command = charging_limit_max
                        
    if current_state != command or force:
        '''if entity_id == CONFIG['ev_car']['entity_ids']['charge_switch_entity_id'] and command == "on":
            wake_up_ev()'''
    
        if not allow_command_entity_integration(entity_id, command, check_only=True) and not force:
            _LOGGER.warning(f"Limit reached, cant send command to ev {entity_id}: {command}")
            return
        
        allow_command_entity_integration(entity_id, command)
        
        _LOGGER.debug(f"Sending command: {entity_id} {command}")
        set_state(entity_id, command)
    else:
        _LOGGER.debug(f"Ignoring command {entity_id} state already: {command}")
        
def peak_battery_level_after_last_plug():
    _LOGGER = globals()['_LOGGER'].getChild("peak_battery_level_after_last_plug")
    
    max_battery_level = 0.0
    
    try:
        if not is_charger_configured():
            return 0.0
        
        to_time_stamp = getTime() - datetime.timedelta(minutes=1)
        from_time_stamp = to_time_stamp - datetime.timedelta(days=7)
        
        status_dict = get_values(CONFIG['charger']['entity_ids']['status_entity_id'], from_time_stamp, to_time_stamp, include_timestamps=True, error_state={})
        
        last_connected = None
        for ts in sorted(status_dict.keys(), reverse=True):
            value = status_dict[ts]
            if value in CHARGER_NOT_READY_STATUS:
                break
            elif value in CHARGER_READY_STATUS:
                last_connected = ts
        
        if last_connected is None:
            return 0.0
        
        ev_entity_id = CONFIG['ev_car']['entity_ids']['usable_battery_level_entity_id'] if is_ev_configured() else f"input_number.{__name__}_battery_level"
        from_time_stamp = last_connected
        
        max_battery_level = max(get_values(ev_entity_id, from_time_stamp, to_time_stamp, error_state=[]), default=0.0)
    except Exception as e:
        _LOGGER.error(f"peak_battery_level_after_last_plug(): {e}")
        
    return max_battery_level

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
        distance = distance_per_percentage() * battery_level()
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
    
def is_battery_fully_charged():
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
        error_message = f"Cant load {__name__}_drive_efficiency_db: {e}"
        _LOGGER.error(error_message)
        save_error_to_file(error_message, caller_function_name = "load_drive_efficiency()")
        my_persistent_notification(error_message, f"{TITLE} warning", persistent_notification_id=f"{__name__}_load_drive_efficiency")
    
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
    _LOGGER = globals()['_LOGGER'].getChild("set_state_drive_efficiency")
    if not is_ev_configured(): return
    
    try:
        drive_efficiency = get_list_values(DRIVE_EFFICIENCY_DB)
        
        if not drive_efficiency:
            _LOGGER.warning("DRIVE_EFFICIENCY_DB is empty or contains no valid float values.")
            return
        
        set_state(f"sensor.{__name__}_drive_efficiency", drive_efficiency[0])
        set_attr(f"sensor.{__name__}_drive_efficiency.ema", float(calculate_ema(reverse_list(drive_efficiency))))
        set_attr(f"sensor.{__name__}_drive_efficiency.mean", float(average(drive_efficiency)))
        
        for item in get_attr(f"sensor.{__name__}_drive_efficiency"):
            if "dato" in item:
                state.delete(f"sensor.{__name__}_drive_efficiency.{item}")

        for i, item in enumerate(DRIVE_EFFICIENCY_DB):
            try:
                set_attr(f"sensor.{__name__}_drive_efficiency.dato_{item[0]}", round(item[1], 2))
            except:
                set_attr(f"sensor.{__name__}_drive_efficiency.dato_{i}", round(item, 2))
    except Exception as e:
        _LOGGER.error(f"Cant set drive efficiency: {e}")

def load_km_kwh_efficiency():
    _LOGGER = globals()['_LOGGER'].getChild("load_km_kwh_efficiency")
    global KM_KWH_EFFICIENCY_DB
    
    if not is_ev_configured(): return
    
    try:
        create_yaml(f"{__name__}_km_kwh_efficiency_db", db=KM_KWH_EFFICIENCY_DB)
        KM_KWH_EFFICIENCY_DB = load_yaml(f"{__name__}_km_kwh_efficiency_db")
    except Exception as e:
        error_message = f"Cant load {__name__}_km_kwh_efficiency_db: {e}"
        _LOGGER.error(error_message)
        save_error_to_file(error_message, caller_function_name = "load_km_kwh_efficiency()")
        my_persistent_notification(error_message, f"{TITLE} warning", persistent_notification_id=f"{__name__}_load_km_kwh_efficiency")
    
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

    if not is_ev_configured():
        return

    try:
        km_kwh_efficiency = get_list_values(KM_KWH_EFFICIENCY_DB)
        value = km_kwh_efficiency[0] if km_kwh_efficiency else 3.0

        set_state(f"sensor.{__name__}_km_per_kwh", round(value, 2))

        if km_kwh_efficiency:
            km_kwh_ema = round(float(calculate_ema(reverse_list(km_kwh_efficiency))), 2)
            wh_km_ema = round(1000 / km_kwh_ema, 2)
            set_attr(f"sensor.{__name__}_km_per_kwh.ema", f"{km_kwh_ema:.2f} km/kWh - {wh_km_ema:.2f} Wh/km")
            
            km_kwh_mean = round(float(average(km_kwh_efficiency)), 2)
            wh_km_mean = round(1000 / km_kwh_mean, 2)
            set_attr(f"sensor.{__name__}_km_per_kwh.mean", f"{km_kwh_mean:.2f} km/kWh - {wh_km_mean:.2f} Wh/km")

        existing_attributes = get_attr(f"sensor.{__name__}_km_per_kwh") or {}
        for item in existing_attributes:
            if "dato" in item:
                state.delete(f"sensor.{__name__}_km_per_kwh.{item}")

        for i, item in enumerate(KM_KWH_EFFICIENCY_DB):
            try:
                km_kwh = round(item[1], 2)
                wh_km = round(1000 / km_kwh, 2)
                set_attr(f"sensor.{__name__}_km_per_kwh.dato_{item[0]}", f"{km_kwh:.2f} km/kWh - {wh_km:.2f} Wh/km")
            except (IndexError, TypeError):
                km_kwh = round(item, 2)
                wh_km = round(1000 / km_kwh, 2)
                set_attr(f"sensor.{__name__}_km_per_kwh.dato_{i}", f"{km_kwh:.2f} km/kWh - {wh_km:.2f} Wh/km")

        set_estimated_range()

    except Exception as e:
        _LOGGER.error(f"Cant set km/kwh efficiency: {e}", exc_info=True)
        my_persistent_notification(
            f"Cant set km/kwh efficiency: {e}",
            f"{TITLE} warning",
            persistent_notification_id=f"{__name__}_set_state_km_kwh_efficiency"
        )

def set_estimated_range():
    _LOGGER = globals()['_LOGGER'].getChild("set_estimated_range")
    
    if not is_ev_configured():
        return
    
    try:
        efficiency_values = get_list_values(KM_KWH_EFFICIENCY_DB)

        if not efficiency_values:
            _LOGGER.warning("KM_KWH_EFFICIENCY_DB is empty or contains no valid float values.")
            return

        ema_efficiency = float(calculate_ema(reverse_list(efficiency_values)))
        range_per_percentage = km_kwh_to_km_percentage(ema_efficiency)

        if range_per_percentage <= 0:
            _LOGGER.warning("Calculated range_per_percentage is not valid (<= 0). Skipping update.")
            return

        battery_lvl = battery_level()
        range_at_battery_level = round(range_per_percentage * battery_lvl, 2)
        range_total = round(range_per_percentage * 100.0, 2)

        set_attr(f"input_number.{__name__}_trip_range_needed.max", round(range_total + 100.0, 0))

        set_state(f"sensor.{__name__}_estimated_range", range_at_battery_level)
        set_attr(f"sensor.{__name__}_estimated_range.total", range_total)

    except Exception as e:
        _LOGGER.error(f"Cant set estimated range: {e}", exc_info=True)
        my_persistent_notification(
            f"Cant set estimated range: {e}",
            f"{TITLE} warning",
            persistent_notification_id=f"{__name__}_estimated_range"
        )
        
def set_last_drive_efficiency_attributes(kilometers, usedkWh, used_battery, cost, efficiency, distance_per_kWh, wh_km):
    if not is_ev_configured(): return
    
    sensor_list = ["_drive_efficiency", "_km_per_kwh", "_estimated_range"]
    for sensor in sensor_list:
        try:
            set_attr(f"sensor.{__name__}{sensor}.last_drive_distance", f"{round(kilometers, 1)}km")
            set_attr(f"sensor.{__name__}{sensor}.last_drive_used", f"{round(usedkWh, 2)}kWh ({round(used_battery,1)}%)")
            set_attr(f"sensor.{__name__}{sensor}.last_drive_cost", f"{round(cost, 2)}kr")
            set_attr(f"sensor.{__name__}{sensor}.last_drive_efficiency", f"{round(efficiency, 1)}% {round(distance_per_kWh, 2)} km/kWh ({wh_km} Wh/km)")
        except Exception as e:
            _LOGGER.error(f"Error setting sensor attributes for sensor.{__name__}{sensor}: {e}")

def drive_efficiency_save_car_stats(bootup=False):
    _LOGGER = globals()['_LOGGER'].getChild("drive_efficiency_save_car_stats")
    def set_last_odometer():
        odometer_value = float(get_state(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], float_type=True, error_state="unknown"))
        set_state(f"sensor.{__name__}_drive_efficiency_last_odometer", odometer_value)
        
    def set_last_battery_level():
        peak_battery_level = max(battery_level(), peak_battery_level_after_last_plug())
        set_state(f"sensor.{__name__}_drive_efficiency_last_battery_level", peak_battery_level)
        
        attr_list = get_attr(f"sensor.{__name__}_drive_efficiency_last_battery_level") or {}
        for item in attr_list:
            state.delete(f"sensor.{__name__}_drive_efficiency_last_battery_level.{item}")
                
        set_attr(f"sensor.{__name__}_drive_efficiency_last_battery_level.battery_level_expenses_cost", BATTERY_LEVEL_EXPENSES['battery_level_expenses_cost'])
        set_attr(f"sensor.{__name__}_drive_efficiency_last_battery_level.battery_level_expenses_kwh", BATTERY_LEVEL_EXPENSES['battery_level_expenses_kwh'])
        set_attr(f"sensor.{__name__}_drive_efficiency_last_battery_level.battery_level_expenses_percentage", BATTERY_LEVEL_EXPENSES['battery_level_expenses_percentage'])
        set_attr(f"sensor.{__name__}_drive_efficiency_last_battery_level.battery_level_expenses_solar_percentage", BATTERY_LEVEL_EXPENSES['battery_level_expenses_solar_percentage'])
        set_attr(f"sensor.{__name__}_drive_efficiency_last_battery_level.battery_level_expenses_unit", BATTERY_LEVEL_EXPENSES['battery_level_expenses_unit'])
        
    
    if bootup:
        if is_ev_configured() and get_state(f"sensor.{__name__}_drive_efficiency_last_odometer", try_history=False) in ENTITY_UNAVAILABLE_STATES:
            _LOGGER.info("Setting last odometer")
            set_last_odometer()
            
        if get_state(f"sensor.{__name__}_drive_efficiency_last_battery_level", try_history=False) in ENTITY_UNAVAILABLE_STATES:
            _LOGGER.info("Setting last battery level")
            set_last_battery_level()
    else:
        if is_ev_configured():
            set_last_odometer()
        set_last_battery_level()
    
def drive_efficiency(state=None):
    _LOGGER = globals()['_LOGGER'].getChild("drive_efficiency")
    global DRIVE_EFFICIENCY_DB, KM_KWH_EFFICIENCY_DB, PREHEATING, LAST_DRIVE_EFFICIENCY_DATA
    
    state = str(state).lower()
    
    heating_states = ("preheat", "preheat_cancel")
    states = tuple(chain(EV_PLUGGED_STATES, EV_UNPLUGGED_STATES, heating_states))
    
    if state not in states:
        _LOGGER.warning(f"Ignoring state not in {states}: {state}")
        return
        
    try:
        if state == "preheat":
            drive_efficiency_save_car_stats()
            PREHEATING = True
            return
        elif state == "preheat_cancel":
            PREHEATING = False
            return

        if state in EV_UNPLUGGED_STATES:
            if not PREHEATING:
                drive_efficiency_save_car_stats()
            PREHEATING = False
        elif state in EV_PLUGGED_STATES:
            if not is_ev_configured():
                distancePerkWh = km_percentage_to_km_kwh(distance_per_percentage())
                efficiency = 100.0
                kilometers = 0.0
                
                last_battery_level = float(get_state(f"sensor.{__name__}_drive_efficiency_last_battery_level", float_type=True, error_state=battery_level()))
                
                usedBattery = last_battery_level - battery_level()
                usedkWh = percentage_to_kwh(usedBattery)
                
                if usedkWh == 0.0 or usedBattery == 0.0:
                    _LOGGER.warning("Used kWh or Used Battery is 0.0, ignoring drive")
                    return
                
            else:
                if not DRIVE_EFFICIENCY_DB:
                    load_drive_efficiency()
                if not KM_KWH_EFFICIENCY_DB:
                    load_km_kwh_efficiency()
                    
                if not is_entity_available(f"sensor.{__name__}_drive_efficiency_last_odometer"):
                    raise Exception(f"sensor.{__name__}_drive_efficiency_last_odometer is not available, ignoring drive")
                if not is_entity_available(f"sensor.{__name__}_drive_efficiency_last_battery_level"):
                    raise Exception(f"sensor.{__name__}_drive_efficiency_last_battery_level is not available, ignoring drive")
                if not is_entity_available(CONFIG['ev_car']['entity_ids']['odometer_entity_id']):
                    raise Exception(f"{CONFIG['ev_car']['entity_ids']['odometer_entity_id']} is not available, ignoring drive")

                current_odometer = float(get_state(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], float_type=True, try_history=True))
                last_odometer = float(get_state(f"sensor.{__name__}_drive_efficiency_last_odometer", float_type=True, error_state=current_odometer))
                last_battery_level = float(get_state(f"sensor.{__name__}_drive_efficiency_last_battery_level", float_type=True, error_state=battery_level()))
                
                if not is_ev_configured() and last_battery_level == 0.0:
                    last_battery_level = get_max_recommended_charge_limit_battery_level() - battery_level()
                    _LOGGER.warning(f"Last battery level is 0.0, recalculating from current battery level ({get_max_recommended_charge_limit_battery_level()} - {battery_level()} = {last_battery_level})")

                usedBattery = last_battery_level - battery_level()
                kilometers = current_odometer - last_odometer
                usedkWh = percentage_to_kwh(usedBattery)

                if usedkWh == 0.0 or usedBattery == 0.0:
                    _LOGGER.warning("Used kWh or Used Battery is 0.0, ignoring drive")
                    return

                distancePerkWh = kilometers / usedkWh
                distancePerPercentage = kilometers / usedBattery
                cars_distance_per_percentage = round(battery_range() / battery_level(), 2)
                efficiency = abs(round((distancePerPercentage / cars_distance_per_percentage) * 100.0, 2))

                _LOGGER.info(f"distancePerPercentage {kilometers} / {usedBattery} = {distancePerPercentage}")
                _LOGGER.info(f"distancePerkWh {kilometers} / {usedkWh} = {distancePerkWh}")
                _LOGGER.info(f"cars_distance_per_percentage {battery_range()} / {battery_level()} = {cars_distance_per_percentage}")
                _LOGGER.info(f"efficiency {kilometers} / {usedBattery} = {efficiency}")

                _LOGGER.debug(
                    f"battery_range(): {battery_range()} battery_level(): {battery_level()} "
                    f"usedBattery: {usedBattery} kilometers: {kilometers} usedkWh: {usedkWh} "
                    f"cars_distance_per_percentage: {cars_distance_per_percentage} distancePerkWh: {distancePerkWh} efficiency: {efficiency}%"
                )

                if kilometers <= 10.0 or usedBattery <= 5.0:
                    _LOGGER.warning(f"{kilometers}km <= 10.0 or {usedBattery} usedBattery <= 5.0, ignoring drive")
                    return

                if efficiency > 150.0:
                    _LOGGER.warning(
                        f"Efficiency too high: {efficiency}%. Ignoring. "
                        f"UsedBattery: {usedBattery}, usedkWh: {usedkWh}, kilometers: {kilometers} "
                        f"(start odometer: {last_odometer}, end odometer: {current_odometer})"
                    )
                    return

                DRIVE_EFFICIENCY_DB.insert(0, [getTime(), efficiency])
                DRIVE_EFFICIENCY_DB = DRIVE_EFFICIENCY_DB[:CONFIG['database']['drive_efficiency_db_data_to_save']]
                save_drive_efficiency()

                KM_KWH_EFFICIENCY_DB.insert(0, [getTime(), distancePerkWh])
                KM_KWH_EFFICIENCY_DB = KM_KWH_EFFICIENCY_DB[:CONFIG['database']['km_kwh_efficiency_db_data_to_save']]
                save_km_kwh_efficiency()
            
            cost_str = ""
            cost = 0.0
            
            if "battery_level_expenses_unit" in BATTERY_LEVEL_EXPENSES and BATTERY_LEVEL_EXPENSES['battery_level_expenses_unit'] is not None:
                unit = BATTERY_LEVEL_EXPENSES['battery_level_expenses_unit']
                cost = round(unit * usedkWh, 2)
                cost_str = f"Pris: {cost:.2f}kr\n"
            
            wh_km = round(1000 / distancePerkWh, 2)
            
            LAST_DRIVE_EFFICIENCY_DATA = {
                "timestamp": getTime(),
                "distance": kilometers,
                "usedkWh": usedkWh,
                "usedBattery": usedBattery,
                "cost": cost,
                "efficiency": efficiency,
                "distancePerkWh": distancePerkWh,
                "wh_km": wh_km
            }
            
            if CONFIG['notification']['efficiency_on_cable_plug_in']:
                my_notify(message = f"""
                        Kilometer: {round(kilometers, 1)}km
                        Brugt: {round(usedkWh, 2)}kWh ({round(usedBattery,1)}%)
                        {cost_str}
                        Kørsel effektivitet: {round(efficiency, 1)}%
                        {round(distancePerkWh, 2)} km/kWh ({wh_km} Wh/km)
                        """, title = f"{TITLE} Sidste kørsel effektivitet", notify_list = CONFIG['notify_list'], admin_only = False, always = True)
                
                
            set_last_drive_efficiency_attributes(kilometers, usedkWh, usedBattery, cost, efficiency, distancePerkWh, wh_km)
    except Exception as e:
        _LOGGER.error(f"Error in drive_efficiency: {e}")
        my_persistent_notification(
            f"Error in drive_efficiency:\n{e}",
            f"{TITLE} warning",
            persistent_notification_id=f"{__name__}_drive_efficiency"
        )

def range_to_battery_level(extraRange=None, batteryBuffer=None, date=None):
    _LOGGER = globals()['_LOGGER'].getChild("range_to_battery_level")

    minRangeInBatteryLevel = get_min_charge_limit_battery_level()
    extraRange = extraRange if extraRange is not None else get_entity_daily_distance(day_text=None, date=date)
    batteryBuffer = batteryBuffer if batteryBuffer is not None else get_min_daily_battery_level()

    try:
        if not isinstance(extraRange, (int, float)):
            raise ValueError(f"extraRange should be a number, but got: {extraRange}")

        minRangeInBatteryLevel = round_up(calc_distance_to_battery_level(extraRange)) + batteryBuffer
        _LOGGER.debug(f"extraRange: {extraRange}, minRangeInBatteryLevel: {minRangeInBatteryLevel}")

    except Exception as e:
        _LOGGER.error(
            f"Error calculating battery level - extraRange: {extraRange}, batteryBuffer: {batteryBuffer}, "
            f"minRangeInBatteryLevel: {minRangeInBatteryLevel}: {e}"
        )

    return min(minRangeInBatteryLevel, 100.0)

def kwh_needed_for_charging(targetLevel=None, battery=None):
    _LOGGER = globals()['_LOGGER'].getChild("kwh_needed_for_charging")

    targetLevel = targetLevel if targetLevel is not None else get_min_daily_battery_level()
    battery = battery if battery is not None else battery_level()

    kwh = percentage_to_kwh(targetLevel - battery, include_charging_loss=True)
    _LOGGER.debug(f"targetLevel:{targetLevel} battery:{battery} kwh:{kwh} without loss kwh:{percentage_to_kwh(targetLevel - battery, include_charging_loss=True)}")

    return max(kwh, 0.0)

def verify_charge_limit(limit):
    _LOGGER = globals()['_LOGGER'].getChild("verify_charge_limit")

    if not is_entity_configured(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id']):
        return limit

    try:
        integration = get_integration(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'])
        if integration in ('kia_uvo', 'cupra_we_connect'):
            limit = float(round_up(limit / 10) * 10)

        limit = min(max(limit, get_min_charge_limit_battery_level()), 100.0)

    except Exception as e:
        _LOGGER.error(f"Error verifying charge limit: {e}")
        limit = get_max_recommended_charge_limit_battery_level()

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
    
    def rename_key_recursive(data, old_key, new_key):
        renamed = False

        if isinstance(data, dict):
            if old_key in data:
                data[new_key] = data.pop(old_key)
                renamed = True
            for k, v in data.items():
                nested, changed = rename_key_recursive(v, old_key, new_key)
                data[k] = nested
                renamed = renamed or changed

        elif isinstance(data, list):
            for i, item in enumerate(data):
                data[i], changed = rename_key_recursive(item, old_key, new_key)
                renamed = renamed or changed

        return data, renamed
    
    try:
        create_yaml(f"{__name__}_charging_history_db", db=CHARGING_HISTORY_DB)
        CHARGING_HISTORY_DB = load_yaml(f"{__name__}_charging_history_db")
    except Exception as e:
        error_message = f"Cant load {__name__}_charging_history_db: {e}"
        _LOGGER.error(error_message)
        save_error_to_file(error_message, caller_function_name = "load_charging_history()")
        my_persistent_notification(error_message, f"{TITLE} error", persistent_notification_id=f"{__name__}_load_charging_history")
    
    if CHARGING_HISTORY_DB == {} or not CHARGING_HISTORY_DB:
        CHARGING_HISTORY_DB = {}
        save_charging_history()
    
    CHARGING_HISTORY_DB, renamed_kWh_solar = rename_key_recursive(CHARGING_HISTORY_DB, "kWh_solar", "kWh_from_local_energy")
    
    if renamed_kWh_solar:
        _LOGGER.info(f"Renamed key 'kWh_solar' to 'kWh_from_local_energy' in {__name__}_charging_history_db.yaml")
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
                my_persistent_notification(f"Cant add last charging session to CURRENT_CHARGING_SESSION: {e}", f"{TITLE} error", persistent_notification_id=f"{__name__}_load_charging_history")
    
    if is_entity_available(CONFIG['ev_car']['entity_ids']['odometer_entity_id']):
        now = getTime()
        added_odometer = False
        for key, value in CHARGING_HISTORY_DB.items():
            if "odometer" not in value:
                from_time_stamp = key
                to_time_stamp = from_time_stamp + datetime.timedelta(minutes=1)
                history_odometer = get_values(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], from_time_stamp, to_time_stamp, float_type=True, error_state=None)
                if history_odometer:
                    added_odometer = True
                    _LOGGER.info(f"Adding odometer to history key {key}: {int(min(history_odometer))} km")
                    CHARGING_HISTORY_DB[key]["odometer"] = int(min(history_odometer))
        if added_odometer:
            save_charging_history()
    
    set_state(f"sensor.{__name__}_charging_history", f"Brug Markdown kort med dette i: {{{{ states.sensor.{__name__}_charging_history.attributes.history }}}}")
    
    charging_history_combine_and_set(get_ending_byte_size=True if CHARGING_HISTORY_ENDING_BYTE_SIZE is None else False)
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
            error_message = f"Cant save {__name__}_charging_history_db: {e}"
            _LOGGER.error(error_message)
            save_error_to_file(error_message, caller_function_name = "save_charging_history()")
            my_persistent_notification(error_message, f"{TITLE} error", persistent_notification_id=f"{__name__}_save_charging_history")
        
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
                
                if len(sorted_keys) > 1:
                    for i in range(1, min(len(sorted_keys), 20)):
                        if hoursBetween(now, sorted_keys[i]) == 0 and getHour(now) == getHour(sorted_keys[i]):
                            start = sorted_keys[i]
                            
                            _LOGGER.info(f"Found another charging session in current hour {start}: {CHARGING_HISTORY_DB[start]}")
                            start_charger_meter = CHARGING_HISTORY_DB[start]["start_charger_meter"]
                            
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
                added_kwh_by_solar, solar_kwh_of_local_energy, powerwall_kwh_of_local_energy = calc_local_energy_kwh(getMinute(), added_kwh, solar_period_current_hour = True)
                added_percentage = kwh_to_percentage(added_kwh, include_charging_loss = True)
                price = calc_kwh_price(getMinute(), solar_period_current_hour = True)
                cost = added_kwh * price
                
                if added_kwh_by_solar > 0.0 or emoji_parse({'solar': True}) in emoji:
                    emoji = join_unique_emojis(emoji, emoji_parse({'solar': True}))
                else:
                    return False

                CHARGING_HISTORY_DB[start]["kWh"] = round(added_kwh, 3)
                CHARGING_HISTORY_DB[start]["kWh_from_local_energy"] = round(added_kwh_by_solar, 3)
                CHARGING_HISTORY_DB[start]["solar_kwh_of_local_energy"] = solar_kwh_of_local_energy
                CHARGING_HISTORY_DB[start]["powerwall_kwh_of_local_energy"] = powerwall_kwh_of_local_energy
                
                if len(emoji.split(" ")) > 1:
                    if solar_kwh_of_local_energy <= 0.0:
                        emojis = set(emoji.split(" "))
                        emojis.discard(emoji_parse({'solar': True}))
                        emoji = " ".join(emojis)
                        
                    if powerwall_kwh_of_local_energy <= 0.0:
                        emojis = set(emoji.split(" "))
                        emojis.discard(emoji_parse({'powerwall': True}))
                        emoji = " ".join(emojis)
                    
                CHARGING_HISTORY_DB[start]["percentage"] = round(added_percentage, 1)
                CHARGING_HISTORY_DB[start]["unit"] = round(price, 3)
                CHARGING_HISTORY_DB[start]["cost"] = round(cost, 3)
                CHARGING_HISTORY_DB[start]["emoji"] = emoji
                CHARGING_HISTORY_DB[start]["ended"] = ended
                CHARGING_HISTORY_DB[start]["start_charger_meter"] = start_charger_meter
                CHARGING_HISTORY_DB[start]["end_charger_meter"] = end_charger_meter
                
                if last_session != CHARGING_HISTORY_DB[start]:
                    _LOGGER.info(f"Last charging session to: {last_session}")
                    _LOGGER.info(f"Recalculated current hour charging sessions to: {CHARGING_HISTORY_DB[start]}")
                    _LOGGER.info(f"{pformat(CHARGING_HISTORY_DB[start], width=200, compact=True)}")
                    return True
            except Exception as e:
                _LOGGER.error(f"Cant calculate last charging session to CHARGING_HISTORY_DB({start}): {e}")
                my_persistent_notification(f"Cant calculate last charging session to CHARGING_HISTORY_DB({start}): {e}", f"{TITLE} error", persistent_notification_id=f"{__name__}_charging_history_recalc_price")
    return False

def charging_history_combine_and_set(get_ending_byte_size=False):
    _LOGGER = globals()['_LOGGER'].getChild("charging_history_combine_and_set")
    global CHARGING_HISTORY_DB, CHARGING_HISTORY_ENDING_BYTE_SIZE
    
    efficiency_adjustment = 1.15
    
    efficiency_factors = {
        1: 0.85,  # Januar
        2: 0.87,  # Februar
        3: 0.90,  # Marts
        4: 0.95,  # April
        5: 1.00,  # Maj
        6: 1.02,  # Juni
        7: 1.03,  # Juli
        8: 1.02,  # August
        9: 1.00,  # September
        10: 0.95, # Oktober
        11: 0.90, # November
        12: 0.87  # December
    }
    efficiency_factors = {month: factor * efficiency_adjustment for month, factor in efficiency_factors.items()}
    
    def calculate_estimated_km(kwh, efficiency_factors, month):
        try:
            efficiency_factor = efficiency_factors.get(month, 1.0)
            efficiency_factor_diff = 1.0 + (1.0 - efficiency_factor)
            
            km_per_kwh = float(get_state(f"sensor.{__name__}_km_per_kwh", float_type=True, error_state=0.0))
            
            try:
                km_per_kwh = get_attr(f"sensor.{__name__}_km_per_kwh", "mean", error_state=None)
                km_per_kwh = float(km_per_kwh.split(" ")[0])
            except (TypeError, AttributeError, ValueError):
                pass
            
            adjusted_km_per_kwh = km_per_kwh * efficiency_factor
            return round(kwh * adjusted_km_per_kwh, 1), True
        except Exception as e:
            _LOGGER.error(f"Error calculating estimated km: {e}")
            return 0.0, False
    
    history = []
    combined_db = {}
    
    if CHARGING_HISTORY_DB:
        total = {
            "cost": {"total": 0.0},
            "kwh": {"total": 0.0},
            "percentage": {"total": 0.0},
            "solar_kwh": {"total": 0.0},
            "charging_kwh_day": {"total": 0.0},
            "charging_kwh_night": {"total": 0.0},
            "km": {"total": 0.0},
            "odometer": {},
            "odometer_first_charge_datetime": None,
        }
        
        details = False
        
        length = 10
        sub_length = 50
        sub_details_count = 0
        
        current_history_bytes_size = 0
        max_entity_attributes_bytes_size = 16384
        history_bytes_buffer = 0 if CHARGING_HISTORY_ENDING_BYTE_SIZE is None else CHARGING_HISTORY_ENDING_BYTE_SIZE # Safe buffer bootup size
        
        max_history_bytes_size = max_entity_attributes_bytes_size - history_bytes_buffer
        history_to_big_anounced = False
        
        current_history_counter = 0
        max_history_length = 250
        #max_history_length -= length # Buffer to details
        
        skip_counter = 0
        solar_in_months = False
        sorted_db = sorted(CHARGING_HISTORY_DB.items(), key=lambda item: item[0], reverse=True)
        sorted_db_length = len(sorted_db)
        
        now = getTime()
        
        header = "| Tid |  | % | kWh | Pris |"
        align = "|:---:|:---|:---:|:---:|:---:|"
        add_header = False
        
        def history_loop_append(d):
            nonlocal history, current_history_bytes_size
            
            if isinstance(d, list):
                history.extend(d)
                current_history_bytes_size += len("\n".join(d).encode('utf-8'))
            else:
                history.append(d)
                current_history_bytes_size += len(d.encode('utf-8'))
        
        history_loop_append("<center>\n")
        history_loop_append(header)
        history_loop_append(align)
            
        for i, (when, data) in enumerate(sorted_db):
            if skip_counter == 0:
                if not history_to_big_anounced:
                    if current_history_bytes_size >= max_history_bytes_size:
                        history_to_big_anounced = True
                        history_loop_append("##### Home Assistant tillader ikke at vise mere historik")
                    elif current_history_counter == length and not details:
                        details = True
                        history_loop_append([
                            "<details>",
                            "<summary><b>Se mere historik</b></summary>\n"
                        ])
                        add_header = True
                    elif current_history_bytes_size < max_history_bytes_size - 1 and current_history_counter > length and current_history_counter >= sub_length and current_history_counter % sub_length == 0 and (len(CHARGING_HISTORY_DB) - i) >= sub_length: # and current_history_counter <= max_history_length:
                        history_loop_append([
                            "\n",
                            "<details>",
                            "<summary><b>Se mere historik</b></summary>\n"
                        ])
                        sub_details_count += 1
                        add_header = True
                
                started = when
                charging_session = data["charging_session"] if "charging_session" in data else None
                ended = data['ended']
                emoji = data['emoji']
                percentage = data['percentage']
                kWh = data["kWh"]
                kWh_from_local_energy = data.get("kWh_from_local_energy", 0.0)
                solar_kwh_of_local_energy = data.get("solar_kwh_of_local_energy", 0.0)
                powerwall_kwh_of_local_energy = data.get("powerwall_kwh_of_local_energy", 0.0)
                cost = data['cost']
                unit = data['unit']
                start_charger_meter = None
                end_charger_meter = None
                odometer = None
                
                if "start_charger_meter" in data and "end_charger_meter" in data:
                    start_charger_meter = data["start_charger_meter"]
                    end_charger_meter = data["end_charger_meter"]
                    
                if "odometer" in data:
                    odometer = data["odometer"]
                    
                    month = getMonthFirstDay(when)
                    if not total["odometer_first_charge_datetime"]:
                        total["odometer_first_charge_datetime"] = when
                    else:
                        total["odometer_first_charge_datetime"] = min(total["odometer_first_charge_datetime"], when)
                
                from_to = "-"
                
                combine_after = 5
                
                if i > combine_after and ended != ">":
                    charging_session = None
                    
                    for x in range(i+1, sorted_db_length+1):
                        if x+1 <= sorted_db_length:
                            next_when, next_data = sorted_db[x]
                            if daysBetween(when, now) > 7:
                                if daysBetween(when, next_when) == 0:
                                    emoji = join_unique_emojis(emoji, next_data['emoji'])
                                else:
                                    break
                            else:
                                if daysBetween(when, next_when) == 0 and hoursBetween(when, next_when) <= 1 and emoji == next_data['emoji']:
                                    pass
                                else:
                                    break
                                
                            started = next_when
                            percentage += next_data['percentage']
                            kWh += next_data["kWh"]
                            kWh_from_local_energy += next_data.get("kWh_from_local_energy", 0.0)
                            solar_kwh_of_local_energy += next_data.get("solar_kwh_of_local_energy", 0.0)
                            powerwall_kwh_of_local_energy += next_data.get("powerwall_kwh_of_local_energy", 0.0)
                            cost += next_data['cost']
                            if kWh > 0.0:
                                unit = cost / kWh
                            
                            if "start_charger_meter" in next_data:
                                start_charger_meter = next_data["start_charger_meter"]
                            
                            if "odometer" in next_data:
                                if odometer:
                                    odometer = min(odometer, next_data["odometer"])
                                
                            skip_counter += 1
                        else:
                            break
                
                emoji = emoji_sorting(emoji)
                
                if len(emoji.split(" ")) > 1:
                    if solar_kwh_of_local_energy <= 0.0:
                        emojis = set(emoji.split(" "))
                        emojis.discard(emoji_parse({'solar': True}))
                        emoji = " ".join(emojis)
                        
                    if powerwall_kwh_of_local_energy <= 0.0:
                        emojis = set(emoji.split(" "))
                        emojis.discard(emoji_parse({'powerwall': True}))
                        emoji = " ".join(emojis)
                
                combined_db[started] = {
                    "cost": round(cost, 3),
                    "emoji": emoji,
                    "ended": ended,
                    "kWh": round(kWh, 3),
                    "kWh_from_local_energy": round(kWh_from_local_energy, 3),
                    "solar_kwh_of_local_energy": round(solar_kwh_of_local_energy, 3),
                    "powerwall_kwh_of_local_energy": round(powerwall_kwh_of_local_energy, 3),
                    "percentage": round(percentage, 1),
                    "unit": round(unit, 3)
                }
                
                if start_charger_meter is not None and end_charger_meter is not None:
                    combined_db[started]["start_charger_meter"] = start_charger_meter
                    combined_db[started]["end_charger_meter"] = end_charger_meter
                    
                if odometer is not None:
                    combined_db[started]["odometer"] = odometer
                
                if charging_session:
                    combined_db[started]["charging_session"] = charging_session
                
                if current_history_bytes_size < max_history_bytes_size: #current_history_counter <= max_history_length and current_history_bytes_size <= max_history_bytes_size
                    if add_header:
                        add_header = False
                        
                        history_loop_append([
                            header,
                            align
                        ])
                    
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
                    
                    history_loop_append(f"| {started}{from_to}{ended} | {emoji} | {percentage} | {kWh} | {cost} ({unit}) |")
                    
                    current_history_counter += 1
            else:
                skip_counter = max(skip_counter - 1, 0)
                
            if current_history_counter > length and (len(CHARGING_HISTORY_DB) - i) == 1:
                history_loop_append(["</details>", "\n"] * (sub_details_count + 1))
            
            month = getMonthFirstDay(when)
            
            if month not in total['cost']:
                total['cost'][month] = 0.0
                total['kwh'][month] = 0.0
                total['percentage'][month] = 0.0
                total['solar_kwh'][month] = 0.0
                total['charging_kwh_day'][month] = 0.0
                total['charging_kwh_night'][month] = 0.0
                total['km'][month] = 0.0
                
            total['cost'][month] += data['cost']
            total['kwh'][month] += data["kWh"]
            total['percentage'][month] += data['percentage']
            
            if is_day(when):
                total['charging_kwh_day'][month] += data["kWh"]
                total['charging_kwh_day']["total"] += data["kWh"]
            else:
                total['charging_kwh_night'][month] += data["kWh"]
                total['charging_kwh_night']["total"] += data["kWh"]
            
            if "kWh_from_local_energy" in data and data['kWh_from_local_energy'] > 0.0:
                total['solar_kwh'][month] += data['kWh_from_local_energy']
                total['solar_kwh']["total"] += data['kWh_from_local_energy']
                solar_in_months = True

            total['cost']["total"] += data['cost']
            total['kwh']["total"] += data["kWh"]
            total['percentage']["total"] += data['percentage']
            
            if "odometer" in data:
                if month not in total['odometer']:
                    total['odometer'][month] = data["odometer"]
                else:
                    total['odometer'][month] = min(total['odometer'][month], data["odometer"])
        
        if details:
            history.extend([
                "</details>",
                "\n"
            ])
        
        for month in total['odometer']:
            if add_months(month, 1) in total['odometer']:
                total['km'][month] = round(total['odometer'][add_months(month, 1)] - total['odometer'][month], 1)
            else:
                total['km'][month] = round(get_state(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], float_type=True, error_state=total['odometer'][month]) - total['odometer'][month], 1)
                
            total['km']['total'] += total['km'][month]
        
        estimated_values_used = False
        
        if CONFIG['ev_car']['entity_ids']['odometer_entity_id']:
            for month in total['km']:
                if month == "total":
                    continue
                
                estimated_km = 0.0
                if total['km'][month] == 0.0:
                    estimated_km, estimated_values_used = calculate_estimated_km(
                        total['kwh'].get(month, 0.0), efficiency_factors, month.month
                    )
                    total['km'][month] = estimated_km
                    total['km']['total'] += estimated_km
                elif month == getMonthFirstDay(total["odometer_first_charge_datetime"]):
                    kwh = sum([ value['kWh'] for key, value in CHARGING_HISTORY_DB.items() if getMonthFirstDay(key) == month and "odometer" not in value])
                    estimated_km, estimated_values_used = calculate_estimated_km(kwh, efficiency_factors, month.month)
                    total['km'][month] = total['km'][month] + estimated_km
                    total['km']['total'] += estimated_km
                
                km_kwh = 0.0
                wh_km = 0.0
                
                if total['km'][month] > 0.0 and total['kwh'][month] > 0.0:
                    km_kwh = round(total['km'][month] / total['kwh'][month], 2)
                    wh_km = round(1000 / km_kwh, 2) if km_kwh > 0.0 else 0.0
                    
                efficiency_label = f"{km_kwh:.1f}<br>({wh_km:.1f})" if km_kwh > 0.0 else ""
                total['km'][month] = [total['km'][month], f"{'~' if estimated_km > 0.0 else ''}{int(round(total['km'][month], 0))}", efficiency_label]
        else:
            for month in total['km']:
                if month == "total":
                    continue
                
                total['km'][month] = [total['km'][month], "", ""]
        
        if total['kwh']["total"] > 0.0:
            solar_string = ""
            if total['solar_kwh']["total"] > 0.0:
                total_solar_percentage = round(total['solar_kwh']["total"] / total['kwh']["total"] * 100.0, 1)
                solar_string = f" ({emoji_parse({'solar': True})}{total['solar_kwh']['total']:.1f}/{total_solar_percentage}%)"
                
            history.append("---")
            history.append("<details>")
            history.append(f"\n<summary><b>Ialt {round(total['kwh']["total"],1)}kWh {solar_string} {round(total['cost']["total"],2):.2f} kr ({round(total['cost']["total"] / total['kwh']["total"],2):.2f})</b></summary>\n")
            
            solar_header = f"<br>({emoji_parse({'solar': True})})" if solar_in_months else ""
            km_header = "Km" if total['km']['total'] > 0.0 else ""
            km_kwh_header = "Km/kWh<br>(Wh/km)" if total['km']['total'] > 0.0 else ""
            history.extend([
                f"| Måned | {km_header} | {km_kwh_header} | kWh{solar_header} | Pris | Kr/kWh<br>(Kr/Km) |",
                "|:---:|:---:|:---:|:---:|:---:|:---:|"
            ])
            
            datetime_keys = [key for key in total['cost'].keys() if isinstance(key, datetime.datetime)]
            i = 0
            for month in sorted(datetime_keys):
                solar_kwh = ""
                solar_percentage = ""
                
                if total['solar_kwh'][month] > 0.0 and total['kwh'][month] > 0.0:
                    total_solar_percentage = round(total['solar_kwh'][month] / total['kwh'][month] * 100.0, 1)
                    
                    solar_kwh = f"<br>({round(total['solar_kwh'][month], 1)})"
                    solar_percentage = f"<br>({round(total_solar_percentage, 1)}%)"
                    
                unit_price = round(total['cost'][month] / total['kwh'][month],2) if total['kwh'][month] > 0.0 else 0.0
                unit_string = f"{unit_price:.2f}<br>({round(total['cost'][month] / total['km'][month][0], 2):.2f})" if total['km'][month][0] > 0.0 else f"{unit_price:.2f}"
                
                background_color_start = "<font color=grey>" if i % 2 == 0 else ""
                background_color_end = "</font>" if i % 2 == 0 else ""
                
                history.append(f"| {background_color_start}{month.strftime('%B')}<br>{month.strftime('%Y')}{background_color_end} | {background_color_start}{total['km'][month][1]}{background_color_end} | {background_color_start}{total['km'][month][2]}{background_color_end} | {background_color_start}{round(total['kwh'][month],1)}{solar_kwh}{solar_percentage}{background_color_end} | {background_color_start}{round(total['cost'][month],2):.2f}{background_color_end} | {background_color_start}{unit_string}{background_color_end} |")
                i += 1
            
            total_solar = ""
            if total['solar_kwh']['total'] > 0.0 and total['kwh']['total'] > 0.0:
                total_solar_percentage = round(total['solar_kwh']['total'] / total['kwh']['total'] * 100.0, 1)
                total_solar = f"<br>**({round(total['solar_kwh']['total'], 1)})**<br>**({round(total_solar_percentage, 1)}%)**"
                
            km_kwh = 0.0
            wh_km = 0.0
            
            if total['km']['total'] > 0.0 and total['kwh']['total'] > 0.0:
                km_kwh = round(total['km']['total'] / total['kwh']['total'], 2)
                wh_km = round(1000 / km_kwh, 2)
            efficiency_label = f"**{km_kwh:.1f}<br>({wh_km:.1f})**" if km_kwh > 0.0 else ""
            
            total_km = f"**{round(total['km']['total'],1)}**" if total['km']['total'] > 0.0 else ""
            unit_price = round(total['cost']["total"] / total['kwh']["total"],2) if total['kwh']["total"] > 0.0 else 0.0
            unit_string = f"{unit_price:.2f}<br>({round(total['cost']["total"] / total['km']['total'],2):.2f})" if total['km']['total'] > 0.0 else f"{unit_price:.2f}"
            
            history.append(f"| **Ialt** | {total_km} | {efficiency_label} | **{round(total['kwh']['total'], 1)}**{total_solar} | **{round(total['cost']['total'], 2):.2f}** | **{unit_string}** |")
            
            if estimated_values_used:
                history.append("\n##### ~ = Estimeret km udfra forbrug og effektivitet")
                
            history.append("---")
            history.append("\n**Ladnings fordeling**")
            history.append("| Måned | Dag kWh | Nat kWh |")
            history.append("|:---|:---:|:---:|")
            
            datetime_keys = [key for key in total['charging_kwh_day'].keys() if isinstance(key, datetime.datetime)]
            for month in sorted(datetime_keys):
                procent_day = round(total['charging_kwh_day'][month] / total['kwh'][month] * 100.0, 1) if total['kwh'][month] > 0.0 else 0.0
                procent_night = round(total['charging_kwh_night'][month] / total['kwh'][month] * 100.0, 1) if total['kwh'][month] > 0.0 else 0.0
                
                history.append(f"| {month.strftime('%B')} {month.strftime('%Y')} | {round(total['charging_kwh_day'][month],1)} ({procent_day}%) | {round(total['charging_kwh_night'][month],1)} ({procent_night}%) |")
            procent_day = round(total['charging_kwh_day']["total"] / total['kwh']["total"] * 100.0, 1) if total['kwh']["total"] > 0.0 else 0.0
            procent_night = round(total['charging_kwh_night']["total"] / total['kwh']["total"] * 100.0, 1) if total['kwh']["total"] > 0.0 else 0.0
            history.append(f"| **Ialt** | **{round(total['charging_kwh_day']["total"],1)} ({procent_day}%)** | **{round(total['charging_kwh_night']["total"],1)} ({procent_night}%)** |")
            history.append("\n</details>\n")
            
        history.append("</center>")
    
    total_history_bytes_size = len("\n".join(history).encode('utf-8'))
    CHARGING_HISTORY_ENDING_BYTE_SIZE = total_history_bytes_size - current_history_bytes_size + 1000
    
    if not get_ending_byte_size:
        set_attr(f"sensor.{__name__}_charging_history.history", "\n".join(history) if history else "**Ingen lade historik**")
        
        CHARGING_HISTORY_DB = combined_db
        save_charging_history()
    
def charging_power_to_emulated_battery_level():
    _LOGGER = globals()['_LOGGER'].getChild("charging_power_to_emulated_battery_level")

    if is_ev_configured():
        return

    global CURRENT_CHARGING_SESSION

    if not CURRENT_CHARGING_SESSION.get('start'):
        return
    
    now = getTime()
    past = now - datetime.timedelta(minutes=CONFIG['cron_interval'])

    watt = get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0)

    if watt == 0.0:
        _LOGGER.warning(f"DEBUG CURRENT_CHARGING_SESSION: {CURRENT_CHARGING_SESSION}, watt: {watt}")
        return

    current_charger_meter = float(get_state(CONFIG['charger']['entity_ids']['kwh_meter_entity_id'], float_type=True, error_state=0.0))
    added_kwh = round(current_charger_meter - CURRENT_CHARGING_SESSION.get('start_charger_meter', 0.0), 1)

    if "last_charger_meter" in CURRENT_CHARGING_SESSION:
        added_kwh = round(current_charger_meter - CURRENT_CHARGING_SESSION['last_charger_meter'], 1)

    CURRENT_CHARGING_SESSION['last_charger_meter'] = current_charger_meter
    added_percentage = round(kwh_to_percentage(added_kwh, include_charging_loss=True))

    current_battery_level = battery_level()
    completed_battery_level = get_completed_battery_level()
    new_battery_level = min(round(current_battery_level + added_percentage, 0), completed_battery_level)

    _LOGGER.info(f"Adding {added_percentage}% to virtual battery level: {current_battery_level}% → {new_battery_level}%")

    set_state(entity_id=f"input_number.{__name__}_battery_level", new_state=new_battery_level)

def charging_history(charging_data=None, charging_type=""):
    _LOGGER = globals()['_LOGGER'].getChild("charging_history")
    global CHARGING_HISTORY_RUNNING, CHARGING_HISTORY_QUEUE

    CHARGING_HISTORY_QUEUE.append([charging_data, charging_type])

    if CHARGING_HISTORY_RUNNING:
        _LOGGER.warning(f"Queue is already running, current queue size: {len(CHARGING_HISTORY_QUEUE)}")
        return

    CHARGING_HISTORY_RUNNING = True

    try:
        while CHARGING_HISTORY_QUEUE:
            job = CHARGING_HISTORY_QUEUE.pop(0)
            _charging_history(charging_data=job[0], charging_type=job[1])

    except Exception as e:
        _LOGGER.error(f"Charging history queue failed: {e}")
        my_persistent_notification(
            f"Charging history queue failed: {e}",
            f"{TITLE} error",
            persistent_notification_id=f"{__name__}_charging_history_queue_failed"
        )

    finally:
        CHARGING_HISTORY_RUNNING = False

def _charging_history(charging_data = None, charging_type = ""):
    _LOGGER = globals()['_LOGGER'].getChild("_charging_history")
    global CHARGING_HISTORY_DB, CURRENT_CHARGING_SESSION
    
    def get_current_statistic(charging_ended = False):
        start = CURRENT_CHARGING_SESSION['start']
        charger_meter = float(get_state(CONFIG['charger']['entity_ids']['kwh_meter_entity_id'], float_type=True))
        added_kwh = round(charger_meter - CURRENT_CHARGING_SESSION['start_charger_meter'], 1)
        added_kwh_by_solar, solar_kwh_of_local_energy, powerwall_kwh_of_local_energy = calc_local_energy_kwh(minutesBetween(CURRENT_CHARGING_SESSION['start'], getTime(), error_value=getMinute()), added_kwh, solar_period_current_hour = False)
        added_percentage = round(kwh_to_percentage(added_kwh, include_charging_loss = True), 1)
        price = round(calc_kwh_price(minutesBetween(CURRENT_CHARGING_SESSION['start'], getTime(), error_value=getMinute()), solar_period_current_hour = True), 3)
        cost = round(added_kwh * price, 2)
        
        CHARGING_HISTORY_DB[start]["percentage"] = round(added_percentage, 1)
        CHARGING_HISTORY_DB[start]["kWh"] = round(added_kwh, 3)
        CHARGING_HISTORY_DB[start]["kWh_from_local_energy"] = round(added_kwh_by_solar, 3)
        CHARGING_HISTORY_DB[start]["solar_kwh_of_local_energy"] = solar_kwh_of_local_energy
        CHARGING_HISTORY_DB[start]["powerwall_kwh_of_local_energy"] = powerwall_kwh_of_local_energy
        CHARGING_HISTORY_DB[start]["cost"] = round(cost, 3)
        CHARGING_HISTORY_DB[start]["unit"] = round(price, 3)
        CHARGING_HISTORY_DB[start]["start_charger_meter"] = CURRENT_CHARGING_SESSION['start_charger_meter']
        CHARGING_HISTORY_DB[start]["end_charger_meter"] = charger_meter
        CHARGING_HISTORY_DB[start]["charging_session"] = CURRENT_CHARGING_SESSION
        
        if charging_ended:
            ended = f"{getTime().strftime('%H:%M')}"
            _LOGGER.warning(f"ended:{ended} added_percentage:{added_percentage} added_kwh:{added_kwh} cost:{cost} price:{price} charging_data:{charging_data} CURRENT_CHARGING_SESSION:{CURRENT_CHARGING_SESSION} emoji:{CURRENT_CHARGING_SESSION['emoji']}")
            CHARGING_HISTORY_DB[start]["ended"] = ended
            
            if CHARGING_HISTORY_DB[start]["charging_session"]["type"] == "local_energy":
                if CHARGING_HISTORY_DB[start]["kWh_from_local_energy"] > 0.0:
                    solar_ratio = CHARGING_HISTORY_DB[start]["kWh_from_local_energy"] / CHARGING_HISTORY_DB[start]["kWh"]
                    
                    if solar_ratio < 0.5:
                        CHARGING_HISTORY_DB[start]["emoji"] = join_unique_emojis(CHARGING_HISTORY_DB[start]["emoji"], emoji_parse({'grid_charging': True}))
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
        
        if CHARGING_HISTORY_DB and len(CHARGING_HISTORY_DB) > 1:
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
            "kWh": round(charging_data['kWh'], 3),
            "cost": round(charging_data['Cost'], 3),
            "unit": round(charging_data['Price'], 3),
            "charging_session": CURRENT_CHARGING_SESSION,
            "start_charger_meter": CURRENT_CHARGING_SESSION['start_charger_meter'],
            "end_charger_meter": CURRENT_CHARGING_SESSION['start_charger_meter'],
        }
        if CONFIG['ev_car']['entity_ids']['odometer_entity_id']:
            odometer = get_state(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], float_type=True, error_state=None)
            if odometer:
                CHARGING_HISTORY_DB[start]["odometer"] = int(odometer)
        #append_overview_output(f"{CURRENT_CHARGING_SESSION['emoji']} {CURRENT_CHARGING_SESSION['type']}", start.strftime("%Y-%m-%d %H:%M"))
        
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

def stop_current_charging_session():
    charging_history(None, "")

def reset_current_battery_level_expenses():
    global BATTERY_LEVEL_EXPENSES
    
    BATTERY_LEVEL_EXPENSES = {
        "battery_level_expenses_kwh": 0.0,
        "battery_level_expenses_percentage": 0.0,
        "battery_level_expenses_solar_percentage": 0.0,
        "battery_level_expenses_cost": 0.0,
        "battery_level_expenses_unit": None,
    }

def current_battery_level_expenses():
    global BATTERY_LEVEL_EXPENSES
    
    current_battery_level = battery_level()# - max(get_min_daily_battery_level(), get_min_trip_battery_level())
    
    try:
        if CHARGING_HISTORY_DB:
            for key in dict(sorted(CHARGING_HISTORY_DB.items(), key=lambda item: item[0], reverse=True)).keys():
                if round(BATTERY_LEVEL_EXPENSES["battery_level_expenses_percentage"]) < round(current_battery_level):
                    if (
                        "cost" not in CHARGING_HISTORY_DB[key] or
                        "kWh" not in CHARGING_HISTORY_DB[key] or
                        "kWh_from_local_energy" not in CHARGING_HISTORY_DB[key] or
                        "percentage" not in CHARGING_HISTORY_DB[key]
                    ):
                        continue
                    
                    cost = CHARGING_HISTORY_DB[key]["cost"]
                    kwh = CHARGING_HISTORY_DB[key]["kWh"]
                    percentage = CHARGING_HISTORY_DB[key]["percentage"]
                    solar_percentage = kwh_to_percentage(CHARGING_HISTORY_DB[key]["kWh_from_local_energy"], include_charging_loss=True)
                    
                    new_battery_level = percentage + BATTERY_LEVEL_EXPENSES["battery_level_expenses_percentage"]
                    if new_battery_level > current_battery_level and percentage > 0.0:
                        diff = (percentage - (new_battery_level - current_battery_level)) / percentage
                        cost = cost * diff
                        kwh = kwh * diff
                        percentage = percentage * diff
                        solar_percentage = solar_percentage * diff
                    BATTERY_LEVEL_EXPENSES[key] = {
                        "cost": cost,
                        "kWh": kwh,
                        "percentage": percentage,
                        "solar_percentage": solar_percentage,
                        "unit": cost / kwh if kwh > 0.0 else 0.0
                        
                    }
                    BATTERY_LEVEL_EXPENSES["battery_level_expenses_kwh"] += kwh
                    BATTERY_LEVEL_EXPENSES["battery_level_expenses_percentage"] += percentage
                    BATTERY_LEVEL_EXPENSES["battery_level_expenses_solar_percentage"] += solar_percentage
                    BATTERY_LEVEL_EXPENSES["battery_level_expenses_cost"] += cost
                else:
                    break
    
            if BATTERY_LEVEL_EXPENSES["battery_level_expenses_kwh"] > 0.0:
                BATTERY_LEVEL_EXPENSES['battery_level_expenses_unit'] = BATTERY_LEVEL_EXPENSES["battery_level_expenses_cost"] / BATTERY_LEVEL_EXPENSES["battery_level_expenses_kwh"]

    except Exception as e:
        _LOGGER.warning(f"Error in battery level cost calculation: {e}")

    return BATTERY_LEVEL_EXPENSES

def get_hour_prices():
    _LOGGER = globals()['_LOGGER'].getChild("get_hour_prices")
    global USING_OFFLINE_PRICES, LAST_SUCCESSFUL_GRID_PRICES
    
    LAST_SUCCESSFUL_GRID_PRICES.pop("missing_hours", None)
    
    USING_OFFLINE_PRICES = False
    
    now = getTime()
    current_hour = reset_time_to_hour(now)
    
    hour_prices = {}
    price_adder_day_between_divider = 30
    try:
        all_prices_loaded = True
        
        if CONFIG['prices']['entity_ids']['power_prices_entity_id'] not in state.names(domain="sensor"):
            raise Exception(f"{CONFIG['prices']['entity_ids']['power_prices_entity_id']} not loaded")
            
        if "last_update" in LAST_SUCCESSFUL_GRID_PRICES and minutesBetween(LAST_SUCCESSFUL_GRID_PRICES["last_update"], now) <= 60:
            hour_prices = LAST_SUCCESSFUL_GRID_PRICES["prices"]
        else:
            power_prices_attr = get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id'])
            
            if "raw_today" in power_prices_attr:
                for raw in power_prices_attr['raw_today']:
                    if isinstance(raw['hour'], datetime.datetime) and isinstance(raw['price'], (int, float)) and daysBetween(current_hour, raw['hour']) == 0:
                        hour_prices[raw['hour'].replace(tzinfo=None)] = round(raw['price'] - get_refund(), 2)
                    else:
                        all_prices_loaded = False
                        
            if "forecast" in power_prices_attr:
                for raw in power_prices_attr['forecast']:
                    if isinstance(raw['hour'], datetime.datetime) and isinstance(raw['price'], (int, float)) and daysBetween(current_hour, raw['hour']) > 0:
                        hour_prices[raw['hour'].replace(tzinfo=None)] = round(raw['price'] + (daysBetween(current_hour, raw['hour']) / price_adder_day_between_divider) - get_refund(), 2)
                    else:
                        all_prices_loaded = False

            if "tomorrow_valid" in power_prices_attr:
                if power_prices_attr['tomorrow_valid']:
                    if "raw_tomorrow" not in power_prices_attr or len(power_prices_attr['raw_tomorrow']) < 23: #Summer and winter time compensation
                        _LOGGER.warning(f"Raw_tomorrow not in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes, raw_tomorrow len({len(power_prices_attr['raw_tomorrow'])})")
                    else:
                        for raw in power_prices_attr['raw_tomorrow']:
                            if isinstance(raw['hour'], datetime.datetime) and isinstance(raw['price'], (int, float)) and daysBetween(current_hour, raw['hour']) == 1:
                                hour_prices[raw['hour'].replace(tzinfo=None)] = round(raw['price'] - get_refund(), 2)
                            else:
                                all_prices_loaded = False
            
            if "raw_today" not in power_prices_attr:
                raise Exception(f"Real prices not in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes")
            elif len(power_prices_attr['raw_today']) < 23: #Summer and winter time compensation
                raise Exception(f"Not all real prices in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes, raw_today len({len(power_prices_attr['raw_today'])})")

            if "forecast" not in power_prices_attr:
                raise Exception(f"Forecast not in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes")
            elif len(power_prices_attr['forecast']) < 100: #Full forecast length is 142
                raise Exception(f"Not all forecast prices in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes, forecast len({len(power_prices_attr['forecast'])})")

            if not all_prices_loaded:
                raise Exception(f"Not all prices loaded in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes")
            else:
                LAST_SUCCESSFUL_GRID_PRICES = {
                    "last_update": getTime(),
                    "prices": hour_prices
                }
    except Exception as e:
        if "last_update" in LAST_SUCCESSFUL_GRID_PRICES and minutesBetween(LAST_SUCCESSFUL_GRID_PRICES["last_update"], now) <= 120:
            hour_prices = LAST_SUCCESSFUL_GRID_PRICES["prices"]
            _LOGGER.warning(f"Not all prices loaded in {CONFIG['prices']['entity_ids']['power_prices_entity_id']} attributes, using last successful")
        else:
            _LOGGER.warning(f"Cant get all online prices, using database: {e}")

            USING_OFFLINE_PRICES = True
            missing_hours = {}
            try:
                if "history" not in KWH_AVG_PRICES_DB:
                    raise Exception(f"Missing history in KWH_AVG_PRICES_DB")
                
                for h in range(24):
                    for d in range(7):
                        if d not in KWH_AVG_PRICES_DB['history'][h]:
                            raise Exception(f"Missing hour {h} and day of week {d} in KWH_AVG_PRICES_DB")

                        timestamp = reset_time_to_hour(current_hour.replace(hour=h)) + datetime.timedelta(days=d)
                        timestamp = timestamp.replace(tzinfo=None)
                        
                        if timestamp in hour_prices:
                            continue
                        
                        avg_price = average(KWH_AVG_PRICES_DB['history'][h][d]) # Refund is already included in KWH_AVG_PRICES_DB
                        price = round(avg_price + (daysBetween(current_hour, timestamp) / price_adder_day_between_divider), 2)
                        
                        missing_hours[timestamp] = price
                        hour_prices[timestamp] = price
                        
                if missing_hours:
                    _LOGGER.info(f"Using following offline prices: {missing_hours}")
                    
                    LAST_SUCCESSFUL_GRID_PRICES["missing_hours"] = missing_hours.copy()
                    
            except Exception as e:
                error_message = f"Cant get offline prices: {e}"
                _LOGGER.error(error_message)
                save_error_to_file(error_message, caller_function_name = "cheap_grid_charge_hours()")
                my_persistent_notification(f"Kan ikke hente offline priser: {e}", f"{TITLE} error", persistent_notification_id=f"{__name__}_offline_prices_error")
                raise Exception(f"Offline prices error: {e}")
            
            missing_hours_list = [f"- {timestamp.strftime('%d/%m %H:%M')}: {price:.2f}kr" for timestamp, price in LAST_SUCCESSFUL_GRID_PRICES["missing_hours"].items()]
            my_persistent_notification(f"Kan ikke hente alle online priser, bruger database priser:\n{'\n'.join(missing_hours_list)}\n\n{e}", f"{TITLE} warning", persistent_notification_id=f"{__name__}_real_prices_error")
    
    return hour_prices

def get_expensive_hours(day=0):
    countExpensive = 0
    expensiveDict = {}
    
    day_timestamp = getTime().date() + datetime.timedelta(days=day)
    
    for timestamp, price in sorted(get_hour_prices().items(), key=lambda kv: (kv[1],kv[0]), reverse=True):
        if timestamp.date() == day_timestamp:
            if countExpensive < 4:
                expensiveDict[timestamp] = price
            else:
                break
            countExpensive += 1
    
    return expensiveDict

def cheap_grid_charge_hours():
    _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours")
    global USING_OFFLINE_PRICES, LAST_SUCCESSFUL_GRID_PRICES, CHARGING_PLAN, CHARGE_HOURS
    
    if CONFIG['prices']['entity_ids']['power_prices_entity_id'] not in state.names(domain="sensor"):
        _LOGGER.error(f"{CONFIG['prices']['entity_ids']['power_prices_entity_id']} not in entities")
        my_persistent_notification(f"Kan ikke hente strøm priser, {CONFIG['prices']['entity_ids']['power_prices_entity_id']} findes ikke under domain sensor:", f"{TITLE} warning", persistent_notification_id=f"{__name__}_real_prices_not_found")
        return

    today = getTimeStartOfDay()
    current_hour = reset_time_to_hour(getTime())
    now = getTime()
    
    chargeHours = {}
    charge_hours_alternative = {}
    
    totalCost = 0.0
    totalkWh = 0.0
    
    solar_over_production = {}
    work_overview = {}
    charging_plan = {
        "workday_in_week": False
    }
    
    
    hour_prices = get_hour_prices()

    sorted_by_cheapest_price = sorted(hour_prices.items(), key=lambda kv: (kv[1], kv[0]))
    
    reset_current_battery_level_expenses()
    current_battery_level_expenses()
    
    def change_timestamp_with_minutes(timestamp: datetime.datetime):
        _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours.change_timestamp_with_minutes")
        
        what_day = daysBetween(getTime(), timestamp)
        work_minute = 0
        trip_minute = 0
        if isinstance(charging_plan[what_day]['work_last_charging'], datetime.datetime):
            if charging_plan[what_day]['work_last_charging'].hour == timestamp.hour and charging_plan[what_day]['work_last_charging'].minute != 0:
                work_minute = max(charging_plan[what_day]['work_last_charging'].minute, work_minute)
        if isinstance(charging_plan[what_day]['work_homecoming'], datetime.datetime):
            if charging_plan[what_day]['work_homecoming'].hour == timestamp.hour and charging_plan[what_day]['work_homecoming'].minute != 0:
                work_minute = max(charging_plan[what_day]['work_homecoming'].minute, work_minute)
        
        if isinstance(charging_plan[what_day]['trip_last_charging'], datetime.datetime):
            if charging_plan[what_day]['trip_last_charging'].hour == timestamp.hour and charging_plan[what_day]['trip_last_charging'].minute != 0:
                trip_minute = max(charging_plan[what_day]['trip_last_charging'].minute, trip_minute)
        if isinstance(charging_plan[what_day]['trip_homecoming'], datetime.datetime):
            if charging_plan[what_day]['trip_homecoming'].hour == timestamp.hour and charging_plan[what_day]['trip_homecoming'].minute != 0:
                trip_minute = max(charging_plan[what_day]['trip_homecoming'].minute, trip_minute)
        
        return timestamp.replace(minute=max(work_minute, trip_minute, 0))
        
    
    def available_for_charging_prediction(timestamp: datetime.datetime, trip_datetime = None, trip_homecoming_datetime = None):
        _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours.available_for_charging_prediction")
        working = False
        on_trip = False
        day = daysBetween(getTime(), timestamp)
        
        try:
            if charging_plan[day]['workday']:
                working = in_between(timestamp.hour, charging_plan[day]['work_goto'].hour, charging_plan[day]['work_homecoming'].hour)

            if trip_datetime:
                on_trip = in_between(timestamp.hour, trip_datetime.hour, trip_homecoming_datetime.hour)
        except Exception as e:
            _LOGGER.error(f"day:{day} timestamp:{timestamp} charging_plan[{day}][work_goto].hour:{charging_plan[day]['work_goto'].hour} charging_plan[{day}][work_homecoming].hour:{charging_plan[day]['work_homecoming'].hour} trip_datetime:{trip_datetime} trip_homecoming_datetime:{trip_homecoming_datetime} working:{working} on_trip:{on_trip} error:{e}")
        
        return working, on_trip
    
    def kwh_available_in_hour(hour):
        _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours.kwh_available_in_hour")
        hour_in_chargeHours = False
        kwh_available = False
        
        kwh = MAX_KWH_CHARGING - 1.0
        
        percentage_missed = hour.minute / 60
        kwh_missed = kwh * percentage_missed
        
        kwh -= kwh_missed
        if hour in chargeHours:
            hour_in_chargeHours = True
            if chargeHours[hour]['kWh'] < kwh:
                kwh_available = True
        return [hour_in_chargeHours, kwh_available]

    def check_max_battery_level_allowed(day, what_day, battery_level_id, max_recommended_battery_level, battery_level_to_added):
        _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours.check_max_battery_level_allowed")
        charging_sessions_id = "battery_level_before_work" if battery_level_id == "battery_level_before_work" else "battery_level_after_work"
        max_battery_level = 0.0
        
        for i in range(max(what_day - 1, 0), day + 1):
            if charging_sessions_id == "battery_level_before_work":
                if i == max(what_day - 1, 0) and day > 0:
                    max_battery_level = max(
                        sum(charging_plan[i]['battery_level_at_midnight']) + battery_level_to_added,
                        max_battery_level
                        )
                    
                if  i >= what_day:
                    max_battery_level = max(
                        sum(charging_plan[i]['battery_level_at_midnight']) + battery_level_to_added,
                        sum(charging_plan[i]['battery_level_after_work']) + battery_level_to_added,
                        sum(charging_plan[i]['battery_level_before_work']) + battery_level_to_added,
                        max_battery_level
                        )
            elif charging_sessions_id == "battery_level_after_work":
                if i >= what_day:
                    max_battery_level = max(
                        sum(charging_plan[i]['battery_level_at_midnight']) + battery_level_to_added,
                        sum(charging_plan[i]['battery_level_after_work']) + battery_level_to_added,
                        max_battery_level
                        )
                
                if i > what_day:
                    max_battery_level = max(
                        sum(charging_plan[i]['battery_level_before_work']) + battery_level_to_added,
                        max_battery_level
                        )
        if max_battery_level > max_recommended_battery_level:
            kwh_allowed = percentage_to_kwh(max_recommended_battery_level - max_battery_level, include_charging_loss = True)
            return kwh_allowed
        return percentage_to_kwh(battery_level_to_added, include_charging_loss = True)

    def add_to_charge_hours(kwhNeeded, totalCost, totalkWh, hour, price, very_cheap_price, ultra_cheap_price, kwh_available, battery_level = None, check_max_charging_plan={"day": None, "what_day": None, "battery_level_id": None}, max_recommended_battery_level = None, rules = []):
        _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours.add_to_charge_hours")
        cost = 0.0
        kwh = MAX_KWH_CHARGING
        battery_level_added = False
            
        price = float(price)
        kwhNeeded = float(kwhNeeded)
        
        percentage_missed = hour.minute / 60
        kwh_missed = kwh * percentage_missed
        kwh -= kwh_missed

            
        if battery_level:
            if max_recommended_battery_level is None:
                max_recommended_battery_level = get_max_recommended_charge_limit_battery_level()
                
            battery_level_diff = round(max_recommended_battery_level - (battery_level + kwh_to_percentage(kwh, include_charging_loss = True)),2)
            kwh_diff = round(percentage_to_kwh(battery_level_diff, include_charging_loss = True),2)
            if (battery_level + kwh_to_percentage(kwh, include_charging_loss = True)) > max_recommended_battery_level:
                kwh -= abs(kwh_diff)
            
        if kwh_available == True and hour in chargeHours:
            kwh -= chargeHours[hour]['kWh']
            
        if check_max_charging_plan and check_max_charging_plan['day'] is not None:
            kwh_allowed = check_max_battery_level_allowed(check_max_charging_plan['day'], check_max_charging_plan['what_day'], check_max_charging_plan['battery_level_id'], max_recommended_battery_level, kwh_to_percentage(kwh, include_charging_loss = True))
            kwh = kwh + kwh_allowed if kwh_allowed < 0.0 else kwh_allowed
        
        if kwh > 0.5:
            if hour not in chargeHours:
                chargeHours[hour] = {
                    "Cost": 0.0,
                    "kWh": 0.0,
                    "battery_level": 0.0,
                    "Price": round(price, 2),
                    "ChargingAmps": CONFIG['charger']['charging_max_amp']
                }
            
            if (kwhNeeded - kwh) < 0.0:
                kwh = kwhNeeded
                kwhNeeded = 0.0
            else:
                kwhNeeded = kwhNeeded - kwh
                
            cost = kwh * price
            totalCost = totalCost + cost
            battery_level_added = kwh_to_percentage(kwh, include_charging_loss = True)

            chargeHours[hour]['Cost'] = round(chargeHours[hour]['Cost'] + cost, 2)
            chargeHours[hour]['kWh'] = round(chargeHours[hour]['kWh'] + kwh, 2)
            chargeHours[hour]['battery_level'] = round(chargeHours[hour]['battery_level'] + battery_level_added, 2)
            totalkWh = round(totalkWh + kwh, 2)
                
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

        return [kwhNeeded, totalCost, totalkWh, battery_level_added, cost]

    def cheap_price_check(price):
        _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours.cheap_price_check")
        very_cheap_price = False
        ultra_cheap_price = False
        
        try:
            lowest_values = sorted(hour_prices.values())[:CONFIG['database']['kwh_avg_prices_db_data_to_save']]
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
        _LOGGER = globals()['_LOGGER'].getChild("cheap_grid_charge_hours.future_charging")
        global BATTERY_LEVEL_EXPENSES
        
        nonlocal trip_date_time
        nonlocal trip_target_level
        
        def what_battery_level(what_day, hour, price, day):
            battery_level_id = "battery_level_at_midnight"
            max_recommended_charge_limit_battery_level = get_max_recommended_charge_limit_battery_level()
            return_fail_list = [False, max_recommended_charge_limit_battery_level]
            
            if what_day < 0:
                _LOGGER.warning(f"Error in hour_prices: {hour} is before current time {getTime()} continue to next cheapest hour/price")
                return return_fail_list
            
            total_trip_battery_level_needed = charging_plan[day]["trip_battery_level_needed"] + charging_plan[day]["trip_battery_level_above_max"]
            if charging_plan[day]["trip"] and max_recommended_charge_limit_battery_level < total_trip_battery_level_needed: # if charging_plan[day]["trip"] and in_between(day - what_day, 1, 0) and max_recommended_charge_limit_battery_level < total_trip_battery_level_needed:
                max_recommended_charge_limit_battery_level = total_trip_battery_level_needed
            
            what_day_battery_level_before_work = sum(charging_plan[what_day]['battery_level_before_work'])
            what_day_battery_level_after_work = max(sum(charging_plan[what_day]['battery_level_after_work']), sum(charging_plan[what_day]['battery_level_at_midnight']))
            after_what_day_battery_level_after_work = max(sum(charging_plan[min(what_day + 1, 7)]['battery_level_after_work']), sum(charging_plan[min(what_day + 1, 7)]['battery_level_at_midnight']))
            
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
        
        def battery_level_full_on_next_departure(what_day):
            if what_day == 7:
                return False
            
            for day in range(what_day + 1,8):
                if charging_plan[day]['trip']:
                    return False
                
                if charging_plan[day]['workday']:
                    if round(sum(charging_plan[day]["battery_level_before_work"]),0) >= get_max_recommended_charge_limit_battery_level():
                        return True
                    break
            return False
        
        unused_solar_kwh = {}
        unused_solar_cost = {}
        solar_unit = get_solar_sell_price()
        
        ignored_reference_battery_level = 0.0
        
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
                trip_battery_needed = charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max']

                if charging_plan[day]['workday'] and charging_plan[day]['trip_goto'] >= charging_plan[day]['work_goto']:
                    reference_battery_level = sum(charging_plan[day]['battery_level_after_work']) - charging_plan[day]['work_battery_level_needed']
                else:
                    reference_battery_level = sum(charging_plan[day]['battery_level_before_work'])

                charging_plan[day]['trip_kwh_needed'] = max(kwh_needed_for_charging(trip_battery_needed, reference_battery_level), 0.0)
                
            _LOGGER.debug(f"---------------------------------{day} {charging_plan[day]['day_text']} {charging_plan[day]['work_goto']} {day}---------------------------------")
                
            if charging_plan[day]['workday']:
                charging_plan[day]['battery_level_after_work'].append(charging_plan[day]['work_battery_level_needed'] * -1)
            
            charging_plan[day]['battery_level_at_midnight'].append(sum(charging_plan[day]['battery_level_after_work']))
            charging_plan[day]['battery_level_at_midnight'].append(charging_plan[day]['solar_prediction'])
            
            fill_up_days = {
                1: 0.0,
                4: 0.0,
                7: 0.0
                }
            kwh_needed_to_fill_up = kwh_needed_for_charging(get_max_recommended_charge_limit_battery_level(), sum(charging_plan[day]['battery_level_at_midnight']))
            kwh_needed_to_fill_up_share = kwh_needed_to_fill_up / len(fill_up_days)
            
            for key in fill_up_days.keys():
                fill_up_days[key] += kwh_needed_to_fill_up_share
            
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
                    last_charging = min(charging_plan[day]['work_last_charging'], charging_plan[day]['trip_last_charging']) if charging_plan[day]['workday'] else charging_plan[day]['trip_last_charging']
                                    
                _LOGGER.debug(f"charging_plan[{day}]['work_goto'] {charging_plan[day]['work_goto']} / charging_plan[{day}]['trip_last_charging'] {charging_plan[day]['trip_last_charging']} / last_charging {last_charging}")
                
                kwh_needed_today = max(kwh_needed_for_charging(charging_plan[day]['work_battery_level_needed'] + get_min_daily_battery_level(), sum(charging_plan[day]['battery_level_before_work'])), 0.0)
                charging_plan[day]['work_kwh_needed'] = kwh_needed_today
                kwh_needed_today += charging_plan[day]['trip_kwh_needed']
                _LOGGER.debug(f"charging_plan[{day}]['work_battery_level_needed'] {charging_plan[day]['work_battery_level_needed']}")
                _LOGGER.debug(f"kwh_needed_today {kwh_needed_today}")
                
                
                #Workaround for cold weather
                if kwh_needed_today <= (CONFIG['ev_car']['battery_size'] / 100):
                    kwh_needed_today = 0.0
                
                while_count = 0
                while_loop = True
                
                while while_loop and while_count < 2:
                    for timestamp, price in sorted_by_cheapest_price:
                        if charging_plan[day]['workday'] and charging_plan[day]['trip'] and while_count == 0:
                            #_LOGGER.info(f"DEBUG {timestamp} {price} {charging_plan[day]['work_homecoming']} < {charging_plan[day]['trip_last_charging']} {charging_plan[day]['work_homecoming'] < charging_plan[day]['trip_last_charging']} {sum(charging_plan[day]['battery_level_before_work'])} >= ({charging_plan[day]['work_battery_level_needed']} + {get_min_daily_battery_level()}) {sum(charging_plan[day]['battery_level_before_work']) >= (charging_plan[day]['work_battery_level_needed'] + get_min_daily_battery_level())}")
                            
                            if (charging_plan[day]['work_homecoming'] < charging_plan[day]['trip_last_charging']
                                and sum(charging_plan[day]['battery_level_before_work']) >= (charging_plan[day]['work_battery_level_needed'] + get_min_trip_battery_level())):
                                last_charging = charging_plan[day]['trip_last_charging']
                                _LOGGER.info(f"Enought battery level for work, planning for trip {sum(charging_plan[day]['battery_level_before_work'])} >= ({charging_plan[day]['work_battery_level_needed']} + {get_min_trip_battery_level()})")
                                break
                            
                        if not in_between(timestamp, current_hour, last_charging):
                            continue
                            
                        timestamp = change_timestamp_with_minutes(timestamp)
                        
                        hour_in_chargeHours, kwh_available = kwh_available_in_hour(timestamp)
                        if hour_in_chargeHours and not kwh_available:
                            continue
                        
                        what_day = daysBetween(getTime(), timestamp)
                        battery_level_id, max_recommended_charge_limit_battery_level = what_battery_level(what_day, timestamp, price, day)
                        if not battery_level_id:
                            _LOGGER.debug(f"battery_level_id not found for day ({what_day}) {timestamp} {price}kr. continue to next cheapest timestamp/price")
                            continue
                        
                        if battery_level_full_on_next_departure(what_day):
                            _LOGGER.debug(f"Max battery level reached for day ({what_day}) before work {timestamp} {price}kr. continue to next cheapest timestamp/price")
                            continue

                        working, on_trip = available_for_charging_prediction(timestamp, trip_date_time, trip_homecoming_date_time)
                        if working or on_trip:
                            continue
                        
                        #Code below temporary disabled, maybe not needed anymore
                        '''if len(chargeHours) > 1:
                            filteredDict = {k: v for k, v in chargeHours.items() if type(k) is datetime.datetime}
                            if len(filteredDict) > 1:
                                first_charging_session = sorted(filteredDict.keys())[0]
                                trip_battery_level_needed = charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max']
                                
                                try:
                                    if (chargeHours[first_charging_session]['trip'] and
                                    timestamp < first_charging_session and
                                    trip_battery_level_needed != 100):
                                        if what_day != 0 and not charging_plan[day]['workday']:
                                            continue
                                except:
                                    pass'''
                        
                        if round(kwh_needed_today, 1) > 0.0 and kwh_to_percentage(kwh_needed_today, include_charging_loss = True) > 0.0:
                            '''if round(sum(charging_plan[what_day][battery_level_id]), 0) >= get_max_recommended_charge_limit_battery_level() - 1.0:
                                #Workaround for cold battery percentage: ex. 90% normal temp = 89% cold temp
                                continue'''
                            
                            kwh_needed_today, totalCost, totalkWh, battery_level_added, cost_added = add_to_charge_hours(kwh_needed_today, totalCost, totalkWh, timestamp, price, None, None, kwh_available, sum(charging_plan[what_day][battery_level_id]), check_max_charging_plan={"day": day, "what_day": what_day, "battery_level_id": battery_level_id}, max_recommended_battery_level=max_recommended_charge_limit_battery_level, rules=charging_plan[day]['rules'])
                            
                            if timestamp in chargeHours and battery_level_added:
                                total_trip_battery_level_needed = charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max']
                                
                                battery_level_sum = total_trip_battery_level_needed + charging_plan[day]['work_battery_level_needed']
                                if battery_level_sum > 0.0:
                                    if "trip" in charging_plan[day]['rules']:
                                        cost_trip = (total_trip_battery_level_needed / battery_level_sum) * cost_added
                                        charging_plan[day]['trip_total_cost'] += cost_trip
                                        
                                    if filter(lambda x: 'workday_preparation' in x, charging_plan[day]['rules']):
                                        cost_work = (charging_plan[day]['work_battery_level_needed'] / battery_level_sum) * cost_added
                                        charging_plan[day]['work_total_cost'] += cost_work
                                    
                                charging_sessions_id = add_charging_session_to_day(timestamp, what_day, battery_level_id)
                                add_charging_to_days(day, what_day, charging_sessions_id, battery_level_added)
                        else:
                            while_loop = False
                            break
                    while_count += 1
                
            if solar_charging_enabled():
                if day > 0:
                    unused_solar_kwh[getTimePlusDays(day).date()] = charging_plan[day_before]['solar_kwh_prediction']
                    unused_solar_cost[getTimePlusDays(day).date()] = charging_plan[day_before]['solar_cost_prediction']
            
            try:
                days_need_between_recommended_full_charge = int(float(get_state(f"input_number.{__name__}_full_charge_recommended", error_state=0)))
                days_since_last_fully_charged = daysBetween(get_state(f"input_datetime.{__name__}_last_full_charge", try_history=True, error_state=resetDatetime()), getTime())
                need_recommended_full_charge = days_need_between_recommended_full_charge != 0 and days_since_last_fully_charged > days_need_between_recommended_full_charge and day == 1
                
                if need_recommended_full_charge:
                    _LOGGER.info(f"Days since last fully charged: {days_since_last_fully_charged}. Need full charge: {need_recommended_full_charge}")
                    
                fill_up = fill_up_charging_enabled()# and charging_plan[day]['offday'] and day in fill_up_days.keys()
                
                if fill_up or need_recommended_full_charge:
                    rules = []
                    kwh_needed_to_fill_up_day = fill_up_days.get(day, 0.0)
                    
                    if fill_up and kwh_needed_to_fill_up_day <= 0.0:
                        if sum(charging_plan[day]['battery_level_at_midnight']) < charging_plan[day]['offday_battery_level_needed'] + get_min_daily_battery_level():
                            kwh_needed_to_fill_up_day = kwh_needed_for_charging(charging_plan[day]['offday_battery_level_needed'] + get_min_daily_battery_level(), sum(charging_plan[day]['battery_level_at_midnight']))
                    
                    if need_recommended_full_charge:
                        kwh_needed_to_fill_up_day = max(kwh_needed_for_charging(100.0, battery_level() + charging_plan[day]['solar_prediction']), kwh_needed_to_fill_up_day)
                        _LOGGER.info(f"Needed for full charge: {round(kwh_needed_to_fill_up_day,1)}kWh")
                        rules.append("battery_health")
                    elif fill_up:
                        #kwh_needed_to_fill_up_day = max(kwh_needed_for_charging(get_max_recommended_charge_limit_battery_level()), kwh_needed_to_fill_up_day)
                        rules.append("fill_up")
                        
                    if kwh_needed_to_fill_up_day > 0.0:
                        for timestamp, price in sorted_by_cheapest_price:
                            if not in_between(timestamp, current_hour, last_charging):
                                continue
                            
                            timestamp = change_timestamp_with_minutes(timestamp)
                            
                            hour_in_chargeHours, kwh_available = kwh_available_in_hour(timestamp)
                            if hour_in_chargeHours and not kwh_available:
                                continue
                            
                            what_day = daysBetween(getTime(), timestamp)
                            battery_level_id, max_recommended_charge_limit_battery_level = what_battery_level(what_day, timestamp, price, day)
                            
                            if not battery_level_id:
                                continue
                            
                            if need_recommended_full_charge:
                                max_recommended_charge_limit_battery_level = 100.0 #Ignore solar over production
                                
                                if not is_ev_configured(): #Sets battery level to 0.0 at midnight
                                    battery_level_id = "battery_level_at_midnight"
                                    
                                    '''if battery_level_id not in charging_plan[what_day]:
                                        battery_level_id = "battery_level_after_work"
                                        
                                    if battery_level_id not in charging_plan[what_day]:
                                        battery_level_id = "battery_level_before_work"'''
                                        
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
                                kwh_needed_to_fill_up_day, totalCost, totalkWh, battery_level_added, cost_added = add_to_charge_hours(kwh_needed_to_fill_up_day, totalCost, totalkWh, timestamp, price, None, None, kwh_available, sum(charging_plan[what_day][battery_level_id]), check_max_charging_plan={"day": day, "what_day": what_day, "battery_level_id": battery_level_id}, max_recommended_battery_level=max_recommended_charge_limit_battery_level, rules=rules)

                                very_cheap_kwh_needed_today -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                ultra_cheap_kwh_needed_today -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                            
                            elif ultra_cheap_price and ultra_cheap_kwh_needed_today > 0.0:
                                ultra_cheap_kwh_needed_today, totalCost, totalkWh, battery_level_added, cost_added = add_to_charge_hours(ultra_cheap_kwh_needed_today, totalCost, totalkWh, timestamp, price, very_cheap_price, ultra_cheap_price, kwh_available, sum(charging_plan[what_day][battery_level_id]), check_max_charging_plan={"day": day, "what_day": what_day, "battery_level_id": battery_level_id}, max_recommended_battery_level=max_recommended_charge_limit_battery_level, rules=rules)
                                very_cheap_kwh_needed_today -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                kwh_needed_to_fill_up_day -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                
                            elif very_cheap_price and very_cheap_kwh_needed_today > 0.0:
                                very_cheap_kwh_needed_today, totalCost, totalkWh, battery_level_added, cost_added = add_to_charge_hours(very_cheap_kwh_needed_today, totalCost, totalkWh, timestamp, price, very_cheap_price, ultra_cheap_price, kwh_available, sum(charging_plan[what_day][battery_level_id]), check_max_charging_plan={"day": day, "what_day": what_day, "battery_level_id": battery_level_id}, max_recommended_battery_level=max_recommended_charge_limit_battery_level, rules=rules)
                                ultra_cheap_kwh_needed_today -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                                kwh_needed_to_fill_up_day -= percentage_to_kwh(battery_level_added, include_charging_loss=True)
                            else:
                                continue
                            
                            if timestamp in chargeHours and battery_level_added:
                                charging_sessions_id = add_charging_session_to_day(timestamp, what_day, battery_level_id)
                                add_charging_to_days(day, what_day, charging_sessions_id, battery_level_added)
                                if charging_plan[day]['offday']:
                                    charging_plan[day]['offday_total_cost'] += cost_added
            except Exception as e:
                error_message = f"Error in fill up or need recommended full charge for day {day}: {e}"
                _LOGGER.warning(error_message)
                save_error_to_file(error_message, caller_function_name = "cheap_grid_charge_hours().future_charging().fill_up_or_need_recommended_full_charge")
                my_persistent_notification(error_message, f"{TITLE} error", persistent_notification_id=f"{__name__}_fill_up_or_need_recommended_full_charge_error")

            try:
                solar_kwh = 0.0
                solar_percentage = 0.0
                solar_unit = 0.0
                
                if sum(unused_solar_kwh.values()) > 0.0:
                    total_solar_kwh = sum(unused_solar_kwh.values())
                    total_solar_price = sum(unused_solar_cost.values())
                    
                    if total_solar_kwh > 0.0:
                        solar_unit = total_solar_price / total_solar_kwh
                    
                    solar_percentage = kwh_to_percentage(total_solar_kwh, include_charging_loss=True)
                    
                temp_events = []
                for event_type in ('workday', 'trip', 'offday'):
                    
                    from_battery = 0.0
                    from_battery_solar = 0.0
                    if charging_plan[day][event_type]:
                        if event_type in ('workday', 'trip') and charging_plan[day][event_type]:
                            goto_key = 'trip_goto' if event_type == 'trip' else 'work_goto'
                            event_time_start = charging_plan[day][goto_key]
                            event_time_end = charging_plan[day]['trip_homecoming'] if event_type == 'trip' else charging_plan[day]['work_homecoming']
                            
                            emoji = emoji_parse({'trip': True}) if event_type == 'trip' else charging_plan[day]['emoji']
                            battery_level_needed_key = 'trip_battery_level_needed' if event_type == 'trip' else 'work_battery_level_needed'
                            battery_level_needed = charging_plan[day][battery_level_needed_key] if battery_level_needed_key =="work_battery_level_needed" else charging_plan[day][battery_level_needed_key] + charging_plan[day]["trip_battery_level_above_max"]
                            kwh_needed = charging_plan[day]['trip_kwh_needed' if event_type == 'trip' else 'work_kwh_needed']
                            cost = charging_plan[day]["trip_total_cost" if event_type == "trip" else "work_total_cost"]
                        elif event_type == 'offday' and charging_plan[day][event_type] and day > 0:
                            event_time_start = charging_plan[day]['start_of_day']
                            event_time_end = charging_plan[day]['end_of_day']
                            
                            emoji = charging_plan[day]['emoji']
                            battery_level_needed = charging_plan[day]['offday_battery_level_needed']
                            kwh_needed = max(charging_plan[day]['offday_kwh_needed'], 0.0)
                            cost = charging_plan[day]["offday_total_cost"]
                        else:
                            continue
                        
                        unused_solar_kwh.clear()
                        unused_solar_cost.clear()
                        
                        if solar_percentage > battery_level_needed:
                            diff = solar_percentage - battery_level_needed
                            diff_kwh = percentage_to_kwh(diff, include_charging_loss=True)
                            unused_solar_kwh[getTimePlusDays(day).date()] = diff_kwh
                            unused_solar_cost[getTimePlusDays(day).date()] = diff_kwh * solar_unit
                            
                        solar_percentage = min(solar_percentage, battery_level_needed)
                        grid_battery_level_needed = battery_level_needed - solar_percentage
                        
                        solar_kwh += percentage_to_kwh(solar_percentage, include_charging_loss=True)
                        solar_cost = solar_unit * solar_kwh
                        cost += solar_cost

                        if event_type in ('workday', 'trip'):
                            kwh_needed += solar_kwh
                        elif event_type == 'offday':
                            #kwh_needed = max(charging_plan[day]['offday_kwh_needed'] - kwh_needed, 0.0)
                            kwh_needed += solar_kwh
                        
                        battery_level_expenses_solar_percentage_loop = 0.0
                        battery_level_expenses_solar_kwh_loop = 0.0
                        reference_battery_level = get_min_daily_battery_level() if event_type in ("workday", "offday") else get_min_trip_battery_level()
                        
                        for key in sorted([k for k in BATTERY_LEVEL_EXPENSES.copy().keys() if type(k) is datetime.datetime]):
                            
                            if ignored_reference_battery_level < reference_battery_level:
                                ignored_reference_battery_level += BATTERY_LEVEL_EXPENSES[key]["percentage"]
                                
                                if ignored_reference_battery_level > reference_battery_level:
                                    diff = ignored_reference_battery_level - reference_battery_level
                                    
                                    amount = diff / BATTERY_LEVEL_EXPENSES[key]["percentage"] if BATTERY_LEVEL_EXPENSES[key]["percentage"] > 0.0 else 0.0
                                    BATTERY_LEVEL_EXPENSES[key]["percentage"] *= amount
                                    BATTERY_LEVEL_EXPENSES[key]["solar_percentage"] *= amount
                                    
                                BATTERY_LEVEL_EXPENSES["battery_level_expenses_percentage"] -= BATTERY_LEVEL_EXPENSES[key]["percentage"]
                                
                            if ignored_reference_battery_level >= reference_battery_level and grid_battery_level_needed > 0.0 and BATTERY_LEVEL_EXPENSES["battery_level_expenses_percentage"] > 0.0:
                                battery_level_expenses_grid_amount = min(grid_battery_level_needed, BATTERY_LEVEL_EXPENSES[key]["percentage"])
                                grid_battery_level_needed -= battery_level_expenses_grid_amount
                                BATTERY_LEVEL_EXPENSES["battery_level_expenses_percentage"] -= battery_level_expenses_grid_amount
                                
                                battery_level_expenses_grid_percentage_loop = battery_level_expenses_grid_amount
                                battery_level_expenses_grid_kwh_loop = percentage_to_kwh(battery_level_expenses_grid_percentage_loop, include_charging_loss=True)
                                battery_level_expenses_grid_cost_loop = BATTERY_LEVEL_EXPENSES['battery_level_expenses_unit'] * battery_level_expenses_grid_kwh_loop
                                
                                kwh_needed += battery_level_expenses_grid_kwh_loop
                                cost += battery_level_expenses_grid_cost_loop
                                
                                if round(battery_level_expenses_grid_kwh_loop, 1) > 0.0:
                                    from_battery += battery_level_expenses_grid_kwh_loop
                                
                                if BATTERY_LEVEL_EXPENSES["battery_level_expenses_solar_percentage"] > 0.0:
                                    battery_level_expenses_solar_amount = min(battery_level_expenses_grid_percentage_loop, BATTERY_LEVEL_EXPENSES[key]["solar_percentage"])
                                    BATTERY_LEVEL_EXPENSES["battery_level_expenses_solar_percentage"] -= battery_level_expenses_solar_amount
                                    
                                    battery_level_expenses_solar_percentage_loop += min(battery_level_expenses_solar_amount, grid_battery_level_needed)
                                    battery_level_expenses_solar_kwh_loop += percentage_to_kwh(battery_level_expenses_solar_amount, include_charging_loss=True)
                                    
                                    if round(battery_level_expenses_solar_kwh_loop, 1) > 0.0:
                                        from_battery_solar = battery_level_expenses_solar_kwh_loop
                        
                        if kwh_needed > percentage_to_kwh(battery_level_needed, include_charging_loss=True):
                            cost_unit = cost / kwh_needed
                            kwh_needed = percentage_to_kwh(battery_level_needed, include_charging_loss=True)
                            cost = kwh_needed * cost_unit
                        
                        from_grid = max(kwh_needed - solar_kwh - from_battery - from_battery_solar, 0.0)
                        
                        solar_percentage_label = solar_percentage + battery_level_expenses_solar_percentage_loop
                        solar_kwh_label = solar_kwh + battery_level_expenses_solar_kwh_loop
                        
                        if solar_kwh_label > percentage_to_kwh(battery_level_needed, include_charging_loss=True):
                            solar_percentage_label = battery_level_needed
                            solar_kwh_label = percentage_to_kwh(battery_level_needed, include_charging_loss=True)
                        
                        solar_percentage_label = round(solar_percentage_label, 0)
                        solar_kwh_label = round(solar_kwh_label, 1)
                        solar_label = f"{solar_percentage_label:.0f}% {solar_kwh_label:.1f}kWh" if solar_kwh_label > 0.0 else ""
                        
                        solar_kwh = 0.0
                        solar_percentage = 0.0
                        
                        temp_events.append({
                            "time": event_time_start,
                            "data": {
                                "emoji": emoji,
                                "day": f"*{getDayOfWeekText(event_time_start, translate=True).capitalize()}*",
                                "date": f"*{date_to_string(date = event_time_start, format = "%d/%m")}*",
                                "goto": f"*{date_to_string(date = event_time_start, format = "%H:%M")}*",
                                "homecoming": f"*{date_to_string(date = event_time_end, format = "%H:%M")}*",
                                "solar": solar_label,
                                "solar_kwh": solar_kwh_label,
                                "battery_needed": battery_level_needed,
                                "kwh_needed": percentage_to_kwh(battery_level_needed, include_charging_loss=True),
                                "cost": cost,
                                "from_grid": from_grid,
                                "from_battery": from_battery,
                                "from_battery_solar": from_battery_solar,
                                "event_type": event_type
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
        
            try: #Alternative charging estimate
                charger_status = get_state(CONFIG['charger']['entity_ids']['status_entity_id'], float_type=False, error_state="unavailable")
                
                dates = [date for date in [charging_plan[day]['work_homecoming'], charging_plan[day]['trip_homecoming'], getTime() if day == 0 and charger_status in tuple(chain(CHARGER_READY_STATUS, CHARGER_CHARGING_STATUS, CHARGER_COMPLETED_STATUS)) else None] if date is not None]
                homecoming_alternative = min(dates) if dates else charging_plan[day_before]['start_of_day']
                
                dates = [date for date in [charging_plan[day_after]['work_last_charging'], charging_plan[day_after]['trip_last_charging'], charging_plan[day]['trip_last_charging']] if date is not None]
                last_charging_alternative = min(dates) if dates else charging_plan[day_after]['end_of_day']
                    
                if now <= last_charging_alternative and day < 7:
                    if day == 0:
                        used_battery_level_alternative = max(get_max_recommended_charge_limit_battery_level() - battery_level(), 0.0)
                    else:
                        work_battery_level_needed_alternative = charging_plan[day]['work_battery_level_needed']
                        trip_battery_level_needed_alternative = charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max'] + charging_plan[day_after]['trip_battery_level_needed'] + charging_plan[day_after]['trip_battery_level_above_max']
                        typical_daily_battery_level_needed_alternative = calc_distance_to_battery_level(get_entity_daily_distance()) if fill_up_charging_enabled() else 0.0
                        total_battery_level_needed_alternative = work_battery_level_needed_alternative + trip_battery_level_needed_alternative + typical_daily_battery_level_needed_alternative
                        used_battery_level_alternative = max(total_battery_level_needed_alternative, 0.0)
                    
                        if charging_plan[day]["trip"]:
                            diff_min_alternative = max(get_min_daily_battery_level() - get_min_trip_battery_level(), 0.0) if used_battery_level_alternative > 0.0 else 0.0
                            used_battery_level_alternative += charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max'] + diff_min_alternative
                    
                    kwh_needed_today_alternative = kwh_needed_for_charging(used_battery_level_alternative, 0.0)
                    kwh_solar_alternative = min(charging_plan[day_before]['solar_kwh_prediction'], kwh_needed_today_alternative) if day > 0 else 0.0
                    kwh_needed_today_alternative -= kwh_solar_alternative
                    
                    if kwh_solar_alternative > 0.0:
                        solar_price = charging_plan[day_before]['solar_cost_prediction'] / charging_plan[day_before]['solar_kwh_prediction']
                        
                        location = sun.get_astral_location(hass)
                        sunrise = location[0].sunrise(charging_plan[day]['start_of_day']).replace(tzinfo=None)
                        charge_hours_alternative[sunrise] = {
                            "emoji": emoji_parse({'solar': True}),
                            "day": f"{day} {charging_plan[day]['day_text']}",
                            "used_battery_level_alternative": used_battery_level_alternative,
                            "Price": solar_price,
                            "kWh": kwh_solar_alternative,
                            "Cost": kwh_solar_alternative * solar_price,
                            "solar": True
                        }
                    
                    for timestamp, price in sorted_by_cheapest_price:
                        if timestamp not in charge_hours_alternative and in_between(timestamp, homecoming_alternative - datetime.timedelta(hours=1), last_charging_alternative + datetime.timedelta(hours=1)):
                            working, on_trip = available_for_charging_prediction(timestamp, trip_date_time, trip_homecoming_date_time)
                            if working or on_trip:
                                continue
                            
                            if round(kwh_needed_today_alternative, 1) > 0.0:
                                if (kwh_needed_today_alternative - MAX_KWH_CHARGING) < 0.0:
                                    kwh = kwh_needed_today_alternative
                                    kwh_needed_today_alternative = 0.0
                                else:
                                    kwh = MAX_KWH_CHARGING
                                    kwh_needed_today_alternative -= kwh
                                cost = kwh * price
                                
                                emoji = charging_plan[day_after]['emoji'] if charging_plan[day_after]['emoji'] else "⛽"
                                charge_hours_alternative[timestamp] = {
                                    "emoji": f"{emoji}",
                                    "day": f"{day_after} {charging_plan[day_after]['day_text']}",
                                    "used_battery_level_alternative": used_battery_level_alternative,
                                    "Price": price,
                                    "kWh": kwh,
                                    "Cost": cost
                                }
                            else:
                                break
            except Exception as e:
                _LOGGER.warning(f"Cant create alternative charging estimate for day {day}: {e}")
            
            try:
                if solar_charging_enabled() and charging_plan[day]['solar_prediction'] > 0.0:
                    date = date_to_string(date = charging_plan[day]['start_of_day'], format = "%d/%m")
                    
                    location = sun.get_astral_location(hass)
                    sunrise = location[0].sunrise(charging_plan[day]['start_of_day']).replace(tzinfo=None)
                    sunrise_text = f"{emoji_parse({'sunrise': True})}{date_to_string(date = sunrise, format = '%H:%M')}"
                    sunset = location[0].sunset(charging_plan[day]['start_of_day']).replace(tzinfo=None)
                    sunset_text = f"{emoji_parse({'sunset': True})}{date_to_string(date = sunset, format = '%H:%M')}"
                    
                    timeperiod = []
                    if charging_plan[day]['workday']:
                        if sunrise <= charging_plan[day]['work_goto']:
                            timeperiod.append(f"{sunrise_text}-{emoji_parse({'goto': True})}{date_to_string(date = charging_plan[day]['work_goto'], format = '%H:%M')}")
                            if sunset >= charging_plan[day]['work_homecoming']:
                                timeperiod.append("<br>")
                        if sunset >= charging_plan[day]['work_homecoming']:
                            timeperiod.append(f"{emoji_parse({'homecoming': True})}{date_to_string(date = charging_plan[day]['work_homecoming'], format = '%H:%M')}-{sunset_text}")
                    elif charging_plan[day]['trip']:
                        if sunrise <= charging_plan[day]['trip_goto']:
                            timeperiod.append(f"{sunrise_text}-{emoji_parse({'trip': True})}{date_to_string(date = charging_plan[day]['trip_goto'], format = '%H:%M')}")
                            if sunset >= charging_plan[day]['trip_homecoming']:
                                timeperiod.append("<br>")
                        if sunset >= charging_plan[day]['trip_homecoming']:
                            timeperiod.append(f"{emoji_parse({'homecoming': True})}{date_to_string(date = charging_plan[day]['trip_homecoming'], format = '%H:%M')}-{sunset_text}")
                    else:
                        timeperiod.append(f"{sunrise_text}-{sunset_text}")
                        
                    solar_over_production[day] = {
                        "day": f"{getDayOfWeekText(charging_plan[day]['start_of_day'], translate = True).capitalize()}",
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
                
            if charging_plan[day]['offday']:
                charging_plan[day]['battery_level_at_midnight'].append(charging_plan[day]['offday_battery_level_needed'] * -1)
        #_LOGGER.error(f"charge_hours_alternative:\n{pformat(charge_hours_alternative, width=200, compact=True)}")
        return [totalCost, totalkWh]
    
    trip_planned = is_trip_planned()
    trip_date_time = get_trip_date_time() if get_trip_date_time() != resetDatetime() and trip_planned else None
    trip_homecoming_date_time = get_trip_homecoming_date_time() if get_trip_homecoming_date_time() != resetDatetime() and trip_planned else None
    trip_range = get_trip_range() if get_trip_range() != 0.0 and trip_planned else None
    trip_target_level = get_trip_target_level() if get_trip_target_level() != 0.0 and trip_planned else None
    
    local_energy_prediction_output = local_energy_prediction()
    
    solar_kwh_prediction = local_energy_prediction_output[0]
    solar_price_prediction = local_energy_prediction_output[1]
    
    total_kwh_from_solar_available = solar_kwh_prediction['today']
    total_solar_price = [solar_price_prediction['today']]
    
    if solar_charging_enabled():
        attr_dict = {
            today.date(): f"{round(total_kwh_from_solar_available, 2)}% {round((total_kwh_from_solar_available * average(total_solar_price)), 2)}kr"
            }
        
        for date in [today + datetime.timedelta(days=1), today + datetime.timedelta(days=2), today + datetime.timedelta(days=3), today + datetime.timedelta(days=4)]:
            if date.date() in solar_kwh_prediction:
                attr_dict[date.date()] = f"{round(kwh_to_percentage(solar_kwh_prediction[date], include_charging_loss = True), 2)}% {round((solar_kwh_prediction[date] * solar_price_prediction[date]), 2)}kr"
                total_kwh_from_solar_available += solar_kwh_prediction[date]
                total_solar_price.append(solar_price_prediction[date])
    
        attr_dict['Total'] = f"{round(kwh_to_percentage(total_kwh_from_solar_available, include_charging_loss = True), 2)}% {round(total_kwh_from_solar_available * average(total_solar_price), 2)}kr"
        set_attr(f"sensor.{__name__}_charge_very_cheap_battery_level.unused_solar_production_availability_prediction", attr_dict)
        set_attr(f"sensor.{__name__}_charge_ultra_cheap_battery_level.unused_solar_production_availability_prediction", attr_dict)
    
    ev_charge_very_cheap_battery_level = max(0, int(round(get_very_cheap_grid_charging_max_battery_level() - kwh_to_percentage(total_kwh_from_solar_available, include_charging_loss = True), 0)))
    ev_charge_ultra_cheap_battery_level = max(0, int(round(get_ultra_cheap_grid_charging_max_battery_level() - kwh_to_percentage(total_kwh_from_solar_available, include_charging_loss = True), 0)))
    
    set_state(f"sensor.{__name__}_charge_very_cheap_battery_level", ev_charge_very_cheap_battery_level)
    set_state(f"sensor.{__name__}_charge_ultra_cheap_battery_level", ev_charge_ultra_cheap_battery_level)
    
    workday_rules =["first_workday_preparation", "second_workday_preparation", "third_workday_preparation", "fourth_workday_preparation", "fifth_workday_preparation", "sixth_workday_preparation", "seventh_workday_preparation", "eighth_workday_preparation"]
    workday_labels =["Første arbejdsdag", "Anden arbejdsdag", "Tredje arbejdsdag", "Fjerde arbejdsdag", "Femte arbejdsdag", "Sjette arbejdsdag", "Syvende arbejdsdag", "Ottende arbejdsdag"]
    workday_emoji = []
    
    for i, rule in enumerate(workday_rules):
        workday_labels[i] =  f"{emoji_parse({rule: True})} {workday_labels[i]}"
        workday_emoji.append(f"{emoji_parse({rule: True})}")
    
    charging_plan_warnings = {}
    
    def charging_plan_warnings_add(plan, warning):
        nonlocal charging_plan_warnings
        
        if plan not in charging_plan_warnings:
            charging_plan_warnings[plan] = []
        charging_plan_warnings[plan].append(warning)
    
    for day in range(8):
        start_of_day_datetime = getTimeStartOfDay() + datetime.timedelta(days=day)
        end_of_day_datetime = getTimeEndOfDay() + datetime.timedelta(days=day)
        day_text = getDayOfWeekText(end_of_day_datetime)
        
        charging_plan[day] = {
            "start_of_day": start_of_day_datetime,
            "end_of_day": end_of_day_datetime,
            "trip": False,
            "trip_goto": None,
            "trip_homecoming": None,
            "trip_last_charging": None,
            "trip_kwh_needed": 0.0,
            "trip_battery_level_needed": 0.0,
            "trip_battery_level_above_max": 0.0,
            "trip_total_cost": 0.0,
            "offday": False,
            "offday_range_needed": 0.0,
            "offday_battery_level_needed": 0.0,
            "offday_kwh_needed": 0.0,
            "offday_total_cost": 0.0,
            "work_last_charging": None,
            "work_total_cost": 0.0,
            "workday": False,
            "work_range_needed": 0.0,
            "work_battery_level_needed": 0.0,
            "work_kwh_needed": 0.0,
            "work_goto": None,
            "work_homecoming": None,
            "work_last_charging": None,
            "work_total_cost": 0.0,
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
        
        if workplan_charging_enabled() and get_state(f"input_boolean.{__name__}_workday_{day_text}") == "on":
            work_goto = end_of_day_datetime.replace(hour=get_state(f'input_datetime.{__name__}_workday_departure_{day_text}').hour, minute=get_state(f'input_datetime.{__name__}_workday_departure_{day_text}').minute, second=0)
                
            diff = minutesBetween(now, work_goto)
            if day == 0 and ready_to_charge() and in_between(diff, CHARGING_ALLOWED_AFTER_GOTO_TIME, 0):
                work_goto = work_goto + datetime.timedelta(hours=1)

            if (day == 0 and now < work_goto) or day > 0:
                
                charging_plan['workday_in_week'] = True
                charging_plan[day]['workday'] = True
                
                charging_plan[day]['work_goto'] = work_goto
                charging_plan[day]['work_homecoming'] = end_of_day_datetime.replace(hour=get_state(f'input_datetime.{__name__}_workday_homecoming_{day_text}').hour, minute=get_state(f'input_datetime.{__name__}_workday_homecoming_{day_text}').minute, second=0)
                
                hours_before = max(1, min(2, hoursBetween(now, charging_plan[day]['work_goto'])))
                charging_plan[day]['work_last_charging'] = reset_time_to_hour(work_goto) - datetime.timedelta(hours=hours_before)
                
                charging_plan[day]['work_range_needed'] = get_entity_daily_distance(day_text = day_text)
                charging_plan[day]['work_battery_level_needed'] = calc_distance_to_battery_level(charging_plan[day]['work_range_needed'])
            
                if len(workday_labels) > 0:
                    charging_plan[day]['label'] = workday_labels.pop(0)
                    charging_plan[day]['emoji'] = workday_emoji.pop(0)
                    charging_plan[day]['rules'].append(workday_rules.pop(0))
            
                if charging_plan[day]['work_goto'] == charging_plan[day]['work_homecoming']:
                    charging_plan_warnings_add("work", f"{getDayOfWeekText(end_of_day_datetime, translate = True).capitalize()} afgang og hjemkomst er ens")
                    
                if charging_plan[day]['work_range_needed'] == 0.0:
                    charging_plan_warnings_add("work", f"{getDayOfWeekText(end_of_day_datetime, translate = True).capitalize()}safstand i alt er 0 km")
        
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
                charging_plan[day]['trip_battery_level_needed'] = range_to_battery_level(trip_range, get_min_trip_battery_level(), trip_date_time)
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
                
                if (charging_plan[day]['workday'] and
                ((charging_plan[day]['trip_last_charging'] < charging_plan[day]['work_homecoming'] and charging_plan[day]['trip_last_charging'] > charging_plan[day]['work_last_charging']) or
                (getTime() > charging_plan[day]['work_last_charging'] and battery_level() < max_recommended_battery_level - 1))):
                    charging_plan[day]['trip_last_charging'] = max(charging_plan[day]['work_last_charging'], reset_time_to_hour(getTime()))
                    last_charging = charging_plan[day]['trip_last_charging']

                for i in range(charging_hours):
                    charging_hour = last_charging - datetime.timedelta(hours=i)
                    
                    try:
                        hour_in_chargeHours, kwh_available = kwh_available_in_hour(charging_hour)
                        very_cheap_price, ultra_cheap_price = cheap_price_check(hour_prices[charging_hour])
                        
                        trip_kwh_needed, totalCost, totalkWh, battery_level_added, cost_added = add_to_charge_hours(trip_kwh_needed, totalCost, totalkWh, charging_hour, hour_prices[charging_hour], very_cheap_price, ultra_cheap_price, kwh_available, max_recommended_battery_level, None, trip_target_level, ['trip'])
                        charging_plan[day]['trip_kwh_needed'] += percentage_to_kwh(battery_level_added, include_charging_loss=False)
                        charging_plan[day]["trip_total_cost"] += chargeHours[charging_hour]["Cost"]
                        
                        charging_sessions_id = "battery_level_before_work"
                        
                        work_goto = charging_plan[day]['work_goto']
                        if not charging_plan[day]['work_goto']:
                            work_goto = charging_plan[day]['end_of_day']
                        
                        if charging_plan[day]['trip_goto'] >= work_goto:
                            charging_plan[day]['battery_level_after_work'].append(battery_level_added)
                            charging_sessions_id = "battery_level_after_work" if charging_plan[day]['trip_goto'] >= work_goto else "battery_level_before_work"
                        else:
                            charging_plan[day]['battery_level_before_work'].append(battery_level_added)
                            charging_plan[day]['battery_level_after_work'].append(battery_level_added)
                    
                        if charging_sessions_id not in charging_plan[day]['charging_sessions']:
                            charging_plan[day]['charging_sessions'][charging_sessions_id] = {}
                        charging_plan[day]['charging_sessions'][charging_sessions_id][charging_hour] = chargeHours[charging_hour]
                    except Exception as e:
                        _LOGGER.warning(f"Date not yet in database: {charging_hour} ({e})")
        elif fill_up_charging_enabled():
            charging_plan[day]['offday'] = True
            charging_plan[day]['offday_range_needed'] = get_entity_daily_distance()
            charging_plan[day]['offday_battery_level_needed'] = calc_distance_to_battery_level(charging_plan[day]['offday_range_needed'])
            charging_plan[day]['offday_kwh_needed'] = percentage_to_kwh(charging_plan[day]['offday_battery_level_needed'], include_charging_loss=True)
            charging_plan[day]['emoji'] = emoji_parse({'fill_up': True})
            
        charging_plan[day]['trip_battery_level_needed'] = max(charging_plan[day]['trip_battery_level_needed'], 0.0)
        
        charging_plan[day]['total_needed_battery_level'] = (charging_plan[day]['work_battery_level_needed'] + get_min_daily_battery_level()) if charging_plan[day]['workday'] else 0.0
        charging_plan[day]['total_needed_battery_level'] += charging_plan[day]['trip_battery_level_needed'] + charging_plan[day]['trip_battery_level_above_max']
        charging_plan[day]['total_needed_battery_level'] = min(round_up(charging_plan[day]['total_needed_battery_level']), 100.0)
        
        total_solar_available = 0.0
        total_solar_available_price = []
        
        if solar_charging_enabled():
            if day == 0 and ((charging_plan[day]['workday'] and getTime() >= charging_plan[day]['work_homecoming']) or not charging_plan[day]['workday']):
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
    
    if charging_plan_warnings:
        warning_message = ""
        for plan in charging_plan_warnings.keys():
            warning_message += f"### Fejl i opsætningen af Arbejdsplan opladning\n"
            for warning in charging_plan_warnings[plan]:
                warning_message += f"- **{warning}**\n"
        my_persistent_notification(warning_message, f"{TITLE} Fejl i opladningsstrategier", persistent_notification_id=f"{__name__}_charging_plan_warnings")
    
    totalCost, totalkWh = future_charging(totalCost, totalkWh)
    
    chargeHours['total_cost'] = totalCost
    chargeHours['total_kwh'] = totalkWh
    chargeHours['total_procent'] = round(kwh_to_percentage(totalkWh, include_charging_loss = True), 2)
    
    expensiveList = []
    expensiveDict = {}
    
    for timestamp, price in get_expensive_hours().items():
        expensiveList.append(timestamp)
        expensiveDict[str(timestamp)] = f"{price:.2f} kr"
        
    set_attr(f"input_boolean.{__name__}_forced_charging_daily_battery_level.expensive_hours", dict(sorted(expensiveDict.items())))
    chargeHours['expensive_hours'] = expensiveList
    
    todays_max_battery_level = max(sum(charging_plan[0]["battery_level_before_work"]), sum(charging_plan[0]["battery_level_at_midnight"]), sum(charging_plan[0]["battery_level_after_work"]))
    tomorrow_max_battery_level = max(sum(charging_plan[1]["battery_level_before_work"]), sum(charging_plan[1]["battery_level_at_midnight"]), sum(charging_plan[1]["battery_level_after_work"]))
    chargeHours['max_charging_level_today'] = round(max(todays_max_battery_level, tomorrow_max_battery_level, charging_plan[day]['total_needed_battery_level'], get_min_charge_limit_battery_level()), 2)
    
    if chargeHours['max_charging_level_today'] > get_max_recommended_charge_limit_battery_level():
        chargeHours['max_charging_level_today'] = max(get_max_recommended_charge_limit_battery_level(), get_trip_target_level())
        
    '''_LOGGER.error(f"todays_max_battery_level:{todays_max_battery_level}")
    _LOGGER.error(f"tomorrow_max_battery_level:{tomorrow_max_battery_level}")
    _LOGGER.error(f"charging_plan[day]['total_needed_battery_level']:{charging_plan[day]['total_needed_battery_level']}")
    _LOGGER.error(f"get_min_charge_limit_battery_level:{get_min_charge_limit_battery_level()}")
    _LOGGER.error(f"chargeHours['max_charging_level_today']:{chargeHours['max_charging_level_today']}")'''

    for day in charging_plan.keys():
        if not isinstance(day, int): continue
        charging_plan[day]['battery_level_before_work_sum'] = sum(charging_plan[day]['battery_level_before_work'])
        charging_plan[day]['battery_level_after_work_sum'] = sum(charging_plan[day]['battery_level_after_work'])
        charging_plan[day]['battery_level_at_midnight_sum'] = sum(charging_plan[day]['battery_level_at_midnight'])

    _LOGGER.debug(f"charging_plan:\n{pformat(charging_plan, width=200, compact=True)}")
    _LOGGER.debug(f"chargeHours:\n{pformat(chargeHours, width=200, compact=True)}")
    
    charging_plan_attr = dict()
    charging_hours_attr = dict()
    try:
        for key, value in charging_plan.items():
            if isinstance(key, int):
                title = f"Day {key} {str(value['day_text']).capitalize().replace('_', ' ')} ({value['label'] if value['label'] else ''})"
                charging_plan_attr[title] = {}
                for k, v in value.items():
                    if "_sum" in k or k == "total_needed_battery_level" and v:
                        charging_plan_attr[title][str(k).capitalize().replace("_", " ").replace("sum", "")] = f"{v:.2f}%"
                    
                    if "solar_" in k and v:
                        if "kwh" in k:
                            charging_plan_attr[title][str(k).capitalize().replace("_", " ")] = f"{v:.2f} kWh"
                        elif "cost" in k:
                            charging_plan_attr[title][str(k).capitalize().replace("_", " ")] = f"{v:.2f} kr"
                        else :
                            charging_plan_attr[title][str(k).capitalize().replace("_", " ")] = f"{v:.2f}%"
                        
                    if (k == "workday" and v) or (k == "trip" and v):
                        if k == "workday":
                            charging_plan_attr[title]["Work goto"] = f"{value["work_goto"]}"
                            charging_plan_attr[title]["Work homecoming"] = f"{value["work_homecoming"]}"
                            charging_plan_attr[title]["Work last_charging"] = f"{value["work_last_charging"]}"
                            charging_plan_attr[title]["Work range_needed"] = f"{value["work_range_needed"]} km"
                            charging_plan_attr[title]["Work total_cost"] = f"{value["work_total_cost"]:.2f} kr"
                            charging_plan_attr[title]["Work battery level needed"] = f"{value["work_battery_level_needed"]:.2f}%"
                            charging_plan_attr[title]["Work kwh_needed"] = f"{value["work_kwh_needed"]:.2f} kWh"
                        if k == "trip":
                            charging_plan_attr[title]["Trip goto"] = f"{value["trip_goto"]}"
                            charging_plan_attr[title]["Trip homecoming"] = f"{value["trip_homecoming"]}"
                            charging_plan_attr[title]["Trip last charging"] = f"{value["trip_last_charging"]}"
                            charging_plan_attr[title]["Trip total cost"] = f"{value["trip_total_cost"]:.2f} kr"
                            charging_plan_attr[title]["Trip battery level needed"] = f"{value["trip_battery_level_needed"]:.2f}%"
                            charging_plan_attr[title]["Trip battery level above max"] = f"{value["trip_battery_level_above_max"]:.2f}%"
                            charging_plan_attr[title]["Trip kWh needed"] = f"{value["trip_kwh_needed"]:.2f} kWh"
                charging_plan_attr[title] = dict(sorted(charging_plan_attr[title].items()))
    except Exception as e:
        _LOGGER.error(f"Failed to create charging plan attributes: {e}")
        _LOGGER.error(f"charging_plan:\n{pformat(charging_plan, width=200, compact=True)}")

    try:
        for key, value in chargeHours.items():
            if key == "expensive_hours":
                charging_hours_attr[str(key).capitalize().replace("_", " ")] = value
            elif key == "max_charging_level_today":
                charging_hours_attr[str(key).capitalize().replace("_", " ")] = f"{value:.2f}%" if value else "0.0%"
            elif key == "total_procent":
                charging_hours_attr[str(key).capitalize().replace("_", " ")] = f"{value:.2f}%"
            elif key == "total_kwh":
                charging_hours_attr[str(key).capitalize().replace("_", " ")] = f"{value:.2f} kWh"
            elif key == "total_cost":
                charging_hours_attr[str(key).capitalize().replace("_", " ")] = f"{value:.2f} kr"
            else:
                charging_hours_attr[str(key)] = [f"{value['battery_level']:.2f}%", f"{value['kWh']:.2f} kWh", f"{value['Cost']:.2f} kr"]
    except Exception as e:
        _LOGGER.error(f"Failed to create charging plan charging_hours attributes: {e}")
        _LOGGER.error(f"charging_plan:\n{pformat(charging_plan, width=200, compact=True)}")
    
    set_attr(f"sensor.ev_current_charging_rule.charging_plan", charging_plan_attr)
    set_attr(f"sensor.ev_current_charging_rule.charging_hours", charging_hours_attr)
    
    old_charge_hours = CHARGE_HOURS.copy()
    
    CHARGING_PLAN = charging_plan
    CHARGE_HOURS = chargeHours
    
    if check_next_24_hours_diff(old_charge_hours, chargeHours) and old_charge_hours:
        append_overview_output("Charging plan changed, next 24 hours updated")
        
    overview = []
    
    try:
        if LAST_DRIVE_EFFICIENCY_DATA:
            kr_km = round(LAST_DRIVE_EFFICIENCY_DATA['cost'] / LAST_DRIVE_EFFICIENCY_DATA['distance'], 2) if LAST_DRIVE_EFFICIENCY_DATA['distance'] > 0 else 0.0
            
            overview.append("<center>\n")
            overview.append("## 🛣️ Sidste kørsel effektivitet ##")
            overview.append("|  |  |")
            overview.append("|:---|---:|")
            overview.append(f"| **📅 Kørselsdato** | **{date_to_string(LAST_DRIVE_EFFICIENCY_DATA['timestamp'], format='%d/%m %H:%M')}** |")
            overview.append(f"| **🚗 Sidste kørsel afstand** | **{round(LAST_DRIVE_EFFICIENCY_DATA['distance'], 1):.1f} km** |")
            overview.append(f"| **🔋 Brugt batteri** | **{round(LAST_DRIVE_EFFICIENCY_DATA['usedBattery'], 1):.1f}% ({round(LAST_DRIVE_EFFICIENCY_DATA['usedkWh'], 2):.2f} kWh)** |")
            overview.append(f"| **💰 Udgift** | **{round(LAST_DRIVE_EFFICIENCY_DATA['cost'], 2):.2f} kr ({kr_km:.2f} kr/km)**")
            overview.append(f"| **📊 Kørsel effektivitet** | **{round(LAST_DRIVE_EFFICIENCY_DATA['efficiency'], 1):.1f}%** |")
            overview.append(f"| **📏 Afstand pr. kWh** | **{round(LAST_DRIVE_EFFICIENCY_DATA['distancePerkWh'], 2):.2f} km/kWh ({LAST_DRIVE_EFFICIENCY_DATA['wh_km']} Wh/km)** |")
            overview.append("***")
            overview.append("</center>\n")
    except Exception as e:
        _LOGGER.error(f"Failed to calculate last drive efficiency: {e}")
    
    try:
        battery_level_expenses_report = BATTERY_LEVEL_EXPENSES["battery_level_expenses_cost"]
        battery_level_expenses_kwh_report = BATTERY_LEVEL_EXPENSES["battery_level_expenses_kwh"]
        battery_level_expenses_solar_percentage_report = BATTERY_LEVEL_EXPENSES["battery_level_expenses_solar_percentage"]
        battery_level_expenses_unit_report = BATTERY_LEVEL_EXPENSES['battery_level_expenses_unit'] if BATTERY_LEVEL_EXPENSES['battery_level_expenses_unit'] is not None else 0.0
        
        if battery_level_expenses_kwh_report > 0.0:
            overview.append("<center>\n")
            overview.append("## 🔎 Batteri niveau udgifter ##")
            overview.append("|  |  |")
            overview.append("|:---|---:|")
            overview.append(f"| **🔋 Nuværende batteri niveau** | **{round(battery_level(), 0):.0f}% {round(battery_level_expenses_kwh_report, 1):.1f} kWh** |")
            
            if battery_level_expenses_solar_percentage_report > 0.0:
                overview.append(f"| **☀️ Solcelle andel** | **{round(battery_level_expenses_solar_percentage_report,0):.0f}% {round(percentage_to_kwh(battery_level_expenses_solar_percentage_report), 1)} kWh** |")
                
            overview.append(f"| **💰 Udgift** | **{round(battery_level_expenses_report, 2):.2f} kr** |")
            overview.append(f"| **🧮 Enhedspris** | {round(percentage_to_kwh(battery_level_expenses_unit_report, include_charging_loss=True), 2):.2f} kr/% **{round(battery_level_expenses_unit_report, 2):.2f} kr/kWh** |")
            overview.append("</center>\n")
            overview.append("***")
    except Exception as e:
        _LOGGER.error(f"Failed to calculate battery level cost: {e}")
        
    try:
        def planning_basis_markdown():
            nonlocal overview
            
            if "last_update" in LAST_SUCCESSFUL_GRID_PRICES:
                overview.append(f"\n\n<details><summary>Se planlægningsgrundlag</summary>\n")
                overview.extend(get_hours_plan())
                overview.append("</details>\n")
        
        sorted_charge_hours = sorted(
            {k: v for k, v in chargeHours.items() if isinstance(k, datetime.datetime)}.items(),
            key=lambda kv: kv[0]
        )
        
        merged_intervals = []
        has_combined = False
        current_interval = None
        
        for timestamp, value in sorted_charge_hours:
            if current_interval is None:
                current_interval = {
                    "start": timestamp,
                    "end": timestamp,
                    "type": emoji_parse(value),
                    "percentage": value['battery_level'],
                    "kWh": round(value['kWh'], 2),
                    "cost": round(value['Cost'], 2),
                    "unit": round(value['Price'], 2),
                }
            else:
                if timestamp == current_interval["end"].replace(minute=0) + datetime.timedelta(hours=1) and daysBetween(current_interval["start"], timestamp) == 0:
                    has_combined = True
                    current_interval["end"] = timestamp
                    current_interval["type"] = join_unique_emojis(current_interval["type"], emoji_parse(value))
                    current_interval["percentage"] += value['battery_level']
                    current_interval["kWh"] += round(value['kWh'], 2)
                    current_interval["cost"] += round(value['Cost'], 2)
                else:
                    merged_intervals.append(current_interval)
                    current_interval = {
                        "start": timestamp,
                        "end": timestamp,
                        "type": emoji_parse(value),
                        "percentage": value['battery_level'],
                        "kWh": round(value['kWh'], 2),
                        "cost": round(value['Cost'], 2),
                        "unit": round(value['Price'], 2),
                    }
        
        if current_interval:
            merged_intervals.append(current_interval)
        
        overview.append("<center>\n")
        overview.append("## 📖 Lade oversigt ##")
        
        if merged_intervals:
            overview.append("|  | Tid | % | kWh | Kr/kWh | Pris |")
            overview.append("|---:|:---:|---:|---:|:---:|---:|")
            
            for d in merged_intervals:
                if d['start'].strftime('%H') == d['end'].strftime('%H'):
                    time_range = f"{d['start'].strftime('%d/%m %H:%M')}"
                else:
                    time_range = f"{d['start'].strftime('%d/%m %H')}-{d['end'].strftime('%H:%M')}"
                
                overview.append(f"| {emoji_text_format(d['type'], group_size=3)} | **{time_range}** | **{int(round(d['percentage'], 0))}** | **{d['kWh']:.2f}** | **{d['unit']:.2f}** | **{d['cost']:.2f}** |")
            
            if has_combined:
                overview.append(f"\n<details><summary><b>Ialt {int(round(chargeHours['total_procent'],0))}% {chargeHours['total_kwh']} kWh {chargeHours['total_cost']:.2f} kr ({round(chargeHours['total_cost'] / chargeHours['total_kwh'],2)} kr/kWh)</b></summary>")
                overview.append("\n|  | Tid | % | kWh | Kr/kWh | Pris |")
                overview.append("|---:|:---:|---:|---:|:---:|---:|")
                
                for timestamp, value in sorted_charge_hours:
                    overview.append(f"| {emoji_parse(value)} | **{timestamp.strftime('%d/%m %H:%M')}** | **{int(round(value['battery_level'], 0))}** | **{round(value['kWh'], 2):.2f}** | **{round(value['Price'], 2):.2f}** | **{round(value['Cost'], 2):.2f}** |")
                
                planning_basis_markdown()
                    
                overview.append("</details>\n")
            else:
                overview.append(f"\n**Ialt {int(round(chargeHours['total_procent'],0))}% {chargeHours['total_kwh']} kWh {chargeHours['total_cost']:.2f} kr ({round(chargeHours['total_cost'] / chargeHours['total_kwh'],2)} kr/kWh)**")
                
                planning_basis_markdown()
            
            if USING_OFFLINE_PRICES:
                overview.append(f"\n\n<details><summary><b>Bruger offline priser til nogle timepriser!!!</b></summary>\n")
                overview.append("\n| Tidspunkt | &nbsp;&nbsp; | Pris |")
                overview.append("|:---:|:---:|:---:|")
                
                missing_hours_list = [f"| ***{timestamp.strftime('%d/%m %H:%M')}*** |  | {price:.2f}kr |" for timestamp, price in LAST_SUCCESSFUL_GRID_PRICES["missing_hours"].items()]
                overview.append("\n".join(missing_hours_list))
                
                overview.append("</details>\n\n")
            
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
        work_overview_total_kwh = []
        work_overview_total_cost = []
        
        overview.append("<center>\n")
        overview.append("## 🗓️ Afgangsplan ##")
        
        if work_overview:
            solar_header = f"{emoji_parse({'solar': True})}Sol" if is_solar_configured() else ""
            overview.append(f"|  | Dag | Behov | {solar_header} | Pris |")
            overview.append(f"|:---|:---:|:---:|:---:|:---:|")
            
            
            for k, d in work_overview.items():
                work_overview_total_kwh.append(d['kwh_needed'])
                work_overview_total_cost.append(d['cost'])
                
                battery_usage = ""
                
                if k % 1 == 0:
                    if d["event_type"] == "trip":
                        total_trip_battery_level_needed = max((charging_plan[int(k)]['trip_battery_level_needed'] + charging_plan[int(k)]['trip_battery_level_above_max'] - get_min_trip_battery_level()), 0.0)
                        battery_level_before_trip_sum = int(round(charging_plan[int(k)]['battery_level_after_work_sum'],0))
                        battery_level_after_trip_sum = int(round(battery_level_before_trip_sum - total_trip_battery_level_needed,0))
                        battery_usage = f"<br>{emoji_parse({'battery_usage': True})}{battery_level_before_trip_sum}-{battery_level_after_trip_sum}%"
                    elif d["event_type"] == "work":
                        battery_level_before_work_sum = int(round(charging_plan[int(k)]['battery_level_before_work_sum'],0))
                        battery_level_after_work_sum = int(round(battery_level_before_work_sum - d['battery_needed'],0))
                        battery_usage = f"<br>{emoji_parse({'battery_usage': True})}{battery_level_before_work_sum}-{battery_level_after_work_sum}%"
                    else:
                        battery_level_at_midnight_sum = int(round(min(charging_plan[int(k)]['battery_level_at_midnight_sum'] + d['battery_needed'], 100.0),0))
                        battery_level_after_offday_sum = int(round(battery_level_at_midnight_sum - d['battery_needed'],0))
                        battery_usage = f"<br>{emoji_parse({'battery_usage': True})}{battery_level_at_midnight_sum}-{battery_level_after_offday_sum}%"
                    
                
                d['emoji'] = f"**{emoji_text_format(d['emoji'])}**" if d['emoji'] else ""
                d['day'] = f"**{d['day']}**" if d['day'] else ""
                d['date'] = f"**{d['date']}**" if d['date'] else ""
                d['goto'] = f"**{d['goto']}**" if d['goto'] else ""
                d['goto'] = f"{d['goto']}**-{d['homecoming']}**" if d['goto'] and d['homecoming'] else d['goto']
                d['battery_needed'] = f"{int(d['battery_needed'])}" if d['battery_needed'] else ""
                d['kwh_needed'] = f"**{round(d['kwh_needed'], 1)}**" if d['kwh_needed'] else ""
                d['cost'] = f"**{d['cost']:.2f}**" if d['cost'] else ""
                d['from_grid'] = emoji_parse({'grid_charging': True}) if d['from_grid'] > 0.0 else ""
                d['from_battery'] = emoji_parse({'battery_stored': True}) if d['from_battery'] > 0.0 else ""
                d['from_battery_solar'] = emoji_parse({'battery_stored': True}) if d['from_battery_solar'] > 0.0 else ""
                d['solar'] = f"{emoji_parse({'solar': True})}{d['solar']}" if d['solar_kwh'] > 0.0 and is_solar_configured() else ""
                
                need_label = f"**{d['from_grid']}{d['from_battery']}{d['battery_needed']}% {d['kwh_needed']}kWh{battery_usage}**" if d['battery_needed'] or d['kwh_needed'] else ""
                solar_label = f"**{d['from_battery_solar']}{d['solar']}**" if d['solar'] and is_solar_configured() else ""
                
                overview.append(f"| {d['emoji']} | {d['day']}<br>{d['date']}<br>{d['goto']} | {need_label} | {solar_label} | {d['cost']} |")
        else:
            overview.append(f"**Ingen kommende afgang planlagt**")
        
        work_overview_total_kwh_sum = sum(work_overview_total_kwh)
        work_overview_total_cost_sum = sum(work_overview_total_cost)
        work_overview_per_kwh = work_overview_total_cost_sum / work_overview_total_kwh_sum if work_overview_total_kwh_sum > 0.0 else 0.0
        
        if work_overview_total_kwh_sum > 0.0:
            overview.append(f"\n**Ialt {round(work_overview_total_kwh_sum, 1):.1f}kWh {round(work_overview_total_cost_sum, 2):.2f}kr ({round(work_overview_per_kwh, 2):.2f} kr/kWh)**")
            
            work_overview_solar_text = "solcelle & " if is_solar_configured() else ""
            overview.append(f"##### 📎Afgangsplan inkludere estimeret udgifter fra nettet, {work_overview_solar_text}batteri niveau #####")
        
        overview_alternative = []
        total_kwh_charge_hours_alternative = []
        total_cost_charge_hours_alternative = []
        
        for timestamp, value in sorted({k: v for k, v in charge_hours_alternative.items() if type(k) is datetime.datetime}.items(), key=lambda kv: (kv[0])):
            timestamp_str = timestamp.strftime('%d/%m %H:%M')
            if "solar" in value:
                timestamp_str = timestamp.strftime('%d/%m')

            overview_alternative.append(f"| {value['emoji']} | **{timestamp_str}** | **{int(round(kwh_to_percentage(value['kWh'], include_charging_loss=True),0))}** | **{round(value['kWh'], 2):.2f}** | **{round(value['Price'], 2):.2f}** | **{round(value['Cost'], 2):.2f}** |")
            total_kwh_charge_hours_alternative.append(value['kWh'])
            total_cost_charge_hours_alternative.append(value['Cost'])
            
        total_kwh_charge_hours_alternative_sum = sum(total_kwh_charge_hours_alternative)
        total_cost_charge_hours_alternative_sum = sum(total_cost_charge_hours_alternative)
        total_charge_hours_per_kwh_alternative = total_cost_charge_hours_alternative_sum / total_kwh_charge_hours_alternative_sum if total_kwh_charge_hours_alternative_sum > 0.0 else 0.0
        
        
        if work_overview_total_kwh_sum > 0.0 and total_kwh_charge_hours_alternative_sum > 0.0:
            overview.append("<details>")
            overview.append(f"<summary>Skøn ved daglig opladning {round(total_charge_hours_per_kwh_alternative * work_overview_total_kwh_sum, 2):.2f}kr {round(total_charge_hours_per_kwh_alternative, 2):.2f}kr/kWh<br>ved {round(work_overview_total_kwh_sum, 1):.1f}kWh forskel {round((total_charge_hours_per_kwh_alternative * work_overview_total_kwh_sum) - work_overview_total_cost_sum, 2):.2f}kr</summary>\n")
                        
            overview.append("### Lade oversigt (**Dagligt opladningsskøn**) ###")
            overview.append("|  | Tid | % | kWh | Kr/kWh | Pris |")
            overview.append("|---:|:---:|---:|---:|:---:|---:|")
            
            overview.extend(overview_alternative)
            
            overview.append(f"\n**Ialt {round(total_kwh_charge_hours_alternative_sum, 1):.1f}kWh {round(total_cost_charge_hours_alternative_sum, 2):.2f}kr {round(total_charge_hours_per_kwh_alternative, 2):.2f}kr/kWh**")

            overview.append("</details>\n")
            
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
            overview.append("<center>\n")
            overview.append("## 🌞 Solcelle over produktion ##")
            
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

def calc_charging_amps(power = 0.0, max_allowed = None, report = False):
    _LOGGER = globals()['_LOGGER'].getChild("calc_charging_amps")
    power = float(power)
    power = power
    
    powerDict = {}
    
    if float(CONFIG['solar']['charging_single_phase_max_amp']) > 0.0:
        for i in range(int(CONFIG['solar']['charging_single_phase_min_amp']),int(CONFIG['solar']['charging_single_phase_max_amp']) + 1):
            watt = float(i) * CONFIG['charger']['power_voltage']
            powerDict[watt] = {
                "amp": float(i),
                "phase": 1.0,
                "watt": watt
            }

    maxSinglePhaseWatt = max(powerDict.keys()) if powerDict else 0.0

    for i in range(int(CONFIG['solar']['charging_three_phase_min_amp']),int(CONFIG['charger']['charging_max_amp']) + 1):
        watt = float(i) * (CONFIG['charger']['power_voltage']  * CONFIG['charger']['charging_phases'])
        if maxSinglePhaseWatt < watt or maxSinglePhaseWatt == 0.0:
            powerDict[watt] = {
                "amp": float(i),
                "phase": CONFIG['charger']['charging_phases'],
                "watt": watt
            }
    
    minWatt = min(powerDict.keys()) - 50.0
    powerDict[minWatt] = {
            "amp": 0.0,
            "phase": CONFIG['charger']['charging_phases'],
            "watt": 0.0
            }
    
    if report:
        log_lines = []
        if is_solar_configured():
            log_lines.append("### Charging amps ###")
            example_1 = 500 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            example_2 = 1500 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            example_3 = 3000 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            example_4 = 4000 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            example_5 = 5000 + CONFIG['solar']['allow_grid_charging_above_solar_available']
            log_lines.append(f"Voltage above(+)/under(-) overproduction available: {CONFIG['solar']['allow_grid_charging_above_solar_available']}W")
            log_lines.append("Solar overproduction examples:")
            log_lines.append(f"1. overproduction 500W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_1}W {get_closest_key(example_1, powerDict)}")
            log_lines.append(f"2. overproduction 1500W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_2}W {get_closest_key(example_2, powerDict)}")
            log_lines.append(f"3. overproduction 3000W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_3}W {get_closest_key(example_3, powerDict)}")
            log_lines.append(f"4. overproduction 4000W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_4}W {get_closest_key(example_4, powerDict)}")
            log_lines.append(f"5. overproduction 5000W + {CONFIG['solar']['allow_grid_charging_above_solar_available']}W={example_5}W {get_closest_key(example_5, powerDict)}\n")
            log_lines.append("Solar overproduction charging:")
            
            first = "<"
            for key in sorted(powerDict):
                log_lines.append(f"{first}{int(key)} W: {int(powerDict[key]['amp'])} A {int(powerDict[key]['phase'])} phase = {int(powerDict[key]['watt'])} W")
                first = ""
        else:
            log_lines.append(f"Max charging: {CONFIG['charger']['charging_max_amp']}A {CONFIG['charger']['charging_phases']} phase = {MAX_WATT_CHARGING}W")
        return "\n".join(log_lines)
    output = get_closest_key(power, powerDict, max_allowed=max_allowed)
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
        integration = get_integration(CONFIG['charger']['entity_ids']['status_entity_id'])
            
        if not is_entity_available(CONFIG['charger']['entity_ids']['status_entity_id']):
            raise Exception(f"Ev charger integration ({integration}) unavailable: {CONFIG['charger']['entity_ids']['status_entity_id']}")
        
        if integration == "easee":
            charger_id = get_attr(CONFIG['charger']['entity_ids']['status_entity_id'], "id", error_state=None)
            if not charger_id:
                raise Exception(f"No charger id found for {CONFIG['charger']['entity_ids']['status_entity_id']} return id: {str(charger_id)}")
            
            if service.has_service(integration, "set_circuit_dynamic_limit"):
                service.call(integration, "set_circuit_dynamic_limit", blocking=True,
                                    charger_id=get_attr(CONFIG['charger']['entity_ids']['status_entity_id'], "id"),
                                    current_p1=phase_1,
                                    current_p2=phase_2,
                                    current_p3=phase_3,
                                    time_to_live=60)
            else:
                raise Exception("Easee integration dont has service set_circuit_dynamic_limit")
            
            if service.has_service(integration, "set_charger_dynamic_limit"):
                service.call(integration, "set_charger_dynamic_limit", blocking=True,
                                    charger_id=get_attr(CONFIG['charger']['entity_ids']['status_entity_id'], "id"),
                                    current=max(phase_1, phase_2, phase_3))
            else:
                raise Exception("Easee integration dont has service set_charger_dynamic_limit")
        else:
            raise(Exception(f"Charger brand is not Easee: {integration}"))
        successful = True
        
        _LOGGER.info(f"Setting chargers({charger_id}) charging amps to {phase_1}/{phase_2}/{phase_3} watt:{watt}")
    except Exception as e:
        _LOGGER.warning(f"Cant set dynamic amps on charger: {e}")
        _LOGGER.warning(f"Setting ev cars charging amps to {amps}")
        my_persistent_notification(f"Cant set dynamic amps on charger: {e}\nSetting ev cars charging amps to {amps}", f"{TITLE} warning", persistent_notification_id=f"{__name__}_dynamic_charging_amps")
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
            error_message = f"Cant set dynamic amps on charger: {e}\nCant set ev charging amps: {e_second}"
            _LOGGER.error(error_message)
            save_error_to_file(error_message, caller_function_name = f"set_charger_charging_amps(phase = {phase}, amps = {amps}, watt = {watt})")
            my_persistent_notification(error_message, f"{TITLE} error", persistent_notification_id=f"{__name__}_charging_amps")
    
    try:
        if is_ev_configured() and is_entity_configured(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id']):
            if not is_entity_available(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id']):
                raise Exception(f"Ev charging amps entity unavailable: {CONFIG['ev_car']['entity_ids']['charging_amps_entity_id']}")
            
            max_amps = float(get_attr(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id'], "max"))
            current_amps = float(get_state(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id']))
            if current_amps == 0.0:
                _LOGGER.info(f"Ev charging amps was set to 0 amps, setting ev to max {max_amps}")
                ev_send_command(CONFIG['ev_car']['entity_ids']['charging_amps_entity_id'], max_amps)
    except Exception as e:
        error_message = f"Cant set ev charging amps to {CONFIG['charger']['charging_max_amp']}: {e}"
        _LOGGER.warning(error_message)
        save_error_to_file(error_message, caller_function_name = f"set_charger_charging_amps(phase = {phase}, amps = {amps}, watt = {watt})")
        my_persistent_notification(error_message, f"{TITLE} warning", persistent_notification_id=f"{__name__}_ev_charging_amps")
            
            
    if successful:
        CURRENT_CHARGING_AMPS = [phase_1, phase_2, phase_3]
    else:
        _LOGGER.warning(f"Cant set charger to phase:{phase} amps:{phase_1}/{phase_2}/{phase_3} watt:{watt}")

def power_from_ignored(from_time_stamp, to_time_stamp):
    _LOGGER = globals()['_LOGGER'].getChild("power_from_ignored")
    
    def average_since_sum(entity_id):
        _LOGGER = globals()['_LOGGER'].getChild("power_from_ignored.average_since_sum")
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

def powerwall_max_charging_power(period=60):
    _LOGGER = globals()['_LOGGER'].getChild("powerwall_max_charging_power")
    
    if not is_powerwall_configured():
        return 0.0
    
    to_time_stamp = getTime()
    from_time_stamp = to_time_stamp - datetime.timedelta(minutes=period)
            
    max_power = CONFIG['solar']['powerwall_charging_power_limit']

    try:
        powerwall_values = get_values(CONFIG['home']['entity_ids']['powerwall_watt_flow_entity_id'], from_time_stamp, to_time_stamp, float_type=True, convert_to="W", error_state=None)
        
        if powerwall_values is None or len(powerwall_values) == 0:
            raise Exception(f"No powerwall values for {CONFIG['home']['entity_ids']['powerwall_watt_flow_entity_id']} found from {from_time_stamp} to {to_time_stamp}")
        
        if CONFIG['home']['invert_powerwall_watt_flow_entity_id']:
            max_power = abs(max(get_specific_values(powerwall_values, positive_only = True)))
        else:
            max_power = abs(min(get_specific_values(powerwall_values, negative_only = True)))
    except Exception as e:
        _LOGGER.warning(f"Cant get powerwall values for {CONFIG['home']['entity_ids']['powerwall_watt_flow_entity_id']}from {from_time_stamp} to {to_time_stamp}: {e}")
        
    return max_power

def charge_from_powerwall(from_time_stamp, to_time_stamp):
    _LOGGER = globals()['_LOGGER'].getChild("charge_from_powerwall")
    
    if not is_powerwall_configured():
        return 0.0
    
    powerwall_charging_consumption = 0.0
    
    try:
        if is_powerwall_configured():
            powerwall_values = get_values(CONFIG['home']['entity_ids']['powerwall_watt_flow_entity_id'], from_time_stamp, to_time_stamp, float_type=True, convert_to="W", error_state=[0.0])
            
            if CONFIG['home']['invert_powerwall_watt_flow_entity_id']:
                powerwall_charging_consumption = abs(round(average(get_specific_values(powerwall_values, positive_only = True)), 0))
            else:
                powerwall_charging_consumption = abs(round(average(get_specific_values(powerwall_values, negative_only = True)), 0))
    except Exception as e:
        _LOGGER.warning(f"Cant get powerwall values from {from_time_stamp} to {to_time_stamp}: {e}")
        
    return powerwall_charging_consumption

def discharge_from_powerwall(from_time_stamp, to_time_stamp):
    _LOGGER = globals()['_LOGGER'].getChild("discharge_from_powerwall")
    
    if not is_powerwall_configured():
        return 0.0
    
    powerwall_discharging_consumption = 0.0
    
    try:
        if is_powerwall_configured():
            powerwall_values = get_values(CONFIG['home']['entity_ids']['powerwall_watt_flow_entity_id'], from_time_stamp, to_time_stamp, float_type=True, convert_to="W", error_state=[0.0])
            
            if CONFIG['home']['invert_powerwall_watt_flow_entity_id']:
                powerwall_discharging_consumption = abs(round(average(get_specific_values(powerwall_values, negative_only = True)), 0))
            else:
                powerwall_discharging_consumption = abs(round(average(get_specific_values(powerwall_values, positive_only = True)), 0))
    except Exception as e:
        _LOGGER.warning(f"Cant get powerwall values from {from_time_stamp} to {to_time_stamp}: {e}")
        
    return powerwall_discharging_consumption

def power_values(from_time_stamp = None, to_time_stamp = None, period = None):
    _LOGGER = globals()['_LOGGER'].getChild("power_values")
    global TASKS
    
    random_int = random.randint(0, 10000)
    
    task_names = {
        "power_consumption": f"power_consumption_{random_int}",
        "ignored_consumption": f"ignored_consumption_{random_int}",
        "powerwall_charging_consumption": f"powerwall_charging_consumption_{random_int}",
        "powerwall_discharging_consumption": f"powerwall_discharging_consumption_{random_int}",
        "ev_used_consumption": f"ev_used_consumption_{random_int}",
        "solar_production": f"solar_production_{random_int}"
    }
    
    power_consumption = 0.0
    ignored_consumption = 0.0
    powerwall_charging_consumption = 0.0
    powerwall_discharging_consumption = 0.0
    ev_used_consumption = 0.0
    solar_production = 0.0
    power_consumption_without_ignored = 0.0
    power_consumption_without_ignored_ev = 0.0
    power_consumption_without_all_exclusion = 0.0
    
    try:
        if period is not None:
            now = getTime()
            to_time_stamp = now
            from_time_stamp = now - datetime.timedelta(minutes=period)
        
        TASKS[task_names["power_consumption"]] = task.create(get_average_value, CONFIG['home']['entity_ids']['power_consumption_entity_id'], from_time_stamp, to_time_stamp, convert_to="W", error_state=0.0)
        TASKS[task_names["ignored_consumption"]] = task.create(power_from_ignored, from_time_stamp, to_time_stamp)
        TASKS[task_names["powerwall_charging_consumption"]] = task.create(charge_from_powerwall, from_time_stamp, to_time_stamp)
        TASKS[task_names["powerwall_discharging_consumption"]] = task.create(discharge_from_powerwall, from_time_stamp, to_time_stamp)
        TASKS[task_names["ev_used_consumption"]] = task.create(get_average_value, CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], from_time_stamp, to_time_stamp, convert_to="W", error_state=0.0)
        TASKS[task_names["solar_production"]] = task.create(get_average_value, CONFIG['solar']['entity_ids']['production_entity_id'], from_time_stamp, to_time_stamp, convert_to="W", error_state=0.0)
        
        done, pending = task.wait({TASKS[task_names["power_consumption"]], TASKS[task_names["ignored_consumption"]],
                                TASKS[task_names["powerwall_charging_consumption"]], TASKS[task_names["powerwall_discharging_consumption"]],
                                TASKS[task_names["ev_used_consumption"]], TASKS[task_names["solar_production"]]})
        
        power_consumption = abs(round(float(TASKS[task_names["power_consumption"]].result()), 2))
        ignored_consumption = abs(TASKS[task_names["ignored_consumption"]].result())
        powerwall_charging_consumption = TASKS[task_names["powerwall_charging_consumption"]].result()
        powerwall_discharging_consumption = TASKS[task_names["powerwall_discharging_consumption"]].result()
        ev_used_consumption = abs(round(float(TASKS[task_names["ev_used_consumption"]].result()), 2))
        solar_production = abs(round(float(TASKS[task_names["solar_production"]].result()), 2))
                    
        if not CONFIG['home']['power_consumption_entity_id_include_powerwall_discharging']:
            power_consumption += powerwall_discharging_consumption
                
        if CONFIG['home']['power_consumption_entity_id_include_powerwall_charging']:
            power_consumption -= powerwall_charging_consumption
            
        power_consumption_without_ignored = round(power_consumption - ignored_consumption, 2)
        power_consumption_without_ignored_ev = round(power_consumption_without_ignored - ev_used_consumption, 2)
        power_consumption_without_all_exclusion = max(round(power_consumption_without_ignored_ev - powerwall_charging_consumption, 2), 0.0)
    finally:
        for task_name in task_names.values():
            task_cancel(task_name, task_remove=True, timeout=3.0, wait_period=0.2)
            
    return {
        "power_consumption": power_consumption,
        "ignored_consumption": ignored_consumption,
        "powerwall_charging_consumption": powerwall_charging_consumption,
        "powerwall_discharging_consumption": powerwall_discharging_consumption,
        "ev_used_consumption": ev_used_consumption,
        "solar_production": solar_production,
        "power_consumption_without_ignored": power_consumption_without_ignored,
        "power_consumption_without_ignored_ev": power_consumption_without_ignored_ev,
        "power_consumption_without_all_exclusion": power_consumption_without_all_exclusion
    }

def local_energy_available(period=None, timeFrom=0, timeTo=None, solar_only=False, without_all_exclusion=False, include_local_energy_distribution=False, update_entity=True):
    _LOGGER = globals()["_LOGGER"].getChild("local_energy_available")
    global TASKS, POWERWALL_CHARGING_TEXT

    if not is_solar_configured(): return 0.0

    random_int = random.randint(0, 10000)
    task_names = {
        "discharge_above_needed": f"discharge_above_needed_{random_int}",
        "powerwall_battery_level": f"powerwall_battery_level_{random_int}",
        "powerwall_reserved_battery_level": f"powerwall_reserved_battery_level_{random_int}",
        "powerwall_charging_power": f"powerwall_charging_power_{random_int}",
        "powerwall_charging_timestamps": f"powerwall_charging_timestamps_{random_int}"
    }
    
    watts_available_from_local_energy = 0.0
    
    try:
        now = getTime()
        current_hour = getTime().replace(minute=0, second=0, tzinfo=None)
        if timeTo is not None:
            # Range mode
            from_time_stamp = now - datetime.timedelta(minutes=timeFrom)
            to_time_stamp = now - datetime.timedelta(minutes=timeTo)
            period = minutesBetween(to_time_stamp, from_time_stamp, error_value=0)
        else:
            # Single period mode
            if period is None:
                period = CONFIG["solar"]["solarpower_use_before_minutes"]
            period = max(period, CONFIG["cron_interval"])
            to_time_stamp = now
            from_time_stamp = now - datetime.timedelta(minutes=period)

        values = power_values(from_time_stamp = from_time_stamp, to_time_stamp = to_time_stamp)

        ignored_consumption = values["ignored_consumption"]
        power_consumption = values["power_consumption"]
        power_consumption_without_ignored = values["power_consumption_without_ignored"]
        power_consumption_without_ignored_ev = values["power_consumption_without_ignored_ev"]
        power_consumption_without_all_exclusion = values["power_consumption_without_all_exclusion"]
        powerwall_charging_consumption = values["powerwall_charging_consumption"]
        powerwall_discharging_consumption = values["powerwall_discharging_consumption"]
        ev_used_consumption = values["ev_used_consumption"]
        solar_production = values["solar_production"]
        total_production = solar_production
        
        if without_all_exclusion:
            watts_available_from_local_energy = total_production - power_consumption_without_all_exclusion
            power_needed_from_powerwall = max(power_consumption_without_all_exclusion - solar_production, 0.0)
            powerwall_discharging_available = max(powerwall_discharging_consumption - power_needed_from_powerwall, 0.0)
        else:
            watts_available_from_local_energy = total_production - power_consumption_without_ignored
            power_needed_from_powerwall = max(power_consumption_without_ignored - solar_production, 0.0)
            powerwall_discharging_available = max(powerwall_discharging_consumption - power_needed_from_powerwall, 0.0)
            
        watts_available_from_local_energy_solar_only = watts_available_from_local_energy

        if is_powerwall_configured():
            
            TASKS[task_names["discharge_above_needed"]] = task.create(get_powerwall_discharge_above_needed)
            TASKS[task_names["powerwall_battery_level"]] = task.create(get_powerwall_battery_level)
            TASKS[task_names["powerwall_reserved_battery_level"]] = task.create(get_ev_charge_after_powerwall_battery_level)
            TASKS[task_names["powerwall_charging_power"]] = task.create(powerwall_max_charging_power, period=period)
            TASKS[task_names["powerwall_charging_timestamps"]] = task.create(local_energy_prediction, powerwall_charging_timestamps=True)
            done, pending = task.wait({TASKS[task_names["discharge_above_needed"]],
                                    TASKS[task_names["powerwall_battery_level"]], TASKS[task_names["powerwall_reserved_battery_level"]],
                                    TASKS[task_names["powerwall_charging_power"]], TASKS[task_names["powerwall_charging_timestamps"]]})
            
            discharge_above_needed = TASKS[task_names["discharge_above_needed"]].result()
            powerwall_battery_level = TASKS[task_names["powerwall_battery_level"]].result()
            powerwall_reserved_battery_level = TASKS[task_names["powerwall_reserved_battery_level"]].result()
            powerwall_charging_power = TASKS[task_names["powerwall_charging_power"]].result()
            powerwall_charging_timestamps = TASKS[task_names["powerwall_charging_timestamps"]].result()
            
            powerwall_forced_stop_charging = False
            
            if current_hour in powerwall_charging_timestamps:
                _LOGGER.error(f"current_hour in powerwall_charging_timestamps: {current_hour} for {period} minutes, powerwall charging is forced to {powerwall_charging_power}W")
                
                if not include_local_energy_distribution and powerwall_battery_level < powerwall_reserved_battery_level or (powerwall_max_charging_power(period=CONFIG['cron_interval']) > POWERWALL_CHARGING_TRIGGER and period != 59):
                    watts_available_from_local_energy -= max(powerwall_charging_power, CONFIG["solar"]["powerwall_charging_power_limit"]) if powerwall_charging_power > POWERWALL_CHARGING_TRIGGER else CONFIG["solar"]["powerwall_charging_power_limit"]
            else:
                if powerwall_charging_power > POWERWALL_CHARGING_TRIGGER:
                    _LOGGER.info(f"Forcing powerwall to stop charging power with {powerwall_charging_power}W, because current_hour {current_hour} is not in powerwall_charging_timestamps")
                    watts_available_from_local_energy += powerwall_charging_consumption
                    powerwall_forced_stop_charging = True
                else:
                    watts_available_from_local_energy -= powerwall_charging_consumption
            
            if not solar_only:
                total_production += powerwall_discharging_available
                
                if discharge_above_needed and powerwall_battery_level > powerwall_reserved_battery_level + 1.0:
                    if powerwall_discharging_available < CONFIG["solar"]["powerwall_discharging_power"] / 2.0:
                        watts_available_from_local_energy += CONFIG["solar"]["powerwall_discharging_power"]
                    else:
                        watts_available_from_local_energy += powerwall_discharging_available

            if (powerwall_battery_level < powerwall_reserved_battery_level
                and powerwall_charging_power == 0.0
                and watts_available_from_local_energy > 0.0):
                POWERWALL_CHARGING_TEXT = f"Powerwall {powerwall_battery_level}% lader ikke, selvom batteri niveau er <{powerwall_reserved_battery_level}%"
            elif powerwall_charging_consumption > POWERWALL_CHARGING_TRIGGER and powerwall_discharging_available < POWERWALL_DISCHARGING_TRIGGER:
                if powerwall_forced_stop_charging:
                    POWERWALL_CHARGING_TEXT = f"Powerwall standset – opladning sker senere"
                else:
                    POWERWALL_CHARGING_TEXT = f"Powerwall lader: x̄{int(powerwall_charging_consumption)}W"
            elif powerwall_discharging_available > POWERWALL_DISCHARGING_TRIGGER and powerwall_battery_level > powerwall_reserved_battery_level + 1.0:
                POWERWALL_CHARGING_TEXT = f"Powerwall aflader: x̄{int(powerwall_discharging_available)}W"
            else:
                POWERWALL_CHARGING_TEXT = ""

        watts_available_from_local_energy = round(min(max(watts_available_from_local_energy, 0.0), CONFIG["solar"]["inverter_discharging_power_limit"]), 2)
        watts_available_from_local_energy_solar_only = round(min(max(watts_available_from_local_energy_solar_only, 0.0), CONFIG["solar"]["inverter_discharging_power_limit"]), 2)

        if update_entity:
            set_state(f"sensor.{__name__}_solar_over_production_current_hour", watts_available_from_local_energy_solar_only)
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.from_the_last", f"{period} minutes")
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.ignored_consumption", ignored_consumption)
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.power_consumption", power_consumption)
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.power_consumption_without_ignored", power_consumption_without_ignored)
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.power_consumption_without_ignored_ev", power_consumption_without_ignored_ev)
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.power_consumption_without_all_exclusion", power_consumption_without_all_exclusion)
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.ev_used_consumption", ev_used_consumption)
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.solar_production", solar_production)
            
            if is_powerwall_configured():
                set_attr(f"sensor.{__name__}_solar_over_production_current_hour.powerwall_charging_consumption", powerwall_charging_consumption)
                set_attr(f"sensor.{__name__}_solar_over_production_current_hour.powerwall_discharging_consumption", powerwall_discharging_consumption)
                set_attr(f"sensor.{__name__}_solar_over_production_current_hour.powerwall_discharging_available", powerwall_discharging_available)
                set_attr(f"sensor.{__name__}_solar_over_production_current_hour.total_production", total_production)
                
            set_attr(f"sensor.{__name__}_solar_over_production_current_hour.local_energy_available", watts_available_from_local_energy)


        if include_local_energy_distribution:
            solar_watts_of_local_energy = 0.0
            powerwall_watts_of_local_energy = 0.0
            
            watts_from_local_energy = min(watts_available_from_local_energy, ev_used_consumption)
            
            if watts_from_local_energy > 0.0:
                solar_watts_of_local_energy = (solar_production / total_production) * watts_from_local_energy if total_production > 0.0 else 0.0
                powerwall_watts_of_local_energy = (powerwall_discharging_available / total_production) * watts_from_local_energy if total_production > 0.0 else 0.0
            
            return watts_available_from_local_energy, watts_from_local_energy, solar_watts_of_local_energy, powerwall_watts_of_local_energy
    except Exception as e:
        _LOGGER.error(f"Error calculating local energy available: {e}")
    finally:
        for task_name in task_names.values():
            task_cancel(task_name, task_remove=True)
            
    return watts_available_from_local_energy

def max_local_energy_available_remaining_hour():
    _LOGGER = globals()['_LOGGER'].getChild("max_local_energy_available_remaining_hour")
    global TASKS
    
    if not is_solar_configured():
        return {
            "period": f"No solar installed",
            "watt": 0.0
        }
    
    time_to = getMinute()
    
    if CONFIG['solar']['solarpower_use_before_minutes'] > 0:
        time_to = CONFIG['solar']['solarpower_use_before_minutes'] - CONFIG['cron_interval']
        
        if CONFIG['solar']['solarpower_use_before_minutes'] <= 60:
            def map_minute(minute: int, usage_period: int) -> int:
                if usage_period <= 0:
                    return 0
                return minute % usage_period
            
            time_to = map_minute(getMinute(), CONFIG['solar']['solarpower_use_before_minutes'])
    
    random_int = random.randint(0, 10000)
    predictedSolarPower_task_name = f"max_local_energy_available_remaining_hour_predictedSolarPower_{random_int}"
    total_task_name = f"max_local_energy_available_remaining_hour_total_{random_int}"
    
    try:
        TASKS[predictedSolarPower_task_name] = task.create(local_energy_available, timeFrom=0, timeTo=max(time_to, CONFIG['cron_interval'], 10), without_all_exclusion=True)
        TASKS[total_task_name] = task.create(local_energy_available, timeFrom=0, timeTo=time_to, without_all_exclusion=False, update_entity=False, solar_only=True)
        done, pending = task.wait({TASKS[predictedSolarPower_task_name], TASKS[total_task_name]})
            
        returnDict = {
            "predictedSolarPower": {
                "watt": max(TASKS[predictedSolarPower_task_name].result(), 0.0)
            }
        }
        
        if time_to >= CONFIG['cron_interval']:
            returnDict['total'] = {
                "period": f"0-{time_to}",
                "watt": max(TASKS[total_task_name].result(), 0.0)
            }
        else:
            returnDict['total'] = {
                "period": f"0-{time_to}",
                "watt": 0.0
            }
        
        solar_min_amp = CONFIG['solar']['charging_single_phase_min_amp'] if float(CONFIG['charger']['charging_phases']) > 1.0 else CONFIG['solar']['charging_three_phase_min_amp'] * 3.0
        solar_threadhold = CONFIG['charger']['power_voltage'] * solar_min_amp / 5
        allowed_above_under_solar_available = CONFIG['solar']['allow_grid_charging_above_solar_available'] if returnDict['predictedSolarPower']['watt'] >= solar_threadhold else 0.0
        predictedSolarPower = returnDict['predictedSolarPower']['watt'] + allowed_above_under_solar_available
        
        multiple = 1.0
        
        if CONFIG['solar']['max_to_current_hour']:
            multiple = 1 + round((getMinute() / 60), 2)
        elif CONFIG['solar']['solarpower_use_before_minutes'] > 0:
            period_calculations = CONFIG['solar']['solarpower_use_before_minutes'] / CONFIG['cron_interval']
            multiply_factor = 1.0 if period_calculations > 4.0 else 0.5
            
            #multiple = 1 + round(time_to / CONFIG['solar']['solarpower_use_before_minutes'], 2) #Linear weighting
            multiple = round(1 + max(1.0 - 4.0 * ((time_to - (float(CONFIG['cron_interval'])/2.0))/float(CONFIG['cron_interval']))**2.0, 0.0), 2) #Parabolic weighting
            multiple *= multiply_factor
        else:
            multiple = 0.0
            
        extra_watt = max((returnDict['total']['watt'] * multiple), 0.0)
        
        returnDict['output'] = {
            "period": f"predictedSolarPower:{predictedSolarPower} + {allowed_above_under_solar_available} + {returnDict['total']['period']}:{returnDict['total']['watt']} multiple:{multiple} extra_watt:{extra_watt} (min 0.0)",
            "watt": predictedSolarPower + extra_watt
        }
            
        _LOGGER.debug(f"max_local_energy_available_remaining_hour returnDict:{returnDict}")
        _LOGGER.debug(f"max_local_energy_available_remaining_hour output:{returnDict['output']}")
    finally:
        for task_name in [predictedSolarPower_task_name, total_task_name]:
            task_cancel(task_name, task_remove=True)
            
    return returnDict['output']

def inverter_available(error = ""):
    _LOGGER = globals()['_LOGGER'].getChild("inverter_available")
    
    if not is_solar_configured(): return False
    
    if not is_entity_configured(CONFIG['home']['entity_ids']['power_consumption_entity_id']) or is_entity_available(CONFIG['home']['entity_ids']['power_consumption_entity_id']):
        return True
    
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
    
def forecast_score(data):
    _LOGGER = globals()['_LOGGER'].getChild("forecast_score")
    try:
        if "cloud_coverage" not in data or "uv_index" not in data or "temperature" not in data:
            if "condition" in data and "datetime" in data:
                _LOGGER.debug(f"{data['datetime']}: Missing cloud_coverage, uv_index or temperature in data, using condition: {data['condition']} = {WEATHER_CONDITION_DICT[data['condition']]}")
                return WEATHER_CONDITION_DICT[data["condition"]]
            
            raise Exception("Missing required keys in data")
            
        normalized_cloud_coverage = (100 - data["cloud_coverage"]) / 100
        
        uv_index = data["uv_index"]
        max_uv_index = 11
        normalized_uv_index = min(uv_index / max_uv_index, 1)
        
        temperature = data["temperature"]
        max_temperature = 20
        if temperature <= max_temperature:
            normalized_temperature = temperature / max_temperature
        else:
            normalized_temperature = max_temperature / temperature

        cloud_weight = 0.5
        uv_weight = 0.3
        temperature_weight = 0.2

        if data["cloud_coverage"] >= 90:
            normalized_cloud_coverage *= 0.2
            normalized_uv_index *= 0.1
            normalized_temperature *= 0.5

        score = ((
            normalized_cloud_coverage * cloud_weight +
            normalized_uv_index * uv_weight +
            normalized_temperature * temperature_weight
        ) * 100)
    except Exception as e:
        _LOGGER.error(f"Cant calculate forecast score, using 50.0: {e}\n{data}")
        score = 50.0

    return score

def db_cloud_coverage_to_score(database):
    new_database = {}
    for hour in database:
        new_database[hour] = {}
        for cloud_coverage, data in database[hour].items():
            score = 100 - cloud_coverage
            new_database[hour][score] = data
    return new_database

def transform_database(database, step_size=20):
    new_database = {}
    for hour, cloud_data in database.items():
        new_database[hour] = {}

        for cloud_coverage, entries in cloud_data.items():
            score_group = (cloud_coverage // step_size) * step_size
            upper_group = score_group + step_size

            if score_group not in new_database[hour]:
                new_database[hour][score_group] = []
            if upper_group not in new_database[hour] and upper_group <= 100:
                new_database[hour][upper_group] = []

            sorted_entries = sorted(entries, key=lambda x: x[1])

            split_index = len(sorted_entries) // 2

            new_database[hour][score_group].extend(sorted_entries[:split_index])

            if upper_group <= 100:
                new_database[hour][upper_group].extend(sorted_entries[split_index:])

    return new_database

def load_power_values_db():
    _LOGGER = globals()['_LOGGER'].getChild("load_power_values_db")
    global POWER_VALUES_DB
    
    if not is_solar_configured() or not CONFIG['solar']['entity_ids']['forecast_entity_id']: return
    
    version = 1.0
    
    try:
        database = load_yaml(f"{__name__}_power_values_db")
        if "version" in database:
            version = float(database["version"])
            del database["version"]
            
        POWER_VALUES_DB = database.copy()
        
        if not POWER_VALUES_DB:
            create_yaml(f"{__name__}_power_values_db", db=POWER_VALUES_DB)
    except Exception as e:
        error_message = f"Cant load {__name__}_power_values_db: {e}"
        _LOGGER.error(error_message)
        save_error_to_file(error_message, caller_function_name = "load_power_values_db()")
        my_persistent_notification(f"Failed to load {__name__}_power_values_db", f"{TITLE} error", persistent_notification_id=f"{__name__}load_power_values_db")
    
    if POWER_VALUES_DB == {} or not POWER_VALUES_DB:
        POWER_VALUES_DB = {}

    for h in range(24):
        if h not in POWER_VALUES_DB:
            POWER_VALUES_DB[h] = {}
            
    save_power_values_db()
    
def save_power_values_db():
    _LOGGER = globals()['_LOGGER'].getChild("save_solar_available_db")
    global POWER_VALUES_DB
    
    if not is_solar_configured() or not CONFIG['solar']['entity_ids']['forecast_entity_id']: return
    
    if len(POWER_VALUES_DB) > 0:
        db_to_file = POWER_VALUES_DB.copy()
        db_to_file["version"] = POWER_VALUES_DB_VERSION
        save_changes(f"{__name__}_power_values_db", db_to_file)

def power_values_to_db(data):
    _LOGGER = globals()['_LOGGER'].getChild("power_values_to_db")
    global POWER_VALUES_DB
    
    if not is_solar_configured() or not CONFIG['solar']['entity_ids']['forecast_entity_id']: return
    
    if not inverter_available(f"power_values_to_db({data})"):
        return
    
    if len(POWER_VALUES_DB) == 0:
        load_power_values_db()
        
    hour = getHour()
    
    for key, value in data.items():
        if key not in POWER_VALUES_DB[hour]:
            POWER_VALUES_DB[hour][key] = []
            
        POWER_VALUES_DB[hour][key].insert(0, [getTime(), value])
        _LOGGER.debug(f"inserting {value} POWER_VALUES_DB[{hour}] = {POWER_VALUES_DB[hour]}")
        
        POWER_VALUES_DB[hour][key] = POWER_VALUES_DB[hour][key][:CONFIG['database']['power_values_db_data_to_save']]
        _LOGGER.debug(f"removing values over {CONFIG['database']['power_values_db_data_to_save']} POWER_VALUES_DB[{hour}] = {POWER_VALUES_DB[hour][key]}")
    
    save_power_values_db()
    
def load_solar_available_db():
    _LOGGER = globals()['_LOGGER'].getChild("load_solar_available_db")
    global SOLAR_PRODUCTION_AVAILABLE_DB
    
    if not is_solar_configured(): return
    
    version = 1.0
    
    try:
        database = load_yaml(f"{__name__}_solar_production_available_db")
        if "version" in database:
            version = float(database["version"])
            del database["version"]
            
        SOLAR_PRODUCTION_AVAILABLE_DB = database.copy()
        
        if not SOLAR_PRODUCTION_AVAILABLE_DB:
            create_yaml(f"{__name__}_solar_production_available_db", db=SOLAR_PRODUCTION_AVAILABLE_DB)
    except Exception as e:
        error_message = f"Cant load {__name__}_solar_production_available_db: {e}"
        _LOGGER.error(error_message)
        save_error_to_file(error_message, caller_function_name = "load_solar_available_db()")
        my_persistent_notification(f"Failed to load {__name__}_solar_production_available_db", f"{TITLE} error", persistent_notification_id=f"{__name__}_load_solar_available_db")
    
    if SOLAR_PRODUCTION_AVAILABLE_DB == {} or not SOLAR_PRODUCTION_AVAILABLE_DB:
        SOLAR_PRODUCTION_AVAILABLE_DB = {}
    
    for h in range(24):
        if h not in SOLAR_PRODUCTION_AVAILABLE_DB:
            SOLAR_PRODUCTION_AVAILABLE_DB[h] = {}
        for value in weather_values():
            SOLAR_PRODUCTION_AVAILABLE_DB[h].setdefault(value, [])
    
    if version <= 1.0:
        _LOGGER.info(f"Transforming database from version {version} to {SOLAR_PRODUCTION_AVAILABLE_DB_VERSION}")
        SOLAR_PRODUCTION_AVAILABLE_DB = db_cloud_coverage_to_score(SOLAR_PRODUCTION_AVAILABLE_DB)
        SOLAR_PRODUCTION_AVAILABLE_DB = transform_database(SOLAR_PRODUCTION_AVAILABLE_DB)
        
    save_solar_available_db()
    
def save_solar_available_db():
    _LOGGER = globals()['_LOGGER'].getChild("save_solar_available_db")
    global SOLAR_PRODUCTION_AVAILABLE_DB
    
    if not is_solar_configured(): return
    
    if len(SOLAR_PRODUCTION_AVAILABLE_DB) > 0:
        db_to_file = SOLAR_PRODUCTION_AVAILABLE_DB.copy()
        db_to_file["version"] = SOLAR_PRODUCTION_AVAILABLE_DB_VERSION
        save_changes(f"{__name__}_solar_production_available_db", db_to_file)
        
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
    cloudiness_score = None
    
    forecast_dict = get_forecast_dict()
    forecast = get_forecast(forecast_dict)
    cloudiness = forecast_score(forecast)
    
    
    if cloudiness is not None:
        cloudiness_score = get_closest_key(cloudiness, SOLAR_PRODUCTION_AVAILABLE_DB[hour], return_key=True)
    else:
        try:
            try:
                cloudiness_score = WEATHER_CONDITION_DICT[get_state(CONFIG['forecast']['entity_ids']['hourly_service_entity_id'])]
            except:
                cloudiness_score = WEATHER_CONDITION_DICT[get_state(CONFIG['forecast']['entity_ids']['daily_service_entity_id'])]
        except Exception as e:
            _LOGGER.error(f"Cant get states from hourly {CONFIG['forecast']['entity_ids']['daily_service_entity_id']} or daily {CONFIG['forecast']['entity_ids']['daily_service_entity_id']}: {e}")
            return
    
    SOLAR_PRODUCTION_AVAILABLE_DB[hour][cloudiness_score].insert(0, [getTime(), power])
    _LOGGER.debug(f"inserting {power} SOLAR_PRODUCTION_AVAILABLE_DB[{hour}][{cloudiness_score}] = {SOLAR_PRODUCTION_AVAILABLE_DB[hour][cloudiness_score]}")
    
    SOLAR_PRODUCTION_AVAILABLE_DB[hour][cloudiness_score] = SOLAR_PRODUCTION_AVAILABLE_DB[hour][cloudiness_score][:CONFIG['database']['solar_available_db_data_to_save']]
    _LOGGER.debug(f"removing values over {CONFIG['database']['solar_available_db_data_to_save']} SOLAR_PRODUCTION_AVAILABLE_DB[{hour}][{cloudiness_score}] = {SOLAR_PRODUCTION_AVAILABLE_DB[hour][cloudiness_score]}")
    
    save_solar_available_db()

def get_solar_kwh_forecast():
    _LOGGER = globals()['_LOGGER'].getChild("get_solar_kwh_forecast")
    global POWER_VALUES_DB, LAST_SUCCESSFUL_GRID_PRICES
    
    if "forecast_entity_id" in CONFIG['solar']['entity_ids'] and not CONFIG['solar']['entity_ids']['forecast_entity_id']:
        return {}
    
    def forecast_task(base_entity_id, ending):
        _LOGGER = globals()['_LOGGER'].getChild("get_solar_kwh_forecast.forecast_task")
        nonlocal forecast
        
        try:
            entity_id = f"{base_entity_id}_{ending}"
            site_attr = get_attr(entity_id, "detailedHourly", error_state={})
            
            for data in site_attr:
                date = data['period_start'].replace(tzinfo=None)
                
                if date not in hour_prices:
                    continue
                
                watt = round(data['pv_estimate'] * 1000.0, 0)
                                        
                power_consumption_without_all_exclusion = calculate_ema(reverse_list(get_list_values(POWER_VALUES_DB[date.hour].get("power_consumption_without_all_exclusion", [0.0]))))
                available = max(watt - power_consumption_without_all_exclusion, 0.0)
                available_kwh = round(available / 1000.0, 3)
                
                day_of_week = getDayOfWeek(date)
                tariff_dict = get_tariffs(date.hour, day_of_week)
                transmissions_nettarif = tariff_dict["transmissions_nettarif"]
                systemtarif = tariff_dict["systemtarif"]
                tariff_sum = tariff_dict["tariff_sum"]
                
                price = hour_prices[date]
                raw_price = price - tariff_sum
                
                sell_tariffs = sum((solar_production_seller_cut, energinets_network_tariff, energinets_balance_tariff, transmissions_nettarif, systemtarif))
                sell_price = raw_price - sell_tariffs
                
                forecast[date] = (available_kwh, sell_price)
        except Exception as e:
            _LOGGER.error(f"Error: {e}")
        pass
    
    forecast = {}
    
    hour_prices = LAST_SUCCESSFUL_GRID_PRICES['prices'] if "prices" in LAST_SUCCESSFUL_GRID_PRICES else get_hour_prices()
                        
    energinets_network_tariff = SOLAR_SELL_TARIFF["energinets_network_tariff"]
    energinets_balance_tariff = SOLAR_SELL_TARIFF["energinets_balance_tariff"]
    solar_production_seller_cut = SOLAR_SELL_TARIFF["solar_production_seller_cut"]
    
    integration = get_integration(CONFIG['solar']['entity_ids']['forecast_entity_id'])
    
    if integration == "solcast_solar":
        endings = ["today", "tomorrow", "day_3", "day_4", "day_5", "day_6", "day_7"]
        base_entity_id = "_".join(CONFIG['solar']['entity_ids']['forecast_entity_id'].split("_")[:-1])
        
        random_int = random.randint(0, 1000000)
        task_set = set()
        for ending in endings:
            TASKS[f"forecast_task_{ending}_{random_int}"] = task.create(forecast_task, base_entity_id=base_entity_id, ending=ending)
            task_set.add(TASKS[f"forecast_task_{ending}_{random_int}"])
        done, pending = task.wait(task_set)
        
        for ending in endings:
            task_name = f"forecast_task_{ending}_{random_int}"
            task_cancel(task_name, task_remove=True)
            
    return forecast

def local_energy_prediction(powerwall_charging_timestamps = False):
    _LOGGER = globals()['_LOGGER'].getChild("local_energy_prediction")
    global TASKS, SOLAR_PRODUCTION_AVAILABLE_DB, LOCAL_ENERGY_PREDICTION_DB
    
    def get_database_kwh(cloudiness: int | float, date: datetime.datetime) -> list:
        _LOGGER = globals()['_LOGGER'].getChild("local_energy_prediction.get_power")
        hour = getHour(date)
        day_of_week = getDayOfWeek(date)
        
        try:
            power_list = reverse_list(get_list_values(get_closest_key(cloudiness, SOLAR_PRODUCTION_AVAILABLE_DB[hour])))
            power_one_down_list = []
            power_one_up_list = []
            if type(power_list) == list:
                if len(power_list) <= 6 or calculate_ema(power_list) <= 1000.0:
                    if cloudiness >= 20:
                        power_one_down_list = reverse_list(get_list_values(get_closest_key(cloudiness - 20, SOLAR_PRODUCTION_AVAILABLE_DB[hour])))
                    if cloudiness <= 80:
                        power_one_up_list = reverse_list(get_list_values(get_closest_key(cloudiness + 20, SOLAR_PRODUCTION_AVAILABLE_DB[hour])))
                           
                _LOGGER.debug(f"{hour} cloudiness:{cloudiness}% power_list: average({average(power_list)})/ema({calculate_ema(power_list)})={power_list}\npower_one_down: average({average(power_one_down_list)})/ema({calculate_ema(power_one_down_list)})={power_one_down_list}\npower_one_up: average({average(power_one_up_list)})/ema({calculate_ema(power_one_up_list)})={power_one_up_list}")
                
                power_list = [calculate_ema(power_list)] if power_list else []
                power_one_down_list = [calculate_ema(power_one_down_list)] if power_one_down_list else []
                power_one_up_list = [calculate_ema(power_one_up_list)] if power_one_up_list else []
                
                avg_power = max(average(power_list + power_list + power_list + power_one_down_list + power_one_up_list), 0.0)
                avg_kwh = avg_power / 1000
                
                avg_sell_price = float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price'])) if is_solar_configured() else 0.0
                
                if avg_sell_price == -1.0:
                    avg_sell_price = average(KWH_AVG_PRICES_DB['history_sell'][hour][day_of_week])
                
                return [avg_kwh, avg_sell_price]
        except Exception as e:
            _LOGGER.warning(f"Cant get cloudiness: {cloudiness}, hour: {hour}, day_of_week: {day_of_week}. {e}")
        return [0.0, 0.0]

    def process_forecast(day, loop_datetime, is_away, current_hour_factor, cloudiness, solar_forecast_from_integration,
                        total_db, total_db_sell, total_forecast, total_forecast_sell,
                        total_avg, total_avg_sell, timestamps, powerwall_kwh_needed):
        _LOGGER = globals()['_LOGGER'].getChild("local_energy_prediction.process_forecast")
        
        loop_kwh = []
        loop_sell = []

        if is_away and not is_powerwall_configured():
            return powerwall_kwh_needed

        # Cloudiness forecast
        if cloudiness is not None:
            power_factor = 0.5 if loop_datetime in solar_forecast_from_integration else 1.0
            power_factor *= current_hour_factor
            power_cost = get_database_kwh(cloudiness, loop_datetime)
            loop_kwh.append(power_cost[0] * power_factor)
            loop_sell.append(power_cost[1] * power_factor)
            total_db.append(power_cost[0])
            total_db_sell.append(power_cost[1])

        # Solar forecast
        if loop_datetime in solar_forecast_from_integration:
            power_factor = 1.5 if cloudiness is not None else 1.0
            power_factor *= current_hour_factor
            loop_kwh.append(solar_forecast_from_integration[loop_datetime][0] * power_factor)
            loop_sell.append(solar_forecast_from_integration[loop_datetime][1] * power_factor)
            total_forecast.append(solar_forecast_from_integration[loop_datetime][0])
            total_forecast_sell.append(solar_forecast_from_integration[loop_datetime][1])

        # Logging & Aggregation
        if loop_kwh:
            loop_kwh = average(loop_kwh)
            loop_sell = average(loop_sell)
            
            if loop_kwh > 0.0:
                if powerwall_kwh_needed > 0.0:
                    now = getTime()
                    if in_between(loop_datetime, now, now + datetime.timedelta(hours=25)):
                        timestamps.append(loop_datetime)
                        
                    diff = powerwall_kwh_needed - loop_kwh
                    charging_kwh = loop_kwh if diff >= 0.0 else powerwall_kwh_needed
                    powerwall_kwh_needed -= charging_kwh
                    
                    if diff < 0.0:
                        loop_kwh = loop_kwh - abs(diff)
                        
                if powerwall_kwh_needed <= 0.0:
                    total_avg.append(loop_kwh)
                    total_avg_sell.append(loop_sell)
                    
        return powerwall_kwh_needed
                
    def day_prediction_task(day, today, sunrise, sunset, stop_prediction_before, forecast_dict, solar_forecast_from_integration, end_trip, trip_last_charging, using_grid_price):
        _LOGGER = globals()['_LOGGER'].getChild("local_energy_prediction.day_prediction_task")
        global LOCAL_ENERGY_PREDICTION_DB
        nonlocal output, output_sell, powerwall_charging_timestamps_list
        
        date = today + datetime.timedelta(days=day)
        output[date] = 0.0
        output_sell[date] = 0.0
        
        dayName = getDayOfWeekText(getTimePlusDays(day))
        total_database = []
        total_database_sell = []
        total_forecast = []
        total_forecast_sell = []
        total = []
        total_sell = []
        
        total_away_database = []
        total_away_database_sell = []
        total_away_forecast = []
        total_away_forecast_sell = []
        total_away = []
        total_away_sell = []
        
        powerwall_kwh_needed = 0.0
            
        expensive_hours = []
        
        for hour in get_expensive_hours(day=day).keys():
            expensive_hours.append(hour.hour)
            
        current_hour = getHour()
        from_hour = sunrise if day > 0 else max(sunrise, current_hour)
        to_hour = sunset
        
        work_last_charging = None
        end_work = None
        
        try:
            if workplan_charging_enabled() and get_state(f"input_boolean.{__name__}_workday_{dayName}") == "on":
                work_last_charging = date.replace(hour=get_state(f"input_datetime.{__name__}_workday_departure_{dayName}").hour) - datetime.timedelta(hours=stop_prediction_before)
                end_work = date.replace(hour=get_state(f"input_datetime.{__name__}_workday_homecoming_{dayName}").hour)
        except Exception as e:
            _LOGGER.warning(f"Cant get input_datetime.{__name__}_workday_homecoming_{dayName} datetime, using from sunrise: {e}")
            
        if forecast_dict:
            if from_hour <= to_hour:
        
                if is_powerwall_configured():
                    powerwall_battery_level = get_powerwall_battery_level() if day == 0 else 0.0
                    powerwall_reserved_battery_level = get_ev_charge_after_powerwall_battery_level()
                    
                    powerwall_percentage_needed = max(powerwall_reserved_battery_level - powerwall_battery_level, 0.0)
                    powerwall_kwh_needed = powerwall_percentage_needed * CONFIG['solar']['powerwall_battery_size'] / 100
                
                home_hours = []
                for hour in range(from_hour, to_hour + 1):
                    loop_datetime = date.replace(hour = hour)
                    
                    if hour in expensive_hours and using_grid_price:
                        continue
                    
                    forecast = get_forecast(forecast_dict, loop_datetime)
                    cloudiness = forecast_score(forecast) if forecast is not None else None
                    
                    current_hour_factor = 1.0 if from_hour != current_hour else abs((getMinute() / 60.0) - 1)
                    is_away = (
                        (work_last_charging and in_between(loop_datetime, work_last_charging, end_work))
                        or (trip_last_charging and in_between(loop_datetime, trip_last_charging, end_trip))
                    )
                    
                    if is_away:
                        powerwall_kwh_needed = process_forecast(
                            day, loop_datetime, is_away, current_hour_factor,
                            cloudiness, solar_forecast_from_integration,
                            total_away_database, total_away_database_sell,
                            total_away_forecast, total_away_forecast_sell,
                            total_away, total_away_sell,
                            powerwall_charging_timestamps_list, powerwall_kwh_needed
                        )
                    else:
                        home_hours.append(hour)
                    
                for hour in home_hours:
                    loop_datetime = date.replace(hour = hour)
                    
                    forecast = get_forecast(forecast_dict, loop_datetime)
                    cloudiness = forecast_score(forecast) if forecast is not None else None
                    
                    current_hour_factor = 1.0 if from_hour != current_hour else abs((getMinute() / 60.0) - 1)
                    is_away = False
                    
                    powerwall_kwh_needed = process_forecast(
                        day, loop_datetime, is_away, current_hour_factor,
                        cloudiness, solar_forecast_from_integration,
                        total_database, total_database_sell,
                        total_forecast, total_forecast_sell,
                        total, total_sell,
                        powerwall_charging_timestamps_list, powerwall_kwh_needed
                    )
                        
            total = sum(total)
            total_sell = average(total_sell)
            total_away = sum(total_away)
            total_away_sell = average(total_away_sell)
                
            if not powerwall_charging_timestamps:
                if day not in LOCAL_ENERGY_PREDICTION_DB["solar_prediction"]:
                    LOCAL_ENERGY_PREDICTION_DB["solar_prediction"][day] = {}
                LOCAL_ENERGY_PREDICTION_DB["solar_prediction"][day]["home"] = {
                    "total_database": total_database,
                    "total_database_sell": total_database_sell,
                    "total_forecast": total_forecast,
                    "total_forecast_sell": total_forecast_sell,
                    "total": total,
                    "total_sell": total_sell
                }
                LOCAL_ENERGY_PREDICTION_DB["solar_prediction"][day]["away"] = {
                    "total_database": total_away_database,
                    "total_database_sell": total_away_database_sell,
                    "total_forecast": total_away_forecast,
                    "total_forecast_sell": total_away_forecast_sell,
                    "total": total_away,
                    "total_sell": total_away_sell
                }
            
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
    
    if not is_solar_configured() or not inverter_available(f"Inverter not available)"):
        _LOGGER.error("Solar not configured or inverter not available")
        return output, output_sell
    
    try:
        now = getTime()
        location = sun.get_astral_location(hass)
        sunrise = location[0].sunrise(now).replace(tzinfo=None).hour
        sunset = location[0].sunset(now).replace(tzinfo=None).hour
    except Exception as e:
        _LOGGER.error(f"Error: {e}")
        return output, output_sell
    
    forecast_dict = get_forecast_dict()
    solar_forecast_from_integration = get_solar_kwh_forecast()
    
    trip_planned = is_trip_planned()
    start_trip = get_trip_date_time() if get_trip_date_time() != resetDatetime() and trip_planned else None
    end_trip = get_trip_homecoming_date_time() if get_trip_homecoming_date_time() != resetDatetime() and trip_planned else None
    trip_last_charging = None
    
    if start_trip:
        start_trip = reset_time_to_hour(start_trip)
        end_trip = reset_time_to_hour(end_trip)
        trip_last_charging = start_trip - datetime.timedelta(hours=stop_prediction_before)
        
    using_grid_price = True if float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price'])) == -1.0 else False
    
    powerwall_charging_timestamps_list = []
    
    random_int = random.randint(0, 1000000)
    day_prediction_task_set = set()
    day_prediction_task_names = []
    
    try:
        for day in range(days + 1):
            task_name = f"{__name__}_local_energy_prediction_day_prediction_task_{day}_{random_int}"
            TASKS[task_name] = task.create(day_prediction_task, day, today, sunrise, sunset, stop_prediction_before, forecast_dict, solar_forecast_from_integration, end_trip, trip_last_charging, using_grid_price)
            day_prediction_task_set.add(TASKS[task_name])
            day_prediction_task_names.append(task_name)
        
        done, pending = task.wait(day_prediction_task_set)
    finally:
        for task_name in day_prediction_task_names:
            task_cancel(task_name, task_remove=True)
    
    if powerwall_charging_timestamps:
        LOCAL_ENERGY_PREDICTION_DB["powerwall_charging_timestamps"] = powerwall_charging_timestamps_list
        return powerwall_charging_timestamps_list
    
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
    
    if is_ev_configured():
        set_state(f"input_boolean.{__name__}_trip_preheat", "off")

def trip_charging():
    _LOGGER = globals()['_LOGGER'].getChild("trip_charging")
    if get_trip_date_time() == resetDatetime(): return
    if get_trip_homecoming_date_time() == resetDatetime(): return
     
    if is_trip_planned() and ev_power_connected():
        _LOGGER.debug("trip_charging:True")
        return True
    
def preheat_ev():#TODO Make it work on Tesla and Kia
    _LOGGER = globals()['_LOGGER'].getChild("preheat_ev")
    
    def stop_preheat_no_driving(next_drive, now, preheat_min_before):
        if minutesBetween(next_drive, now, error_value=(preheat_min_before * 3) + 1) > (preheat_min_before * 3) and minutesBetween(next_drive, now, error_value=(preheat_min_before * 3) + 11) <= (preheat_min_before * 3) + 10:
            return True
    
    if TESTING:
        _LOGGER.info(f"TESTING not preheating car")
        return
    
    if not is_ev_configured() or not workplan_charging_enabled():
        return
    
    if not is_entity_available(CONFIG["ev_car"]["entity_ids"]["climate_entity_id"]): return
    
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
        if trip_date_time in ENTITY_UNAVAILABLE_STATES:
            raise Exception(f"input_datetime.{__name__}_trip_date_time is unknown")
    except Exception as e:
        _LOGGER.error(e)
    
    next_work_time = resetDatetime()
    try:
        dayName = getDayOfWeekText(getTime())
        workday = get_state(f"input_boolean.{__name__}_workday_{dayName}")
        work_time = get_state(f"input_datetime.{__name__}_workday_departure_{dayName}")
        if workday == "on" and work_time not in ENTITY_UNAVAILABLE_STATES:
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

    outdoor_temp = 0.0
    forecast_temp = 0.0
    heating_type = "Forvarmer"
    
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
                
    climate_state = get_state(CONFIG["ev_car"]["entity_ids"]["climate_entity_id"], error_state="unknown")
    integration = get_integration(CONFIG['ev_car']['entity_ids']['climate_entity_id'])
    
    if "tessie" == integration:
        if preheat and climate_state == "off" and service.has_service("climate", "turn_on"):
            if not allow_command_entity_integration("Tesla Climate service Preheat", "preheat()", integration = integration, check_only=True): return
            allow_command_entity_integration("Tesla Climate service Preheat", "preheat()", integration = integration)
            
            _LOGGER.info("Preheating ev car")
            
            if outdoor_temp <= -1.0 or forecast_temp <= -1.0:
                service.call("climate", "set_preset_mode", preset_mode="Defrost", blocking=True, entity_id=CONFIG['ev_car']['entity_ids']['climate_entity_id'])
                heating_type = "Optøer"
            else:
                service.call("climate", "turn_on", blocking=True, entity_id=CONFIG['ev_car']['entity_ids']['climate_entity_id'])
                
            drive_efficiency("preheat")
            
            if CONFIG['notification']['preheating']:
                my_notify(message = f"{heating_type} bilen til kl. {next_drive.strftime('%H:%M')}", title = TITLE, notify_list = CONFIG['notify_list'], admin_only = False, always = False)
        elif climate_state == "heat_cool" and service.has_service("climate", "turn_off"):
            if ready_to_charge():
                if stop_preheat_no_driving(next_drive, now, preheat_min_before):
                    if not allow_command_entity_integration("Tesla Climate service Turn off", "preheat()", integration = integration, check_only=True): return
                    allow_command_entity_integration("Tesla Climate service Turn off", "preheat()", integration = integration)
                    
                    _LOGGER.info("Car not moved stopping preheating ev car")
                    service.call("climate", "turn_off", blocking=True, entity_id=CONFIG['ev_car']['entity_ids']['climate_entity_id'])
                    drive_efficiency("preheat_cancel")
                    
                    if CONFIG['notification']['preheating']:
                        my_notify(message = f"Forvarmning af bilen stoppet, pga ingen kørsel kl. {next_drive.strftime('%H:%M')}", title = TITLE, notify_list = CONFIG['notify_list'], admin_only = False, always = False)
    elif integration == "cupra_we_connect" and service.has_service(integration, "volkswagen_id_set_climatisation"):
        vin = get_vin_cupra_born(CONFIG["ev_car"]["entity_ids"]["climate_entity_id"])
        if preheat and vin and climate_state == "off":
            
            if not allow_command_entity_integration("Cupra We Connect Climate service Defrost", "preheat()", integration = integration, check_only=True): return
            allow_command_entity_integration("Cupra We Connect Climate service Defrost", "preheat()", integration = integration)
            
            _LOGGER.info("Preheating ev car")
            service.call(integration, "volkswagen_id_set_climatisation", vin=vin, start_stop="start", blocking=True)
            drive_efficiency("preheat")
            
            if outdoor_temp <= -1.0 or forecast_temp <= -1.0:
                heating_type = "Optøer"
                
            if CONFIG['notification']['preheating']:
                my_notify(message = f"{heating_type} bilen til kl. {next_drive.strftime('%H:%M')}", title = TITLE, notify_list = CONFIG['notify_list'], admin_only = False, always = False)
        elif climate_state == "heating":
            if ready_to_charge():
                if stop_preheat_no_driving(next_drive, now, preheat_min_before):
                    if not allow_command_entity_integration("Cupra We Connect Climate service Turn off", "preheat()", integration = integration, check_only=True): return
                    allow_command_entity_integration("Cupra We Connect Climate service Turn off", "preheat()", integration = integration)
                    
                    _LOGGER.info("Car not moved stopping preheating ev car")
                    service.call(integration, "volkswagen_id_set_climatisation", vin=vin, start_stop="stop", blocking=True)
                    drive_efficiency("preheat_cancel")
                    
                    if CONFIG['notification']['preheating']:
                        my_notify(message = f"Forvarmning af bilen stoppet, pga ingen kørsel kl. {next_drive.strftime('%H:%M')}", title = TITLE, notify_list = CONFIG['notify_list'], admin_only = False, always = False)
    else:
        _LOGGER.warning(f"Integration {integration} not supported")

def ready_to_charge():
    _LOGGER = globals()['_LOGGER'].getChild("ready_to_charge")
    
    def entity_unavailable(entity_id):
        if is_entity_configured(entity_id) and not is_entity_available(entity_id): return True
        
    if entity_unavailable(CONFIG['charger']['entity_ids']['status_entity_id']) or entity_unavailable(CONFIG['charger']['entity_ids']['enabled_entity_id']):
        return
    
    charger_status = get_state(CONFIG['charger']['entity_ids']['status_entity_id'], float_type=False, error_state="connected")
    charger_enabled = get_state(CONFIG['charger']['entity_ids']['enabled_entity_id'], float_type=False, error_state="off") if is_entity_configured(CONFIG['charger']['entity_ids']['enabled_entity_id']) else "on"
    
    if charger_enabled != "on":
        _LOGGER.warning(f"Charger was off, turning it on")
        start_charging({CONFIG['charger']['entity_ids']['enabled_entity_id']: "charger"})
        
    if charger_status in CHARGER_NOT_READY_STATUS:
        _LOGGER.info("Charger cable disconnected")
        set_charging_rule(f"Lader kabel frakoblet")
        
        if not is_ev_configured() and float(get_state(f"input_number.{__name__}_battery_level", float_type=True, error_state=0.0)) != 0.0:
            _LOGGER.info("Reseting battery level to 0.0")
            set_state(entity_id=f"input_number.{__name__}_battery_level", new_state=0.0)
        return
    elif manual_charging_enabled() or manual_charging_solar_enabled():
        return True
    else:
        if is_ev_configured():
            if is_entity_configured(CONFIG['ev_car']['entity_ids']['location_entity_id']):
                currentLocation = get_state(CONFIG['ev_car']['entity_ids']['location_entity_id'], float_type=False, try_history=True, error_state="home")
            else:
                currentLocation = get_state(CONFIG['charger']['entity_ids']['status_entity_id'], float_type=False, try_history=True, error_state="connected")
            
                if currentLocation in ENTITY_UNAVAILABLE_STATES or currentLocation in CHARGER_NOT_READY_STATUS:
                    currentLocation = "away"
                    _LOGGER.info(f"currentLocation: {currentLocation}, setting to away")
                else:
                    currentLocation = "home"
                    _LOGGER.info(f"currentLocation: {currentLocation}, setting to home")

            
            charger_connector = get_state(CONFIG['charger']['entity_ids']['cable_connected_entity_id'], float_type=False, error_state="on") if is_entity_configured(CONFIG['charger']['entity_ids']['cable_connected_entity_id']) else "not_configured"
            ev_charger_connector = get_state(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id'], float_type=False, error_state="on") if is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']) else "not_configured"
            
            #_LOGGER.info(f"currentLocation: {currentLocation}, charger_connector: {charger_connector}, ev_charger_connector: {ev_charger_connector}")
            if (ev_charger_connector in EV_PLUGGED_STATES or charger_connector in CHARGER_READY_STATUS or
                charger_status in CHARGER_READY_STATUS) and currentLocation != "home":
                _LOGGER.info("To long away from home")
                set_charging_rule(f"⛔Ladekabel forbundet, men bilen ikke hjemme")
                return
            '''elif charger_status in CHARGER_READY_STATUS and not ev_power_connected():
                _LOGGER.info("Charger cable connected, but car not updated")
                set_charging_rule(f"⚠️Ladekabel forbundet, men bilen ikke opdateret")
                return True #Test to charge anyway'''

            #TODO check charger_connector on monta
            if charger_connector != "on" and ev_charger_connector not in EV_PLUGGED_STATES:
                _LOGGER.info("Charger cable is Disconnected")
                set_charging_rule(f"⚠️Ladekabel ikke forbundet til bilen\nPrøver at vække bilen")
                wake_up_ev()
                return True #Test to charge anyway
            
            if not ev_power_connected():
                _LOGGER.info("Chargeport not open")
                set_charging_rule(f"⚠️Elbilens ladeport er ikke åben\nPrøver at vække bilen")
                wake_up_ev()
                return True #Test to charge anyway
            
            if entity_unavailable(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']) or entity_unavailable(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']):
                _LOGGER.info("Chargeport or charge cable entity not available")
                set_charging_rule(f"⛔Elbilens ladeport eller ladekabel er ikke tilgængelig\nPrøver at vække bilen")
                wake_up_ev()
                return
            
    return True

def start_charging(entities = None, force = False):
    _LOGGER = globals()['_LOGGER'].getChild("start_charging")
    if entities is None:
        entities = {
            CONFIG['charger']['entity_ids']['enabled_entity_id']: "charger",
            CONFIG['charger']['entity_ids']['start_stop_charging_entity_id']: "charger",
            CONFIG['ev_car']['entity_ids']['charge_switch_entity_id']: "ev_car",
        }
    
    for entity_id, config_domain in entities.items():
        if is_entity_available(entity_id):
            integration = get_integration(entity_id)
            
            if integration == "cupra_we_connect" and service.has_service(integration, "volkswagen_id_start_stop_charging"):
                charging_state = get_state(entity_id, float_type=False, error_state="off")
                charging_power = get_state(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], float_type=True, error_state=0.0)
                if charging_state == "off" and charging_power <= CONFIG['charger']['power_voltage']:
                    if not allow_command_entity_integration(f"{integration}.volkswagen_id_start_stop_charging service Start charging", "start_charging()", integration = integration, check_only=True):
                        if not force:
                            continue
                    
                    vin = get_vin_cupra_born(entity_id)
                    if not vin:
                        _LOGGER.warning(f"Vin not found for {entity_id}")
                        continue
                    
                    allow_command_entity_integration(f"{integration}.volkswagen_id_start_stop_charging service Start charging", "start_charging()", integration = integration)
                    
                    _LOGGER.info(f"Starting charging for {entity_id} with service {integration}.volkswagen_id_start_stop_charging")
                    service.call(integration, "volkswagen_id_start_stop_charging", vin=vin, start_stop="start", blocking=True)
            elif config_domain == "charger":
                send_command(entity_id, "on")
            elif config_domain == "ev_car":
                ev_send_command(entity_id, "on")
        else:
            if entity_id:
                _LOGGER.warning(f"Entity {entity_id} not available")

def stop_charging(entities = None, force = False):
    _LOGGER = globals()['_LOGGER'].getChild("stop_charging")
    if entities is None:
        entities = {
            CONFIG['charger']['entity_ids']['start_stop_charging_entity_id']: "charger",
            CONFIG['ev_car']['entity_ids']['charge_switch_entity_id']: "ev_car",
        }

    for entity_id, config_domain in entities.items():
        if is_entity_available(entity_id):
            integration = get_integration(entity_id)
            
            if integration == "cupra_we_connect" and service.has_service(integration, "volkswagen_id_start_stop_charging"):
                charging_state = get_state(entity_id, float_type=False, error_state="off")
                charging_power = get_state(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], float_type=True, error_state=0.0)
                if charging_state in EV_PLUGGED_STATES and charging_power > CONFIG['charger']['power_voltage']:
                    if not allow_command_entity_integration(f"{integration}.volkswagen_id_start_stop_charging service Stop charging", "stop_charging()", integration = integration, check_only=True):
                        if not force:
                            continue
                    
                    vin = get_vin_cupra_born(entity_id)
                    if not vin:
                        _LOGGER.warning(f"Vin not found for {entity_id}")
                        continue
                    
                    allow_command_entity_integration(f"{integration}.volkswagen_id_start_stop_charging service Stop charging", "stop_charging()", integration = integration)
                    _LOGGER.info(f"Stopping charging for {entity_id} with service {integration}.volkswagen_id_start_stop_charging")
                    service.call(integration, "volkswagen_id_start_stop_charging", vin=vin, start_stop="stop", blocking=True)
            elif config_domain == "charger":
                send_command(entity_id, "off")
                break
            elif config_domain == "ev_car":
                ev_send_command(entity_id, "off")
                break
        else:
            if entity_id:
                _LOGGER.warning(f"Entity {entity_id} not available")
    
def is_charging():
    _LOGGER = globals()['_LOGGER'].getChild("is_charging")
    global CHARGING_IS_BEGINNING, RESTARTING_CHARGER, RESTARTING_CHARGER_COUNT, CURRENT_CHARGING_SESSION, CHARGING_HISTORY_DB
    
    def reset():
        global CHARGING_IS_BEGINNING, RESTARTING_CHARGER, RESTARTING_CHARGER_COUNT
        
        if RESTARTING_CHARGER_COUNT > 0 or charger_enabled != "on":
            start_charging({CONFIG['charger']['entity_ids']['enabled_entity_id']: "charger"})
            
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
    
    if charger_status in CHARGER_COMPLETED_STATUS or charger_status in CHARGER_CHARGING_STATUS:
        if RESTARTING_CHARGER_COUNT > 0:
            _LOGGER.info("Ev is charging as it should again")
            
            if CURRENT_CHARGING_SESSION['start']:
                when = CURRENT_CHARGING_SESSION['start']
                
                if 1 < RESTARTING_CHARGER_COUNT < 3:
                    if emoji_charging_error not in CHARGING_HISTORY_DB[when]["emoji"]:
                        CHARGING_HISTORY_DB[when]["emoji"] = CHARGING_HISTORY_DB[when]["emoji"].replace(emoji_charging_error, emoji_charging_problem)
                        charging_history_combine_and_set()
            
            my_notify(message = f"Elbilen lader, som den skal igen", title = f"{TITLE} Elbilen lader", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True)
        reset()
        
        if charger_status in CHARGER_CHARGING_STATUS:
            return True
        else:
            return
        
    if not ready_to_charge() or not CURRENT_CHARGING_SESSION['start']:
        reset()
        return
    
    when = CURRENT_CHARGING_SESSION['start']
    if RESTARTING_CHARGER_COUNT == 0 and minutesBetween(getTime(), when, error_value=CONFIG['cron_interval'] + 5) <= CONFIG['cron_interval'] * 2:
        return
    
    if "easee" == get_integration(CONFIG['charger']['entity_ids']['dynamic_circuit_limit']) and is_entity_available(CONFIG['charger']['entity_ids']['dynamic_circuit_limit']):
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
            my_notify(message = f"Starter ladningen igen, {RESTARTING_CHARGER_COUNT} forsøg", title = f"{TITLE} Elbilen lader ikke", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True)
            
            start_charging(force = True)
            RESTARTING_CHARGER = False
        elif charger_status in ENTITY_UNAVAILABLE_STATES:
            set_charging_rule(f"⛔Fejl i ladning af elbilen\nLader ikke tilgængelig")
            raise Exception(f"Charger is unavailable, entity id: {CONFIG['charger']['entity_ids']['status_entity_id']}")
        elif charger_status == "error":
            set_charging_rule(f"⛔Fejl i ladning af elbilen\nKritisk fejl på lader, tjek integration eller Easee app")
            raise Exception(f"Charger critical error, check Easee app or Home Assistant")
        elif charger_status in CHARGER_READY_STATUS:
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
                stop_charging({CONFIG['charger']['entity_ids']['start_stop_charging_entity_id']: "charger"}, force = True)
            else:
                if is_entity_configured(CONFIG['charger']['entity_ids']['enabled_entity_id']):
                    _LOGGER.warning(f"Restarting charger (attempts {RESTARTING_CHARGER_COUNT}): Stopping charger for now")
                    restarting = f"\nGenstarter laderen, {RESTARTING_CHARGER_COUNT} forsøg"
                    stop_charging({CONFIG['charger']['entity_ids']['enabled_entity_id']: "charger"}, force = True)
                else:
                    _LOGGER.warning(f"Restarting ev charging (attempts {RESTARTING_CHARGER_COUNT}): Stopping ev charging for now")
                    restarting = f"\nGenstarter elbil ladningen, {RESTARTING_CHARGER_COUNT} forsøg"
                    stop_charging({CONFIG['ev_car']['entity_ids']['charge_switch_entity_id']: "ev_car"}, force = True)
                
        my_notify(message = f"Elbilen lader ikke som den skal:\n{e}{restarting}", title = f"{TITLE} Elbilen lader ikke", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True)
            
    _LOGGER.debug(f"DEBUG: CHARGING_IS_BEGINNING:{CHARGING_IS_BEGINNING} RESTARTING_CHARGER:{RESTARTING_CHARGER} RESTARTING_CHARGER_COUNT:{RESTARTING_CHARGER_COUNT}")
    _LOGGER.debug(f"DEBUG: charger_enabled:{charger_enabled} charger_status:{charger_status} current_charging_amps:{current_charging_amps} dynamic_circuit_limit:{dynamic_circuit_limit}")

def charging_without_rule():
    _LOGGER = globals()['_LOGGER'].getChild("charging_without_rule")
    global CHARGING_NO_RULE_COUNT
    
    minutes = max(5, int(round_up(CONFIG['cron_interval'] / 2)))
    
    if getMinute() < minutes or TESTING: return False
    
    now = getTime()
    past = now - datetime.timedelta(minutes=minutes)
    
    entity_id = CONFIG['charger']['entity_ids']['power_consumtion_entity_id']
    
    power = get_state(entity_id, float_type=True, error_state=0.0)
    power_avg = round(abs(float(get_average_value(entity_id, past, now, convert_to="W", error_state=0.0))), 3)
    
    trigger_count = 3
    
    if power != 0.0 and (power > CONFIG['charger']['power_voltage'] and power_avg > CONFIG['charger']['power_voltage']):
        if CHARGING_NO_RULE_COUNT > 0:
            stop_charging()
        
        if CHARGING_NO_RULE_COUNT > trigger_count:
            if not CURRENT_CHARGING_SESSION['start']:
                charging_history({'Price': get_current_hour_price(), 'Cost': 0.0, 'kWh': 0.0, 'battery_level': 0.0, 'no_rule': True}, "no_rule")
                
            set_charging_rule(f"{emoji_parse({'no_rule': True})}Lader uden grund {int(power_avg)}W")
            _LOGGER.warning(f"Charging without rule for {entity_id} power: {power}W, power_avg: {power_avg}W {CHARGING_NO_RULE_COUNT} times")
            
            if CHARGING_NO_RULE_COUNT == trigger_count + 1:
                unavailable_entities_str = ""
                unavailable_entities = get_all_unavailable_entities()
                if unavailable_entities:
                    unavailable_entities_str = "\n\nFølgende enheder er ikke tilgængelige:"
                
                for entity in unavailable_entities:
                    unavailable_entities_str += f"\n- {entity}"
                my_notify(message = f"Tjek evt. følgende:\n- Genstart afhænginge integrationer der er offline\n- Genstart Home Assistant{unavailable_entities_str}", title = f"{TITLE} Elbilen lader uden grund", notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True, persistent_notification_id=f"{__name__}_charging_without_rule")
            
            integration = get_integration(entity_id)
            
            if integration:
                my_persistent_notification(message = f"⛔Entity \"{entity_id}\" lader uden grund\nGenstarter {integration.capitalize()}", title = f"{TITLE} Elbilen lader uden grund", persistent_notification_id = f"{__name__}_charging_without_rule_{entity_id}")
                reload_entity_integration(entity_id)
            
            return True

        CHARGING_NO_RULE_COUNT += 1
    else:
        CHARGING_NO_RULE_COUNT = 0
    return False

def charge_if_needed():
    task.unique("charge_if_needed")
    _LOGGER = globals()['_LOGGER'].getChild("charge_if_needed")
    global CHARGE_HOURS
    
    def current_hour_in_charge_hours():
        current_hour = getTime().replace(hour=getHour(), minute=0, second=0, tzinfo=None)
        for timestamp in CHARGE_HOURS:
            if isinstance(timestamp, datetime.datetime) and timestamp.tzinfo is None:
                if timestamp.replace(minute=0, second=0, microsecond=0) == current_hour:
                    return timestamp
        return False
    
    try:
        charging_rule = f"Lader ikke"
        
        trip_date_time = get_trip_date_time() if get_trip_date_time() != resetDatetime() else resetDatetime()
        trip_planned = is_trip_planned()
        
        cheap_grid_charge_hours()
        
        if trip_planned:
            if trip_date_time != resetDatetime() and minutesBetween(getTime(), trip_date_time, error_value=0) < CHARGING_ALLOWED_AFTER_GOTO_TIME:
                _LOGGER.info(f"Trip date {trip_date_time} exceeded by an hour. Reseting trip settings")
                trip_reset()
                cheap_grid_charge_hours()
                
        solar_available = max_local_energy_available_remaining_hour()
        
        solar_period = solar_available['period']
        solar_watt = solar_available['watt']

        powerwall_discharge_watt = 0.0
        if is_powerwall_configured():
            discharge_above_needed = get_powerwall_discharge_above_needed()
            powerwall_battery_level = get_powerwall_battery_level()
            powerwall_reserved_battery_level = get_ev_charge_after_powerwall_battery_level()
            
            powerwall_discharging_consumption = power_values(period=max(CONFIG["cron_interval"] * 2, 20))["powerwall_discharging_consumption"]
            powerwall_discharge_watt = powerwall_discharging_consumption
            if discharge_above_needed and powerwall_battery_level > powerwall_reserved_battery_level + 1.0 and powerwall_discharging_consumption < POWERWALL_DISCHARGING_TRIGGER:
                powerwall_discharge_watt = CONFIG["solar"]["powerwall_discharging_power"] if powerwall_discharging_consumption < POWERWALL_DISCHARGING_TRIGGER else powerwall_discharging_consumption

        inverter_watt = solar_watt
        inverter_amps = calc_charging_amps(inverter_watt, max_allowed=CONFIG["solar"]["inverter_discharging_power_limit"])[:-1]  # Remove last element (watt)
                        
        currentHour = getTime().replace(hour=getHour(), minute=0, second=0, tzinfo=None)
        current_price = get_current_hour_price()
        
        charging_limit = min(range_to_battery_level(), get_max_recommended_charge_limit_battery_level())
        amps = [3.0, 0.0]
                
        '''if trip_planned:
            inverter_amps[1] = 0.0'''
            
        _LOGGER.info(f"Solar Production Available Remaining Hour: {solar_available}")
        
        if inverter_amps[1] != 0.0:
            alsoCheapPower = ""
            charging_limit = get_max_recommended_charge_limit_battery_level()
            solar_using_grid_price = False
            
            if is_solar_configured():
                solar_using_grid_price = True if float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price'])) == -1.0 else False
            
            if current_hour_in_charge_hours():
                timestamp = current_hour_in_charge_hours()
                if "half_min_avg_price" in CHARGE_HOURS[timestamp]:
                    amps = [CONFIG['charger']['charging_phases'], int(CONFIG['charger']['charging_max_amp'])]
                    charging_limit = charging_limit if charging_limit > get_ultra_cheap_grid_charging_max_battery_level() else get_ultra_cheap_grid_charging_max_battery_level()
                    alsoCheapPower = " + Ultra cheap power"
                elif "under_min_avg_price" in CHARGE_HOURS[timestamp]:
                    amps = [CONFIG['charger']['charging_phases'], int(CONFIG['charger']['charging_max_amp'])]
                    charging_limit = charging_limit if charging_limit > get_very_cheap_grid_charging_max_battery_level() else get_very_cheap_grid_charging_max_battery_level()
                    alsoCheapPower = " + Cheap power"
                else:
                    amps = [CONFIG['charger']['charging_phases'], int(CONFIG['charger']['charging_max_amp'])]
                    charging_limit = round_up(battery_level() + CHARGE_HOURS[timestamp]['battery_level'])
                    alsoCheapPower = " + Grid Charging not enough solar production"
                charging_limit = min(charging_limit, get_max_recommended_charge_limit_battery_level())
            elif CONFIG["solar"]["enable_selling_during_expensive_hours"] and solar_using_grid_price and currentHour in CHARGE_HOURS['expensive_hours'] and is_solar_production_available(solar_watt):
                charging_rule = f"Sælger solcelle overproduktion, da rå strøm prisen er dyr ({round(get_solar_sell_price(), 2)}kr.)"
                _LOGGER.info(f"Ignoring solar overproduction, because of expensive hour")
                inverter_amps[1] = 0.0
                
        
        if is_calculating_charging_loss():
            completed_battery_level = float(get_state(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'], float_type=True, error_state=100.0)) if is_ev_configured() and is_entity_configured(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id']) else get_completed_battery_level()
            _LOGGER.info(f"Calculating charging loss {completed_battery_level}%")
            
            if completed_battery_level < get_max_recommended_charge_limit_battery_level():
                completed_battery_level = get_max_recommended_charge_limit_battery_level()
                charging_limit = get_max_recommended_charge_limit_battery_level()
                
            charging_rule = f"{emoji_parse({'charging_loss': True})}Beregner ladetab, lader til {completed_battery_level}%"
            amps = [CONFIG['charger']['charging_phases'], CONFIG['charger']['charging_max_amp']]
            
            battery = round(completed_battery_level - battery_level(), 1)
            kwh = round(percentage_to_kwh(battery, include_charging_loss = True))
            cost = round(current_price * kwh, 2)
            charging_history({'Price': current_price, 'Cost': cost, 'kWh': kwh, 'battery_level': battery, 'charging_loss': True, 'solar': is_solar_production_available(solar_watt), 'powerwall': is_powerwall_discharging(powerwall_discharge_watt)}, "charging_loss")
        elif manual_charging_enabled() or manual_charging_solar_enabled():
            charging_limit = get_max_recommended_charge_limit_battery_level()
            if not manual_charging_solar_enabled():
                _LOGGER.info("Manual charging")
                amps = [CONFIG['charger']['charging_phases'], CONFIG['charger']['charging_max_amp']]
                charging_rule = f"{emoji_parse({'manual': True})}Manuel ladning tilladt {int(amps[0] * amps[1] * CONFIG['charger']['power_voltage'])}W"
            else:
                _LOGGER.info(f"Manual charging solar only")
                amps = inverter_amps
                solar_charging = f" {int(amps[0] * amps[1] * CONFIG['charger']['power_voltage'])}W" if inverter_amps[1] != 0.0 else ""
                charging_rule = f"{emoji_parse({'manual': True, "solar": True})}Manuel ladning tilladt, kun sol {solar_charging}"
                
            if amps[1] > 0.0:
                charging_history({'Price': get_solar_sell_price() if inverter_amps[1] != 0.0 else current_price, 'Cost': 0.0, 'kWh': 0.0, 'battery_level': 0.0, 'manual': True, 'solar': is_solar_production_available(solar_watt)}, "manual")
            else:
                stop_current_charging_session()
        elif ready_to_charge():
            if current_hour_in_charge_hours():
                timestamp = current_hour_in_charge_hours()
                CHARGE_HOURS[timestamp]['solar'] = is_solar_production_available(solar_watt)
                CHARGE_HOURS[timestamp]['powerwall'] = is_powerwall_discharging(powerwall_discharge_watt)
                charging_history(CHARGE_HOURS[timestamp], "planned")
                
                battery_level_plus_charge = battery_level() + CHARGE_HOURS[timestamp]['battery_level']
                max_level_today = CHARGE_HOURS['max_charging_level_today']
                charging_limit = min(round_up(max(battery_level_plus_charge, max_level_today, range_to_battery_level())), 100.0)
                amps = [CONFIG['charger']['charging_phases'], CHARGE_HOURS[timestamp]['ChargingAmps']]
                '''_LOGGER.error(f"battery_level_plus_charge:{battery_level_plus_charge}")
                _LOGGER.error(f"max_level_today:{max_level_today}")
                _LOGGER.error(f"range_to_battery_level():{range_to_battery_level()}")
                _LOGGER.error(f"charging_limit:{charging_limit}")'''
                emoji = emoji_parse(CHARGE_HOURS[timestamp])
                charging_rule = f"Lader op til {emoji}"
                _LOGGER.info(f"Charging because of {emoji} {CHARGE_HOURS[timestamp]['Price']}kr. {int(CONFIG['charger']['charging_phases'])}x{CHARGE_HOURS[timestamp]['ChargingAmps']}amps ({MAX_KWH_CHARGING}kWh)")
            elif get_state(f"input_boolean.{__name__}_forced_charging_daily_battery_level", error_state="on") == "on" and battery_level() < get_min_daily_battery_level():
                if currentHour in CHARGE_HOURS['expensive_hours']:
                    charging_rule = f"{emoji_parse({'low_battery': True})}Lader ikke, pga. for dyr strøm"
                    _LOGGER.info(f"Battery under <{get_min_daily_battery_level()}%, but power is expensive: {date_to_string(CHARGE_HOURS['expensive_hours'], format = '%H:%M')}")
                else:
                    battery = round(get_min_daily_battery_level() - battery_level(), 1)
                    kwh = round(percentage_to_kwh(battery, include_charging_loss = True))
                    cost = round(current_price * kwh, 2)
                    charging_history({'Price': current_price, 'Cost': cost, 'kWh': kwh, 'battery_level': battery, 'low_battery': True, 'solar': is_solar_production_available(solar_watt), 'powerwall': is_powerwall_discharging(powerwall_discharge_watt)}, "low_battery")
                    charging_limit = get_min_daily_battery_level()
                    amps = [CONFIG['charger']['charging_phases'], int(CONFIG['charger']['charging_max_amp'])]
                    charging_rule = f"{emoji_parse({'low_battery': True})}Lader pga. batteriniveauet <{get_min_daily_battery_level()}%"
                    _LOGGER.info(f"Charging because of under <{get_min_daily_battery_level()}%")
            elif solar_charging_enabled() and inverter_amps[1] != 0.0 and battery_level() < (get_max_recommended_charge_limit_battery_level() - 1.0):
                if current_hour_in_charge_hours():
                    timestamp = current_hour_in_charge_hours()
                    CHARGE_HOURS[timestamp]['solar'] = is_solar_production_available(solar_watt)
                    CHARGE_HOURS[timestamp]['powerwall'] = is_powerwall_discharging(powerwall_discharge_watt)
                    charging_history(CHARGE_HOURS[timestamp], "planned")
                else:
                    charging_history({'Price': get_solar_sell_price(), 'Cost': 0.0, 'kWh': 0.0, 'battery_level': 0.0, 'solar': is_solar_production_available(solar_watt), 'powerwall': is_powerwall_discharging(powerwall_discharge_watt)}, "local_energy")
                amps = inverter_amps
                
                solar_string = f"{emoji_parse({'solar': True})}Solcelle" if is_solar_production_available(solar_watt) else ""
                powerwall_string = f"{emoji_parse({'powerwall': True})}Powerwall" if is_powerwall_discharging(powerwall_discharge_watt) else ""
                inverter_string = " &".join([solar_string, powerwall_string]) if is_solar_production_available(solar_watt) and is_powerwall_discharging(powerwall_discharge_watt) else solar_string or powerwall_string

                charging_rule = f"{inverter_string} lader {int(amps[0] * amps[1] * CONFIG['charger']['power_voltage'])}W"
                
                _LOGGER.info(f"EV solar/powerwall charging at max {amps}{alsoCheapPower}")
                _LOGGER.debug(f"solar_watt:{solar_watt} solar_period:{solar_period}")
            else:
                if not charging_without_rule():
                    stop_current_charging_session()
                    _LOGGER.info("No rules for charging")
        else:
            if not charging_without_rule():
                stop_current_charging_session()
                _LOGGER.info("EV not ready to charge")
        
        if fill_up_charging_enabled():
            charging_limit = max(charging_limit, get_max_recommended_charge_limit_battery_level())
        
        if amps[1] > 0.0:
            ev_send_command(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'], verify_charge_limit(charging_limit))
            start_charging()
        else:
            stop_charging()
        
        set_charging_rule(charging_rule)
        set_charger_charging_amps(*amps)
    except Exception as e:
        global ERROR_COUNT
        
        error_message = f"Error running charge_if_needed(), setting charger and car to max: {e}"
        _LOGGER.error(error_message)
        my_persistent_notification(f"Error running charge_if_needed(), setting charger and car to max\nTrying to restart script to fix error in {ERROR_COUNT}/3: {e}", f"{TITLE} error", persistent_notification_id=f"{__name__}_restart_count_error")
        
        if ERROR_COUNT == 3:
            save_error_to_file(error_message, caller_function_name = "charge_if_needed()")
            _LOGGER.error(f"Restarting script to maybe fix error!!!")
            my_persistent_notification(f"Restarting script to maybe fix error!!!", f"{TITLE} error", persistent_notification_id=f"{__name__}_restart_script")
            
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
    
    integration = get_integration(CONFIG['charger']['entity_ids']['status_entity_id'])
    try:
        if integration == "easee":
            if is_entity_available(CONFIG['charger']['entity_ids']['status_entity_id']):
                if service.has_service(integration, "set_charging_cost"):
                    service.call(integration, "set_charging_cost", blocking=True,
                                        charger_id=get_attr(CONFIG['charger']['entity_ids']['status_entity_id'], "id"),
                                        cost_per_kwh=price,
                                        vat=25,
                                        currency_id="DKK")
                else:
                    raise Exception(f"Easee service dont have set_charging_cost, cant set price to {price}")
                _LOGGER.info(f"Setting charging cost to {price} in Easee")
    except Exception as e:
        _LOGGER.error(f"Cant set charging cost for {integration.capitalize()}: {e}")
        my_persistent_notification(f"Cant set charging cost for {integration.capitalize()}: {e}", f"{TITLE} error", persistent_notification_id=f"{__name__}_set_charging_price")

def kwh_charged_by_solar():
    _LOGGER = globals()['_LOGGER'].getChild("kwh_charged_by_solar")
    
    if not is_solar_configured(): return
        
    now = getTime()
    past = now - datetime.timedelta(minutes=60)
    
    ev_watt = round(abs(float(get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0))), 3)
    solar_watt = round(max(local_energy_available(period = 60, without_all_exclusion = True, update_entity = False, solar_only = True), 0.0), 3)
    
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
        my_persistent_notification(f"Cant set input_number.{__name__}_kwh_charged_by_solar: {e}", f"{TITLE} error", persistent_notification_id=f"{__name__}_kwh_charged_by_solar")
    
def solar_charged_percentage():
    _LOGGER = globals()['_LOGGER'].getChild("solar_percentage")
    
    if not is_solar_configured(): return
    
    total_ev_kwh = get_state(CONFIG['charger']['entity_ids']['lifetime_kwh_meter_entity_id'], float_type=True, try_history=True, error_state=None)
    total_solar_ev_kwh = get_state(f"input_number.{__name__}_kwh_charged_by_solar", float_type=True, try_history=True, error_state=None)
    
    if total_ev_kwh is None or total_solar_ev_kwh is None:
        _LOGGER.warning(f"total_ev_kwh or total_solar_ev_kwh is None")
        return
    
    try:
        if float(total_ev_kwh) == 0.0:
            set_state(f"sensor.{__name__}_solar_charged_percentage", 0.0)
            return
            
        set_state(f"sensor.{__name__}_solar_charged_percentage", round(((float(total_solar_ev_kwh) / float(total_ev_kwh)) * 100.0), 1))
    except Exception as e:
        _LOGGER.error(f"Cant set sensor.{__name__}_solar_charged_percentage total_solar_ev_kwh={total_solar_ev_kwh} total_ev_kwh={total_ev_kwh}: {e}")
        my_persistent_notification(f"Cant set sensor.{__name__}_solar_charged_percentage total_solar_ev_kwh={total_solar_ev_kwh} total_ev_kwh={total_ev_kwh}: {e}", f"{TITLE} error", persistent_notification_id=f"{__name__}_solar_charged_percentage")
    
def calc_co2_emitted(period = None, added_kwh = None):
    _LOGGER = globals()['_LOGGER'].getChild("calc_co2_emitted")
    
    if added_kwh is None:
        return 0.0
    
    if not is_entity_available(CONFIG['charger']['entity_ids']['co2_entity_id']): return
    
    if CONFIG['charger']['entity_ids']['co2_entity_id'] not in state.names(domain="sensor"): return
    
    minutes = getMinute() if period is None else period
    
    now = getTime()
    past = now - datetime.timedelta(minutes=minutes)
    
    ev_kwh = round(abs(float(get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="W", error_state=0.0))) / 1000.0, 3)
    solar_kwh_available = round(max(local_energy_available(period = minutes, without_all_exclusion = True, update_entity = False, solar_only = True), 0.0) / 1000.0, 3)
       
    ev_solar_kwh = round(solar_kwh_available, 3)
    ev_grid_kwh =  round(max(ev_kwh - (solar_kwh_available), 0.0), 3)
    
    grid_co2_emitted = 0.0
    grid_co2_kwh = float(get_state(entity_id=CONFIG['charger']['entity_ids']['co2_entity_id'], float_type=True, error_state=0.0))
    try:
        solar_co2_emitted = ((ev_solar_kwh / ev_kwh) * (10 / 1000.0)) #Solar co2 50g * 3years = 0.15 / 15years life = 0.01 = 10g/kWh
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

    values = power_values(from_time_stamp = past, to_time_stamp = now)
    ev_used_consumption = values['ev_used_consumption']
    
    watts_available_from_local_energy, watts_from_local_energy, solar_watts_of_local_energy, powerwall_watts_of_local_energy = local_energy_available(period = minutes, include_local_energy_distribution = True, without_all_exclusion = True, update_entity = False)
    
    min_watt = (SOLAR_CHARGING_TRIGGER_ON if is_solar_configured() else MAX_WATT_CHARGING) / 2 if in_between(getMinute(), 1, 58) else 0.0
    
    if (ev_used_consumption == 0.0 and not in_between(getMinute(), 1, 58)) or ev_used_consumption < min_watt:
        _LOGGER.debug("Calculating ev cost, when ev not charging. For display only")
        ev_used_consumption = SOLAR_CHARGING_TRIGGER_ON if is_solar_configured() else MAX_WATT_CHARGING
    else:
        watts_from_local_energy = round(min(watts_from_local_energy, ev_used_consumption), 3)
    
    ev_grid_watt =  round(max(ev_used_consumption - watts_from_local_energy, 0.0), 3)
    
    grid_kwh_price = float(get_state(CONFIG['prices']['entity_ids']['power_prices_entity_id'], float_type=True)) - get_refund()
    try:
        ev_grid_share = min(round(ev_grid_watt/ev_used_consumption, 2), 100.0)
        ev_grid_cost = round(ev_grid_share * grid_kwh_price, 5)
    except:
        ev_grid_share = 0.0
        ev_grid_cost = 0.0
    _LOGGER.debug(f"grid_kwh_price: {grid_kwh_price}kr")
    _LOGGER.debug(f"ev_grid_cost: ({ev_grid_watt}/{ev_used_consumption}={int(ev_grid_share*100)}%)*{grid_kwh_price} = {ev_grid_cost}")
    
    solar_kwh_price = get_solar_sell_price(set_entity_attr=update_entities)
    try:
        ev_solar_share = min(round(solar_watts_of_local_energy / ev_used_consumption, 2), 100.0)
        ev_solar_cost = round(ev_solar_share * solar_kwh_price, 5)
    except:
        ev_solar_share = 0.0
        ev_solar_cost = 0.0
    _LOGGER.debug(f"solar_kwh_price: {solar_kwh_price}kr")
    _LOGGER.debug(f"ev_solar_cost: ({solar_watts_of_local_energy}/{ev_used_consumption}={int(ev_solar_share*100)}%)*{solar_kwh_price} = {ev_solar_cost}")
    
    powerwall_kwh_price = get_powerwall_kwh_price()
    try:
        ev_powerwall_share = min(round(powerwall_watts_of_local_energy / ev_used_consumption, 2), 100.0)
        ev_powerwall_cost = round(ev_powerwall_share * powerwall_kwh_price, 5)
    except:
        ev_powerwall_share = 0.0
        ev_powerwall_cost = 0.0
    _LOGGER.debug(f"powerwall_kwh_price: {powerwall_kwh_price}kr")
    _LOGGER.debug(f"ev_powerwall_cost: ({powerwall_watts_of_local_energy}/{ev_used_consumption}={int(ev_powerwall_share*100)}%)*{powerwall_kwh_price} = {ev_powerwall_cost}")

    ev_total_price_kwh = round(ev_grid_cost + ev_solar_cost + ev_powerwall_cost, 3)

    if update_entities:
        _LOGGER.info(f"Setting sensor.{__name__}_kwh_cost_price to {ev_total_price_kwh}")
        set_state(f"sensor.{__name__}_kwh_cost_price", ev_total_price_kwh)

        if not is_solar_configured():
            raw_price = get_state(CONFIG['prices']['entity_ids']['power_prices_entity_id'], float_type=True)
            refund = get_refund()
            price = raw_price - refund
            set_attr(f"sensor.{__name__}_kwh_cost_price.raw_price", f"{raw_price:.2f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.refund", f"{refund:.2f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.price", f"{price:.2f} kr/kWh")
        else:
            set_attr(f"sensor.{__name__}_kwh_cost_price.local_energy_and_grid_ratio", "")
            set_attr(f"sensor.{__name__}_kwh_cost_price.solar_share", f"{ev_solar_share*100:.0f}%")
            set_attr(f"sensor.{__name__}_kwh_cost_price.solar_cost", f"{ev_solar_cost:.2f} kr")
            set_attr(f"sensor.{__name__}_kwh_cost_price.solar_kwh_price", f"{solar_kwh_price:.2f} kr/kWh")
            
            if is_powerwall_configured():
                set_attr(f"sensor.{__name__}_kwh_cost_price.powerwall_share", f"{ev_powerwall_share*100:.0f}%")
                set_attr(f"sensor.{__name__}_kwh_cost_price.powerwall_cost", f"{ev_powerwall_cost:.2f} kr")
                set_attr(f"sensor.{__name__}_kwh_cost_price.powerwall_kwh_price", f"{powerwall_kwh_price:.2f} kr/kWh")

            set_attr(f"sensor.{__name__}_kwh_cost_price.grid_share", f"{ev_grid_share*100:.0f}%")
            set_attr(f"sensor.{__name__}_kwh_cost_price.grid_cost", f"{ev_grid_cost:.2f} kr")
            set_attr(f"sensor.{__name__}_kwh_cost_price.grid_kwh_price", f"{grid_kwh_price:.2f} kr/kWh")
            set_attr(f"sensor.{__name__}_kwh_cost_price.ev_kwh_price", f"{ev_total_price_kwh:.2f} kr/kWh")
        
        set_charging_price(ev_total_price_kwh)

    return ev_total_price_kwh

def calc_local_energy_kwh(period = 60, ev_kwh = None, solar_period_current_hour = False):
    _LOGGER = globals()['_LOGGER'].getChild("calc_solar_kwh")
    
    if not is_solar_configured(): return 0.0
    
    minutes = getMinute() if solar_period_current_hour else period
    
    if ev_kwh is None:
        now = getTime()
        past = now - datetime.timedelta(minutes=minutes)
        
        ev_kwh = round(abs(float(get_average_value(CONFIG['charger']['entity_ids']['power_consumtion_entity_id'], past, now, convert_to="kW", error_state=0.0))), 3)
    ev_watt = ev_kwh * 1000.0

    watts_available_from_local_energy, watts_from_local_energy, solar_watts_of_local_energy, powerwall_watts_of_local_energy = local_energy_available(period = minutes, include_local_energy_distribution = True, without_all_exclusion = True, update_entity = False)
    
    _LOGGER.debug(f"ev_watt:{ev_watt} watts_from_local_energy:{watts_from_local_energy} solar_watts_of_local_energy:{solar_watts_of_local_energy} powerwall_watts_of_local_energy:{powerwall_watts_of_local_energy}")
    if watts_from_local_energy > ev_watt:
        miscalculated_ratio = watts_from_local_energy / ev_watt if ev_watt > 0.0 else 0.0
        solar_watts_of_local_energy = solar_watts_of_local_energy * miscalculated_ratio
        powerwall_watts_of_local_energy = powerwall_watts_of_local_energy * miscalculated_ratio
        watts_from_local_energy = ev_watt
    
    solar_kwh_available = round(max(watts_from_local_energy, 0.0) / 1000, 3)
    solar_kwh_of_local_energy = round(solar_watts_of_local_energy / 1000, 3)
    powerwall_kwh_of_local_energy = round(powerwall_watts_of_local_energy / 1000, 3)
    _LOGGER.debug(f"calc_solar_kwh called with period:{minutes} ev_kwh:{ev_kwh} solar_kwh_available:{solar_kwh_available} solar_kwh_of_local_energy:{solar_kwh_of_local_energy} powerwall_kwh_of_local_energy:{powerwall_kwh_of_local_energy}")

    return round(min(solar_kwh_available, ev_kwh), 3), solar_kwh_of_local_energy, powerwall_kwh_of_local_energy

def load_kwh_prices():
    _LOGGER = globals()['_LOGGER'].getChild("load_kwh_prices")
    global KWH_AVG_PRICES_DB
    
    def convert_to_int_if_possible(key):
        try:
            return int(key)
        except (ValueError, TypeError):
            return key
        
    def set_default_values(name):
        global KWH_AVG_PRICES_DB
        nonlocal force_save
        if name not in KWH_AVG_PRICES_DB:
            KWH_AVG_PRICES_DB[name] = {}
            
        for h in range(24):
            if h not in KWH_AVG_PRICES_DB[name]:
                KWH_AVG_PRICES_DB[name][h] = {}
                
            for d in range(7):
                if d not in KWH_AVG_PRICES_DB[name][h]:
                    KWH_AVG_PRICES_DB[name][h][d] = []
                    
        force_save = True
    
    version = 1.0
    force_save = False
    
    try:
        database = load_yaml(f"{__name__}_kwh_avg_prices_db")
        if "version" in database:
            version = float(database["version"])
            del database["version"]
        
        KWH_AVG_PRICES_DB = database.copy()

        if not KWH_AVG_PRICES_DB:
            create_yaml(f"{__name__}_kwh_avg_prices_db", db=KWH_AVG_PRICES_DB)
    except Exception as e:
        error_message = f"Error loading {__name__}_kwh_avg_prices_db: {e}"
        _LOGGER.error(error_message)
        save_error_to_file(error_message, caller_function_name = "load_kwh_prices()")
        my_persistent_notification(f"Kan ikke indlæse {__name__}_kwh_avg_prices_db: {e}", f"{TITLE} error", persistent_notification_id=f"{__name__}_load_kwh_prices")
    
    if KWH_AVG_PRICES_DB == {} or not KWH_AVG_PRICES_DB:
        KWH_AVG_PRICES_DB = {}
        
    for name in ("history", "history_sell"):
        if name not in KWH_AVG_PRICES_DB:
            version = 2.0
            set_default_values(name)
    
    for name in ("max", "mean", "min"):
        if name not in KWH_AVG_PRICES_DB:
            KWH_AVG_PRICES_DB[name] = []
            force_save = True
            
    if version <= 1.0:
        _LOGGER.info(f"Transforming database from version {version} to {KWH_AVG_PRICES_DB_VERSION}")
        old_db = KWH_AVG_PRICES_DB.copy()
                
        for name in ("history", "history_sell"):
            KWH_AVG_PRICES_DB[name] = {}
            
            for h in range(24):
                if h not in KWH_AVG_PRICES_DB[name]:
                    KWH_AVG_PRICES_DB[name][h] = {}
                    
                for d in range(7):
                    if d not in KWH_AVG_PRICES_DB[name][h]:
                        KWH_AVG_PRICES_DB[name][h][d] = old_db[name][h].copy()
        force_save = True
            
    if force_save:
        append_kwh_prices()
        save_kwh_prices()
        
    set_low_mean_price()
    
def save_kwh_prices():
    global KWH_AVG_PRICES_DB
    
    if len(KWH_AVG_PRICES_DB) > 0:
        db_to_file = KWH_AVG_PRICES_DB.copy()
        db_to_file["version"] = KWH_AVG_PRICES_DB_VERSION
        save_changes(f"{__name__}_kwh_avg_prices_db", db_to_file)

def append_kwh_prices():
    _LOGGER = globals()['_LOGGER'].getChild("append_kwh_prices")
    global KWH_AVG_PRICES_DB
    
    if len(KWH_AVG_PRICES_DB) == 0:
        load_kwh_prices()
    
    if CONFIG['prices']['entity_ids']['power_prices_entity_id'] in state.names(domain="sensor"):
        if "today" in get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id']):
            today = get_attr(CONFIG['prices']['entity_ids']['power_prices_entity_id'], "today")
            
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
                
            day_of_week = getDayOfWeek()
            
            for h in range(24):
                KWH_AVG_PRICES_DB['history'][h][day_of_week].insert(0, today[h] - get_refund())
                KWH_AVG_PRICES_DB['history'][h][day_of_week] = KWH_AVG_PRICES_DB['history'][h][day_of_week][:max_length]
                
                if is_solar_configured():
                    tariffs = 0.0
                    
                    if "tariffs" in power_prices_attr:
                        tariffs = attr["tariffs"][str(h)]
                        
                    tariff_sum = sum([transmissions_nettarif, systemtarif, elafgift, tariffs])
                    raw_price = today[h] - tariff_sum

                    energinets_network_tariff = SOLAR_SELL_TARIFF["energinets_network_tariff"]
                    energinets_balance_tariff = SOLAR_SELL_TARIFF["energinets_balance_tariff"]
                    solar_production_seller_cut = SOLAR_SELL_TARIFF["solar_production_seller_cut"]
                    
                    sell_tariffs = sum((solar_production_seller_cut, energinets_network_tariff, energinets_balance_tariff, transmissions_nettarif, systemtarif))
                    sell_price = raw_price - sell_tariffs
                        
                    sell_price = round(sell_price, 3)
                    KWH_AVG_PRICES_DB['history_sell'][h][day_of_week].insert(0, sell_price)
                    KWH_AVG_PRICES_DB['history_sell'][h][day_of_week] = KWH_AVG_PRICES_DB['history_sell'][h][day_of_week][:max_length]
                
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
        my_notify(message = f"Husk at sætte batteri niveauet på elbilen i Home Assistant", title = f"{TITLE} Elbilen batteri niveau", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True)

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
        my_notify(message = f"Skal elbilen tvangslades til minimum daglig batteri niveau\nLader ikke i de 3 dyreste timer", title = f"{TITLE} Elbilen batteri niveau under daglig batteri niveau", data=data, notify_list = CONFIG['notify_list'], admin_only = False, always = True)

if INITIALIZATION_COMPLETE:
    @time_trigger("startup")
    def startup(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("startup")
        global TASKS
        
        log_lines = []
        try:
            log_lines.append(welcome())
            log_lines.append(f"📟{BASENAME} started")
            log_lines.append(f"")
            log_lines.append(f"**Konfiguration:**")
            log_lines.append(f"📟Lader konfiguret: {'Ja' if is_ev_configured() else 'Nej'}")
            log_lines.append(f"📟Elbil konfiguret: {'Ja' if is_ev_configured() else 'Nej'}")
            log_lines.append(f"📟Solcelle konfiguret: {'Ja' if is_solar_configured() else 'Nej'}")
            log_lines.append(f"📟Powerwall konfiguret: {'Ja' if is_powerwall_configured() else 'Nej'}")
            log_lines.append(f"")
            set_charging_rule(f"📟Sætter entities op")
            log_lines.append(f"📟Sætter entities op")
            
            TASKS["startup_set_entity_friendlynames"] = task.create(set_entity_friendlynames)
            TASKS["startup_emoji_description"] = task.create(emoji_description)
            TASKS["startup_set_default_entity_states"] = task.create(set_default_entity_states)
            done, pending = task.wait({TASKS["startup_set_entity_friendlynames"], TASKS["startup_emoji_description"], TASKS["startup_set_default_entity_states"]})
            
            set_charging_rule(f"📟Indlæser databaserne")
            log_lines.append(f"📟Indlæser databaserne")
            
            TASKS["startup_load_power_values_db"] = task.create(load_power_values_db)
            TASKS["startup_load_solar_available_db"] = task.create(load_solar_available_db)
            TASKS["startup_load_kwh_prices"] = task.create(load_kwh_prices)
            TASKS["startup_load_drive_efficiency"] = task.create(load_drive_efficiency)
            TASKS["startup_load_km_kwh_efficiency"] = task.create(load_km_kwh_efficiency)
            done, pending = task.wait({TASKS["startup_load_power_values_db"], TASKS["startup_load_solar_available_db"], TASKS["startup_load_kwh_prices"], TASKS["startup_load_drive_efficiency"], TASKS["startup_load_km_kwh_efficiency"]})
            
            log_lines.append(f"📟Indlæser ladnings historik")
            
            TASKS["startup_load_charging_history"] = task.create(load_charging_history)
            done, pending = task.wait({TASKS["startup_load_charging_history"]})
            
            log_lines.append(f"📟Sætter småting op")
            
            TASKS["startup_solar_charged_percentage"] = task.create(solar_charged_percentage)
            TASKS["startup_is_battery_fully_charged"] = task.create(is_battery_fully_charged)
            TASKS["startup_set_estimated_range"] = task.create(set_estimated_range)
            TASKS["startup_calc_kwh_price"] = task.create(calc_kwh_price, getMinute(), update_entities = True)
            done, pending = task.wait({TASKS["startup_solar_charged_percentage"], TASKS["startup_is_battery_fully_charged"], TASKS["startup_set_estimated_range"], TASKS["startup_calc_kwh_price"]})
            
            log_lines.append(f"")
            log_lines.append(f"🚗 Batteri rækkevidde: {battery_range():.2f} km")
            log_lines.append(f"🚗 Batteri niveau: {battery_level():.0f}%")
            
            TASKS["startup_distance_per_percentage"] = task.create(distance_per_percentage)
            done, pending = task.wait({TASKS["startup_distance_per_percentage"]})
            
            distance_per_percent = TASKS["startup_distance_per_percentage"].result()
            log_lines.append(f"🚗 km/%: {distance_per_percent:.2f} km")
            log_lines.append(f"🚗 HA estimeret rækkevidde: {(battery_level() * distance_per_percent):.2f} km")
            log_lines.append(f"")
            
            TASKS["startup_calc_charging_amps"] = task.create(calc_charging_amps, 0.0, report = True)
            done, pending = task.wait({TASKS["startup_calc_charging_amps"]})
            
            amps_report = TASKS["startup_calc_charging_amps"].result()
            for line in amps_report.splitlines():
                log_lines.append(line)
            log_lines.append(f"")
            
            log_lines.append(f"📟Beregner ladeplan")
            set_charging_rule(f"📟Beregner ladeplan")
            
            TASKS["startup_charge_if_needed"] = task.create(charge_if_needed)
            TASKS["startup_preheat_ev"] = task.create(preheat_ev)
            TASKS["startup_drive_efficiency_save_car_stats"] = task.create(drive_efficiency_save_car_stats, bootup=True)
            done, pending = task.wait({TASKS["startup_charge_if_needed"], TASKS["startup_preheat_ev"], TASKS["startup_drive_efficiency_save_car_stats"]})
            
            if CONFIG['notification']['update_available']:
                TASKS["startup_check_master_updates"] = task.create(check_master_updates)
                done, pending = task.wait({TASKS["startup_check_master_updates"]})
        finally:
            for line in log_lines:
                _LOGGER.info(line)
                
            my_persistent_notification(f"{"\n".join(log_lines)}", f"📟{TITLE} started", persistent_notification_id=f"{__name__}_startup")
            
            for task_name in list(TASKS.keys()):
                if task_name.startswith("startup_"):
                    task_cancel(task_name, task_remove=True)
        
        append_overview_output(f"📟{BASENAME} started")
   
    @time_trigger("startup")
    @state_trigger(f"input_boolean.{__name__}_fill_up")
    @state_trigger(f"input_boolean.{__name__}_workplan_charging")
    def charging_rule(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("charging_rule")
        if trigger_type == "startup":
            if fill_up_charging_enabled() and workplan_charging_enabled():
                set_state(f"input_boolean.{__name__}_fill_up", "off")
                my_persistent_notification(f"❗Deaktivere Optimal ugeopladning (uden Arbejdsplan)\n📎Arbejdsplan opladning & Optimal ugeopladning (uden Arbejdsplan) kan ikke være aktiveret på sammetid", f"📟{TITLE} laderegel konflikt", persistent_notification_id=f"{__name__}_charging_rule_conflict")
        else:
            if value == "on":
                if var_name == f"input_boolean.{__name__}_fill_up":
                    if workplan_charging_enabled():
                        set_state(f"input_boolean.{__name__}_workplan_charging", "off")
                        my_persistent_notification(f"❗Deaktivere Arbejdsplan opladning\n\n📎Arbejdsplan opladning & Optimal ugeopladning (uden Arbejdsplan) kan ikke være aktiveret på sammetid", f"📟{TITLE} laderegel konflikt", persistent_notification_id=f"{__name__}_charging_rule_conflict")
                elif var_name == f"input_boolean.{__name__}_workplan_charging":
                    if fill_up_charging_enabled():
                        set_state(f"input_boolean.{__name__}_fill_up", "off")
                        my_persistent_notification(f"❗Deaktivere Optimal ugeopladning (uden Arbejdsplan)\n\n📎Arbejdsplan opladning & Optimal ugeopladning (uden Arbejdsplan) kan ikke være aktiveret på sammetid", f"📟{TITLE} laderegel konflikt", persistent_notification_id=f"{__name__}_charging_rule_conflict")
                
    @time_trigger(f"cron(0/{CONFIG['cron_interval']} * * * *)")
    @state_trigger(f"input_button.{__name__}_enforce_planning")
    @state_trigger(f"input_boolean.{__name__}_allow_manual_charging_now")
    @state_trigger(f"input_boolean.{__name__}_allow_manual_charging_solar")
    @state_trigger(f"input_boolean.{__name__}_calculate_charging_loss")
    def triggers_charge_if_needed(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("triggers_charge_if_needed")
        global TASKS
        try:
            if trigger_type == "time":
                TASKS["triggers_charge_if_needed_calc_kwh_price"] = task.create(calc_kwh_price, getMinute(), update_entities = True)
                done, pending = task.wait({TASKS["triggers_charge_if_needed_calc_kwh_price"]})
                
            if is_charging():
                TASKS["triggers_charge_if_needed_wake_up_ev"] = task.create(wake_up_ev)
                done, pending = task.wait({TASKS["triggers_charge_if_needed_wake_up_ev"]})
                
            TASKS["triggers_charge_if_needed_charge_if_needed"] = task.create(charge_if_needed)
            TASKS["triggers_charge_if_needed_is_battery_fully_charged"] = task.create(is_battery_fully_charged)
            TASKS["triggers_charge_if_needed_set_estimated_range"] = task.create(set_estimated_range)
            done, pending = task.wait({TASKS["triggers_charge_if_needed_charge_if_needed"], TASKS["triggers_charge_if_needed_is_battery_fully_charged"], TASKS["triggers_charge_if_needed_set_estimated_range"]})
            
            if var_name == f"input_button.{__name__}_enforce_planning" and TESTING:
                TASKS["triggers_charge_if_needed_debug_info"] = task.create(debug_info)
                done, pending = task.wait({TASKS["triggers_charge_if_needed_debug_info"]})
        finally:
            for task_name in list(TASKS.keys()):
                if task_name.startswith("triggers_charge_if_needed_"):
                    task_cancel(task_name, task_remove=True)

    @state_trigger(f"input_number.{__name__}_trip_charge_procent")
    @state_trigger(f"input_number.{__name__}_trip_range_needed")
    @state_trigger(f"input_datetime.{__name__}_trip_date_time")
    @state_trigger(f"input_datetime.{__name__}_trip_homecoming_date_time")
    @state_trigger(f"input_button.{__name__}_trip_reset")
    def state_trigger_ev_trips(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("state_trigger_ev_trips")
        global LAST_TRIP_CHANGE_DATETIME
        
        if var_name == f"input_number.{__name__}_trip_charge_procent":
            if value in ENTITY_UNAVAILABLE_STATES: return
            if get_trip_target_level() != 0.0:
                set_state(f"input_number.{__name__}_trip_range_needed", 0.0)
        elif var_name == f"input_number.{__name__}_trip_range_needed":
            if value in ENTITY_UNAVAILABLE_STATES: return
            if get_trip_range() != 0.0:
                set_state(f"input_number.{__name__}_trip_charge_procent", 0.0)
        elif var_name == f"input_datetime.{__name__}_trip_date_time":
            if value in ENTITY_UNAVAILABLE_STATES: return
            value = toDateTime(value)
            
            if value != resetDatetime() and (get_trip_homecoming_date_time() == resetDatetime() or get_trip_homecoming_date_time() < value):
                set_state(f"input_datetime.{__name__}_trip_homecoming_date_time", getTimeEndOfDay(value))
                
        elif var_name == f"input_datetime.{__name__}_trip_homecoming_date_time":
            if value in ENTITY_UNAVAILABLE_STATES: return
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
                    TASKS["state_trigger_charger_power_stop_current_charging_session"] = task.create(stop_current_charging_session)
                    done, pending = task.wait({TASKS["state_trigger_charger_power_stop_current_charging_session"]})
                    set_charging_rule(f"Lader ikke")
        except:
            pass
        finally:
            for task_name in list(TASKS.keys()):
                if task_name.startswith("state_trigger_charger_power_"):
                    task_cancel(task_name, task_remove=True)
    
    @state_trigger(f"{CONFIG['charger']['entity_ids']['status_entity_id']}")
    def state_trigger_charger_port(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("state_trigger_charger_port")
        global CURRENT_CHARGING_SESSION, TASKS
        try:
            _LOGGER.info(f"Charger port status changed from {old_value} to {value}")
            if old_value in CHARGER_NOT_READY_STATUS:
                
                TASKS["state_trigger_charger_port_notify_set_battery_level"] = task.create(notify_set_battery_level)
                TASKS["state_trigger_charger_port_wake_up_ev"] = task.create(wake_up_ev)
                done, pending = task.wait({TASKS["notify_set_battery_level"], TASKS["wake_up_ev"]})
                
                TASKS["state_trigger_charger_port_charge_if_needed"] = task.create(charge_if_needed)
                done, pending = task.wait({TASKS["state_trigger_charger_port_charge_if_needed"]})
            elif value in CHARGER_NOT_READY_STATUS:
                TASKS["state_trigger_charger_port_stop_current_charging_session"] = task.create(stop_current_charging_session)
                TASKS["state_trigger_charger_port_wake_up_ev"] = task.create(wake_up_ev)
                done, pending = task.wait({TASKS["state_trigger_charger_port_stop_current_charging_session"], TASKS["state_trigger_charger_port_wake_up_ev"]})
                
                set_state(f"input_boolean.{__name__}_allow_manual_charging_now", "off")
                set_state(f"input_boolean.{__name__}_allow_manual_charging_solar", "off")
                set_state(f"input_boolean.{__name__}_forced_charging_daily_battery_level", "off")
            elif old_value in CHARGER_CHARGING_STATUS and value in CHARGER_COMPLETED_STATUS:
                if not is_ev_configured() and CURRENT_CHARGING_SESSION['start']:
                    TASKS["state_trigger_charger_port_stop_current_charging_session"] = task.create(stop_current_charging_session)
                    done, pending = task.wait({TASKS["state_trigger_charger_port_stop_current_charging_session"]})
                    
                    set_state(entity_id=f"input_number.{__name__}_battery_level", new_state=get_completed_battery_level())
        finally:
            for task_name in list(TASKS.keys()):
                if task_name.startswith("state_trigger_charger_port_"):
                    task_cancel(task_name, task_remove=True)
         
    if is_entity_configured(CONFIG['ev_car']['entity_ids']['location_entity_id']):
        @state_trigger(f"{CONFIG['ev_car']['entity_ids']['location_entity_id']}")
        def state_trigger_ev_location(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("state_trigger_ev_location")
            global TASKS
            try:
                if value == "home":
                    TASKS["state_trigger_ev_location_charge_if_needed"] = task.create(charge_if_needed)
                    done, pending = task.wait({TASKS["state_trigger_ev_location_charge_if_needed"]})
            finally:
                for task_name in list(TASKS.keys()):
                    if task_name.startswith("state_trigger_ev_location_"):
                        task_cancel(task_name, task_remove=True)
    
    def wait_until_odometer_stable():
        task.unique("wait_until_odometer_stable")
        _LOGGER = globals()['_LOGGER'].getChild("wait_until_odometer_stable")
        if not is_ev_configured():
            return
        
        max_wait_time_minutes = 30
        updated_within_minutes = 5
        
        try:
            to_datetime = getTime()
            from_datetime = to_datetime - datetime.timedelta(hours=24)
            values = get_values(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], from_datetime, to_datetime, float_type=True, convert_to=None, include_timestamps=True, error_state={})
            if not values or not isinstance(values, dict) or not values.items():
                _LOGGER.warning(f"No odometer values found in the last 24 hours")
                return
            
            values_sorted = sorted(values.items(), reverse=True)
            last_odometer = values_sorted[1][1] if values_sorted else 0.0
            last_odometer_timestamp = values_sorted[1][0] if values_sorted else getTime()
            
            now = getTime()
            
            if minutesBetween(last_odometer_timestamp, now) < updated_within_minutes:
                _LOGGER.info(f"Odometer up to date {int(last_odometer)} {last_odometer_timestamp}, no need to wait")
                return
            
            while minutesBetween(now, getTime()) < max_wait_time_minutes and (not TASKS["wait_until_odometer_stable"].cancelling() or not TASKS["wait_until_odometer_stable"].cancelled()):
                to_datetime = getTime()
                from_datetime = to_datetime - datetime.timedelta(hours=24)
                values = get_values(CONFIG['ev_car']['entity_ids']['odometer_entity_id'], from_datetime, to_datetime, float_type=True, convert_to=None, include_timestamps=True, error_state={})
                
                if not values or not isinstance(values, dict) or not values.items():
                    _LOGGER.warning(f"No odometer values found in the last 24 hours")
                    return
                
                values_sorted = sorted(values.items(), reverse=True)
                if values_sorted:
                    current_odometer = values_sorted[1][1]
                    current_odometer_timestamp = values_sorted[1][0]
                    if current_odometer_timestamp > last_odometer_timestamp:
                        _LOGGER.info(f"Odometer stable at {current_odometer} now, no need to wait anymore")
                        break
                task.wait_until(timeout=60)
        except Exception as e:
            _LOGGER.error(f"Error in wait_until_odometer_stable: {e}")
            
    def power_connected_trigger(value):
        task.unique("power_connected_trigger")
        _LOGGER = globals()['_LOGGER'].getChild("power_connected_trigger")
        global TASKS
        
        try:
            if (is_ev_configured() and ready_to_charge()) or (not is_ev_configured() and value in CHARGER_NOT_READY_STATUS):
                if is_ev_configured() and value in EV_PLUGGED_STATES:
                    task_cancel("power_connected_trigger_wait_until_odometer_stable", task_remove=True)
                    
                    TASKS["power_connected_trigger_wait_until_odometer_stable"] = task.create(wait_until_odometer_stable)
                    done, pending = task.wait({TASKS["power_connected_trigger_wait_until_odometer_stable"]})
                    
                TASKS["power_connected_trigger_drive_efficiency"] = task.create(drive_efficiency, str(value))
                done, pending = task.wait({TASKS["power_connected_trigger_drive_efficiency"]})
            TASKS["power_connected_trigger_notify_battery_under_daily_battery_level"] = task.create(notify_battery_under_daily_battery_level)
            done, pending = task.wait({TASKS["power_connected_trigger_notify_battery_under_daily_battery_level"]})
        finally:
            for task_name in ["power_connected_trigger_wait_until_odometer_stable", "power_connected_trigger_drive_efficiency", "power_connected_trigger_notify_battery_under_daily_battery_level"]:
                task_cancel(task_name, task_remove=True)
        
    if is_entity_configured(CONFIG['charger']['entity_ids']['cable_connected_entity_id']):
        @state_trigger(f"{CONFIG['charger']['entity_ids']['cable_connected_entity_id']}")
        def state_trigger_charger_cable_connected(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("state_trigger_charger_cable_connected")
            try:
                TASKS["state_trigger_charger_cable_connected_wake_up_ev"] = task.create(wake_up_ev)
                done, pending = task.wait({TASKS["state_trigger_charger_cable_connected_wake_up_ev"]})
                
                if not is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']) and not is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']):
                    power_connected_trigger(value)
            finally:
                for task_name in list(TASKS.keys()):
                    if task_name.startswith("state_trigger_charger_cable_connected_"):
                        task_cancel(task_name, task_remove=True)
            
    if is_ev_configured():
        @time_trigger(f"cron(0/5 * * * *)")
        def cron_five_every_minute(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("cron_five_every_minute")
            try:
                TASKS["cron_five_every_minute_preheat_ev"] = task.create(preheat_ev)
                done, pending = task.wait({TASKS["cron_five_every_minute_preheat_ev"]})
            finally:
                for task_name in list(TASKS.keys()):
                    if task_name.startswith("cron_five_every_minute_"):
                        task_cancel(task_name, task_remove=True)
        
        if is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']) or is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']):
            if is_entity_configured(CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']):
                @state_trigger(f"{CONFIG['ev_car']['entity_ids']['charge_port_door_entity_id']}")
                def state_trigger_ev_charger_port(trigger_type=None, var_name=None, value=None, old_value=None):
                    _LOGGER = globals()['_LOGGER'].getChild("state_trigger_ev_charger_port")
                    power_connected_trigger(value)
            else:
                @state_trigger(f"{CONFIG['ev_car']['entity_ids']['charge_cable_entity_id']}")
                def state_trigger_ev_charger_cable(trigger_type=None, var_name=None, value=None, old_value=None):
                    _LOGGER = globals()['_LOGGER'].getChild("state_trigger_ev_charger_cable")
                    power_connected_trigger(value)
    else:
        @state_trigger(f"input_number.{__name__}_battery_level")
        def emulated_battery_level_changed(trigger_type=None, var_name=None, value=None, old_value=None):
            _LOGGER = globals()['_LOGGER'].getChild("emulated_battery_level_changed")
            try:
                old_value = float(old_value)
                value = float(value)
            except:
                return
            
            try:
                if old_value == 0.0 and value > 0.0:
                    TASKS["emulated_battery_level_changed_drive_efficiency"] = task.create(drive_efficiency, "on")
                    done, pending = task.wait({TASKS["emulated_battery_level_changed_drive_efficiency"]})
            finally:
                for task_name in list(TASKS.keys()):
                    if task_name.startswith("emulated_battery_level_changed_"):
                        task_cancel(task_name, task_remove=True)
                
    @time_trigger(f"cron(59 * * * *)")
    def cron_hour_end(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("cron_hour_end")
        global TASKS
        try:
            TASKS['cron_hour_end_local_energy_available'] = task.create(local_energy_available, period = 60, without_all_exclusion = True, solar_only = True)
            TASKS['cron_hour_end_power_values'] = task.create(power_values, period = 60)
            done, pending = task.wait({TASKS['cron_hour_end_local_energy_available'], TASKS['cron_hour_end_power_values']})
            
            cron_local_energy_available = TASKS['cron_hour_end_local_energy_available'].result()
            cron_power_values = TASKS['cron_hour_end_power_values'].result()
            
            TASKS['cron_hour_end_solar_available_append_to_db'] = task.create(solar_available_append_to_db, cron_local_energy_available)
            TASKS['cron_hour_end_power_values_to_db'] = task.create(power_values_to_db, cron_power_values)
            TASKS['cron_hour_end_stop_current_charging_session'] = task.create(stop_current_charging_session)
            TASKS['cron_hour_end_kwh_charged_by_solar'] = task.create(kwh_charged_by_solar)
            TASKS['cron_hour_end_solar_charged_percentage'] = task.create(solar_charged_percentage)
            TASKS['cron_hour_end_commands_history_clean_entity_integration'] = task.create(commands_history_clean_entity_integration)
            done, pending = task.wait({TASKS['cron_hour_end_solar_available_append_to_db'], TASKS['cron_hour_end_power_values_to_db'],
                                    TASKS['cron_hour_end_stop_current_charging_session'], TASKS['cron_hour_end_kwh_charged_by_solar'],
                                    TASKS['cron_hour_end_solar_charged_percentage'], TASKS['cron_hour_end_commands_history_clean_entity_integration']})
        finally:
            for task_name in list(TASKS.keys()):
                if task_name.startswith("cron_hour_end_"):
                    task_cancel(task_name, task_remove=True)
        
    @time_trigger(f"cron(0 0 * * *)")
    def cron_new_day(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("cron_new_day")
        global TASKS
        try:
            TASKS['cron_new_day_reset_counter_entity_integration'] = task.create(reset_counter_entity_integration)
            done, pending = task.wait({TASKS['cron_new_day_reset_counter_entity_integration']})
            
            if CONFIG['notification']['update_available']:
                TASKS["cron_new_day_check_master_updates"] = task.create(check_master_updates)
                done, pending = task.wait({TASKS["cron_new_day_check_master_updates"]})
        finally:
            for task_name in list(TASKS.keys()):
                if task_name.startswith("cron_new_day_"):
                    task_cancel(task_name, task_remove=True)
        
    @time_trigger(f"cron(0 1 * * *)")
    def cron_append_kwh_prices(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("cron_append_kwh_prices")
        global TASKS
        try:
            TASKS["cron_append_kwh_prices_append_kwh_prices"] = task.create(append_kwh_prices)
            done, pending = task.wait({TASKS["cron_append_kwh_prices_append_kwh_prices"]})
        finally:
            for task_name in list(TASKS.keys()):
                if task_name.startswith("cron_append_kwh_prices_"):
                    task_cancel(task_name, task_remove=True)
    
    @state_trigger(f"input_boolean.{__name__}_calculate_charging_loss")#TODO Add phase and amp levels measurements
    @state_trigger(f"{CONFIG['charger']['entity_ids']['status_entity_id']}")
    @state_trigger(f"{CONFIG['charger']['entity_ids']['kwh_meter_entity_id']}")
    def calculate_charging_loss(trigger_type=None, var_name=None, value=None, old_value=None):
        _LOGGER = globals()['_LOGGER'].getChild("calculate_charging_loss")
        
        global CONFIG, CHARGING_LOSS_CAR_BEGIN_KWH, CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL, CHARGING_LOSS_CHARGER_BEGIN_KWH, CHARGING_LOSS_CHARGING_COMPLETED

        if not is_entity_available(CONFIG['charger']['entity_ids']['kwh_meter_entity_id']) or not is_entity_available(CONFIG['charger']['entity_ids']['status_entity_id']):
            if is_calculating_charging_loss():
                _LOGGER.error(f"Entities not available, stopping charging loss calculation")
                my_notify(message = f"Entities ikke tilgængelig, stopper ladetab beregningen", title = f"{TITLE} Fejl", notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True, persistent_notification_id=f"{__name__}_charging_loss_not_available")
                set_state(f"input_boolean.{__name__}_calculate_charging_loss", "off")
            return
        
        try:
            battery_size = CONFIG['ev_car']['battery_size']
            charger_current_kwh = float(get_state(CONFIG['charger']['entity_ids']['kwh_meter_entity_id'], float_type=True, try_history=True, error_state=None))
            completed_battery_level = float(get_state(CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'], float_type=True, error_state=100.0)) if is_ev_configured() and CONFIG['ev_car']['entity_ids']['charging_limit_entity_id'] else get_completed_battery_level()
            completed_battery_size = battery_size * (completed_battery_level / 100.0)
            
            if var_name == f"input_boolean.{__name__}_calculate_charging_loss":
                if value != "on":
                    CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL = 0.0
                    CHARGING_LOSS_CAR_BEGIN_KWH = 0.0
                    CHARGING_LOSS_CHARGER_BEGIN_KWH = 0.0
                    CHARGING_LOSS_CHARGING_COMPLETED = False
                    return
                    
                if not is_ev_configured() and battery_level() == 0.0:
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
                if value in tuple(chain(CHARGER_READY_STATUS, CHARGER_COMPLETED_STATUS)) and old_value in CHARGER_CHARGING_STATUS:
                    CHARGING_LOSS_CHARGING_COMPLETED = True
            elif var_name == f"{CONFIG['charger']['entity_ids']['kwh_meter_entity_id']}":
                    if CHARGING_LOSS_CHARGING_COMPLETED:
                        added_kwh = charger_current_kwh - CHARGING_LOSS_CHARGER_BEGIN_KWH
                        charging_loss = round(((completed_battery_size - CHARGING_LOSS_CAR_BEGIN_KWH) / added_kwh) - 1, 4)
                        
                        if charging_loss >= 0.0:
                            raise Exception(f"Charging loss was not negative {charging_loss * 100.0}%, set charging limit in car and let charging complete")
                        
                        CONFIG['charger']['charging_loss'] = charging_loss
                        
                        set_state(f"input_boolean.{__name__}_calculate_charging_loss", "off")
                        my_notify(message = f"Ladetab beregnet til {round(charging_loss * 100)}%", title = f"{TITLE} Ladetab beregning", notify_list = CONFIG['notify_list'], admin_only = False, always = True)
                        my_persistent_notification(f"Ladetab beregnet til {round(charging_loss * 100)}%", title = f"{TITLE} Ladetab beregning", persistent_notification_id=f"{__name__}_charging_loss_calculated")
            else:
                raise Exception(f"Unknown error: trigger_type={trigger_type}, var_name={var_name}, value={value}, old_value={old_value}")
        except Exception as e:
            CHARGING_LOSS_CAR_BEGIN_BATTERY_LEVEL = 0.0
            CHARGING_LOSS_CAR_BEGIN_KWH = 0.0
            CHARGING_LOSS_CHARGER_BEGIN_KWH = 0.0
            CHARGING_LOSS_CHARGING_COMPLETED = False
            _LOGGER.error(f"Failed to calculate charging loss: {e}")
            my_notify(message = f"Fejlede i beregningen af ladetab:\n{e}", title = f"{TITLE} Fejl", notify_list = CONFIG['notify_list'], admin_only = False, always = True, persistent_notification = True)
            my_persistent_notification(f"Fejlede i beregningen af ladetab:\n{e}", title = f"{TITLE} Fejl", persistent_notification_id=f"{__name__}_charging_loss_error")
            
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
        global CONFIG, TASKS
        
        TASKS['shutdown_stop_current_charging_session'] = task.create(stop_current_charging_session)
        TASKS['shutdown_reset_counter_entity_integration'] = task.create(reset_counter_entity_integration)
        
        if CONFIG_LAST_MODIFIED == get_file_modification_time(f"{__name__}_config.yaml"):
            set_charging_rule(f"📟Lukker scriptet ned\nGemmer konfigurations filen")
            try:
                #CONFIG = load_yaml(f"{__name__}_config")
                CONFIG['ev_car']['typical_daily_distance_non_working_day'] = get_entity_daily_distance()
                CONFIG['ev_car']["workday_distance_needed_monday"] = get_entity_daily_distance("monday")
                CONFIG['ev_car']["workday_distance_needed_tuesday"] = get_entity_daily_distance("tuesday")
                CONFIG['ev_car']["workday_distance_needed_wednesday"] = get_entity_daily_distance("wednesday")
                CONFIG['ev_car']["workday_distance_needed_thursday"] = get_entity_daily_distance("thursday")
                CONFIG['ev_car']["workday_distance_needed_friday"] = get_entity_daily_distance("friday")
                CONFIG['ev_car']["workday_distance_needed_saturday"] = get_entity_daily_distance("saturday")
                CONFIG['ev_car']["workday_distance_needed_sunday"] = get_entity_daily_distance("sunday")
                                
                CONFIG['ev_car']['min_daily_battery_level'] = get_min_daily_battery_level()
                CONFIG['ev_car']['min_trip_battery_level'] = get_min_trip_battery_level()
                CONFIG['ev_car']['min_charge_limit_battery_level'] = get_min_charge_limit_battery_level()
                CONFIG['ev_car']['max_recommended_charge_limit_battery_level'] = get_max_recommended_charge_limit_battery_level()
                CONFIG['ev_car']['very_cheap_grid_charging_max_battery_level'] = get_very_cheap_grid_charging_max_battery_level()
                CONFIG['ev_car']['ultra_cheap_grid_charging_max_battery_level'] = get_ultra_cheap_grid_charging_max_battery_level()
                CONFIG['solar']['ev_charge_after_powerwall_battery_level'] = get_ev_charge_after_powerwall_battery_level()
                
                if is_solar_configured():
                    CONFIG['solar']['production_price'] = float(get_state(f"input_number.{__name__}_solar_sell_fixed_price", float_type=True, error_state=CONFIG['solar']['production_price']))
                
                TASKS['shutdown_save_changes'] = task.create(save_changes, f"{__name__}_config", CONFIG)
                done, pending = task.wait({TASKS['shutdown_save_changes']})
            except Exception as e:
                _LOGGER.error(f"Cant save config from Home assistant to config: {e}")
                my_persistent_notification(f"Kan ikke gemme konfigurationen fra Home Assistant til config: {e}", title = f"{TITLE} Fejl", persistent_notification_id = f"{__name__}_shutdown_error")
        else:
            set_charging_rule(f"📟Lukker scriptet ned\nGemmer ikke konfigurations filen, da den er manuel redigeret")
            _LOGGER.info(f"Config file has been modified, not saving entity states from Home Assistant to config")
            
        done, pending = task.wait({TASKS['shutdown_stop_current_charging_session'], TASKS['shutdown_reset_counter_entity_integration']})
        
        task_shutdown()
            
@state_trigger(f"input_button.{__name__}_restart_script")
def restart(trigger_type=None, var_name=None, value=None, old_value=None):
    _LOGGER = globals()['_LOGGER'].getChild("restart")
    restart_script()
