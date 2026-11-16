"""
Smart deficit irrigation engine based on FAO-56 Penman-Monteith.
محرك الري الناقص الذكي المبني على معادلة بنمان-مونتيث (FAO-56).

English
-------
Computes reference evapotranspiration (ET0) with the FAO-56 Penman-Monteith
equation, converts it to crop evapotranspiration (ETc = Kc x ET0) for wheat,
cotton, maize and barley, runs a root-zone water balance from measured soil
moisture, and recommends a net/gross irrigation depth under a configurable
deficit strategy. Irrigation-water salinity (ECw) is converted into a
leaching requirement (LR, FAO-29 / Rhoades) suited to the saline, often
gypsiferous soils of the Euphrates basin, and an indicative relative yield
(water stress x salinity) is reported.

العربية
-------
يحسب البخر-نتح المرجعي (ET0) بمعادلة بنمان-مونتيث وفق FAO-56، ثم يحوّله إلى
البخر-نتح للمحصول (ETc = Kc × ET0) للقمح والقطن والذرة والشعير، ويجري موازنة
مائية لمنطقة الجذور اعتماداً على رطوبة التربة المقاسة، ويوصي بعمق الري الصافي
والإجمالي وفق استراتيجية ري ناقص قابلة للضبط. يحوّل ملوحة مياه الري (ECw) إلى
معامل غسيل أملاح (LR) مناسب لترب حوض الفرات المالحة والجبسية، ويعطي تقديراً
استرشادياً للإنتاجية النسبية (إجهاد مائي × ملوحة).

Scientific notes / ملاحظات علمية
--------------------------------
* Crop/soil parameters are FAO-56 / FAO-33 / FAO-29 / Maas-Hoffman typical values
  and should be calibrated locally (القيم نموذجية ويجب معايرتها محلياً).
* Daily time step; G (soil heat flux) is taken as 0 for daily steps.
* Requires Python 3.11+ (StrEnum, slots dataclasses).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Final

__all__ = [
    "BilingualText",
    "Crop",
    "CropParameters",
    "CROP_DATABASE",
    "DailyWeather",
    "DeficitIrrigationEngine",
    "DeficitStrategy",
    "Et0Result",
    "FieldConditions",
    "GrowthStage",
    "IrrigationConfig",
    "IrrigationInputError",
    "IrrigationMethod",
    "IrrigationRecommendation",
    "SoilProperties",
    "SoilTexture",
    "crop_coefficient",
    "effective_rainfall",
    "leaching_requirement",
    "penman_monteith_et0",
    "root_depth_m",
]

# --------------------------------------------------------------------------- #
# Physical constants / الثوابت الفيزيائية
# --------------------------------------------------------------------------- #
SOLAR_CONSTANT_MJ_M2_MIN: Final[float] = 0.0820  # Gsc
STEFAN_BOLTZMANN_MJ_K4_M2_DAY: Final[float] = 4.903e-9
ALBEDO_REFERENCE_GRASS: Final[float] = 0.23
HARGREAVES_KRS_INTERIOR: Final[float] = 0.17  # 0.16 interior, 0.19 coastal
ANGSTROM_A: Final[float] = 0.25
ANGSTROM_B: Final[float] = 0.50


# --------------------------------------------------------------------------- #
# Errors and bilingual text / الأخطاء والنصوص ثنائية اللغة
# --------------------------------------------------------------------------- #
class IrrigationInputError(ValueError):
    """
    Raised when an input value is missing or physically invalid.
    يُرفع عند وجود مُدخل ناقص أو غير منطقي فيزيائياً.
    """

    def __init__(self, ar: str, en: str) -> None:
        super().__init__(f"{en} | {ar}")
        self.message_ar = ar
        self.message_en = en


@dataclass(frozen=True, slots=True)
class BilingualText:
    """
    A message in Arabic and English.
    رسالة بالعربية والإنجليزية.
    """

    ar: str
    en: str

    def __str__(self) -> str:
        return f"{self.ar} | {self.en}"


def _require(condition: bool, ar: str, en: str) -> None:
    """Raise IrrigationInputError if condition is False. / يرفع خطأ إذا لم يتحقق الشرط."""
    if not condition:
        raise IrrigationInputError(ar, en)


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp value into [low, high]. / تقييد القيمة ضمن المجال."""
    return max(low, min(high, value))


# --------------------------------------------------------------------------- #
# Enumerations / التعدادات
# --------------------------------------------------------------------------- #
class Crop(StrEnum):
    """Supported crops. / المحاصيل المدعومة."""

    WHEAT = "wheat"  # قمح
    COTTON = "cotton"  # قطن
    MAIZE = "maize"  # ذرة
    BARLEY = "barley"  # شعير


class GrowthStage(StrEnum):
    """
    FAO-56 growth stages. / مراحل النمو حسب FAO-56.

    INITIAL: germination/establishment (الإنبات والتأسيس)
    DEVELOPMENT: rapid canopy development (النمو الخضري السريع)
    MID_SEASON: flowering + yield formation (الإزهار وتكوين الحاصل)
    LATE_SEASON: ripening/senescence (النضج والشيخوخة)
    """

    INITIAL = "initial"
    DEVELOPMENT = "development"
    MID_SEASON = "mid_season"
    LATE_SEASON = "late_season"


class IrrigationMethod(StrEnum):
    """Irrigation method. / طريقة الري."""

    SURFACE = "surface"  # ري سطحي (أحواض/خطوط)
    SPRINKLER = "sprinkler"  # ري بالرش
    DRIP = "drip"  # ري بالتنقيط


class DeficitStrategy(StrEnum):
    """
    Water-management strategy. / استراتيجية إدارة المياه.

    FULL: full irrigation (ري كامل).
    REGULATED_DEFICIT: RDI, deficit only in drought-tolerant stages (ري ناقص منظَّم).
    SUSTAINED_DEFICIT: SDI, constant fraction in all stages (ري ناقص مستدام).
    """

    FULL = "full"
    REGULATED_DEFICIT = "regulated_deficit"
    SUSTAINED_DEFICIT = "sustained_deficit"


class SoilTexture(StrEnum):
    """Typical Euphrates-basin soil textures. / قوام الترب النموذجي في حوض الفرات."""

    CLAY = "clay"  # طينية
    SILTY_CLAY_LOAM = "silty_clay_loam"  # طينية سلتية لومية (تربة الفيضان)
    CLAY_LOAM = "clay_loam"  # لومية طينية
    LOAM = "loam"  # لومية
    SANDY_LOAM = "sandy_loam"  # لومية رملية
    GYPSIFEROUS_LOAM = "gypsiferous_loam"  # لومية جبسية (البادية/الجزيرة)


# --------------------------------------------------------------------------- #
# Crop database / قاعدة بيانات المحاصيل
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class CropParameters:
    """
    Agronomic parameters of a crop.
    المعاملات الزراعية للمحصول.

    kc_ini/kc_mid/kc_end : FAO-56 crop coefficients (معاملات المحصول)
    root_min_m/root_max_m: effective root depth range, m (عمق الجذور الفعّال)
    depletion_fraction   : p, readily-available fraction at ETc = 5 mm/day (FAO-56 Table 22)
    ky_by_stage          : yield response factor per stage (FAO-33, approximate)
    ece_threshold        : a, ECe at which yield loss starts, dS/m (Maas-Hoffman)
    ece_slope            : b, % yield loss per dS/m above threshold (Maas-Hoffman)
    """

    crop: Crop
    name_ar: str
    kc_ini: float
    kc_mid: float
    kc_end: float
    root_min_m: float
    root_max_m: float
    depletion_fraction: float
    ky_by_stage: dict[GrowthStage, float]
    ece_threshold: float
    ece_slope: float

    @property
    def ece_zero_yield(self) -> float:
        """ECe at zero yield, dS/m. / الملوحة التي ينعدم عندها الحاصل."""
        return self.ece_threshold + 100.0 / self.ece_slope

    def ece_for_relative_yield(self, relative_yield_pct: float) -> float:
        """
        ECe (dS/m) that gives the requested relative yield.
        الملوحة (dS/m) التي تعطي الإنتاجية النسبية المطلوبة.
        """
        return self.ece_threshold + (100.0 - relative_yield_pct) / self.ece_slope


CROP_DATABASE: Final[dict[Crop, CropParameters]] = {
    Crop.WHEAT: CropParameters(
        crop=Crop.WHEAT,
        name_ar="قمح",
        kc_ini=0.35,
        kc_mid=1.15,
        kc_end=0.25,
        root_min_m=0.30,
        root_max_m=1.20,
        depletion_fraction=0.55,
        ky_by_stage={
            GrowthStage.INITIAL: 0.20,
            GrowthStage.DEVELOPMENT: 0.20,
            GrowthStage.MID_SEASON: 0.60,
            GrowthStage.LATE_SEASON: 0.10,
        },
        ece_threshold=6.0,
        ece_slope=7.1,
    ),
    Crop.COTTON: CropParameters(
        crop=Crop.COTTON,
        name_ar="قطن",
        kc_ini=0.35,
        kc_mid=1.18,
        kc_end=0.70,
        root_min_m=0.30,
        root_max_m=1.20,
        depletion_fraction=0.65,
        ky_by_stage={
            GrowthStage.INITIAL: 0.20,
            GrowthStage.DEVELOPMENT: 0.25,
            GrowthStage.MID_SEASON: 0.55,
            GrowthStage.LATE_SEASON: 0.15,
        },
        ece_threshold=7.7,
        ece_slope=5.2,
    ),
    Crop.MAIZE: CropParameters(
        crop=Crop.MAIZE,
        name_ar="ذرة",
        kc_ini=0.30,
        kc_mid=1.20,
        kc_end=0.60,
        root_min_m=0.30,
        root_max_m=1.20,
        depletion_fraction=0.55,
        ky_by_stage={
            GrowthStage.INITIAL: 0.40,
            GrowthStage.DEVELOPMENT: 0.40,
            GrowthStage.MID_SEASON: 1.50,
            GrowthStage.LATE_SEASON: 0.35,
        },
        ece_threshold=1.7,
        ece_slope=12.0,
    ),
    Crop.BARLEY: CropParameters(
        crop=Crop.BARLEY,
        name_ar="شعير",
        kc_ini=0.35,
        kc_mid=1.15,
        kc_end=0.25,
        root_min_m=0.30,
        root_max_m=1.00,
        depletion_fraction=0.55,
        ky_by_stage={
            GrowthStage.INITIAL: 0.20,
            GrowthStage.DEVELOPMENT: 0.25,
            GrowthStage.MID_SEASON: 0.60,
            GrowthStage.LATE_SEASON: 0.10,
        },
        ece_threshold=8.0,
        ece_slope=5.0,
    ),
}


# --------------------------------------------------------------------------- #
# Soil / التربة
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class SoilProperties:
    """
    Soil hydraulic properties (volumetric, m3/m3).
    الخصائص المائية للتربة (حجمية، م³/م³).

    field_capacity : θfc, السعة الحقلية
    wilting_point  : θwp, نقطة الذبول
    """

    field_capacity: float
    wilting_point: float

    def __post_init__(self) -> None:
        _require(
            0.0 < self.wilting_point < self.field_capacity < 0.7,
            "يجب أن تتحقق العلاقة 0 < نقطة الذبول < السعة الحقلية < 0.7",
            "Require 0 < wilting_point < field_capacity < 0.7",
        )

    @classmethod
    def from_texture(cls, texture: SoilTexture) -> SoilProperties:
        """
        Typical values (FAO-56 Table 19, mid-range). Gypsiferous soils hold less water.
        قيم نموذجية (منتصف المجال في FAO-56)؛ الترب الجبسية أقل احتفاظاً بالماء.
        """
        table: dict[SoilTexture, tuple[float, float]] = {
            SoilTexture.CLAY: (0.36, 0.22),
            SoilTexture.SILTY_CLAY_LOAM: (0.33, 0.20),
            SoilTexture.CLAY_LOAM: (0.30, 0.17),
            SoilTexture.LOAM: (0.25, 0.12),
            SoilTexture.SANDY_LOAM: (0.20, 0.09),
            SoilTexture.GYPSIFEROUS_LOAM: (0.24, 0.11),
        }
        fc, wp = table[texture]
        return cls(field_capacity=fc, wilting_point=wp)


# --------------------------------------------------------------------------- #
# Inputs / المُدخلات
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class DailyWeather:
    """
    Daily weather record for ET0.
    سجل الطقس اليومي لحساب ET0.

    tmin_c, tmax_c        : air temperature, °C (الحرارة الدنيا والعظمى)
    wind_speed_ms         : mean wind speed at wind_height_m, m/s (سرعة الرياح)
    latitude_deg          : decimal degrees, north positive (خط العرض)
    elevation_m           : station elevation, m (الارتفاع عن سطح البحر)
    day_of_year           : 1..366 (رقم اليوم في السنة)
    rh_mean_pct / rh_min_pct+rh_max_pct : relative humidity (الرطوبة النسبية)
    solar_radiation_mj_m2 : Rs, MJ/m2/day (الإشعاع الشمسي) - preferred
    sunshine_hours        : n, used if Rs missing (ساعات سطوع الشمس)
    rainfall_mm           : daily rainfall (الهطول)
    If neither Rs nor sunshine is given, Hargreaves estimation is used.
    إذا لم يتوفر Rs ولا ساعات السطوع تُستخدم طريقة هارغريفز للتقدير.
    """

    tmin_c: float
    tmax_c: float
    wind_speed_ms: float
    latitude_deg: float
    elevation_m: float
    day_of_year: int
    rh_mean_pct: float | None = None
    rh_min_pct: float | None = None
    rh_max_pct: float | None = None
    solar_radiation_mj_m2: float | None = None
    sunshine_hours: float | None = None
    wind_height_m: float = 2.0
    rainfall_mm: float = 0.0

    def __post_init__(self) -> None:
        _require(-60.0 <= self.tmin_c <= self.tmax_c <= 65.0,
                 "الحرارة غير منطقية: يجب أن تكون الدنيا ≤ العظمى ضمن [-60, 65]",
                 "Temperatures invalid: need -60 <= tmin <= tmax <= 65 °C")
        _require(self.wind_speed_ms >= 0.0, "سرعة الرياح سالبة", "Wind speed is negative")
        _require(self.wind_height_m > 0.0, "ارتفاع قياس الرياح يجب أن يكون موجباً",
                 "Wind measurement height must be positive")
        _require(-66.5 <= self.latitude_deg <= 66.5,
                 "خط العرض خارج مجال الصلاحية [-66.5, 66.5]",
                 "Latitude outside validity range [-66.5, 66.5]")
        _require(-400.0 <= self.elevation_m <= 6000.0, "الارتفاع غير منطقي", "Elevation is implausible")
        _require(1 <= self.day_of_year <= 366, "رقم اليوم يجب أن يكون بين 1 و366",
                 "day_of_year must be within 1..366")
        _require(self.rainfall_mm >= 0.0, "الهطول سالب", "Rainfall is negative")
        has_mean = self.rh_mean_pct is not None
        has_pair = self.rh_min_pct is not None and self.rh_max_pct is not None
        _require(has_mean or has_pair,
                 "يجب توفير الرطوبة المتوسطة أو (الصغرى والعظمى)",
                 "Provide mean RH or both min and max RH")
        for name, val in (("rh_mean_pct", self.rh_mean_pct), ("rh_min_pct", self.rh_min_pct),
                          ("rh_max_pct", self.rh_max_pct)):
            if val is not None:
                _require(0.0 <= val <= 100.0, f"الرطوبة {name} خارج [0, 100]",
                         f"{name} outside [0, 100]")
        if has_pair:
            _require(self.rh_min_pct <= self.rh_max_pct,  # type: ignore[operator]
                     "الرطوبة الصغرى أكبر من العظمى", "rh_min is greater than rh_max")
        if self.solar_radiation_mj_m2 is not None:
            _require(0.0 <= self.solar_radiation_mj_m2 <= 45.0, "الإشعاع الشمسي غير منطقي",
                     "Solar radiation implausible (0..45 MJ/m2/day)")
        if self.sunshine_hours is not None:
            _require(0.0 <= self.sunshine_hours <= 24.0, "ساعات السطوع غير منطقية",
                     "Sunshine hours must be within 0..24")


@dataclass(frozen=True, slots=True)
class FieldConditions:
    """
    Field state used to compute the recommendation.
    حالة الحقل المستخدمة في التوصية.

    soil_moisture   : measured root-zone VWC. Fraction (0.27) or percent (27) accepted.
                      الرطوبة الحجمية المقاسة؛ تُقبل كنسبة (0.27) أو مئوية (27).
    water_ec_dsm    : ECw of irrigation water, dS/m (ملوحة مياه الري)
    soil_ece_dsm    : measured saturation-extract ECe, dS/m; if None it is estimated
                      من ملوحة التربة المقاسة؛ إن لم تتوفر تُقدَّر من ECw
    stage_progress  : 0..1 position within the stage (موقع الحقل داخل المرحلة)
    area_ha         : irrigated area for volume totals (المساحة بالهكتار)
    """

    crop: Crop
    stage: GrowthStage
    soil_moisture: float
    soil: SoilProperties
    water_ec_dsm: float
    soil_ece_dsm: float | None = None
    stage_progress: float = 0.5
    area_ha: float = 1.0

    def __post_init__(self) -> None:
        _require(0.0 <= self.stage_progress <= 1.0, "تقدم المرحلة يجب أن يكون بين 0 و1",
                 "stage_progress must be within 0..1")
        _require(self.water_ec_dsm >= 0.0, "ملوحة المياه سالبة", "ECw is negative")
        _require(self.soil_ece_dsm is None or self.soil_ece_dsm >= 0.0, "ملوحة التربة سالبة",
                 "Soil ECe is negative")
        _require(self.area_ha > 0.0, "المساحة يجب أن تكون موجبة", "Area must be positive")
        _require(self.soil_moisture >= 0.0, "رطوبة التربة سالبة", "Soil moisture is negative")
        _require(self.soil_moisture <= 100.0, "رطوبة التربة أكبر من 100%",
                 "Soil moisture greater than 100%")

    @property
    def soil_moisture_fraction(self) -> float:
        """Soil moisture as m3/m3. / رطوبة التربة كنسبة حجمية."""
        return self.soil_moisture / 100.0 if self.soil_moisture > 1.0 else self.soil_moisture


@dataclass(frozen=True, slots=True)
class IrrigationConfig:
    """
    Engine configuration. / إعدادات المحرك.

    method                      : irrigation method (طريقة الري)
    strategy                    : deficit strategy (استراتيجية الري)
    sustained_deficit_fraction  : fraction of requirement applied under SDI (نسبة SDI)
    water_availability_fraction : cap from water scarcity, 0..1 (سقف توفر المياه)
    target_relative_yield_pct   : yield target used to choose tolerable ECe for LR
                                  (الإنتاجية المستهدفة لاختيار الملوحة المقبولة)
    application_efficiency      : Ea override, 0..1 (كفاءة الإضافة؛ الافتراضي حسب الطريقة)
    planning_horizon_days       : look-ahead for trigger test (أفق التخطيط بالأيام)
    emergency_ks_threshold      : below this Ks, deficit is relaxed (حد الطوارئ)
    max_leaching_requirement    : upper bound for LR (الحد الأعلى لمعامل الغسيل)
    root_zone_ece_factor        : ECe ≈ factor x ECw when ECe not measured (≈1.5 at LF 15-20%)
    """

    method: IrrigationMethod = IrrigationMethod.SURFACE
    strategy: DeficitStrategy = DeficitStrategy.REGULATED_DEFICIT
    sustained_deficit_fraction: float = 0.75
    water_availability_fraction: float = 1.0
    target_relative_yield_pct: float = 90.0
    application_efficiency: float | None = None
    planning_horizon_days: int = 1
    emergency_ks_threshold: float = 0.6
    max_leaching_requirement: float = 0.5
    root_zone_ece_factor: float = 1.5

    def __post_init__(self) -> None:
        _require(0.3 <= self.sustained_deficit_fraction <= 1.0,
                 "نسبة الري الناقص المستدام يجب أن تكون بين 0.3 و1",
                 "sustained_deficit_fraction must be within 0.3..1")
        _require(0.0 < self.water_availability_fraction <= 1.0,
                 "توفر المياه يجب أن يكون في (0, 1]", "water_availability_fraction must be in (0, 1]")
        _require(50.0 <= self.target_relative_yield_pct <= 100.0,
                 "الإنتاجية المستهدفة بين 50 و100", "target_relative_yield_pct must be 50..100")
        _require(self.application_efficiency is None or 0.2 <= self.application_efficiency <= 1.0,
                 "كفاءة الإضافة بين 0.2 و1", "application_efficiency must be 0.2..1")
        _require(1 <= self.planning_horizon_days <= 7, "أفق التخطيط بين 1 و7 أيام",
                 "planning_horizon_days must be 1..7")
        _require(0.0 < self.max_leaching_requirement < 1.0, "الحد الأعلى للغسيل في (0, 1)",
                 "max_leaching_requirement must be in (0, 1)")

    @property
    def efficiency(self) -> float:
        """Effective application efficiency Ea. / كفاءة الإضافة الفعلية."""
        if self.application_efficiency is not None:
            return self.application_efficiency
        return {
            IrrigationMethod.SURFACE: 0.60,
            IrrigationMethod.SPRINKLER: 0.75,
            IrrigationMethod.DRIP: 0.90,
        }[self.method]


# --------------------------------------------------------------------------- #
# Penman-Monteith FAO-56 / معادلة بنمان-مونتيث
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class Et0Result:
    """
    ET0 calculation output. / مخرجات حساب ET0.

    et0_mm        : reference ET, mm/day (البخر-نتح المرجعي)
    rs_mj_m2      : solar radiation used (الإشعاع المستخدم)
    rn_mj_m2      : net radiation (صافي الإشعاع)
    solar_estimated : True if Rs came from sunshine/Hargreaves (الإشعاع مقدَّر)
    """

    et0_mm: float
    rs_mj_m2: float
    rn_mj_m2: float
    solar_estimated: bool


def saturation_vapour_pressure(temp_c: float) -> float:
    """e°(T) in kPa (FAO-56 Eq. 11). / ضغط بخار التشبع."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def slope_vapour_pressure_curve(temp_c: float) -> float:
    """Δ in kPa/°C (FAO-56 Eq. 13). / ميل منحنى ضغط بخار التشبع."""
    return 4098.0 * saturation_vapour_pressure(temp_c) / (temp_c + 237.3) ** 2


def atmospheric_pressure(elevation_m: float) -> float:
    """P in kPa (FAO-56 Eq. 7). / الضغط الجوي."""
    return 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26


def wind_speed_at_2m(wind_ms: float, height_m: float) -> float:
    """Convert wind speed to 2 m height (FAO-56 Eq. 47). / تحويل سرعة الرياح إلى ارتفاع 2 م."""
    if math.isclose(height_m, 2.0):
        return wind_ms
    return wind_ms * 4.87 / math.log(67.8 * height_m - 5.42)


def _solar_declination(day_of_year: int) -> float:
    return 0.409 * math.sin(2.0 * math.pi * day_of_year / 365.0 - 1.39)


def _sunset_hour_angle(lat_rad: float, decl: float) -> float:
    return math.acos(_clamp(-math.tan(lat_rad) * math.tan(decl), -1.0, 1.0))


def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    """Ra in MJ/m2/day (FAO-56 Eq. 21). / الإشعاع خارج الغلاف الجوي."""
    lat = math.radians(latitude_deg)
    decl = _solar_declination(day_of_year)
    ws = _sunset_hour_angle(lat, decl)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
    return (24.0 * 60.0 / math.pi) * SOLAR_CONSTANT_MJ_M2_MIN * dr * (
        ws * math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.sin(ws)
    )


def daylight_hours(latitude_deg: float, day_of_year: int) -> float:
    """N in hours (FAO-56 Eq. 34). / طول النهار الفلكي."""
    lat = math.radians(latitude_deg)
    return 24.0 / math.pi * _sunset_hour_angle(lat, _solar_declination(day_of_year))


def penman_monteith_et0(weather: DailyWeather) -> Et0Result:
    """
    FAO-56 Penman-Monteith reference evapotranspiration (daily).
    البخر-نتح المرجعي اليومي بمعادلة بنمان-مونتيث (FAO-56، المعادلة 6).

    ET0 = [0.408 Δ (Rn-G) + γ 900/(T+273) u2 (es-ea)] / [Δ + γ (1 + 0.34 u2)]
    """
    t_mean = (weather.tmax_c + weather.tmin_c) / 2.0
    pressure = atmospheric_pressure(weather.elevation_m)
    gamma = 0.000665 * pressure
    delta = slope_vapour_pressure_curve(t_mean)

    e_tmax = saturation_vapour_pressure(weather.tmax_c)
    e_tmin = saturation_vapour_pressure(weather.tmin_c)
    es = (e_tmax + e_tmin) / 2.0
    if weather.rh_min_pct is not None and weather.rh_max_pct is not None:
        ea = (e_tmin * weather.rh_max_pct / 100.0 + e_tmax * weather.rh_min_pct / 100.0) / 2.0
    else:
        ea = (weather.rh_mean_pct or 0.0) / 100.0 * es
    ea = min(ea, es)

    ra = extraterrestrial_radiation(weather.latitude_deg, weather.day_of_year)
    estimated = False
    if weather.solar_radiation_mj_m2 is not None:
        rs = weather.solar_radiation_mj_m2
    elif weather.sunshine_hours is not None:
        n_max = daylight_hours(weather.latitude_deg, weather.day_of_year)
        n_act = min(weather.sunshine_hours, n_max)
        rs = (ANGSTROM_A + ANGSTROM_B * n_act / n_max) * ra
        estimated = True
    else:
        rs = HARGREAVES_KRS_INTERIOR * math.sqrt(weather.tmax_c - weather.tmin_c) * ra
        estimated = True

    rso = (0.75 + 2e-5 * weather.elevation_m) * ra
    rs_ratio = _clamp(rs / rso, 0.3, 1.0) if rso > 0.0 else 0.5
    rns = (1.0 - ALBEDO_REFERENCE_GRASS) * rs
    tk4 = ((weather.tmax_c + 273.16) ** 4 + (weather.tmin_c + 273.16) ** 4) / 2.0
    rnl = STEFAN_BOLTZMANN_MJ_K4_M2_DAY * tk4 * (0.34 - 0.14 * math.sqrt(ea)) * (1.35 * rs_ratio - 0.35)
    rn = rns - rnl

    u2 = wind_speed_at_2m(weather.wind_speed_ms, weather.wind_height_m)
    numerator = 0.408 * delta * rn + gamma * 900.0 / (t_mean + 273.0) * u2 * (es - ea)
    denominator = delta + gamma * (1.0 + 0.34 * u2)
    et0 = max(0.0, numerator / denominator)
    return Et0Result(et0_mm=et0, rs_mj_m2=rs, rn_mj_m2=rn, solar_estimated=estimated)


# --------------------------------------------------------------------------- #
# Crop, roots, rain, leaching / المحصول والجذور والمطر والغسيل
# --------------------------------------------------------------------------- #
def crop_coefficient(params: CropParameters, stage: GrowthStage, progress: float) -> float:
    """
    Stage-based Kc with linear interpolation in transition stages.
    معامل المحصول Kc حسب المرحلة مع استيفاء خطي في مراحل الانتقال.
    """
    if stage is GrowthStage.INITIAL:
        return params.kc_ini
    if stage is GrowthStage.DEVELOPMENT:
        return params.kc_ini + (params.kc_mid - params.kc_ini) * progress
    if stage is GrowthStage.MID_SEASON:
        return params.kc_mid
    return params.kc_mid + (params.kc_end - params.kc_mid) * progress


def root_depth_m(params: CropParameters, stage: GrowthStage, progress: float) -> float:
    """
    Effective root depth by stage. / عمق الجذور الفعّال حسب المرحلة.
    """
    if stage is GrowthStage.INITIAL:
        return params.root_min_m
    if stage is GrowthStage.DEVELOPMENT:
        return params.root_min_m + (params.root_max_m - params.root_min_m) * progress
    return params.root_max_m


def effective_rainfall(rain_mm: float) -> float:
    """
    Simplified daily effective rainfall: first 2 mm lost to interception, 80% of rest infiltrates.
    الهطول الفعّال المبسّط: أول 2 مم تُفقد بالاعتراض و80% من الباقي يتسرب.
    """
    return 0.0 if rain_mm <= 2.0 else 0.8 * (rain_mm - 2.0)


def leaching_requirement(
    ecw_dsm: float,
    params: CropParameters,
    method: IrrigationMethod,
    target_relative_yield_pct: float,
    max_lr: float,
) -> tuple[float, bool]:
    """
    Leaching requirement LR (FAO-29, Rhoades).
    معامل غسيل الأملاح LR (FAO-29، رودس).

    Surface/sprinkler: LR = ECw / (5 ECe - ECw)
    Drip (high frequency): LR = ECw / (2 ECe_max)
    ECe is the tolerable ECe for the target yield. / ECe هي الملوحة المقبولة للإنتاجية المستهدفة.

    Returns (LR, was_capped). / يعيد (LR، هل تم تقييده بالحد الأعلى).
    """
    if ecw_dsm <= 0.0:
        return 0.0, False
    if method is IrrigationMethod.DRIP:
        lr = ecw_dsm / (2.0 * params.ece_zero_yield)
    else:
        ece_tol = params.ece_for_relative_yield(target_relative_yield_pct)
        denominator = 5.0 * ece_tol - ecw_dsm
        if denominator <= 0.0:
            return max_lr, True
        lr = ecw_dsm / denominator
    if lr > max_lr:
        return max_lr, True
    return max(0.0, lr), False


# --------------------------------------------------------------------------- #
# Output / المخرجات
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class IrrigationRecommendation:
    """
    Full irrigation recommendation. / التوصية الكاملة للري.

    All depths in mm; volumes in m3 (1 mm over 1 ha = 10 m3).
    جميع الأعماق بالمليمتر والأحجام بالمتر المكعب (1 مم على هكتار = 10 م³).
    """

    et0_mm: float
    kc: float
    etc_mm: float
    ks: float
    eta_mm: float
    root_depth_m: float
    taw_mm: float
    raw_mm: float
    depletion_mm: float
    effective_rain_mm: float
    trigger_depth_mm: float
    deficit_factor: float
    irrigate: bool
    net_depth_mm: float
    leaching_requirement: float
    application_efficiency: float
    gross_depth_mm: float
    volume_m3_per_ha: float
    total_volume_m3: float
    days_until_irrigation: float | None
    root_zone_ece_dsm: float
    water_stress_yield_loss_pct: float
    salinity_yield_loss_pct: float
    expected_relative_yield_pct: float
    warnings: tuple[BilingualText, ...] = field(default_factory=tuple)
    summary: BilingualText = field(default_factory=lambda: BilingualText("", ""))

    def to_dict(self) -> dict[str, Any]:
        """
        JSON-serialisable dict (e.g. for offline_sync decisions).
        قاموس قابل للتسلسل إلى JSON (مثلاً لحفظه كقرار في offline_sync).
        """
        data = asdict(self)
        data["warnings"] = [{"ar": w.ar, "en": w.en} for w in self.warnings]
        data["summary"] = {"ar": self.summary.ar, "en": self.summary.en}
        return data


# --------------------------------------------------------------------------- #
# Engine / المحرك
# --------------------------------------------------------------------------- #
class DeficitIrrigationEngine:
    """
    Deficit irrigation decision engine.
    محرك قرار الري الناقص.

    Method / الطريقة
    ----------------
    1. ET0 (Penman-Monteith) -> ETc = Kc x ET0.
    2. Root-zone balance: TAW = 1000 (θfc-θwp) Zr; RAW = p TAW; Dr from measured moisture;
       Ks = (TAW-Dr)/((1-p) TAW) when Dr > RAW.
    3. Deficit factor DF by strategy and stage sensitivity (Ky); relaxed in emergencies.
    4. Trigger depth = RAW + (1-DF)(TAW-RAW), capped at 0.9 TAW. Irrigate when the
       depletion projected over the planning horizon reaches the trigger.
    5. Net depth = DF x projected depletion; gross = net / (Ea (1-LR)).
    6. Indicative yield: (1 - Ky(1-ETa/ETc)) x (1 - salinity loss), Maas-Hoffman.

    Example / مثال
    --------------
    >>> engine = DeficitIrrigationEngine(IrrigationConfig(method=IrrigationMethod.DRIP))
    >>> weather = DailyWeather(tmin_c=18, tmax_c=38, wind_speed_ms=2.5, latitude_deg=35.3,
    ...                        elevation_m=220, day_of_year=180, rh_mean_pct=30,
    ...                        solar_radiation_mj_m2=28)
    >>> cond = FieldConditions(Crop.COTTON, GrowthStage.MID_SEASON, 0.21,
    ...                        SoilProperties.from_texture(SoilTexture.CLAY_LOAM), 2.5)
    >>> result = engine.recommend(weather, cond)
    """

    def __init__(self, config: IrrigationConfig | None = None) -> None:
        self.config: IrrigationConfig = config or IrrigationConfig()

    # -- strategy ---------------------------------------------------------- #
    def _deficit_factor(self, ky: float, ks: float, warnings: list[BilingualText]) -> float:
        """
        Fraction of the requirement to replenish. / نسبة الاحتياج التي يجب تعويضها.
        """
        cfg = self.config
        if cfg.strategy is DeficitStrategy.FULL:
            factor = 1.0
        elif cfg.strategy is DeficitStrategy.SUSTAINED_DEFICIT:
            factor = cfg.sustained_deficit_fraction
        elif ky >= 0.9:
            factor = 1.0  # critical / حرجة
        elif ky >= 0.45:
            factor = 0.9  # high sensitivity / حساسية عالية
        elif ky >= 0.25:
            factor = 0.75  # moderate / متوسطة
        else:
            factor = 0.6  # tolerant / متحملة

        if ks < cfg.emergency_ks_threshold and factor < 0.9:
            factor = 0.9
            warnings.append(BilingualText(
                "إجهاد مائي شديد: تم رفع نسبة الري إلى 90% لتجنب فقد الحاصل.",
                "Severe water stress: deficit relaxed to 90% to avoid yield collapse."))
        if factor > cfg.water_availability_fraction:
            factor = cfg.water_availability_fraction
            warnings.append(BilingualText(
                "تم تقييد الري بسقف توفر المياه المتاح.",
                "Irrigation capped by available water supply."))
        return factor

    # -- main -------------------------------------------------------------- #
    def recommend(self, weather: DailyWeather, conditions: FieldConditions) -> IrrigationRecommendation:
        """
        Produce a recommendation for one field and one day.
        يُنتج توصية لحقل واحد ولليوم الحالي.
        """
        cfg = self.config
        params = CROP_DATABASE[conditions.crop]
        soil = conditions.soil
        warnings: list[BilingualText] = []

        # 1) ET0 / ETc
        et0_res = penman_monteith_et0(weather)
        if et0_res.solar_estimated:
            warnings.append(BilingualText(
                "الإشعاع الشمسي مقدَّر (ساعات السطوع أو هارغريفز)؛ دقة ET0 أقل.",
                "Solar radiation was estimated (sunshine/Hargreaves); ET0 is less accurate."))
        kc = crop_coefficient(params, conditions.stage, conditions.stage_progress)
        etc = kc * et0_res.et0_mm

        # 2) Root-zone water balance
        zr = root_depth_m(params, conditions.stage, conditions.stage_progress)
        taw = 1000.0 * (soil.field_capacity - soil.wilting_point) * zr
        p = _clamp(params.depletion_fraction + 0.04 * (5.0 - etc), 0.10, 0.80)
        raw = p * taw

        theta = conditions.soil_moisture_fraction
        if theta > soil.field_capacity:
            warnings.append(BilingualText(
                "الرطوبة المقاسة أعلى من السعة الحقلية: تشبع أو خطأ معايرة حساس.",
                "Measured moisture exceeds field capacity: saturation or sensor calibration error."))
            theta = soil.field_capacity
        if theta < soil.wilting_point:
            warnings.append(BilingualText(
                "الرطوبة المقاسة أقل من نقطة الذبول: خطر ذبول دائم.",
                "Measured moisture is below wilting point: risk of permanent wilting."))
        depletion = _clamp(1000.0 * (soil.field_capacity - theta) * zr, 0.0, taw)
        rain_eff = effective_rainfall(weather.rainfall_mm)
        depletion_eff = max(0.0, depletion - rain_eff)
        ks = 1.0 if depletion_eff <= raw else max(0.0, (taw - depletion_eff) / ((1.0 - p) * taw))
        eta = ks * etc

        # 3) Strategy
        ky = params.ky_by_stage[conditions.stage]
        factor = self._deficit_factor(ky, ks, warnings)
        trigger = min(raw + (1.0 - factor) * (taw - raw), 0.9 * taw)

        # 4) Decision
        projected = min(taw, depletion_eff + etc * cfg.planning_horizon_days)
        irrigate = projected >= trigger
        net = factor * projected if irrigate else 0.0
        days_left: float | None = None
        if not irrigate and etc > 0.0:
            days_left = round(max(0.0, (trigger - depletion_eff) / etc), 1)

        # 5) Salinity and leaching
        lr, lr_capped = leaching_requirement(
            conditions.water_ec_dsm, params, cfg.method,
            cfg.target_relative_yield_pct, cfg.max_leaching_requirement)
        if lr_capped:
            warnings.append(BilingualText(
                "ملوحة المياه عالية جداً لهذا المحصول: معامل الغسيل بلغ الحد الأعلى؛ فكّر بمصدر مياه أفضل أو محصول أكثر تحملاً.",
                "Water salinity is too high for this crop: LR hit its cap; consider better water or a more tolerant crop."))
        if conditions.water_ec_dsm > 3.0:
            warnings.append(BilingualText(
                "ECw > 3 dS/m: قيد شديد على استخدام المياه (Ayers & Westcot).",
                "ECw > 3 dS/m: severe restriction on use (Ayers & Westcot)."))
        ea = cfg.efficiency
        gross = net / (ea * (1.0 - lr)) if irrigate else 0.0

        ece_root = (conditions.soil_ece_dsm if conditions.soil_ece_dsm is not None
                    else cfg.root_zone_ece_factor * conditions.water_ec_dsm)
        if ece_root >= params.ece_zero_yield:
            warnings.append(BilingualText(
                "ملوحة منطقة الجذور تتجاوز حد انعدام الحاصل لهذا المحصول.",
                "Root-zone salinity exceeds the zero-yield limit for this crop."))
        if conditions.soil_ece_dsm is not None and conditions.soil_ece_dsm > params.ece_threshold:
            warnings.append(BilingualText(
                "ملوحة التربة المقاسة فوق عتبة التحمل: يُنصح بغسيل إضافي وتصريف جيد.",
                "Measured soil ECe is above the tolerance threshold: extra leaching and drainage advised."))

        # 6) Yield estimate
        eta_ratio = factor if irrigate else ks
        water_loss = _clamp(ky * (1.0 - eta_ratio), 0.0, 1.0)
        salt_loss = _clamp(params.ece_slope * max(0.0, ece_root - params.ece_threshold) / 100.0, 0.0, 1.0)
        rel_yield = 100.0 * (1.0 - water_loss) * (1.0 - salt_loss)

        volume_ha = gross * 10.0
        summary = self._summary(conditions, irrigate, net, gross, volume_ha, days_left, factor, lr)
        return IrrigationRecommendation(
            et0_mm=round(et0_res.et0_mm, 2),
            kc=round(kc, 3),
            etc_mm=round(etc, 2),
            ks=round(ks, 3),
            eta_mm=round(eta, 2),
            root_depth_m=round(zr, 2),
            taw_mm=round(taw, 1),
            raw_mm=round(raw, 1),
            depletion_mm=round(depletion, 1),
            effective_rain_mm=round(rain_eff, 1),
            trigger_depth_mm=round(trigger, 1),
            deficit_factor=round(factor, 2),
            irrigate=irrigate,
            net_depth_mm=round(net, 1),
            leaching_requirement=round(lr, 3),
            application_efficiency=ea,
            gross_depth_mm=round(gross, 1),
            volume_m3_per_ha=round(volume_ha, 1),
            total_volume_m3=round(volume_ha * conditions.area_ha, 1),
            days_until_irrigation=days_left,
            root_zone_ece_dsm=round(ece_root, 2),
            water_stress_yield_loss_pct=round(water_loss * 100.0, 1),
            salinity_yield_loss_pct=round(salt_loss * 100.0, 1),
            expected_relative_yield_pct=round(rel_yield, 1),
            warnings=tuple(warnings),
            summary=summary,
        )

    @staticmethod
    def _summary(cond: FieldConditions, irrigate: bool, net: float, gross: float,
                 volume_ha: float, days_left: float | None, factor: float,
                 lr: float) -> BilingualText:
        """Bilingual one-paragraph decision text. / نص القرار الموجز بالعربية والإنجليزية."""
        name_ar = CROP_DATABASE[cond.crop].name_ar
        if irrigate:
            ar = (f"{name_ar}: يُنصح بالري الآن. العمق الصافي {net:.1f} مم والإجمالي {gross:.1f} مم "
                  f"({volume_ha:.0f} م³/هكتار) بنسبة تعويض {factor:.0%} ومعامل غسيل {lr:.0%}.")
            en = (f"{cond.crop.value}: irrigate now. Net {net:.1f} mm, gross {gross:.1f} mm "
                  f"({volume_ha:.0f} m3/ha) at {factor:.0%} replenishment with LR {lr:.0%}.")
        else:
            when_ar = f"خلال نحو {days_left} يوم" if days_left is not None else "لاحقاً"
            when_en = f"in about {days_left} day(s)" if days_left is not None else "later"
            ar = f"{name_ar}: لا حاجة للري اليوم؛ الري المتوقع {when_ar}."
            en = f"{cond.crop.value}: no irrigation needed today; next irrigation expected {when_en}."
        return BilingualText(ar=ar, en=en)
