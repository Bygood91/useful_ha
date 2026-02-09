import asyncio
import logging
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import template
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EVENT_HOMEASSISTANT_STARTED
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Configuration des deux entités UsefulHa."""
    unavailable_sensor = UsefulHaUnavailableSensor(config_entry)
    update_sensor = UsefulHaUpdateSensor(config_entry)
    
    async_add_entities([unavailable_sensor, update_sensor], True)

class UsefulHaBaseSensor(SensorEntity):
    """Classe de base avec Device Info."""
    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._state = "Initialisation"
        self._attributes = {}
        self._is_ready = False

    @property
    def device_info(self) -> DeviceInfo:
        """Définit l'appareil regroupant les entités."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="Useful for HA",
            manufacturer="UsefulHa",
            model="useful_ha",
            sw_version="1.0.0",
        )

    async def async_added_to_hass(self):
        async def enable_monitoring(_=None):
            await asyncio.sleep(30)
            self._is_ready = True
            self.async_schedule_update_ha_state(True)

        if self.hass.is_running:
            self.hass.async_create_task(enable_monitoring())
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, enable_monitoring)

    @property
    def state(self): return self._state

    @property
    def extra_state_attributes(self): return self._attributes


class UsefulHaUnavailableSensor(UsefulHaBaseSensor):
    """Capteur pour les entités indisponibles."""
    _attr_name = "Entités Indisponibles"
    _attr_unit_of_measurement = "entités"
    _attr_icon = "mdi:alert-circle-outline"

    @property
    def unique_id(self):
        return f"{self._config_entry.entry_id}_unavailable_count"

    @property
    def icon(self):
        """Changement d'icône dynamique selon l'état."""
        try:
            # Si l'état est un nombre supérieur à 0
            if int(self._state) > 0:
                return "mdi:alert-circle"
        except (ValueError, TypeError):
            pass
        return "mdi:alert-circle-outline"

    async def async_update(self):
        if not self._is_ready: return

        opts = self._config_entry.options
        data = self._config_entry.data
        
        # Filtres
        use_defaults = opts.get("default_filters", data.get("default_filters", True))
        raw_exclusions = opts.get("excluded_entities", data.get("excluded_entities", ""))
        excluded_items = [x.strip().lower() for x in raw_exclusions.split(",") if x.strip()]
        
        if use_defaults:
            excluded_items.extend(["sensor.backup", "event", "conversation", "tts", "update", "person"])

        unavailable_ids = []
        for e in self.hass.states.async_all():
            eid = e.entity_id.lower()
            if e.state not in [STATE_UNAVAILABLE, STATE_UNKNOWN] or eid == self.entity_id:
                continue
            if eid.startswith(("persistent_notification.", "button.", "scene.")):
                continue
            if any(eid == item or eid.split(".")[0] == item or eid.startswith(item) for item in excluded_items):
                continue
            unavailable_ids.append(eid)

        self._state = len(unavailable_ids)
        self._attributes = {"entities": unavailable_ids}


class UsefulHaUpdateSensor(UsefulHaBaseSensor):
    """Capteur pour les mises à jour avec système de notification."""
    _attr_name = "Mises à jour disponibles"
    _attr_unit_of_measurement = "updates"

    def __init__(self, config_entry):
        super().__init__(config_entry)
        self._last_updates = set()

    @property
    def unique_id(self):
        return f"{self._config_entry.entry_id}_update_count"

    @property
    def icon(self):
        """Changement d'icône dynamique selon l'état."""
        try:
            # Si l'état est un nombre supérieur à 0
            if int(self._state) > 0:
                return "mdi:package-up"
        except (ValueError, TypeError):
            pass
        return "mdi:package-variant"

    async def async_update(self):
        if not self._is_ready: return

        opts = self._config_entry.options
        data = self._config_entry.data
        
        current_updates = [
            e.entity_id for e in self.hass.states.async_all() 
            if e.entity_id.split(".")[0] == "update" and e.state == "on"
        ]

        # --- LOGIQUE NOTIFICATION ---
        new_updates = [uid for uid in current_updates if uid not in self._last_updates]
        
        if new_updates:
            send_persistent = opts.get("persistent_notifications", data.get("persistent_notifications", True))
            notify_services = opts.get("notify_service", data.get("notify_service", []))

            tpl_str = """Il y a {{ states.update | selectattr('state', 'eq', 'on') | list | count }} mise(s) à jour en attente :
{% for item in states.update | selectattr('state', 'eq', 'on') -%}
  • {{ item.attributes.friendly_name }} (v{{ item.attributes.latest_version }})
{% endfor %}"""
            
            rendered_msg = template.Template(tpl_str, self.hass).async_render()

            if send_persistent:
                # On ajoute le lien en bas du message
                persistent_msg = f"{rendered_msg}\n\n[Voir les mises à jour](/config/updates)"
                
                await self.hass.services.async_call("persistent_notification", "create", {
                    "title": "🛠️ Mises à jour disponibles",
                    "message": persistent_msg
                })

            if notify_services:
                notif_data = {
                    "group": "updates-ha",
                    "clickAction": "/config/updates",
                    "notification_icon": "mdi:home-assistant"
                }

                for service_name in notify_services:
                    try:
                        await self.hass.services.async_call("notify", service_name, {
                            "title": "🛠️ UsefulHa : Updates",
                            "message": rendered_msg,
                            "data": notif_data
                        })
                    except Exception as e:
                        _LOGGER.error("Erreur notify.%s : %s", service_name, e)

        self._last_updates = set(current_updates)
        self._state = len(current_updates)
        self._attributes = {"updates_list": current_updates}