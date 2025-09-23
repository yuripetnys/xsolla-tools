import subprocess, qrcode, csv
from ulid import ULID
from steam_api import _request_from_steam_storeapi as steam_request, retrieve_pricing_per_appid
from xsolla_api import XsollaProjectAPI
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask

###################

def _import_from_steam_generate_sku(games: str, game_info) -> str:
    valid_characters = "abcdefghijklmnopqrstuvwxyz_"
    fmt_name = "".join([c for c in game_info["name"].replace(" ", "_").lower() if c in valid_characters])
    main_sku = str(game_info["steam_appid"]) + "_" + fmt_name
    main_sku = main_sku[:130]

    games_sku = [g["sku"] for g in games]
    
    attempt = 1
    sku = main_sku
    while sku in games_sku:
        attempt = attempt + 1
        sku = main_sku + "_v" + str(attempt)
    return sku

def _import_from_steam_generate_payload(sku: str, game_info: str, prices) -> dict:
    payload = {}
    payload["sku"] = sku
    payload["name"] = {"en-US": game_info["name"]}
    payload["description"] = {"en-US": game_info["short_description"]}

    if len(payload["description"]["en-US"]) >= 255:
        payload["description"]["en-US"] = payload["description"]["en-US"][:250] + "(...)"

    payload["long_description"] = {"en-US": game_info["short_description"]}
    payload["is_enabled"] = True
    payload["is_free"] = False
    payload["is_show_in_store"] = True
    payload["image_url"] = game_info["header_image"]

    payload["unit_items"] = [{}]
    payload["unit_items"][0]["sku"] = f"{sku}_Steam"
    payload["unit_items"][0]["name"] = {"en-US": game_info["name"] + "_Steam"}
    payload["unit_items"][0]["drm_name"] = "Steam"
    payload["unit_items"][0]["drm_sku"] = "steam"
    payload["unit_items"][0]["prices"] = list([{"amount": prices[p], "currency": p, "is_enabled": True, "is_default": p == "USD"} for p in prices])

    return payload

def import_from_steam(api_key: str, project_id: str, steam_app_id: str) -> None:
    try:        
        print("Step 1: Retrieving game info from Steam...")
        game_info = steam_request(appid=steam_app_id)

        print("Step 2: Retrieving prices from Steam...")
        game_prices = retrieve_pricing_per_appid(appid=steam_app_id)

        print("Step 3: Retrieve games list from project...")
        x = XsollaProjectAPI(api_key, project_id)
        games = x.get_games()

        print("Step 4: Adding on Xsolla...")
        sku = _import_from_steam_generate_sku(games, game_info)
        p = _import_from_steam_generate_payload(sku, game_info, game_prices)
        x.create_game(p)

        print(f"Game {steam_app_id} imported successfully.")

    except Exception as e:
        print(f"Error: {e}")

###################

def delete_game(api_key: str, project_id: str, game_sku: str) -> None:
    try:        
        print(f"Deleting SKU {game_sku}...")
        x = XsollaProjectAPI(api_key, project_id)
        x.delete_game_by_sku(game_sku)
        print(f"SKU {game_sku} successfully deleted")

    except Exception as e:
        print(f"Error: {e}")

###################

def recalculate_bundle(api_key: str, project_id: str, bundle_sku: str, discount: float = 0) -> None:
    if discount < 0 or discount > 0.99:
        raise Exception("Invalid value. Discount must be a float between 0 and 1")
    
    x = XsollaProjectAPI(api_key, project_id)
    
    print("Step 1: Pulling bundle data...")
    bundle_data = x.get_bundle(bundle_sku)
    bundle_items = bundle_data["content"]
    bundle_price: dict = {}

    game_key_data_cache = []

    print("Step 2: Grabbing prices for individual bundle items...")
    for item in bundle_items:
        item_sku = item["sku"]
        item_qty = item["quantity"]

        print(f"Grabbing prices for SKU {item_sku}...")
        match item["type"]:
            case "virtual_good":
                item_prices = x.get_virtual_item(item_sku)["prices"]
                pass
            case "bundle":
                if item["bundle_type"] == "virtual_currency_package":
                    item_prices = x.get_virtual_currency_package(item_sku)["prices"]
                    pass
                elif item["bundle_type"] == "standard":
                    item_prices = x.get_bundle(item_sku)["prices"]
                    pass
            case "game_key":
                if not game_key_data_cache:
                    game_key_data_cache = x.get_games()
                item_prices = [i for g in game_key_data_cache for i in g["unit_items"] if i["sku"] == item_sku][0]["prices"]

        print(f"{item_sku}: {item_prices[0]["currency"]} {item_prices[0]["amount"]}")
        if not bundle_price:
            for price in item_prices:
                currency = price["currency"]
                bundle_price[currency] = price["amount"] * item_qty
        else:
            currency_list = list(bundle_price.keys())
            for currency in currency_list:
                item_currency_prices = [p for p in item_prices if p["currency"] == currency]
                if len(item_currency_prices) == 0:
                    print(f"WARNING: Unable to find pricing in {currency} for {item_sku}. Final pricing for bundle {bundle_sku} will not have pricing in {currency}.")
                    bundle_price.pop(currency)
                else:
                    bundle_price[currency] = bundle_price[currency] + item_currency_prices[0]["amount"] * item_qty

    for currency in bundle_price:
        bundle_price[currency] = round(bundle_price[currency] * (1 - discount), 2)
    
    print("Step 3: Submitting new prices to Xsolla...")
    bundle_price_fmt = [{
        "currency": c,
        "amount": bundle_price[c],
        "is_default": c == "USD",
        "is_enabled": True
        } for c in bundle_price]
    bundle_data["prices"] = bundle_price_fmt
    x.update_bundle(bundle_sku, bundle_data)
    print("Bundle prices updated successfully.")

###################

def update_prices(api_key: str, project_id: str, game_sku: str, steam_app_id: str) -> None:

    print("Step 1: Retrieving prices from Steam...")
    game_prices = retrieve_pricing_per_appid(steam_app_id)

    print("Step 2: Retrieving SKU data from Xsolla...")
    x = XsollaProjectAPI(api_key, project_id)
    game_info = x.get_game_by_sku(game_sku)

    print("Step 3: Apply new prices...")
    conv_game_prices = list([{
        "amount": game_prices[c],
        "currency": c,
        "is_default": c == "USD",
        "is_enabled": True
        } for c in game_prices])

    if "unit_items" in game_info:
        for item in game_info["unit_items"]:
            item["prices"] = conv_game_prices
    else:
        game_info["prices"] = conv_game_prices
    
    print("Step 3: Uploading new prices to Xsolla...")
    x.update_game_by_sku(game_sku, game_info)

    print("SKU prices updated successfully!")

###################

def _run_subprocess(args) -> int:
    try:
        sp = subprocess.Popen(args=args, stdout=subprocess.PIPE, text=True)
    except Exception as e:
        print(e)
        return 404
    
    while True:
        line = sp.stdout.readline()
        if line != "":
            print(line, end="")
        
        code = sp.poll()
        if code is not None:
            break
    return code

def publish_launcher_build(launcher_key, game_folder_path, build_loader_path, build_description, set_as_value) -> None:

    print(f"Step 1: Initializing build upload...")
    init_command = [build_loader_path, "--init", "--api-key", launcher_key, "--game-path", game_folder_path]
    code = _run_subprocess(init_command)
    if code != 0:
        print(f"init_command finished with error {code}")
        return

    print(f"Step 2: Starting build upload...")
    update_command = [build_loader_path, "--update", "--game-path", game_folder_path]
    if build_description:
        update_command.extend(["--descr", build_description])
    if set_as_value == "draft":
        update_command.append("--set-build-on-test")
    elif set_as_value == "published":
        update_command.append("--set-build-on-master")
    code = _run_subprocess(update_command)
    if code != 0:
        print(f"init_command finished with error {code}")
        return
    
    print(f"Build uploaded successfully!")

###################

def generate_keys(fn: str, num_of_keys: int):
    with open(fn, mode="w", encoding="utf_8") as f:
        for _ in range(num_of_keys):
            ulid = str(ULID())
            ulid = ulid[:6]+"-"+ulid[6:12]+"-"+ulid[12:19]+"-"+ulid[19:]
            f.write(ulid+"\n")
    print("f{num_of_keys} keys successfully generated at {fn}!")

###################

XSOLLA_MAGENTA = (255, 0, 91)
XSOLLA_PURPLE = (105,57,249)
XSOLLA_PALE_BLUE = (102,95,160)
XSOLLA_BLACK = (24,23,27)
XSOLLA_WHITE = (255,255,255)

def generate_qrcode(project_id, sku, sku_type, fn):
    URL = f"https://purchase.xsolla.com/pages/buy?type={sku_type}&project_id={project_id}&sku={sku}&ui_settings=eyJ0aGVtZSI6ICJkYXJrIn0"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(URL)
    qr.make_image(image_factory=StyledPilImage,color_mask=SolidFillColorMask(front_color=XSOLLA_MAGENTA,back_color=XSOLLA_WHITE),embeded_image_path="logo.png").save(fn)
    
###################

def export_gamekey_prices_to_csv(api_key: str, project_id: str, fn: str):
    x = XsollaProjectAPI(api_key, project_id)
    print(f"Getting gamekey price data for project {project_id}...")
    games = x.get_games()
    skus_with_prices = [[game, sku] for game in games for sku in game['unit_items'] if len(sku['prices']) > 0]
    currencies = sorted(list(set([price['currency'] for _, sku in skus_with_prices for price in sku['prices']])))

    print(f"Saving gamekey price data to {fn}...")
    with open(fn, mode="w", encoding="utf_8_sig", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(["SKU", "Sub-SKU", "Default"] + currencies)

        for game, sku in skus_with_prices:
            csv_line = []
            csv_line.append(game['sku'])
            csv_line.append(sku['sku'])
            csv_line.append([p['currency'] for p in sku['prices'] if p['is_default']][0])
            for c in currencies:
                p = [p['amount'] for p in sku['prices'] if p['currency'] == c]
                if len(p) == 1:
                    csv_line.append(p[0])
                elif len(p) == 0:
                    csv_line.append(None)
                else:
                    raise Exception("API error: returned two prices for the same currency??")
            csv_writer.writerow(csv_line)

    print(f"Done!")

def import_gamekey_prices_from_csv(api_key: str, project_id: str, fn: str):
    x = XsollaProjectAPI(api_key, project_id)

    print(f"Opening and parsing {fn}...")
    with open(fn, mode="r", encoding="utf_8_sig") as f:
        csv_reader = csv.reader(f)
        header = None
        skus = []
        for line in csv_reader:
            if header is None:
                header = line
            else:
                skus.append(line)

    currencies = header[3:]
    for sku in skus:
        game_name = sku[0]
        sku_name = sku[1]
        print(f"Parsing CSV data for {sku_name}...")
        default_currency = sku[2]
        amounts = sku[3:]
        if len(amounts) != len(currencies):
            raise Exception(f"Error parsing {sku_name} from {fn}. Number of prices and number of currencies do not match.")
        
        new_prices = [{
                'amount': float(a),
                'currency': c,
                'is_default': c == default_currency,
                'is_active': True
            } for a, c in zip(amounts, currencies) if a != '']

        print(f"Retrieving data for {sku_name}...")
        
        try:
            payload = x.get_game_by_sku(game_name)
        except Exception as e:
            print(str(e))
            return
        
        #dumb fixes
        if "periods" in payload and len(payload["periods"]) == 0:
            payload.pop("periods")    
        subsku_payload = [sku for sku in payload['unit_items'] if sku['sku'] == sku_name][0]
        subsku_payload['prices'] = new_prices
        print(f"Updating {sku_name} with new prices...")
        x.update_game_by_sku(game_name, payload)

    print(f"Done!")