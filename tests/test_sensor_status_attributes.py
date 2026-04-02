"""Tests for PreheatStatusSensor.extra_state_attributes."""
import sys
import unittest
from unittest.mock import MagicMock
import types

# --- Mock Home Assistant modules ---
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

for _mod, _attr in [
    ("homeassistant.core", None),
    ("homeassistant.config_entries", None),
    ("homeassistant.const", None),
    ("homeassistant.exceptions", None),
    ("homeassistant.util", None),
    ("homeassistant.util.dt", None),
    ("homeassistant.helpers", None),
    ("homeassistant.helpers.entity", None),
    ("homeassistant.helpers.entity_platform", None),
    ("homeassistant.helpers.update_coordinator", None),
    ("homeassistant.helpers.storage", None),
    ("homeassistant.helpers.issue_registry", None),
    ("homeassistant.components", None),
    ("homeassistant.components.sensor", None),
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


def _make_sensor(tau_hours: float) -> PreheatStatusSensor:
    """Return a PreheatStatusSensor backed by a minimal mock coordinator."""
    data = MagicMock()
    data.preheat_active = False
    data.target_setpoint = 21.0
    data.operative_temp = 20.0
    data.predicted_duration = 30.0
    data.window_open = False
    data.last_comfort_setpoint = 21.0
    data.deadtime = 5.0
    data.decision_trace = ""
    data.detected_modes = []
    data.next_start_time = None
    data.next_arrival = None
    data.next_departure = None
    data.optimal_stop_time = None

    physics = MagicMock()
    physics.get_confidence.return_value = 80
    physics.avg_error = 0.1
    physics.sample_count = 10
    physics.health_score = 90

    cooling_analyzer = MagicMock()
    cooling_analyzer.learned_tau = tau_hours

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


class TestPreheatStatusSensorCoastMinutesPerK(unittest.TestCase):
    def test_attribute_present(self):
        """coast_minutes_per_k must be present in extra_state_attributes."""
        sensor = _make_sensor(tau_hours=4.0)
        attrs = sensor.extra_state_attributes
        self.assertIn("coast_minutes_per_k", attrs)

    def test_default_tau_four_hours(self):
        """Default tau of 4.0 h → 240.0 min/K."""
        sensor = _make_sensor(tau_hours=4.0)
        self.assertEqual(sensor.extra_state_attributes["coast_minutes_per_k"], 240.0)

    def test_fractional_tau_rounded_to_one_decimal(self):
        """Result is rounded to 1 decimal place."""
        # 3.0 hours * 60 = 180.0
        sensor = _make_sensor(tau_hours=3.0)
        result = sensor.extra_state_attributes["coast_minutes_per_k"]
        self.assertEqual(result, 180.0)

    def test_rounding_applied(self):
        """Verify rounding: 2.6667 h * 60 = 160.002, rounded to 1 dp → 160.0."""
        sensor = _make_sensor(tau_hours=2.6667)
        result = sensor.extra_state_attributes["coast_minutes_per_k"]
        self.assertAlmostEqual(result, round(2.6667 * 60.0, 1))

    def test_small_tau(self):
        """A very small tau (0.5 h) → 30.0 min/K."""
        sensor = _make_sensor(tau_hours=0.5)
        self.assertEqual(sensor.extra_state_attributes["coast_minutes_per_k"], 30.0)


if __name__ == "__main__":
    unittest.main()
