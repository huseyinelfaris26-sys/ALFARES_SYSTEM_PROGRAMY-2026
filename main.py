import flet as ft


def main(page: ft.Page):
    page.title = "JaziraAgri OS"
    page.padding = 24
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    counter = ft.Text(
        value="0",
        size=48,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.BLUE,
    )

    def increment(event: ft.Event[ft.FilledButton]) -> None:
        counter.value = str(int(counter.value or "0") + 1)
        page.update()

    def reset(event: ft.Event[ft.TextButton]) -> None:
        counter.value = "0"
        page.update()

    page.appbar = ft.AppBar(
        title=ft.Text("JaziraAgri OS"),
        bgcolor=ft.Colors.SURFACE_TINT,
        actions=[
            ft.IconButton(
                icon=ft.Icons.SETTINGS,
                tooltip="الإعدادات",
            )
        ],
    )

    page.add(
        ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=24,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.STAR),
                        ft.Text(
                            "JaziraAgri OS",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                ),
                counter,
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                    controls=[
                        ft.FilledButton(
                            text="زيادة",
                            icon=ft.Icons.ADD,
                            on_click=increment,
                        ),
                        ft.TextButton(
                            text="تصفير",
                            icon=ft.Icons.REFRESH,
                            on_click=reset,
                        ),
                    ],
                ),
                ft.Container(
                    content=ft.Text("تطبيق إدارة الزراعة"),
                    bgcolor=ft.Colors.AMBER_100,
                    padding=12,
                    border_radius=8,
                ),
            ],
        )
    )


if __name__ == "__main__":
    ft.run(main)
