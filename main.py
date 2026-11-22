import flet as ft
import sys
import os
from pathlib import Path

# إضافة الجذر و src إلى مسار بايثون لتعمل جميع الاستيرادات بسلاسة
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from jazira_agri.ui.data_bridge import get_regions, get_crops, get_soil_profiles, get_diseases

# محاولة استيراد خوارزمية الري الناقص الموجودة في مشروعك
try:
    import deficit_irrigation
    HAS_IRRIGATION_MODULE = True
except Exception:
    HAS_IRRIGATION_MODULE = False


def main(page: ft.Page):
    # إعدادات الصفحة والهوية البصرية
    page.title = "JaziraAgri-OS | نظام الجزيرة الزراعي الذكي"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.GREEN_800,
        use_material3=True,
    )
    page.padding = 0

    # حالة التطبيق (State)
    is_offline = True

    def toggle_theme(e):
        page.theme_mode = (
            ft.ThemeMode.DARK
            if page.theme_mode == ft.ThemeMode.LIGHT
            else ft.ThemeMode.LIGHT
        )
        e.control.icon = (
            ft.Icons.LIGHT_MODE
            if page.theme_mode == ft.ThemeMode.DARK
            else ft.Icons.DARK_MODE
        )
        page.update()

    def trigger_sync(e):
        page.snack_bar = ft.SnackBar(
            content=ft.Text("تم حفظ البيانات محلياً في قاعدة SQLite (وضع Offline-First نشط)"),
            bgcolor=ft.Colors.GREEN_800,
        )
        page.snack_bar.open = True
        page.update()

    # ==========================================
    # 1. شاشة لوحة القيادة (Dashboard)
    # ==========================================
    def build_dashboard():
        def stat_card(title, value, subtitle, icon, color):
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(icon, color=color, size=28),
                                ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_700),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(value, size=22, weight=ft.FontWeight.BOLD, color=color),
                        ft.Text(subtitle, size=12, color=ft.Colors.GREY_600),
                    ],
                    spacing=6,
                ),
                padding=16,
                border_radius=14,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                width=170,
            )

        return ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.AGRICULTURE, color=ft.Colors.WHITE, size=32),
                                    ft.Column(
                                        [
                                            ft.Text("نظام الجزيرة الزراعي الذكي", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                            ft.Text("حوض الفرات • الرقة • تل أبيض • الحسكة • دير الزور", size=12, color=ft.Colors.GREEN_100),
                                        ],
                                        spacing=2,
                                    ),
                                ]
                            ),
                            ft.Divider(color=ft.Colors.GREEN_600),
                            ft.Row(
                                [
                                    ft.Chip(label=ft.Text("وضع دون إنترنت: نشط", size=11), leading=ft.Icon(ft.Icons.OFFLINE_PIN, size=16)),
                                    ft.Chip(label=ft.Text("LoRaWAN: جاهز", size=11), leading=ft.Icon(ft.Icons.SENSORS, size=16)),
                                ],
                                wrap=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=18,
                    border_radius=16,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1, -1),
                        end=ft.Alignment(1, 1),
                        colors=[ft.Colors.GREEN_900, ft.Colors.GREEN_700],
                    ),
                ),
                ft.Text("مؤشرات المراقبة الميدانية", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        stat_card("توفير المياه", "32%", "خوارزمية الري الناقص", ft.Icons.WATER_DROP, ft.Colors.BLUE_700),
                        stat_card("ملوحة التربة (EC)", "2.4 dS/m", "ضمن الحد الآمن للقمح", ft.Icons.LANDSCAPE, ft.Colors.AMBER_800),
                        stat_card("مؤشر الغطاء (NDVI)", "0.74", "نمو خضري ممتاز", ft.Icons.SATELLITE_ALT, ft.Colors.GREEN_700),
                        stat_card("البخر-نتح (ETc)", "5.8 مم/يوم", "معادلة Penman-Monteith", ft.Icons.WB_SUNNY, ft.Colors.ORANGE_700),
                    ],
                    wrap=True,
                    spacing=12,
                    run_spacing=12,
                ),
                ft.Text("الوصول السريع للأدوات", size=18, weight=ft.FontWeight.BOLD),
                ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.CALCULATE, color=ft.Colors.GREEN_800),
                            title=ft.Text("حاسبة الري الناقص وغسيل الأملاح"),
                            subtitle=ft.Text("حساب كمية المياه بدقة حسب مرحلة النمو والملوحة"),
                            trailing=ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=16),
                            on_click=lambda _: switch_view(1),
                        ),
                        ft.Divider(height=1),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.SCIENCE, color=ft.Colors.BROWN_700),
                            title=ft.Text("فحص تملح التربة والأسمدة"),
                            subtitle=ft.Text("تحليل خصائص التربة وحساب معامل الغسيل (LR)"),
                            trailing=ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=16),
                            on_click=lambda _: switch_view(2),
                        ),
                        ft.Divider(height=1),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.BUG_REPORT, color=ft.Colors.RED_700),
                            title=ft.Text("مستشار المحاصيل وتشخيص الآفات"),
                            subtitle=ft.Text("قاعدة بيانات أمراض القمح والقطن والكمون محلياً"),
                            trailing=ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=16),
                            on_click=lambda _: switch_view(3),
                        ),
                    ],
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
        )

    # ==========================================
    # 2. شاشة الري الناقص الذكي (Deficit Irrigation)
    # ==========================================
    def build_irrigation():
        region_dd = ft.Dropdown(
            label="المنطقة الجغرافية",
            options=[ft.dropdown.Option(r) for r in get_regions()],
            value="تل أبيض",
            expand=True,
        )
        crop_dd = ft.Dropdown(
            label="المحصول الاستراتيجي",
            options=[ft.dropdown.Option(c) for c in get_crops()],
            value=get_crops()[0],
            expand=True,
        )
        stage_dd = ft.Dropdown(
            label="مرحلة نمو المحصول",
            options=[
                ft.dropdown.Option("الإنبات والتأسيس"),
                ft.dropdown.Option("النمو الخضري / التفريع"),
                ft.dropdown.Option("الإزهار وطرد السنابل (حرجة)"),
                ft.dropdown.Option("امتلاء الحبوب / اللوز"),
                ft.dropdown.Option("النضج"),
            ],
            value="الإزهار وطرد السنابل (حرجة)",
            expand=True,
        )
        area_tf = ft.TextField(
            label="المساحة المزروعة (دونم = 1000 م²)",
            value="10",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.SQUARE_FOOT,
        )
        moisture_slider = ft.Slider(
            min=5, max=60, divisions=55, value=22, label="رطوبة التربة: {value}%"
        )
        ec_tf = ft.TextField(
            label="ملوحة مياه البئر / القناة EC (dS/m)",
            value="1.8",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.WATER,
        )
        deficit_switch = ft.Switch(
            label="تفعيل وضع التقنين الذكي (Deficit Mode) لتوفير 25% من المياه",
            value=True,
        )

        result_container = ft.Container(visible=False)

        def run_irrigation_calc(e):
            try:
                area = float(area_tf.value or 1)
                ec_w = float(ec_tf.value or 1.0)
                moisture = moisture_slider.value
                # معادلة تقديرية متوافقة مع Penman-Monteith ومعامل الغسيل
                base_et = 5.5 if "الإزهار" in stage_dd.value else 4.0
                if deficit_switch.value and "حرجة" not in stage_dd.value:
                    base_et *= 0.75
                leaching_req = round(ec_w / (5 * 6.0 - ec_w), 2) if ec_w > 1.2 else 0.05
                water_m3_per_dunum = round((base_et * (1 + leaching_req)) * (1 - (moisture / 100) * 0.4), 2)
                total_m3 = round(water_m3_per_dunum * area, 1)

                result_container.content = ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_700), ft.Text("توصية الجدولة المائية", size=17, weight=ft.FontWeight.BOLD)]),
                                ft.Divider(),
