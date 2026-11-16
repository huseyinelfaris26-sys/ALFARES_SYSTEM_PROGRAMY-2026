"""جلب وتحليل بيانات الطقس والتبخر النتح"""
from .forecast import WeatherForecast
from .evapotranspiration import Evapotranspiration

__all__ = ["WeatherForecast", "Evapotranspiration"]
