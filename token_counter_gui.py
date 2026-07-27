import flet as ft
import tiktoken
from deep_translator import GoogleTranslator

FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/pressstart2p/PressStart2P-Regular.ttf"

enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def main(page: ft.Page):
    page.title = "Contador de Tokens"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.fonts = {"PressStart2P": FONT_URL}

    text_input = ft.TextField(
        multiline=True,
        min_lines=3,
        max_lines=6,
        hint_text="Ingresa el texto aqui...",
        text_style=ft.TextStyle(size=10, color=ft.colors.WHITE, font_family="PressStart2P"),
        border_color="#FF4444",
        focused_border_color="#FF6666",
        bgcolor="#1a0000",
        cursor_color="#FF4444",
        hint_style=ft.TextStyle(size=10, color="#FF444488", font_family="PressStart2P"),
    )

    dropdown = ft.Dropdown(
        options=[
            ft.dropdown.Option("ES -> EN"),
            ft.dropdown.Option("EN -> ES"),
        ],
        value="ES -> EN",
        text_style=ft.TextStyle(size=10, color=ft.colors.WHITE, font_family="PressStart2P"),
        bgcolor="#1a0000",
        border_color="#FF4444",
        focused_bgcolor="#2a0000",
    )

    original_text = ft.Text("", size=9, color="#FF8888", font_family="PressStart2P", selectable=True)
    translated_text = ft.Text("", size=9, color="#FF8888", font_family="PressStart2P", selectable=True)

    comparison_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("METRICA", size=10, color="#FF4444", font_family="PressStart2P")),
            ft.DataColumn(ft.Text("ORIGINAL", size=10, color="#FF4444", font_family="PressStart2P")),
            ft.DataColumn(ft.Text("TRADUCIDO", size=10, color="#FF4444", font_family="PressStart2P")),
            ft.DataColumn(ft.Text("DIFERENCIA", size=10, color="#FF4444", font_family="PressStart2P")),
        ],
        rows=[],
        border=ft.border.all(1, "#FF444433"),
        heading_row_color="#8B000033",
        heading_row_height=40,
        data_row_color={"": "#0d0000"},
        data_row_min_height=35,
    )

    def translate_action(e):
        text = text_input.value
        if not text.strip():
            return

        target = dropdown.value.split("->")[1].strip().lower()

        try:
            translator = GoogleTranslator(source="auto", target=target)
            translated = translator.translate(text)
        except Exception as ex:
            translated = f"[Error al traducir: {ex}]"

        orig_tokens = count_tokens(text)
        trans_tokens = count_tokens(translated)
        orig_chars = len(text)
        trans_chars = len(translated)

        diff_tokens = trans_tokens - orig_tokens
        diff_chars = trans_chars - orig_chars
        pct_tokens = (diff_tokens / orig_tokens * 100) if orig_tokens else 0
        pct_chars = (diff_chars / orig_chars * 100) if orig_chars else 0

        original_text.value = f"> Original: {text}"
        translated_text.value = f"> Traduccion: {translated}"

        tok_color = "#66FF66" if diff_tokens <= 0 else "#FF6666"
        char_color = "#66FF66" if diff_chars <= 0 else "#FF6666"

        comparison_table.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text("TOKENS", size=10, color="#FF4444", font_family="PressStart2P")),
                ft.DataCell(ft.Text(str(orig_tokens), size=10, color=ft.colors.WHITE, font_family="PressStart2P")),
                ft.DataCell(ft.Text(str(trans_tokens), size=10, color=ft.colors.WHITE, font_family="PressStart2P")),
                ft.DataCell(ft.Text(f"{diff_tokens:+d} ({pct_tokens:+.1f}%)", size=10, color=tok_color, font_family="PressStart2P")),
            ]),
            ft.DataRow(cells=[
                ft.DataCell(ft.Text("CHARS", size=10, color="#FF4444", font_family="PressStart2P")),
                ft.DataCell(ft.Text(str(orig_chars), size=10, color=ft.colors.WHITE, font_family="PressStart2P")),
                ft.DataCell(ft.Text(str(trans_chars), size=10, color=ft.colors.WHITE, font_family="PressStart2P")),
                ft.DataCell(ft.Text(f"{diff_chars:+d} ({pct_chars:+.1f}%)", size=10, color=char_color, font_family="PressStart2P")),
            ]),
        ]
        page.update()

    button = ft.ElevatedButton(
        "TRADUCIR",
        on_click=translate_action,
        style=ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor="#8B0000",
            overlay_color="#FF2222",
            text_style=ft.TextStyle(size=11, font_family="PressStart2P"),
            shape=ft.RoundedRectangleBorder(radius=4),
        ),
    )

    page.add(
        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("CONTADOR DE TOKENS", size=16, color="#FF4444", font_family="PressStart2P"),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(bottom=20),
                ),
                text_input,
                ft.Row([dropdown, button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color="#FF444433", height=20),
                original_text,
                translated_text,
                ft.Divider(color="#FF444433", height=10),
                ft.Container(content=comparison_table, alignment=ft.alignment.center),
            ], scroll=ft.ScrollMode.AUTO),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=["#8B0000", "#4A0000", "#000000"],
            ),
            padding=30,
            expand=True,
        )
    )


ft.app(target=main)
