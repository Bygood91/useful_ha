from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from .const import DOMAIN

DEFAULT_LIST_STR = "sensor.backup, event, conversation, tts, update, person"

class UsefulHaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        
        if user_input is None:
            return self.async_create_entry(
                title="Useful for HA", 
                data={
                    "default_filters": True,
                    "persistent_notifications": True,
                    "excluded_entities": "",
                    "notify_service": []
                }
            )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UsefulHaOptionsFlow(config_entry)

class UsefulHaOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        # Conservé comme demandé
        pass

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        data = self.config_entry.data

        # --- RÉCUPÉRATION DES SERVICES ---
        all_services = self.hass.services.async_services()
        notify_options = []
        if "notify" in all_services:
            notify_options = [
                {"value": srv, "label": srv.replace("_", " ").title()} 
                for srv in sorted(all_services["notify"].keys())
                if srv not in ["persistent_notification", "notify", "send_message"]
            ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                # --- SECTION FILTRES ---
                vol.Optional("default_filters", default=opts.get("default_filters", data.get("default_filters", True))): bool,
                vol.Optional("excluded_entities", description={"suggested_value": opts.get("excluded_entities", data.get("excluded_entities", ""))}): str,
                
                # --- SECTION UPDATES (Le séparateur sera injecté ici via le JSON) ---
                vol.Optional("persistent_notifications", default=opts.get("persistent_notifications", data.get("persistent_notifications", True))): bool,
                vol.Optional("notify_service", default=opts.get("notify_service", data.get("notify_service", []))): SelectSelector(
                    SelectSelectorConfig(
                        options=notify_options,
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN
                    )
                ),
            }),
            description_placeholders={"default_list": DEFAULT_LIST_STR}
        )