"""Tests for optional AI and weather integrations without network calls."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from jazira_agri.weather.forecast import WeatherForecast


class WeatherForecastTests(unittest.TestCase):
    def test_rejects_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            WeatherForecast(91, 40)

    @patch("jazira_agri.weather.forecast.requests.get")
    def test_requests_seven_day_daily_data(self, get):
        response = Mock()
        response.json.return_value = {"daily": {"time": ["2026-01-01"]}}
        get.return_value = response
        result = WeatherForecast(36.5, 39.0).get_7day()
        self.assertEqual(result, response.json.return_value)
        self.assertEqual(get.call_args.kwargs["params"]["forecast_days"], 7)
        self.assertEqual(get.call_args.kwargs["timeout"], 15.0)

    @patch("jazira_agri.weather.forecast.requests.get", side_effect=requests.Timeout)
    def test_network_failure_returns_none(self, _get):
        self.assertIsNone(WeatherForecast(36.5, 39.0).get_7day())


if __name__ == "__main__":
    unittest.main()
