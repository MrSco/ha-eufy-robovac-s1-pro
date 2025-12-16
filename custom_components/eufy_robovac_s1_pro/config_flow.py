import logging
import json

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback

from .const import DOMAIN, CONF_ROOM_MAPPINGS
from .eufy_local_id_grabber.clients import EufyHomeSession

logger = logging.getLogger(__name__)

EUFY_LOGIN_SCHEMA = vol.Schema({vol.Required("username"): str, vol.Required("password"): str})


class EufyVacuumConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] | None = None) -> data_entry_flow.FlowResult:
        errors = {}

        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]

            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            client = EufyHomeSession(username, password)

            try:
                await self.hass.async_add_executor_job(client.get_user_info)
            except Exception:
                logger.exception("Error when logging in with %s", username)

                # TODO: proper exception handling
                errors["username"] = errors["password"] = "Username or password is incorrect"
            else:
                return self.async_create_entry(
                    title=username,
                    data={CONF_EMAIL: username, CONF_PASSWORD: password},
                )

        return self.async_show_form(step_id="user", data_schema=EUFY_LOGIN_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return EufyVacuumOptionsFlow(config_entry)


class EufyVacuumOptionsFlow(OptionsFlow):
    """Handle options flow for room mappings."""

    async def async_step_init(self, user_input: dict | None = None) -> data_entry_flow.FlowResult:
        """Manage the options."""
        return await self.async_step_room_mappings()

    async def async_step_room_mappings(self, user_input: dict | None = None) -> data_entry_flow.FlowResult:
        """Manage room mappings."""
        if user_input is not None:
            # Parse the JSON input
            try:
                room_mappings = json.loads(user_input.get("room_mappings_json", "{}"))
                return self.async_create_entry(
                    title="",
                    data={CONF_ROOM_MAPPINGS: room_mappings}
                )
            except json.JSONDecodeError:
                return self.async_show_form(
                    step_id="room_mappings",
                    data_schema=self._get_room_mappings_schema(),
                    errors={"room_mappings_json": "Invalid JSON format"}
                )

        return self.async_show_form(
            step_id="room_mappings",
            data_schema=self._get_room_mappings_schema(),
            description_placeholders={
                "example": json.dumps({
                    "workshop": "MAomCgoKBggCGgIILRgBEgwIARICCAK6AQMQy34aBggBEAMoLSABKAESAggBGAQgAw==",
                    "closet": "NworCgoKBggCGgIILRgBEhEIARICCAK6AQgI0AUQy34YBBoGCAEQAygtIAEoARIECAEQAhgDIAM="
                }, indent=2)
            }
        )

    def _get_room_mappings_schema(self) -> vol.Schema:
        """Get the schema for room mappings."""
        current_mappings = self.config_entry.options.get(CONF_ROOM_MAPPINGS, {})
        current_json = json.dumps(current_mappings, indent=2) if current_mappings else "{}"

        return vol.Schema({
            vol.Optional("room_mappings_json", default=current_json): str,
        })
