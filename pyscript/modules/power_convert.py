__version__ = "1.0.0"
from hass_manager import get_state, get_attr

from logging import getLogger
BASENAME = f"pyscript.modules.{__name__}"
_LOGGER = getLogger(BASENAME)

def power_convert(power = 0.0, entity_id = "", output = "W"):
    """
    Converts the power value of a specified entity to a different unit of measurement.
    Logs a warning and returns the original power value if conversion fails.

    Parameters:
    - power (float): The default power value to return if conversion fails.
    - entity_id (str): The entity ID whose power value is to be converted.
    - output (str): The unit to convert the power value to.

    Returns:
    - float: The converted power value or the original value if conversion fails.
    """
    _LOGGER = globals()['_LOGGER'].getChild("power_convert")
    try:
        power_type = get_attr(entity_id, "unit_of_measurement")
        return convert_units(power, power_type, output)
    except Exception as e:
        _LOGGER.error(f"power_convert(): Cant convert {entity_id} {power} to {output}: {e}")
        
    return power

def convert_units(value, from_unit, to_unit):
    """Converts a value from one unit of measurement to another.

    Args:
        value (float): The value to convert.
        from_unit (str): The unit of measurement the value is currently in.
        to_unit (str): The unit of measurement to convert the value to.

    Returns:
        float: The converted value.
    """
    _LOGGER = globals()['_LOGGER'].getChild("convert_units")
    from_unit = from_unit.replace("h", "")
    to_unit = to_unit.replace("h", "")

    # Define conversion factors for different units of measurement.
    conversion_factors = {
        "mm": {"cm": 0.1, "m": 0.001, "km": 0.000001},
        "cm": {"mm": 10, "m": 0.01, "km": 0.0001},
        "m": {"mm": 1000, "cm": 100, "km": 0.001},
        "km": {"mm": 1000000, "cm": 100000, "m": 1000},
        "kg": {"g": 1000},
        "g": {"kg": 0.001},
        "L": {"ml": 1000},
        "ml": {"L": 0.001},
        "mW": {"mW": 1, "W": 0.001, "kW": 0.000001, "MW": 0.000000001, "GW": 0.000000000001},
        "W": {"mW": 1000, "W": 1, "kW": 0.001, "MW": 0.000001, "GW": 0.000000001},
        "kW": {"mW": 1000000,"W": 1000, "kW": 1, "MW": 0.001, "GW": 0.000001},
        "MW": {"mW": 1000000000, "W": 1000000, "kW": 1000, "MW": 1, "GW": 0.001},
        "GW": {"mW": 1000000000000, "W": 1000000000, "kW": 1000000, "GW": 1}
    }

    # Check if the units are valid.
    if from_unit not in conversion_factors or to_unit not in conversion_factors:
        raise ValueError(f"Invalid units: {from_unit} or {to_unit}")

    # Get the conversion factor.
    conversion_factor = conversion_factors[from_unit][to_unit]

    # Convert the value.
    converted_value = value * conversion_factor

    _LOGGER.debug(f"{value}{from_unit}->{to_unit}: {value} * {conversion_factor} = {converted_value}")
    return converted_value