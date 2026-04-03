"""Tests for the price / inhibit policy logic in PreheatStatusSensor and coordinator."""
import sys
import unittest
from unittest.mock import MagicMock
import types

# --- Minimal Home Assistant module mocks (mirror test_sensor_status_attributes.py) ---
ha = types.ModuleType("homeassistant")
ha.__path__ = []
sys.modules.setdefault("homeassistant", ha)

class _MockEntity:
    _attr_has_entity_name = True
    should_poll = False
    def __init__(self):
        self.hass = None
        self.entity_id = "test.entity"

class _MockSensorEntity(_MockEntity):
    pass

class _MockCoordinatorEntity(_MockEntity):
    def __init__(self, coordinator):
        super().__init__()
        self.coordinator = coordinator
    def __class_getitem__(cls, item):
        return cls

for _mod in [
    "homeassistant.core",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.exceptions",
    "homeassistant.util",
    "homeassistant.util.dt",
    "homeassistant.helpers",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.issue_registry",
    "homeassistant.components",
    "homeassistant.components.sensor",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_duc = sys.modules["homeassistant.helpers.update_coordinator"]
_duc.CoordinatorEntity = _MockCoordinatorEntity

_sensor_mod = sys.modules["homeassistant.components.sensor"]
_sensor_mod.SensorEntity = _MockSensorEntity
_sensor_mod.SensorDeviceClass = MagicMock()
_sensor_mod.SensorStateClass = MagicMock()

from custom_components.preheat.sensor import PreheatStatusSensor
from custom_components.preheat.const import INHIBIT_BLOCK_PREHEAT, INHIBIT_FORCE_ECO


def _make_sensor(inhibit_active: bool = False, inhibit_reason: str | None = None) -> PreheatStatusSensor:
    """Return a PreheatStatusSensor backed by a minimal mock coordinator."""
    data = MagicMock()
    data.preheat_active = False
    data.target_setpoint = 21.0
    data.operative_temp = 20.0
    data.predicted_duration = 30.0
    data.window_open = False
    data.last_comfort_setpoint = 21.0
    data.deadtime = 5.0
    data.detected_modes = []
    data.next_start_time = None
    data.next_arrival = None
    data.next_departure = None
    data.optimal_stop_time = None
    data.decision_trace = {
        "inhibit_active": inhibit_active,
        "inhibit_reason": inhibit_reason,
    }

    physics = MagicMock()
    physics.get_confidence.return_value = 80
    physics.avg_error = 0.1
    physics.sample_count = 10
    physics.health_score = 90

    cooling_analyzer = MagicMock()
    cooling_analyzer.learned_tau = 4.0

    coordinator = MagicMock()
    coordinator.data = data
    coordinator.physics = physics
    coordinator.cooling_analyzer = cooling_analyzer

    entry = MagicMock()
    entry.entry_id = "test_entry"

    sensor = PreheatStatusSensor.__new__(PreheatStatusSensor)
    sensor.coordinator = coordinator
    sensor._entry = entry
    return sensor


class TestInhibitPolicyAttributes(unittest.TestCase):
    """Tests that inhibit_active and inhibit_reason are surfaced in sensor attributes."""

    def test_inhibit_active_false_by_default(self):
        """When no inhibit is set, inhibit_active must be False."""
        sensor = _make_sensor(inhibit_active=False, inhibit_reason=None)
        attrs = sensor.extra_state_attributes
        self.assertIn("inhibit_active", attrs)
        self.assertFalse(attrs["inhibit_active"])

    def test_inhibit_reason_none_by_default(self):
        """When no inhibit is set, inhibit_reason must be None."""
        sensor = _make_sensor(inhibit_active=False, inhibit_reason=None)
        attrs = sensor.extra_state_attributes
        self.assertIn("inhibit_reason", attrs)
        self.assertIsNone(attrs["inhibit_reason"])

    def test_block_preheat_policy_reflected(self):
        """When block_preheat inhibit is active, attributes must reflect it."""
        sensor = _make_sensor(inhibit_active=True, inhibit_reason=INHIBIT_BLOCK_PREHEAT)
        attrs = sensor.extra_state_attributes
        self.assertTrue(attrs["inhibit_active"])
        self.assertEqual(attrs["inhibit_reason"], INHIBIT_BLOCK_PREHEAT)

    def test_force_eco_policy_reflected(self):
        """When force_eco_signal inhibit is active, attributes must reflect it."""
        sensor = _make_sensor(inhibit_active=True, inhibit_reason=INHIBIT_FORCE_ECO)
        attrs = sensor.extra_state_attributes
        self.assertTrue(attrs["inhibit_active"])
        self.assertEqual(attrs["inhibit_reason"], INHIBIT_FORCE_ECO)

    def test_decision_trace_none_defaults_to_not_inhibited(self):
        """When decision_trace is None (e.g. startup), inhibit attributes must be safe defaults."""
        sensor = _make_sensor()
        sensor.coordinator.data.decision_trace = None
        attrs = sensor.extra_state_attributes
        self.assertFalse(attrs["inhibit_active"])
        self.assertIsNone(attrs["inhibit_reason"])


class TestInhibitConstants(unittest.TestCase):
    """Tests that the inhibit mode constants are defined correctly."""

    def test_block_preheat_constant(self):
        self.assertEqual(INHIBIT_BLOCK_PREHEAT, "block_preheat")

    def test_force_eco_constant(self):
        self.assertEqual(INHIBIT_FORCE_ECO, "force_eco_signal")

    def test_none_constant(self):
        from custom_components.preheat.const import INHIBIT_NONE
        self.assertEqual(INHIBIT_NONE, "none")


class TestCheapPreheatLeadConfig(unittest.TestCase):
    """Tests that inhibit_preheat_offset_min constant and default are sane."""

    def test_default_is_zero(self):
        from custom_components.preheat.const import DEFAULT_INHIBIT_PREHEAT_OFFSET_MIN
        self.assertEqual(DEFAULT_INHIBIT_PREHEAT_OFFSET_MIN, 0)

    def test_conf_key(self):
        from custom_components.preheat.const import CONF_INHIBIT_PREHEAT_OFFSET_MIN
        self.assertEqual(CONF_INHIBIT_PREHEAT_OFFSET_MIN, "inhibit_preheat_offset_min")

    def test_inhibit_entity_conf_key(self):
        from custom_components.preheat.const import CONF_INHIBIT_ENTITY
        self.assertEqual(CONF_INHIBIT_ENTITY, "inhibit_entity_id")

    def test_inhibit_mode_conf_key(self):
        from custom_components.preheat.const import CONF_INHIBIT_MODE
        self.assertEqual(CONF_INHIBIT_MODE, "inhibit_mode")


if __name__ == "__main__":
    unittest.main()
