import flet as ft
import sys
from pathlib import Path
from datetime import date
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

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

VALID_USER = "HUSIEN ALFARES"
VALID_PASS = "H99155729614a"


# =========================================================
# تحليل صورة الورقة باستخدام RGB
# =========================================================

def analyze_leaf_image(image_path: str) -> dict:
    img = Image.open(image_path).convert("RGB")
    img = img.resize((200, 200))

    pixels = list(img.getdata())
    total = len(pixels)

    healthy_green = 0
    yellow_stress = 0
    brown_necrosis = 0

    for r, g, b in pixels:
        if (r > 235 and g > 235 and b > 235) or (
            r < 20 and g < 20 and b < 20
        ):
            total -= 1
            continue

        if g > r * 1.12 and g > b * 1.15:
            healthy_green += 1
        elif r > 140 and g > 130 and b < 100:
            yellow_stress += 1
        elif r > g * 1.15 and r > b * 1.2 and g < 130:
            brown_necrosis += 1

    total = max(total, 1)

    green_pct = round(healthy_green / total * 100, 1)
    yellow_pct = round(yellow_stress / total * 100, 1)
    brown_pct = round(brown_necrosis / total * 100, 1)

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
        diagnosis = "لم تظهر نسبة مرتفعة من الاصفرار أو المناطق البنية"
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

    salinity_history = [2.1, 2.3, 2.8, 3.2, 2.9]

    # -----------------------------------------------------
    # أدوات مساعدة
    # -----------------------------------------------------

    def show_message(message, color=ft.Colors.GREEN_800):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=color,
        )
        page.snack_bar.open = True
        page.update()

    def make_field(label, value="", hint=""):
        return ft.TextField(
            label=label,
            value=value,
            hint_text=hint,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )

    def make_dropdown(label, options, value):
        return ft.Dropdown(
            label=label,
            options=[
                ft.dropdown.Option(key=k, text=v)
                for k, v in options
            ],
            value=value,
            expand=True,
        )

    def parse_number(field, label):
        try:
            return float(field.value.strip().replace(",", "."))
        except (ValueError, AttributeError):
            raise ValueError(f"أدخل قيمة رقمية صحيحة في حقل: {label}")

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
                ft.Text(subtitle, size=13, color=ft.Colors.GREY_700)
            )

        return ft.Column(controls, spacing=4)

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
                scroll=ft.ScrollMode.AUTO,
                expand=True,
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
                        f"{salinity_history[-1]}",
                        "آخر قيمة تجريبية",
                        ft.Icons.LANDSCAPE,
                    ),
                ],
                wrap=True,
                spacing=10,
            ),

            ft.Row(
                [
                    ft.Button(
                        "حساب الاحتياج المائي",
                        icon=ft.Icons.CALCULATE,
                        on_click=lambda e: show_irrigation(),
                    ),
                    ft.Button(
                        "تحليل صورة نبات",
                        icon=ft.Icons.CAMERA_ALT,
                        on_click=lambda e: show_image_analysis(),
                    ),
                ],
                wrap=True,
            ),

            ft.Button(
                "متابعة ملوحة التربة",
                icon=ft.Icons.SHOW_CHART,
                on_click=lambda e: show_salinity(),
            ),

            ft.Divider(),

            ft.Text(
                "ملاحظة: القيم المعروضة في لوحة القيادة ليست قراءات "
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
            "أدخل الرطوبة الحجمية المقاسة",
        )

        rainfall = make_field(
            "الأمطار اليومية (ملم)",
            "0",
        )

        tmin = make_field("درجة الحرارة الصغرى °C", "18")
        tmax = make_field("درجة الحرارة العظمى °C", "32")
        humidity = make_field("الرطوبة النسبية المتوسطة (%)", "40")
        wind = make_field("سرعة الرياح (متر/ثانية)", "2")

        latitude = make_field(
            "خط العرض",
            "",
            "أدخل إحداثيات موقع الحقل",
        )

        elevation = make_field(
            "ارتفاع الحقل عن سطح البحر (متر)",
            "",
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

                moisture_value = parse_number(
                    moisture,
                    "رطوبة التربة",
                )

                # تحويل النسبة المئوية إلى كسر عشري عند الحاجة
                if moisture_value > 1:
                    moisture_value = moisture_value / 100

                rain_value = parse_number(
                    rainfall,
                    "الأمطار",
                )

                tmin_value = parse_number(tmin, "الحرارة الصغرى")
                tmax_value = parse_number(tmax, "الحرارة العظمى")
                humidity_value = parse_number(humidity, "الرطوبة")
                wind_value = parse_number(wind, "سرعة الرياح")
                latitude_value = parse_number(latitude, "خط العرض")
                elevation_value = parse_number(elevation, "ارتفاع الحقل")
                solar_value = parse_number(solar, "الإشعاع الشمسي")
                water_ec_value = parse_number(water_ec, "ملوحة مياه الري")
                area_value = parse_number(area, "مساحة الحقل")
                progress_value = parse_number(progress, "تقدم مرحلة النمو")

                soil_ec_value = (
                    parse_number(soil_ec, "ملوحة التربة")
                    if soil_ec.value.strip()
                    else None
                )

                if not 0 < moisture_value <= 1:
                    raise ValueError(
                        "رطوبة التربة يجب أن تكون أكبر من صفر وحتى 100%."
                    )

                if rain_value < 0:
                    raise ValueError("الأمطار لا يمكن أن تكون سالبة.")

                if tmin_value > tmax_value:
                    raise ValueError(
                        "الحرارة الصغرى لا يمكن أن تكون أكبر من العظمى."
                    )

                if not 0 <= humidity_value <= 100:
                    raise ValueError(
                        "الرطوبة النسبية يجب أن تكون بين 0 و100."
                    )

                if wind_value < 0 or solar_value < 0:
                    raise ValueError(
                        "الرياح والإشعاع الشمسي لا يمكن أن يكونا سالبين."
                    )

                if not -90 <= latitude_value <= 90:
                    raise ValueError("خط العرض يجب أن يكون بين -90 و90.")

                if area_value <= 0:
                    raise ValueError("مساحة الحقل يجب أن تكون أكبر من صفر.")

                if not 0 <= progress_value <= 1:
                    raise ValueError(
                        "تقدم مرحلة النمو يجب أن يكون بين 0 و1."
                    )

                if water_ec_value < 0:
                    raise ValueError("ملوحة المياه لا يمكن أن تكون سالبة.")

                if soil_ec_value is not None and soil_ec_value < 0:
                    raise ValueError("ملوحة التربة لا يمكن أن تكون سالبة.")

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
                    warnings_text = "\n\nتحذيرات:\n" + "\n".join(
                        f"• {warning.ar}"
                        for warning in recommendation.warnings
                    )

                summary_text = recommendation.summary.ar

                output = (
                    f"{summary_text}\n\n"
                    f"ET0: {recommendation.et0_mm:.2f} ملم/يوم\n"
                    f"ETc: {recommendation.etc_mm:.2f} ملم/يوم\n"
                    f"عمق الري الصافي: {recommendation.net_depth_mm:.2f} ملم\n"
                    f"عمق الري الإجمالي: {recommendation.gross_depth_mm:.2f} ملم\n"
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

            ft.Button(
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

        history_text = ft.Text(
            "القراءات المسجلة:\n"
            + "\n".join(
                f"{i + 1}. {value} dS/m"
                for i, value in enumerate(salinity_history)
            ),
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

                latest_text.value = f"آخر قراءة: {value} dS/m"

                history_text.value = (
                    "القراءات المسجلة:\n"
                    + "\n".join(
                        f"{i + 1}. {reading} dS/m"
                        for i, reading in enumerate(salinity_history)
                    )
                )

                page.update()

            except Exception as ex:
                show_message(str(ex), ft.Colors.RED_800)

        controls = [
            latest_text,
            ec_input,

            ft.Button(
                "إضافة قراءة",
                icon=ft.Icons.ADD,
                on_click=add_reading,
            ),

            ft.Divider(),

            history_text,

            ft.Text(
                "هذه القراءات محفوظة في ذاكرة الجلسة الحالية فقط. "
                "لم يتم ربطها بعد بقاعدة بيانات دائمة.",
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
            expand=True,
        )

        result_box = ft.Container(
            padding=15,
            border_radius=12,
            bgcolor=ft.Colors.GREEN_50,
            content=ft.Text(
                "أدخل مسار الصورة ثم اضغط تحليل الصورة."
            ),
        )

        def analyze_image(e):

            try:
                path = image_path.value.strip()

                if not path:
                    raise ValueError("أدخل مسار الصورة أولاً.")

                if not Path(path).is_file():
                    raise ValueError(
                        "لم يتم العثور على الصورة في المسار المحدد."
                    )

                result = analyze_leaf_image(path)

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
                        ft.Divider(),
                        ft.Text(
                            "التوصية الأولية:",
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(result["advice"]),
                    ],
                    spacing=8,
                )

                page.update()

            except Exception as ex:
                result_box.content = ft.Text(
                    f"تعذر تحليل الصورة:\n{ex}",
                    color=ft.Colors.RED_800,
                )
                page.update()

        controls = [
            ft.Text(
                "تحليل الألوان في صورة الورقة",
                size=16,
                weight=ft.FontWeight.BOLD,
            ),

            image_path,

            ft.Button(
                "تحليل الصورة",
                icon=ft.Icons.CAMERA_ALT,
                on_click=analyze_image,
            ),

            result_box,

            ft.Text(
                "ملاحظة: هذه أداة تحليل ألوان RGB وليست نموذج ذكاء "
                "اصطناعي مدرباً على تشخيص الأمراض. النتائج استرشادية فقط.",
                size=12,
                color=ft.Colors.GREY_700,
            ),
        ]

        show_screen(
            "تحليل صور النباتات",
            "تحليل أولي للألوان الخضراء والصفراء والبنية",
            controls,
        )

    # =====================================================
    # تسجيل الدخول
    # =====================================================

    def show_login():

        username = ft.TextField(
            label="اسم المستخدم",
            prefix_icon=ft.Icons.PERSON,
        )

        password = ft.TextField(
            label="كلمة المرور",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK,
        )

        def login(e):

            if (
                username.value.strip() == VALID_USER
                and password.value == VALID_PASS
            ):
                show_dashboard()
            else:
                show_message(
                    "اسم المستخدم أو كلمة المرور غير صحيحة.",
                    ft.Colors.RED_800,
                )

        page.clean()

        page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Container(
                    width=420,
                    padding=25,
                    border_radius=18,
                    bgcolor=ft.Colors.GREEN_50,
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.AGRICULTURE,
                                size=65,
                                color=ft.Colors.GREEN_800,
                            ),

                            ft.Text(
                                "جزيرة الزراعي",
                                size=25,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREEN_900,
                            ),

                            ft.Text(
                                "نظام الإدارة والتحليل الزراعي الذكي",
                                size=13,
                            ),

                            ft.Divider(),

                            username,
                            password,

                            ft.Button(
                                "تسجيل الدخول",
                                icon=ft.Icons.LOGIN,
                                on_click=login,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15,
                    ),
                ),
            )
        )

        page.update()

    # بدء التطبيق
    show_login()


# =========================================================
# تشغيل التطبيق
# =========================================================

if __name__ == "__main__":
    ft.app(target=main)
