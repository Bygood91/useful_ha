from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

DOMAIN = "useful_ha"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configuration de l'intégration."""
    # Enregistre le listener pour les changements d'options
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    # Charge la plateforme sensor
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Recharge l'intégration quand les options changent."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Déchargement propre."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])