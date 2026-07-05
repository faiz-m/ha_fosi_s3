"""Tests for the Fosi S3 config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.fosi_s3.pyfosi import FosiS3ConnectionError

from custom_components.fosi_s3.const import DOMAIN
from .conftest import make_device_info


async def test_user_flow_shows_form(hass: HomeAssistant) -> None:
    """First step should show the host input form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_fosi_client
) -> None:
    """Successful connection should create a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"host": "10.0.0.100"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Room"
    assert result["data"] == {"host": "10.0.0.100"}
    assert mock_fosi_client.connect.await_count >= 1
    mock_fosi_client.disconnect.assert_awaited_once()


async def test_user_flow_connection_error(
    hass: HomeAssistant, mock_fosi_client
) -> None:
    """Connection failure should show error on the form."""
    mock_fosi_client.connect.side_effect = FosiS3ConnectionError("Connection refused")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"host": "10.0.0.100"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    mock_fosi_client.disconnect.assert_awaited_once()


async def test_user_flow_unexpected_error(
    hass: HomeAssistant, mock_fosi_client
) -> None:
    """Unexpected exception should show 'unknown' error."""
    mock_fosi_client.connect.side_effect = RuntimeError("boom")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"host": "10.0.0.100"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_host_as_unique_id_fallback(
    hass: HomeAssistant, mock_fosi_client
) -> None:
    """If no system_member_id, use host as unique_id."""
    mock_fosi_client.device_info = make_device_info(system_member_id="")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"host": "10.0.0.100"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    # The unique_id is set on the entry. We verify it by attempting to add again.
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == "10.0.0.100"


async def test_user_flow_product_name_as_title_fallback(
    hass: HomeAssistant, mock_fosi_client
) -> None:
    """If no device_name, title should fall back to product_name."""
    mock_fosi_client.device_info = make_device_info(device_name="")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"host": "10.0.0.100"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Fosi S3"
