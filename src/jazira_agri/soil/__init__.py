"""تحليل خصائص التربة وتوصيات الأسمدة"""
from .soil_analysis import SoilAnalysis
from .salinity import SalinityChecker
from .fertilizer import FertilizerAdvisor

__all__ = ["SoilAnalysis", "SalinityChecker", "FertilizerAdvisor"]
