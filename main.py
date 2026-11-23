import math
import sys
from datetime import date
from pathlib import Path

import flet as ft
from PIL import Image, ImageOps


# =========================================================
# مسارات المشروع
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent

for directory in (ROOT_DIR, ROOT_DIR / "src"):
    directory_string = str(directory)
    if directory_string not in sys.path:
        sys.path.insert(0, directory_string)


from jazira_agri.intelligence.deficit_irrigation import (
    Crop,
    GrowthStage,
    IrrigationMethod,
    IrrigationConfig,
    DeficitStrategy,
    SoilTexture,
    SoilProperties,
    DailyWeather,
    FieldConditions,
    DeficitIrrigationEngine,
)


# =========================================================
# بيانات الدخول الحالية
# =========================================================

VALID_USER = "HUSIEN ALFARES"
VALID_PASS = "H99155729614a"


# =========================================================
# تحليل صورة الورقة باستخدام RGB
# =========================================================

def analyze_leaf_image(image_path: str) -> dict:
    path = Path(image_path).expanduser()

    if not path.is_file():
        raise ValueError(
            "لم يتم العثور على الصورة في المسار المحدد."
        )

    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        image = image.convert("RGB")
        image = image.resize((200, 200))

    healthy_green = 0
    yellow_stress = 0
    brown_necrosis = 0
    valid_pixels = 0

    for red, green, blue in image.getdata():
        is_nearly_white = (
            red > 235
            and green > 235
            and blue > 235
        )

        is_nearly_black = (
            red < 20
            and green < 20
            and blue < 20
        )

        if is_nearly_white or is_nearly_black:
            continue

        valid_pixels += 1

        if green > red * 1.12 and green > blue * 1.15:
            healthy_green += 1

        elif red > 140 and green > 130 and blue < 100:
            yellow_stress += 1

        elif (
            red > green * 1.15
            and red > blue * 1.2
            and green < 130
        ):
            brown_necrosis += 1

    if valid_pixels == 0:
        raise ValueError(
            "الصورة لا تحتوي على ألوان كافية للتحليل بعد استبعاد "
            "المناطق شديدة السواد أو البياض. اختر صورة أوضح."
        )

    green_pct = round(
        healthy_green / valid_pixels * 100,
        1,
    )

    yellow_pct = round(
        yellow_stress / valid_pixels * 100,
        1,
    )

    brown_pct = round(
        brown_necrosis / valid_pixels * 100,
        1,
    )

    if yellow_pct > 25:
        diagnosis = "اصفرار ملحوظ في أنسجة الورقة"
        advice = (
            "افحص الورقة بحثاً عن أعراض نقص العناصر أو الإصابة المرضية. "
            "هذا التحليل اللوني لا يؤكد التشخيص."
        )

    elif brown_pct > 20:
        diagnosis = "مناطق بنية أو نخرية ظاهرة"
        advice = (
            "افحص أسباب الاحتراق أو التبقع، وتحقق من ملوحة مياه الري "
            "والتربة عند الحاجة."
        )

    else:
        diagnosis = (
            "لم تظهر نسبة مرتفعة من الاصفرار أو المناطق البنية"
        )
        advice = (
            "تابع حالة النبات وافحص الأوراق من الجهتين. "
            "التحليل RGB أولي وليس تشخيصاً مرضياً مؤكداً."
        )

    return {
        "green": green_pct,
        "yellow": yellow_pct,
        "brown": brown_pct,
        "diagnosis": diagnosis,
        "advice": advice,
    }


# =========================================================
# التطبيق الرئيسي
# =========================================================

def main(page: ft.Page):
    page.title = "JaziraAgri-OS | نظام الجزيرة الزراعي الذكي"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT

    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.GREEN_800,
        use_material3=True,
    )

    page.padding = 12
    page.scroll = ft.ScrollMode.AUTO

    snack_bar = ft.SnackBar(content=ft.Text(""))
    page.overlay.append(snack_bar)

    salinity_history = [2.1, 2.3, 2.8, 3.2, 2.9]

    # -----------------------------------------------------
    # أدوات مساعدة
    # -----------------------------------------------------

    def show_message(message, color=ft.Colors.GREEN_800):
        snack_bar.content = ft.Text(
            str(message),
            color=ft.Colors.WHITE,
        )
        snack_bar.bgcolor = color
        snack_bar.open = True
        page.update()

    def make_field(label, value="", hint=""):
        return ft.TextField(
            label=label,
            value=value,
            hint_text=hint,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

    def make_dropdown(label, options, value):
        return ft.Dropdown(
            label=label,
            options=[
                ft.dropdown.Option(
                    key=key,
                    text=text,
                )
                for key, text in options
            ],
            value=value,
        )

    def parse_number(field, label):
        digits_map = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
            "01234567890123456789",
        )

        raw = (field.value or "").strip().translate(digits_map)
        raw = raw.replace("٫", ".").replace(",", ".")

        try:
            value = float(raw)

        except (ValueError, TypeError):
            raise ValueError(
                f"أدخل قيمة رقمية صحيحة في حقل: {label}"
            ) from None

        if not math.isfinite(value):
            raise ValueError(
                f"أدخل قيمة رقمية محدودة في حقل: {label}"
            )

        return value

    def page_title(title, subtitle=""):
        controls = [
            ft.Text(
                title,
                size=23,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.GREEN_900,
            )
        ]

        if subtitle:
            controls.append(
                ft.Text(
                    subtitle,
                    size=13,
                    color=ft.Colors.GREY_700,
                )
            )

        return ft.Column(
            controls,
            spacing=4,
        )

    def arabic_text(value):
        text = getattr(value, "ar", None)
        return str(text if text is not None else value)

    # -----------------------------------------------------
    # التنقل بين الشاشات
    # -----------------------------------------------------

    def switch_view(index):
        if index == 0:
            show_dashboard()

        elif index == 1:
            show_irrigation()

        elif index == 2:
            show_salinity()

        elif index == 3:
            show_image_analysis()

    def navigation_bar():
        return ft.Container(
            padding=8,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50,
            content=ft.Row(
                [
                    ft.TextButton(
                        "الرئيسية",
                        icon=ft.Icons.HOME,
                        on_click=lambda e: switch_view(0),
                    ),
                    ft.TextButton(
                        "الري",
                        icon=ft.Icons.WATER_DROP,
                        on_click=lambda e: switch_view(1),
                    ),
                    ft.TextButton(
                        "الملوحة",
                        icon=ft.Icons.SHOW_CHART,
                        on_click=lambda e: switch_view(2),
                    ),
                    ft.TextButton(
                        "الصور",
                        icon=ft.Icons.CAMERA_ALT,
                        on_click=lambda e: switch_view(3),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                wrap=True,
            ),
        )

    def show_screen(title, subtitle, controls):
        page.clean()

        page.add(
            ft.Column(
                [
                    navigation_bar(),
                    page_title(title, subtitle),
                    *controls,
                ],
                spacing=15,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )

        page.update()

    # =====================================================
    # 1. لوحة القيادة
    # =====================================================

    def show_dashboard():
        def stat_card(title, value, subtitle, icon):
            return ft.Container(
                width=155,
                padding=14,
                border_radius=12,
                bgcolor=ft.Colors.GREEN_50,
                content=ft.Column(
                    [
                        ft.Icon(
                            icon,
                            size=27,
                            color=ft.Colors.GREEN_800,
                        ),
                        ft.Text(
                            title,
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            value,
                            size=19,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREEN_900,
                        ),
                        ft.Text(
                            subtitle,
                            size=10,
                            color=ft.Colors.GREY_700,
                        ),
                    ],
                    spacing=5,
                ),
            )

        controls = [
            ft.Container(
                padding=20,
                border_radius=16,
                bgcolor=ft.Colors.GREEN_900,
                content=ft.Column(
                    [
                        ft.Text(
                            "مرحباً بك في جزيرة الزراعي",
                            size=21,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        ft.Text(
                            "نظام الإدارة والتحليل الزراعي الذكي",
                            size=14,
                            color=ft.Colors.WHITE,
                        ),
                        ft.Text(
                            "حوض الفرات",
                            size=12,
                            color=ft.Colors.GREEN_100,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            ft.Text(
                "الأدوات الزراعية",
                size=18,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Row(
                [
                    stat_card(
                        "حاسبة الري",
                        "ذكي",
                        "محرك الري الناقص",
                        ft.Icons.WATER_DROP,
                    ),
                    stat_card(
                        "ملوحة التربة",
                        str(salinity_history[-1]),
                        "آخر قيمة مسجلة في الجلسة",
                        ft.Icons.LANDSCAPE,
                    ),
                ],
                wrap=True,
                spacing=10,
            ),
            ft.Row(
                [
                    ft.ElevatedButton(
                        "حساب الاحتياج المائي",
                        icon=ft.Icons.CALCULATE,
                        on_click=lambda e: show_irrigation(),
                    ),
                    ft.ElevatedButton(
                        "تحليل صورة نبات",
                        icon=ft.Icons.CAMERA_ALT,
                        on_click=lambda e: show_image_analysis(),
                    ),
                ],
                wrap=True,
            ),
            ft.ElevatedButton(
                "متابعة ملوحة التربة",
                icon=ft.Icons.SHOW_CHART,
                on_click=lambda e: show_salinity(),
            ),
            ft.Divider(),
            ft.Text(
                "ملاحظة: القراءات الأولية المعروضة تجريبية وليست قراءات "
                "ميدانية مباشرة. أدخل بيانات حقلك للحصول على نتائج حسابية.",
                size=12,
                color=ft.Colors.GREY_700,
            ),
        ]

        show_screen(
            "لوحة القيادة",
            "نظام الجزيرة الزراعي الذكي",
            controls,
        )

    # =====================================================
    # 2. حاسبة الري الناقص الذكي
    # =====================================================

    def show_irrigation():
        crop_options = [
            ("wheat", "قمح"),
            ("cotton", "قطن"),
            ("maize", "ذرة"),
            ("barley", "شعير"),
        ]

        stage_options = [
            ("initial", "مرحلة البداية"),
            ("development", "مرحلة النمو"),
            ("mid_season", "منتصف الموسم"),
            ("late_season", "نهاية الموسم"),
        ]

        soil_options = [
            ("clay", "طينية"),
            ("silty_clay_loam", "طينية غرينية"),
            ("clay_loam", "طينية مزيجية"),
            ("loam", "مزيجية"),
            ("sandy_loam", "رملية مزيجية"),
            ("gypsiferous_loam", "مزيجية جبسية"),
        ]

        method_options = [
            ("surface", "ري سطحي"),
            ("sprinkler", "ري بالرش"),
            ("drip", "ري بالتنقيط"),
        ]

        crop_dd = make_dropdown(
            "المحصول",
            crop_options,
            "wheat",
        )

        stage_dd = make_dropdown(
            "مرحلة نمو المحصول",
            stage_options,
            "mid_season",
        )

        soil_dd = make_dropdown(
            "نوع التربة",
            soil_options,
            "clay_loam",
        )

        method_dd = make_dropdown(
            "طريقة الري",
            method_options,
            "surface",
        )

        moisture = make_field(
            "رطوبة التربة (%)",
            "20",
            "أدخل النسبة المئوية، مثلاً 20 تعني 20%",
        )

        rainfall = make_field(
            "الأمطار اليومية (ملم)",
            "0",
        )

        tmin = make_field(
            "درجة الحرارة الصغرى °C",
            "18",
        )

        tmax = make_field(
            "درجة الحرارة العظمى °C",
            "32",
        )

        humidity = make_field(
            "الرطوبة النسبية المتوسطة (%)",
            "40",
        )

        wind = make_field(
            "سرعة الرياح (متر/ثانية)",
            "2",
        )

        latitude = make_field(
            "خط العرض",
            "36.6",
            "أدخل خط عرض موقع الحقل",
        )

        elevation = make_field(
            "ارتفاع الحقل عن سطح البحر (متر)",
            "350",
        )

        solar = make_field(
            "الإشعاع الشمسي (MJ/m²/day)",
            "18",
        )

        water_ec = make_field(
            "ملوحة مياه الري EC (dS/m)",
            "1",
        )

        soil_ec = make_field(
            "ملوحة التربة ECe (dS/m)",
            "",
            "اختياري",
        )

        area = make_field(
            "مساحة الحقل (هكتار)",
            "1",
        )

        progress = make_field(
            "تقدم مرحلة النمو (من 0 إلى 1)",
            "0.5",
        )

        result_box = ft.Container(
            padding=15,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50,
            content=ft.Text(
                "أدخل بيانات الحقل والطقس ثم اضغط حساب التوصية.",
                size=14,
            ),
        )

        def calculate_irrigation(e):
            try:
                crop_map = {
                    "wheat": Crop.WHEAT,
                    "cotton": Crop.COTTON,
                    "maize": Crop.MAIZE,
                    "barley": Crop.BARLEY,
                }

                stage_map = {
                    "initial": GrowthStage.INITIAL,
                    "development": GrowthStage.DEVELOPMENT,
                    "mid_season": GrowthStage.MID_SEASON,
                    "late_season": GrowthStage.LATE_SEASON,
                }

                soil_map = {
                    "clay": SoilTexture.CLAY,
                    "silty_clay_loam": SoilTexture.SILTY_CLAY_LOAM,
                    "clay_loam": SoilTexture.CLAY_LOAM,
                    "loam": SoilTexture.LOAM,
                    "sandy_loam": SoilTexture.SANDY_LOAM,
                    "gypsiferous_loam": SoilTexture.GYPSIFEROUS_LOAM,
                }

                method_map = {
                    "surface": IrrigationMethod.SURFACE,
                    "sprinkler": IrrigationMethod.SPRINKLER,
                    "drip": IrrigationMethod.DRIP,
                }

                if crop_dd.value not in crop_map:
                    raise ValueError("اختر المحصول.")

                if stage_dd.value not in stage_map:
                    raise ValueError("اختر مرحلة النمو.")

                if soil_dd.value not in soil_map:
                    raise ValueError("اختر نوع التربة.")

                if method_dd.value not in method_map:
                    raise ValueError("اختر طريقة الري.")

                moisture_percent = parse_number(
                    moisture,
                    "رطوبة التربة",
                )

                if not 0 < moisture_percent <= 100:
                    raise ValueError(
                        "رطوبة التربة يجب أن تكون أكبر من صفر وحتى 100%."
                    )

                moisture_value = moisture_percent / 100.0

                rain_value = parse_number(
                    rainfall,
                    "الأمطار",
                )

                tmin_value = parse_number(
                    tmin,
                    "الحرارة الصغرى",
                )

                tmax_value = parse_number(
                    tmax,
                    "الحرارة العظمى",
                )

                humidity_value = parse_number(
                    humidity,
                    "الرطوبة النسبية",
                )

                wind_value = parse_number(
                    wind,
                    "سرعة الرياح",
                )

                latitude_value = parse_number(
                    latitude,
                    "خط العرض",
                )

                elevation_value = parse_number(
                    elevation,
                    "ارتفاع الحقل",
                )

                solar_value = parse_number(
                    solar,
                    "الإشعاع الشمسي",
                )

                water_ec_value = parse_number(
                    water_ec,
                    "ملوحة مياه الري",
                )

                area_value = parse_number(
                    area,
                    "مساحة الحقل",
                )

                progress_value = parse_number(
                    progress,
                    "تقدم مرحلة النمو",
                )

                soil_ec_value = (
                    parse_number(
                        soil_ec,
                        "ملوحة التربة",
                    )
                    if (soil_ec.value or "").strip()
                    else None
                )

                if rain_value < 0:
                    raise ValueError(
                        "الأمطار لا يمكن أن تكون سالبة."
                    )

                if tmin_value > tmax_value:
                    raise ValueError(
                        "الحرارة الصغرى لا يمكن أن تكون أكبر من العظمى."
                    )

                if not 0 <= humidity_value <= 100:
                    raise ValueError(
                        "الرطوبة النسبية يجب أن تكون بين 0 و100."
                    )

                if wind_value < 0:
                    raise ValueError(
                        "سرعة الرياح لا يمكن أن تكون سالبة."
                    )

                if solar_value < 0:
                    raise ValueError(
                        "الإشعاع الشمسي لا يمكن أن يكون سالباً."
                    )

                if not -90 <= latitude_value <= 90:
                    raise ValueError(
                        "خط العرض يجب أن يكون بين -90 و90."
                    )

                if area_value <= 0:
                    raise ValueError(
                        "مساحة الحقل يجب أن تكون أكبر من صفر."
                    )

                if not 0 <= progress_value <= 1:
                    raise ValueError(
                        "تقدم مرحلة النمو يجب أن يكون بين 0 و1."
                    )

                if water_ec_value < 0:
                    raise ValueError(
                        "ملوحة المياه لا يمكن أن تكون سالبة."
                    )

                if (
                    soil_ec_value is not None
                    and soil_ec_value < 0
                ):
                    raise ValueError(
                        "ملوحة التربة لا يمكن أن تكون سالبة."
                    )

                soil_properties = SoilProperties.from_texture(
                    soil_map[soil_dd.value]
                )

                weather = DailyWeather(
                    tmin_c=tmin_value,
                    tmax_c=tmax_value,
                    wind_speed_ms=wind_value,
                    latitude_deg=latitude_value,
                    elevation_m=elevation_value,
                    day_of_year=date.today().timetuple().tm_yday,
                    rh_mean_pct=humidity_value,
                    solar_radiation_mj_m2=solar_value,
                    rainfall_mm=rain_value,
                )

                conditions = FieldConditions(
                    crop=crop_map[crop_dd.value],
                    stage=stage_map[stage_dd.value],
                    soil_moisture=moisture_value,
                    soil=soil_properties,
                    water_ec_dsm=water_ec_value,
                    soil_ece_dsm=soil_ec_value,
                    stage_progress=progress_value,
                    area_ha=area_value,
                )

                config = IrrigationConfig(
                    method=method_map[method_dd.value],
                    strategy=DeficitStrategy.REGULATED_DEFICIT,
                )

                engine = DeficitIrrigationEngine(config)

                recommendation = engine.recommend(
                    weather,
                    conditions,
                )

                warnings_text = ""

                if recommendation.warnings:
                    warnings_text = (
                        "\n\nتحذيرات:\n"
                        + "\n".join(
                            f"• {arabic_text(warning)}"
                            for warning in recommendation.warnings
                        )
                    )

                summary_text = arabic_text(
                    recommendation.summary
                )

                output = (
                    f"{summary_text}\n\n"
                    f"ET0: {recommendation.et0_mm:.2f} ملم/يوم\n"
                    f"ETc: {recommendation.etc_mm:.2f} ملم/يوم\n"
                    f"عمق الري الصافي: "
                    f"{recommendation.net_depth_mm:.2f} ملم\n"
                    f"عمق الري الإجمالي: "
                    f"{recommendation.gross_depth_mm:.2f} ملم\n"
                    f"حجم المياه للهكتار: "
                    f"{recommendation.volume_m3_per_ha:.2f} م³\n"
                    f"حجم المياه للحقل: "
                    f"{recommendation.total_volume_m3:.2f} م³\n"
                    f"فقد المحصول المتوقع بسبب الإجهاد المائي: "
                    f"{recommendation.water_stress_yield_loss_pct:.2f}%\n"
                    f"الخسارة المتوقعة بسبب الملوحة: "
                    f"{recommendation.salinity_yield_loss_pct:.2f}%\n"
                    f"الإنتاج النسبي المتوقع: "
                    f"{recommendation.expected_relative_yield_pct:.2f}%"
                    f"{warnings_text}"
                )

                result_box.content = ft.Text(
                    output,
                    size=13,
                    selectable=True,
                )

                result_box.bgcolor = (
                    ft.Colors.GREEN_50
                    if recommendation.irrigate
                    else ft.Colors.BLUE_50
                )

                page.update()

            except Exception as ex:
                result_box.content = ft.Text(
                    f"تعذر حساب التوصية:\n{ex}",
                    color=ft.Colors.RED_800,
                    selectable=True,
                )

                result_box.bgcolor = ft.Colors.RED_50
                page.update()

        controls = [
            ft.Text(
                "بيانات المحصول والتربة",
                size=17,
                weight=ft.FontWeight.BOLD,
            ),
            crop_dd,
            stage_dd,
            soil_dd,
            method_dd,
            ft.Divider(),
            ft.Text(
                "بيانات التربة والمياه",
                size=17,
                weight=ft.FontWeight.BOLD,
            ),
            moisture,
            rainfall,
            water_ec,
            soil_ec,
            area,
            progress,
            ft.Divider(),
            ft.Text(
                "بيانات الطقس والموقع",
                size=17,
                weight=ft.FontWeight.BOLD,
            ),
            tmin,
            tmax,
            humidity,
            wind,
            latitude,
            elevation,
            solar,
            ft.ElevatedButton(
                "احسب توصية الري الذكي",
                icon=ft.Icons.CALCULATE,
                on_click=calculate_irrigation,
            ),
            result_box,
            ft.Text(
                "تنبيه علمي: دقة النتائج تعتمد على دقة قياس رطوبة التربة "
                "وملوحة المياه والتربة وبيانات الطقس وموقع الحقل. "
                "قيم نوع التربة الافتراضية تقديرية وتحتاج معايرة محلية. "
                "لا تعتمد على التوصية وحدها قبل التحقق من القياسات الميدانية.",
                size=11,
                color=ft.Colors.GREY_700,
            ),
        ]

        show_screen(
            "الري الناقص الذكي",
            "حساب الاحتياج المائي باستخدام محرك Deficit Irrigation",
            controls,
        )

    # =====================================================
    # 3. متابعة ملوحة التربة
    # =====================================================

    def show_salinity():
        ec_input = make_field(
            "قراءة ملوحة التربة EC (dS/m)",
            "",
        )

        def history_value():
            return (
                "القراءات المسجلة:\n"
                + "\n".join(
                    f"{index + 1}. {value} dS/m"
                    for index, value in enumerate(salinity_history)
                )
            )

        history_text = ft.Text(
            history_value(),
            selectable=True,
        )

        latest_text = ft.Text(
            f"آخر قراءة: {salinity_history[-1]} dS/m",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN_900,
        )

        def add_reading(e):
            try:
                value = parse_number(
                    ec_input,
                    "ملوحة التربة",
                )

                if value < 0:
                    raise ValueError(
                        "قراءة الملوحة لا يمكن أن تكون سالبة."
                    )

                salinity_history.append(value)

                latest_text.value = (
                    f"آخر قراءة: {value} dS/m"
                )

                history_text.value = history_value()
                ec_input.value = ""

                page.update()

            except Exception as ex:
                show_message(
                    str(ex),
                    ft.Colors.RED_800,
                )

        controls = [
            latest_text,
            ec_input,
            ft.ElevatedButton(
                "إضافة قراءة",
                icon=ft.Icons.ADD,
                on_click=add_reading,
            ),
            ft.Divider(),
            history_text,
            ft.Text(
                "القراءات الخمس الأولية تجريبية. القراءات الجديدة محفوظة "
                "في ذاكرة الجلسة الحالية فقط، ولا توجد قاعدة بيانات دائمة.",
                size=12,
                color=ft.Colors.GREY_700,
            ),
        ]

        show_screen(
            "متابعة ملوحة التربة",
            "إدخال القراءات ومتابعة تغير الملوحة",
            controls,
        )

    # =====================================================
    # 4. تحليل صور الأوراق النباتية
    # =====================================================

    def show_image_analysis():
        image_path = ft.TextField(
            label="مسار صورة الورقة على الجهاز",
            hint_text="/storage/emulated/0/Download/leaf.jpg",
        )

        def on_file_picked(e: ft.FilePickerResultEvent):
            if e.files and e.files[0].path:
                image_path.value = e.files[0].path
                image_path.update()

        file_picker = ft.FilePicker(on_result=on_file_picked)
        if file_picker not in page.overlay:
            page.overlay.append(file_picker)
            page.update()

        result_box = ft.Container(
            padding=15,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50,
            content=ft.Text(
                "اختر صورة من الجهاز أو أدخل مسارها، ثم اضغط تحليل الصورة."
            ),
        )

        def analyze_image(e):
            try:
                path = (image_path.value or "").strip()

                if not path:
                    raise ValueError(
                        "اختر صورة أو أدخل مسارها أولاً."
                    )

                result = analyze_leaf_image(path)

                result_box.bgcolor = ft.Colors.GREEN_50

                result_box.content = ft.Column(
                    [
                        ft.Text(
                            result["diagnosis"],
                            size=17,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            f"المناطق الخضراء: {result['green']}%"
                        ),
                        ft.Text(
                            f"المناطق الصفراء: {result['yellow']}%"
                        ),
                        ft.Text(
                            f"المناطق البنية: {result['brown']}%"
                        ),
                        ft.Text(
                            result["advice"],
                            size=13,
                            color=ft.Colors.GREY_800,
                        ),
                    ],
                    spacing=6,
                )

                page.update()

            except Exception as ex:
                result_box.bgcolor = ft.Colors.RED_50

                result_box.content = ft.Text(
                    f"تعذر تحليل الصورة:\n{ex}",
                    color=ft.Colors.RED_800,
                    selectable=True,
                )

                page.update()

        controls = [
            image_path,
            ft.Row(
                [
                    ft.OutlinedButton(
                        "اختيار صورة",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=lambda e: file_picker.pick_files(
                            allow_multiple=False,
                            file_type=ft.FilePickerFileType.IMAGE,
                        ),
                    ),
                    ft.ElevatedButton(
                        "تحليل الصورة",
                        icon=ft.Icons.SEARCH,
                        on_click=analyze_image,
                    ),
                ],
                wrap=True,
                spacing=10,
            ),
            result_box,
            ft.Text(
                "تنبيه: هذا التحليل يعتمد على نسب الألوان (RGB) فقط "
                "ولا يغني عن الفحص الزراعي المختص.",
                size=12,
                color=ft.Colors.GREY_700,
            ),
        ]

        show_screen(
            "تحليل صور الأوراق",
            "تقدير مبدئي للاصفرار والبقع البنية في الورقة",
            controls,
        )

    show_dashboard()


if __name__ == "__main__":
    ft.app(target=main)
