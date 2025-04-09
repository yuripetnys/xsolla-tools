from xsolla_api import XsollaProjectAPI
from xsolla_tools import recalculate_bundle

# x = XsollaProjectAPI("9fdc3741049b7d57b4a4c4a5829e5b1e98c2bc48", 281141)
# vc_pack = x.get_virtual_currency_package("gold_100")
# v_item = x.get_virtual_item("emerald-sword")
# game = x.get_game_by_sku("1621690_core_keeper")
# bundle = x.get_bundle("test-bundle")

recalculate_bundle("9fdc3741049b7d57b4a4c4a5829e5b1e98c2bc48", 281141, "test-bundle", 0.5)

print(": D")