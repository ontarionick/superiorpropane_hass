import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import voluptuous as vol

from homeassistant import core
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    VOLUME_LITERS,
)
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

import mechanize
from bs4 import BeautifulSoup
from http import cookiejar
import time

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=6)

CONF_TANKS = "tanks"
CONF_TANK_ID = "tank_id"

TANK_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TANK_ID): cv.positive_int,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_TANKS): vol.All(cv.ensure_list, [TANK_SCHEMA]),
    }
)

async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    username = config[CONF_EMAIL]
    password = config[CONF_PASSWORD]
    sensors = [SuperiorPropaneTankSensor(email, password, tank_id) for tank_id in config[CONF_TANKS]]

    async_add_entities(sensors, update_before_add=True)


class SuperiorPropaneTankSensor(Entity):

    def __init__(self, email, password, tank_id):
        """Initialize the sensor."""
        self.email = email
        self.password = password
        self.tank_id = tank_id

        self._name = f"Superior Propane Tank #{self.tank_id}"
        self._state = None
        self._attributes = None
        self._available = True

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return self._attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return VOLUME_LITERS

    async def async_update(self):
        """Fetch new state data for the sensor."""
        _LOGGER.info(f"Updating Superior Propane Tank {self.tank_id}")

        try:
            cj = cookiejar.CookieJar()
            br = mechanize.Browser()
            br.set_cookiejar(cj)
            br.open("https://mysuperior.superiorpropane.com/account/individualLogin")

            br.select_form(action="https://mysuperior.superiorpropane.com/account/loginFirst")
            br.form["login_email"] = self.email
            br.form["login_password"] = self.password
            br.submit()

            br.open("https://mysuperior.superiorpropane.com/dashboard/sync")
            time.sleep(10)

            br.open(f"https://mysuperior.superiorpropane.com/tanks/details/{self.tank_id}")

            soup = BeautifulSoup(br.response().read(), features="html5lib")
            tank_percentage = soup.find("span", id="sliderOutput0").text

            _LOGGER.info(f"Tank Percentage: {tank_percentage}")

            self._state = 100
            self._attributes = {"test": "test"}
            self._available = True
        except Exception as e:
            self._available = False
            _LOGGER.exception(f"Failed to retrieve data from Superior Propane: {e}")