"""Config flow for West Wood Club."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WestWoodApiError, WestWoodAuthError, WestWoodClient
from .const import CONF_CLUBS, CONF_TOKEN, DOMAIN


class WestWoodConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI configuration flow."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._clubs: dict[int, str] = {}

    async def _validate_token(self, token: str) -> dict[int, str]:
        """Return the club list if the token works, else raise."""
        client = WestWoodClient(async_get_clientsession(self.hass), token)
        return await client.async_get_clubs()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step: collect and validate the bearer token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            try:
                self._clubs = await self._validate_token(token)
            except WestWoodAuthError:
                errors['base'] = 'invalid_auth'
            except WestWoodApiError:
                errors['base'] = 'cannot_connect'
            else:
                self._token = token
                return await self.async_step_clubs()

        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    async def async_step_clubs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Second step: pick which clubs to create sensors for."""
        if user_input is not None:
            selected = {
                club_id: name
                for club_id, name in self._clubs.items()
                if str(club_id) in user_input[CONF_CLUBS]
            }
            return self.async_create_entry(
                title='West Wood Club',
                data={
                    CONF_TOKEN: self._token,
                    # Keys are stringified for JSON storage / multi_select.
                    CONF_CLUBS: {str(cid): name for cid, name in selected.items()},
                },
            )

        return self.async_show_form(
            step_id='clubs',
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLUBS): cv.multi_select(
                        {str(cid): name for cid, name in self._clubs.items()}
                    )
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauth when the stored token stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user paste a fresh token, keeping the existing clubs."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            try:
                await self._validate_token(token)
            except WestWoodAuthError:
                errors['base'] = 'invalid_auth'
            except WestWoodApiError:
                errors['base'] = 'cannot_connect'
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id='reauth_confirm',
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )
