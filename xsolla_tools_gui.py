import flet as ft
import re, sys, configparser, os
from xsolla_tools import generate_keys, generate_qrcode, import_from_steam, delete_game, publish_launcher_build, recalculate_bundle, update_prices

class XsollaTool():
    def __init__(self):
        pass

TERMINAL = None

class StdoutRedirector:
    progress_bar_regex = r"\[\=*\s*\] % \d{1,3}\.\d{2}"
    links_regex = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'

    def __init__(self) -> None:
        self.last_line = ""

    def write(self, text) -> None:
        if text.strip():
            stripped_text = text.strip()
            if re.match(self.progress_bar_regex, self.last_line) and re.match(self.progress_bar_regex, text):
                TERMINAL.controls.pop()
            self.last_line = stripped_text

            text_e = ft.Text(font_family="DroidSansMono")
            split_text = re.split(self.links_regex, stripped_text)
            for t in split_text:
                if re.match(self.links_regex, t):
                    text_e.spans.append(ft.TextSpan(
                        t,
                        url=t,
                        style=ft.TextStyle(
                            decoration=ft.TextDecoration.UNDERLINE,
                            decoration_color="lightblue",
                            color="lightblue"
                        )
                    ))
                else:
                    text_e.spans.append(ft.TextSpan(
                        t,
                        style=ft.TextStyle(color="white")
                    ))

            TERMINAL.controls.append(text_e)
            TERMINAL.update()

    def flush(self) -> None:
        pass
sys.stdout = StdoutRedirector()

CONFIG = None
CONFIG_FN = "xsolla_tools_gui.ini"
def init_config() -> None:
    global CONFIG
    CONFIG = configparser.ConfigParser()
    
    if os.path.exists(CONFIG_FN):
        CONFIG.read(CONFIG_FN)
    else:
        CONFIG.add_section("settings")
        with open(CONFIG_FN, mode="w", encoding="utf_8") as f:
            CONFIG.write(f)

def get_config(key: str) -> str | None:
    return CONFIG.get("settings", key, fallback=None)

def set_config(key: str, value: str) -> None:
    CONFIG.set("settings", key, value)
    with open(CONFIG_FN, mode="w", encoding="utf_8") as f:
        CONFIG.write(f)

def print_link(text: str, url: str) -> None:
    e = ft.Text(
        spans=[ft.TextSpan(
            text,
            url=url,
            style=ft.TextStyle(
                decoration=ft.TextDecoration.UNDERLINE,
                decoration_color="lightblue",
                color="lightblue",
                font_family="DroidSansMono")
            )
        ],
    )
    TERMINAL.controls.append(e)
    TERMINAL.update()

def import_from_steam_modal_confirm(page, modal, api_key, project_id, steam_app_ids):
    page.close(modal)
    for id in steam_app_ids:
        import_from_steam(api_key, project_id, id)

def import_from_steam_button_click(page: ft.Page, c: ft.Column, rail: ft.NavigationRail):
    api_key = c.controls[2].value
    project_id = c.controls[3].value
    steam_app_ids: str = c.controls[4].controls[0].value
    steam_app_ids = steam_app_ids.replace(" ","").split(",")

    rail.disabled = True
    c.disabled = True
    if len(steam_app_ids) == 1:
        import_from_steam(api_key, project_id, steam_app_ids[0])
    else:
        modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmation"),
            content=ft.Text(f"Do you want to import {len(steam_app_ids)} Steam games into this project?"),
            actions_alignment=ft.MainAxisAlignment.END
        )
        modal.actions = [
            ft.TextButton("Yes", on_click=lambda e: import_from_steam_modal_confirm(page, modal, api_key, project_id, steam_app_ids)),
            ft.TextButton("No", on_click=lambda e: page.close(modal))
        ]
        rail.page.open(modal)

    rail.disabled = False
    c.disabled = False
    rail.update()
    c.update()

def delete_game_modal_confirm(page, modal, api_key, project_id, ids) -> None:
    page.close(modal)
    for id in ids:
        delete_game(api_key, project_id, id)

def delete_game_button_click(page: ft.Page, c: ft.Column, rail: ft.NavigationRail):
    api_key = c.controls[2].value
    project_id = c.controls[3].value
    game_skus = c.controls[4].controls[0].value
    game_skus = game_skus.replace(" ","").split(",")

    rail.disabled = True
    c.disabled = True

    if len(game_skus) == 1:
        delete_game(api_key, project_id, game_skus[0])
    else:
        modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmation"),
            content=ft.Text(f"Do you want to delete {len(game_skus)} SKUs?"),
            actions_alignment=ft.MainAxisAlignment.END
        )
        modal.actions = [
            ft.TextButton("Yes", on_click=lambda e: delete_game_modal_confirm(page, modal, api_key, project_id, game_skus)),
            ft.TextButton("No", on_click=lambda e: page.close(modal))
        ]
        rail.page.open(modal)
    
    rail.disabled = False
    c.disabled = False
    rail.update()
    c.update()
    
def update_prices_button_click(c: ft.Column, rail: ft.NavigationRail) -> None:
    api_key = c.controls[2].value
    project_id = c.controls[3].value
    game_sku = c.controls[4].controls[0].value
    steam_app_id = c.controls[4].controls[1].value

    rail.disabled = True
    c.disabled = True

    update_prices(api_key, project_id, game_sku, steam_app_id)
    
    rail.disabled = False
    c.disabled = False
    rail.update()
    c.update()

def recalculate_bundle_modal_confirm(page: ft.Page, modal: ft.AlertDialog, api_key: str, project_id: str, bundle_skus: list[str], discount: float):
    page.close(modal)
    for sku in bundle_skus:
        recalculate_bundle(api_key, project_id, sku, discount)

def recalculate_bundle_button_click(page: ft.Page, c: ft.Column, rail: ft.NavigationRail) -> None:
    api_key = c.controls[2].value
    project_id = c.controls[3].value
    bundle_skus = c.controls[4].controls[0].value
    try:
        discount_input_value = c.controls[4].controls[1].value
        discount = float(discount_input_value)
        if discount > 99 or discount < 0:
            raise Exception()
        discount = discount / 100
    except:
        print("Invalid discount value. Please insert a real number from 0 to 100.")
        return

    bundle_skus = bundle_skus.replace(" ","").split(",")

    rail.disabled = True
    c.disabled = True
    if len(bundle_skus) == 1:
        recalculate_bundle(api_key, project_id, bundle_skus[0], discount)
    else:
        modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmation"),
            content=ft.Text(f"Do you want to recalculate prices for {len(bundle_skus)} bundles?"),
            actions_alignment=ft.MainAxisAlignment.END
        )
        modal.actions = [
            ft.TextButton("Yes", on_click=lambda e: recalculate_bundle_modal_confirm(page, modal, api_key, project_id, bundle_skus, discount)),
            ft.TextButton("No", on_click=lambda e: page.close(modal))
        ]
        rail.page.open(modal)

    rail.disabled = False
    c.disabled = False
    rail.update()
    c.update()

def publish_launcher_build_button_click(page: ft.Page, c: ft.Column, rail: ft.NavigationRail) -> None:
    launcher_key = c.controls[2].value
    game_folder_path = c.controls[3].controls[0].value
    build_loader_path = c.controls[3].controls[2].value
    build_description = c.controls[4].controls[0].value
    set_as_value = c.controls[4].controls[1].value
    
    rail.disabled = True
    c.disabled = True

    publish_launcher_build(launcher_key, game_folder_path, build_loader_path, build_description, set_as_value)
    
    rail.disabled = False
    c.disabled = False
    rail.update()
    c.update()

def generate_keys_button_click(page: ft.Page, c: ft.Column, rail: ft.NavigationRail) -> None:
    try:
        num_of_keys = int(c.controls[2].controls[0].value)
    except:
        print("Error - invalid number of keys")
        return

    rail.disabled = True
    c.disabled = True

    def fp_on_result(e: ft.FilePickerResultEvent) -> None:
        if e.path:
            generate_keys(e.path, num_of_keys)

    fp = ft.FilePicker(on_result=fp_on_result)
    page.overlay.append(fp)
    page.update()
    fp.save_file(dialog_title="Select where you want to save the keys", allowed_extensions=["csv", "txt"])
    
    rail.disabled = False
    c.disabled = False
    rail.update()
    c.update()

def generate_qrcode_button_click(page: ft.Page, c: ft.Column, rail: ft.NavigationRail) -> None:
    project_id = c.controls[2].controls[0].value
    sku = c.controls[2].controls[1].value
    sku_type = c.controls[2].controls[1].value

    rail.disabled = True
    c.disabled = True

    def fp_on_result(e: ft.FilePickerResultEvent) -> None:
        if e.path:
            if e.path[-4:] != ".png":
                e.path = e.path + ".png"
            generate_qrcode(project_id, sku, sku_type, e.path)
    fp = ft.FilePicker(on_result=fp_on_result)
    page.overlay.append(fp)
    page.update()
    fp.save_file(dialog_title="Select where you want the QR Code image", allowed_extensions=["png"])

    rail.disabled = False
    c.disabled = False
    rail.update()
    c.update()

def activate_page(content_column, control):
    section = control.destinations[control.selected_index].data
    content_column.controls.pop()
    content_column.controls.append(section)
    content_column.update()

def main(page: ft.Page):
    global TERMINAL
    TERMINAL = ft.Column(expand=True, auto_scroll=True, scroll=ft.ScrollMode.ALWAYS, alignment=ft.VerticalAlignment.START)
    
    init_config()

    page.fonts = { "DroidSansMono": "/fonts/DroidSansMono.ttf" }
    page.title = "Xsolla Tools"
    page.vertical_alignment = ft.MainAxisAlignment.START
    
    api_key_field = ft.TextField(label="Xsolla API Key", password=True, can_reveal_password=True)
    project_id_field = ft.TextField(label="Xsolla Project ID")
    rail = None

    import_from_steam_column = ft.Column([
        ft.Text("Import game from Steam", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        ft.Text("Quickly imports a Steam game as a SKU onto a Xsolla PA project", theme_style=ft.TextThemeStyle.LABEL_LARGE),
        api_key_field,
        project_id_field,
        ft.Row([
            ft.TextField(label="Steam App IDs (separated by comma)"),
            ft.Button(text="Import", on_click=lambda e: import_from_steam_button_click(page, import_from_steam_column, rail))
        ])
    ], expand=True, alignment=ft.MainAxisAlignment.START)

    delete_game_column = ft.Column([
        ft.Text("Delete SKU", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        ft.Text("Deletes one or more SKUs from a specific project. Please ensure that all keys have been removed before deleting it.", theme_style=ft.TextThemeStyle.LABEL_LARGE),
        api_key_field,
        project_id_field,
        ft.Row([            
            ft.TextField(label="Xsolla Game SKUs (separated by comma)"),
            ft.Button(text="Delete", on_click=lambda e: delete_game_button_click(page, delete_game_column, rail))
        ])
    ], expand=True, alignment=ft.MainAxisAlignment.START)

    update_prices_column = ft.Column([
        ft.Text("Update prices from Steam", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        ft.Text("Applies new prices to a SKU based on its pricing on Steam.", theme_style=ft.TextThemeStyle.LABEL_LARGE),
        api_key_field,
        project_id_field,
        ft.Row([
            ft.TextField(label="Game SKU"),
            ft.TextField(label="Steam App ID"),        
            ft.Button(text="Update", on_click=lambda e: update_prices_button_click(update_prices_column, rail))
        ])
    ], expand=True, alignment=ft.MainAxisAlignment.START)

    publish_launcher_game_folder_field = ft.TextField(label="Game folder path", disabled=True, expand=3)
    publish_launcher_build_loader_field = ft.TextField(label="build_loader.exe path", disabled=True, expand=3)
    publish_launcher_build_loader_field.value = get_config("build_loader")
    def publish_launcher_game_folder_file_picker_on_result(e: ft.FilePickerResultEvent) -> None:
        publish_launcher_game_folder_field.value = e.path
        publish_launcher_game_folder_field.update()
    def publish_launcher_build_loader_file_picker_on_result(e: ft.FilePickerResultEvent) -> None:
        if e.files:
            set_config("build_loader", e.files[0].path)
            publish_launcher_build_loader_field.value = e.files[0].path
            publish_launcher_build_loader_field.update()
    publish_launcher_game_folder_file_picker = ft.FilePicker(on_result=publish_launcher_game_folder_file_picker_on_result)
    publish_launcher_build_loader_file_picker = ft.FilePicker(on_result=publish_launcher_build_loader_file_picker_on_result)
    page.overlay.append(publish_launcher_game_folder_file_picker)
    page.overlay.append(publish_launcher_build_loader_file_picker)
    
    publish_launcher_build_column = ft.Column([
        ft.Text("Publish build on Launcher", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        ft.Text("Provides a graphical interface for the build_loader.exe utility, publishing new builds on Launcher.", theme_style=ft.TextThemeStyle.LABEL_LARGE),
        
        ft.TextField(label="Launcher API Key", password=True, can_reveal_password=True),
        ft.Row([
            publish_launcher_game_folder_field,
            ft.Button(text="Browse...", expand=1, on_click=lambda e: publish_launcher_game_folder_file_picker.get_directory_path(dialog_title="Select the directory where the game build is located...")),
            publish_launcher_build_loader_field,
            ft.Button(text="Browse...", expand=1, on_click=lambda e: publish_launcher_build_loader_file_picker.pick_files(dialog_title="Select the location of the build_loader.exe executable...", allow_multiple=False))
        ]),
        ft.Row([
            ft.TextField(label="Build description", expand=3),
            ft.Dropdown(editable=True, label="Set build as...", options=[
                ft.DropdownOption(key="", text="(None)"),
                ft.DropdownOption(key="draft", text="Draft"),
                ft.DropdownOption(key="published", text="Published")
            ], expand=3),
            ft.Button(text="Upload build", on_click=lambda e: publish_launcher_build_button_click(page, publish_launcher_build_column, rail), expand=1)
        ]),
    ], expand=True, alignment=ft.MainAxisAlignment.START)

    generate_keys_column = ft.Column([
        ft.Text("Generate Launcher keys", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        ft.Text("Generates random Launcher keys for DRM-free SKUs.", theme_style=ft.TextThemeStyle.LABEL_LARGE),
        ft.Row([            
            ft.TextField(label="Number of keys"),
            ft.Button(text="Generate", on_click=lambda e: generate_keys_button_click(page, generate_keys_column, rail))
        ])
    ], expand=True, alignment=ft.MainAxisAlignment.START)

    recalculate_bundle_column = ft.Column([
        ft.Text("Recalculate bundle prices", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        ft.Text("Calculates bundle pricing as the sum of the prices of the items included in it. Pricing is provided for a certain currency only if all included items also provide individual prices for said currency.", theme_style=ft.TextThemeStyle.LABEL_LARGE),
        api_key_field,
        project_id_field,
        ft.Row([            
            ft.TextField(label="Bundle SKUs (separated by comma)"),
            ft.TextField(label="Discount (in %)", value="0"),
            ft.Button(text="Recalculate", on_click=lambda e: recalculate_bundle_button_click(page, recalculate_bundle_column, rail))
        ])
    ], expand=True, alignment=ft.MainAxisAlignment.START)

    generate_qrcode_column = ft.Column([
        ft.Text("Generate QR Codes for PayStation", theme_style=ft.TextThemeStyle.TITLE_LARGE),
        ft.Text("Generates QR Codes that can be published on social media or printed at events, sending users directly to a checkout page for a game key. Only works with game keys since they don't require Login.", theme_style=ft.TextThemeStyle.LABEL_LARGE),
        ft.Row([
            ft.TextField(label="Project ID", expand=3),
            ft.TextField(label="Game key SKU", expand=3),
            ft.Dropdown(editable=True, label="SKU Type", options=[
                ft.DropdownOption(key="game", text="Game"),
                ft.DropdownOption(key="bundle", text="Bundle")
            ], expand=3),
            ft.Button(text="Generate", on_click=lambda e: generate_qrcode_button_click(page, generate_qrcode_column, rail), expand=1)
        ])
    ], expand=True, alignment=ft.MainAxisAlignment.START)

    test_terminal_column = ft.Column([
        ft.Text("Delete game"),
        ft.Button(text="Test Terminal", on_click=lambda e: print("This is https://Zombo.com"))
    ], expand=True, alignment=ft.MainAxisAlignment.START)

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        width=200,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.IMPORT_EXPORT,
                selected_icon=ft.Icons.IMPORT_EXPORT_OUTLINED,
                label="Import game from Steam",
                data=import_from_steam_column
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.PRICE_CHANGE,
                selected_icon=ft.Icons.PRICE_CHANGE_OUTLINED,
                label="Update prices from Steam",
                data=update_prices_column
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DELETE,
                selected_icon=ft.Icons.DELETE_OUTLINED,
                label="Delete SKU",
                data=delete_game_column
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.CALCULATE,
                selected_icon=ft.Icons.CALCULATE_OUTLINED,
                label="Calculate bundle prices",
                data=recalculate_bundle_column
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ROCKET_LAUNCH,
                selected_icon=ft.Icons.ROCKET_LAUNCH_OUTLINED,
                label="Submit Launcher build",
                data=publish_launcher_build_column
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.VPN_KEY,
                selected_icon=ft.Icons.VPN_KEY_OUTLINED,
                label="Generate Launcher gamekeys",
                data=generate_keys_column
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.QR_CODE,
                selected_icon=ft.Icons.QR_CODE,
                label="Generate PayStation QR",
                data=generate_qrcode_column
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.VPN_KEY,
                selected_icon=ft.Icons.VPN_KEY_OUTLINED,
                label="Test terminal",
                data=test_terminal_column
            ),
        ],
        on_change=lambda e: activate_page(input_column, e.control),
    )

    input_column = ft.Column([ import_from_steam_column ], alignment=ft.MainAxisAlignment.START)

    page.add(ft.Row([
        rail,
        ft.VerticalDivider(),
        ft.Column([
            input_column,
            ft.Divider(),
            ft.Container(TERMINAL, bgcolor="black", padding=10, border_radius=10, expand=True, alignment=ft.alignment.top_left)
        ], expand=True)
    ], expand=True))

if __name__ == "__main__":
    ft.app(main, assets_dir="assets")
