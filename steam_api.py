import re
from time import sleep
import requests
from enum import Enum
from datetime import datetime, timedelta

def try_date_formats(date: str, date_formats: list[str]) -> datetime:
    for f in date_formats:
        try:
            return datetime.strptime(date, f)
        except:
            continue
    
    raise ValueError("String {} could not match any of these datetime formats: {}".format(date, date_formats))

class SteamAppType(Enum):
    unknown = 0
    game = 1
    dlc = 2
    music = 3
    video = 4
    mod = 5
    hardware = 6
    advertising = 7
    demo = 8
    movie = 9

    def __str__(self) -> str:
        return self.name

    def from_str(s: str) -> "SteamAppType":
        try:
            return SteamAppType[s]
        except:
            return SteamAppType.unknown


class SteamCompany():
    id: int = None
    name: str = ""

    def __init__(self, id: int=None, name: str="") -> None:
        self.id = id
        self.name = name
        pass

    def __str__(self) -> str:
        return "{}/{}".format(self.id, self.name)

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, __value: object) -> bool:
        return self.id == __value.id and self.name == __value.name

    def __hash__(self) -> int:
        return hash((self.id, self.name))

    def from_json(j: object) -> "SteamCompany":
        o = SteamCompany()
        o.name = j
        return o


class SteamCategory():
    id: int = None
    name: str = ""

    def __init__(self, id: int=None, name: str="") -> None:
        self.id = id
        self.name = name
        pass
    
    def __str__(self) -> str:
        return "{}/{}".format(self.id, self.name)
    
    def from_json(j: object) -> "SteamCategory":
        o = SteamCategory()
        o.id = j["id"]
        o.name = j["description"]
        return o
        

class SteamGenre():
    id: int = None
    name: str = ""

    def __init__(self, id: int=None, name: str="") -> None:
        self.id = id
        self.name = name
        pass

    def __str__(self) -> str:
        return "{}/{}".format(self.id, self.name)
    
    def from_json(j: object) -> "SteamGenre":
        o = SteamGenre()
        o.id = j["id"]
        o.name = j["description"]
        return o


class SteamAppStub(object):
    appid: int = None
    name: str = ""

    def __str__(self) -> str:
        return "{}/{}".format(self.appid, self.name)
    

    def from_db(db_obj: object) -> "SteamAppStub":
        o = SteamAppStub()
        o.appid = db_obj[0]
        o.name = db_obj[1]
        return o

    def from_json(j: object) -> "SteamAppStub":
        o = SteamAppStub()
        o.name = j["name"]
        o.appid = int(j["appid"])
        return o


class SteamApp(SteamAppStub):
    has_details: bool = True
    type: SteamAppType = SteamAppType.unknown
    release_date: datetime = ""
    website: str = ""
    support_url: str = ""
    support_email: str = ""
    released: bool = None
    is_free: bool = None
    required_age: int = None
    metacritic: int = None
    recommendations: int = None
    developers: list[SteamCompany] = []
    publishers: list[SteamCompany] = []
    categories: list[SteamCategory] = []
    genres: list[SteamGenre] = []

    def __str__(self) -> str:
        return "{}/{}/{}".format(self.appid, self.name, self.type)
    
    def from_json(j: object) -> "SteamApp":
        o = SteamApp()
        
        fields = [f for f in dir(o) if not callable(getattr(o, f)) and not f.startswith('__')]
        for f in fields:
            if f == "type":
                value = SteamAppType.from_str(j[f])
            elif f == "appid":
                value = j["steam_appid"]
            elif f in ["developers", "publishers"]:
                if f not in j:
                    value = None
                else:
                    value = [SteamCompany.from_json(i) for i in j[f]]
            elif f == "required_age":
                if isinstance(j[f], str):
                    try:
                        value = re.match(r"\d+", j[f])[0]
                    except:
                        value = None
                elif isinstance(j[f], int):
                    value = j[f]
            elif f == "categories":
                if f not in j:
                    value = None
                else:
                    value = [SteamCategory.from_json(i) for i in j[f]]
            elif f == "has_details":
                value = True
            elif f == "genres":
                if f not in j:
                    value = None
                else:
                    value = [SteamGenre.from_json(i) for i in j[f]]
            elif f == "released":
                value = not j["release_date"]["coming_soon"]
            elif f == "metacritic":
                value = j[f]["score"] if f in j and "score" in j[f] else None
            elif f == "recommendations":
                value = j[f]["total"] if f in j and "total" in j[f] else None
            elif f == "release_date":
                if j["release_date"]["coming_soon"]:
                    value = None
                elif j["release_date"]["date"] == "":
                    value = None
                else:
                    value = try_date_formats(j["release_date"]["date"], ["%b %d, %Y", "%b %Y"])
            elif f == "support_url":
                value = j["support_info"]["url"]
            elif f == "support_email":
                value = j["support_info"]["email"]
            else:
                value = j[f]

            setattr(o, f, value)

        return o


LAST_API_CALL_TIMESTAMP = None
def _wait_for_api_flood_protection():
    global LAST_API_CALL_TIMESTAMP

    if LAST_API_CALL_TIMESTAMP is not None:
        delay = 1.5
        wait_time = (LAST_API_CALL_TIMESTAMP + timedelta(seconds=delay) - datetime.now()).total_seconds()

        if wait_time > 0:
            #print("Waiting {}s for the next Steam API call...".format(wait_time))
            sleep(wait_time)
    
    LAST_API_CALL_TIMESTAMP = datetime.now()


def _request_from_steam_storeapi(appid: int, apptype: str ="app", currency: str ="us", locale: str ="en"):
    _wait_for_api_flood_protection()

    url = "https://store.steampowered.com/api/{}details?{}ids={}&cc={}&l={}".format(apptype, apptype, appid, currency, locale)    

    r = requests.get(url)
    if r.status_code != 200:
        raise Exception("Error during Steam request at {}. Error code: {}".format(url, r.status_code))
    
    r_json = r.json()
    r_json = r_json[str(appid)]
    
    if "success" not in r_json:
        raise Exception("ERROR - Invalid JSON, no 'success' field")

    if not r_json["success"]:
        return None

    return r_json["data"]


def _request_from_steam_webapi(interface: str, method: str, parameters: list[tuple[str, str]] = None, version: int = 1):
    _wait_for_api_flood_protection()
    
    if parameters == None or len(parameters) == 0:
        fmt_param = ""
    else:
        fmt_param = "?" + "&".join(map(lambda p: "{}={}".format(p[0], p[1]), parameters))
    
    url = "https://api.steampowered.com/{}/{}/v{}/{}".format(interface, method, version, fmt_param)

    r = requests.get(url)
    if r.status_code != 200:
        raise Exception("Error during Steam request at {}. Error code: {}".format(url, r.status_code))
        
    return r.json()


def _remove_duplicate_stubs(l: list[SteamAppStub]) -> list[SteamAppStub]:
    l.sort(key=lambda a: a.appid)
    
    prev = l[0]
    i = 1
    count = 0
    while i < len(l):
        elem = l[i]
        if elem.appid == prev.appid:
            count = count + 1
            l.remove(elem)
        else:
            prev = elem
            i = i + 1
    
    print("Removed {} duplicate elements".format(count))

    return l


def get_app_list() -> list[SteamAppStub]:
    result = _request_from_steam_webapi("ISteamApps",  "GetAppList", version=2)
    result = result["applist"]["apps"]
    result_list = [SteamAppStub.from_json(r) for r in result]
    return _remove_duplicate_stubs(result_list)


def get_stub_details(stub: SteamAppStub) -> SteamApp:
    j = _request_from_steam_storeapi(stub.appid)

    if j is None:
        return None

    return SteamApp.from_json(j)

CURRENCIES = ["USD", "GBP", "EUR", "RUB", "BRL", "JPY", "MYR", "PHP", "SGD",
              "THB", "VND", "KRW", "UAH", "MXN", "CAD", "AUD", "NZD", "NOK",
              "PLN", "CHF", "CNY", "INR", "CLP", "PEN", "COP", "ZAR", "HKD",
              "TWD", "SAR", "AED", "ILS", "KZT", "KWD", "QAR", "CRC", "UYU"]

def retrieve_pricing_per_appid(appid, currency_list=CURRENCIES):
    prices = {}

    for currency in currency_list:
        print("Getting {} price for AppID {}...".format(currency, appid))
        cc = currency[:2].lower()
        data = _request_from_steam_storeapi(appid, currency=cc)
        if not data:
            #game is not sold in that currency
            continue
        if data["is_free"]:
            print("Game is free - no prices needed")
            return {}
        if "price_overview" not in data:
            continue
        prices[currency] = data["price_overview"]["initial"] / 100
    
    return prices