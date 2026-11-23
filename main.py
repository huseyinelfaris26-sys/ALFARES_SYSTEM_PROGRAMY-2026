import flet as ft
import sys
from pathlib import Path
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from jazira_agri.ui.data_bridge import get_regions, get_crops, get_soil_profiles, get_diseases

VALID_USER = "HUSIEN ALFARES"
VALID_PASS = "H99155729614a"


def analyze_leaf_image(image_path: str) -> dict:
    """تحليل طيفي محلي (RGB) لصورة ورقة النبات دون إنترنت باستخدام Pillow."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize((200, 200))
    pixels = list(img.getdata())
    total = len(pixels)

    healthy_green = 0
    yellow_stress = 0
    brown_necrosis = 0

    for r, g, b in pixels:
        # تجاهل الخلفيات البيضاء أو السوداء الساطعة
        if (r > 235 and g > 235 and b > 235) or (r < 20 and g < 20 and b < 20):
            total -= 1
            continue
        if g > r * 1.12 and g > b * 1.15:
            healthy_green += 1
        elif r > 140 and g > 130 and b < 100:
            yellow_stress += 1
        elif r > g * 1.15 and r > b * 1.2 and g < 130:
            brown_necrosis += 1

    total = max(total, 1)
    green_pct = round((healthy_green / total) * 100, 1)
    yellow_pct = round((yellow_stress / total) * 100, 1)
    brown_pct = round((brown_necrosis / total) * 100, 1)

    if yellow_pct > 25:
        diagnosis = "اصفرار ملحوظ (احتمال نقص نيتروجين أو بداية إصابة بالصدأ الأصفر)"
        advice = "يُنصح بفحص الوجه السفلي للورقة للتأكد من بثور الصدأ، أو إضافة دفعة سماد يوريا/نترات متوازنة."
    elif brown_pct > 20:
        diagnosis = "تبقع بني / احتراق حواف (إجهاد ملوحة أو تبقع فطري)"
        advice = "تأكد من ملوحة مياه الري (EC) وقم بعمل رية غسيل خفيفة، أو استعمل مبيداً فطرياً وقائياً."
    else:
        diagnosis = "نسيج نباتي سليم ونشاط كلوروفيل جيد"
        advice = "استمر في برنامج الري الناقص الحالي وراقب رطوبة التربة بانتظام."

    return {
        "green": green_pct,
        "yellow": yellow_pct,
        "brown": brown_pct,
        "diagnosis": diagnosis,
        "advice": advice,
    }


def main(page: ft.Page):
    page.title = "JaziraAgri-OS | نظام الجزيرة الزراعي الذكي"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.GREEN_800,
        use_material3=True,
    )
    page.padding = 0

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
            content=ft.Text("تم حفظ البيانات محلياً في SQLite (وضع Offline-First نشط)"),
            bgcolor=ft.Colors.GREEN_800,
        )
        page.snack_bar.open = True
        page.update()

    # ==========================================
    # شاشة التطبيق الرئيسية (5 تبويبات متكاملة)
    # ==========================================
    def load_main_app():
        page.clean()

        # قائمة تخزين قراءات الملوحة للرسم البياني التفاعلي
        salinity_history = [2.1, 2.3, 2.8, 3.2, 2.9]

        # ------------------------------------------
        # 1. لوحة القيادة (Dashboard)
        # ------------------------------------------
        def build_dashboard():
            def stat_card(title, value, subtitle, icon, color):
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(icon, color=color, size=26),
                                    ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_800),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(value, size=21, weight=ft.FontWeight.BOLD, color=color),
                            ft.Text(subtitle, size=11, color=ft.Colors.GREY_700),
                        ],
                        spacing=5,
                    ),
                    padding=14,
                    border_radius=14,
                    bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.SURFACE),
                    width=168,
                )

            return ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Image(src="icon.png", width=48, height=48, border_radius=10),
                                        ft.Column(
                                            [
                                                ft.Text("مرحباً، HUSIEN ALFARES", size=17, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                                ft.Text("نظام الجزيرة الزراعي • حوض الفرات", size=12, color=ft.Colors.GREEN_100),
                                            ],
                                            spacing=2,
                                        ),
                                    ]
                                ),
                                ft.Divider(color=ft.Colors.GREEN_600),
                                ft.Row(
                                    [
                                        ft.Chip(label=ft.Text("وضع دون إنترنت: نشط", size=11), leading=ft.Icon(ft.Icons.OFFLINE_PIN, size=16)),
                                        ft.Chip(label=ft.Text("Edge AI Vision: جاهز", size=11), leading=ft.Icon(ft.Icons.CAMERA_ALT, size=16)),
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
                            colors=[ft.Colors.with_opacity(0.92, ft.Colors.GREEN_900), ft.Colors.with_opacity(0.88, ft.Colors.GREEN_700)],
                        ),
                    ),
                    ft.Text("مؤشرات المراقبة الميدانية", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            stat_card("توفير المياه", "32%", "خوارزمية الري الناقص", ft.Icons.WATER_DROP, ft.Colors.BLUE_700),
                            stat_card("ملوحة التربة (EC)", f"{salinity_history[-1]} dS/m", "آخر قراءة مسجلة", ft.Icons.LANDSCAPE, ft.Colors.AMBER_800),
                            stat_card("مؤشر الغطاء (NDVI)", "0.74", "نمو خضري ممتاز", ft.Icons.SATELLITE_ALT, ft.Colors.GREEN_700),
                            stat_card("البخر-نتح (ETc)", "5.8 مم/يوم", "معادلة Penman-Monteith", ft.Icons.WB_SUNNY, ft.Colors.ORANGE_700),
                        ],
                        wrap=True,
                        spacing=12,
                        run_spacing=12,
                    ),
                    ft.Text("الأدوات الذكية المتاحة", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        bgcolor=ft.Colors.with_opacity(0.92, ft.Colors.SURFACE),
                        border_radius=14,
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CAMERA_ALT, color=ft.Colors.TEAL_700),
                                    title=ft.Text("فحص أوراق النبات بالكاميرا (AI Vision)"),
                                    subtitle=ft.Text("تحليل الكلوروفيل والاصفرار والصدأ دون إنترنت"),
                                    trailing=ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=16),
                                    on_click=lambda _: switch_view(3),
                                ),
                                ft.Divider(height=1),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.SHOW_CHART, color=ft.Colors.AMBER_800),
                                    title=ft.Text("الرسوم البيانية لتملح التربة (EC)"),
                                    subtitle=ft.Text("تتبع تطور الملوحة ومعامل غسيل الأملاح"),
                                    trailing=ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=16),
                                    on_click=lambda _: switch_view(2),
                                ),
                                ft.Divider(height=1),
                                ft.ListTile(
                                    leading=ft.Icon(ft.Icons.CALCULATE, color=ft.Colors.GREEN_800),
                                    title=ft.Text("حاسبة الري الناقص الذكي"),
                                    subtitle=ft.Text("جدولة الري حسب المحصول ومرحلة النمو"),
                                    trailing=ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=16),
                                    on_click=lambda _: switch_view(1),
                                ),
                            ],
                        ),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=14,
            )

        # ------------------------------------------
        # 2. الري الناقص الذكي (Irrigation)
        # ------------------------------------------
        def build_irrigation():
            crops_list = get_crops()
            region_dd = ft.Dropdown(
                label="المنطقة الجغرافية",
                options=[ft.dropdown.Option(r) for r in get_regions()],
                value="تل أبيض",
                expand=True,
            )
