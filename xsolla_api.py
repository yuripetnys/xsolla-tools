from typing import Any
import requests

class XsollaProjectAPI:
    def __init__(self, api_key: str, project_id: int) -> None:
        self.api_key = api_key
        self.project_id = project_id
        self.auth = (project_id, api_key)

    def _raise_exc(self, response) -> None:
        if response.status_code == 401:
            error = "Auth error"
        elif response.status_code == 404:
            error = "Game not found"
        elif response.status_code == 422:
            error = "Invalid request"
        else:
            error = f"Unknown error"
        response_json = response.json()
        errormsg = f"[{response.status_code}] {error}. See error message: {response_json["errorMessage"]}."
        if "errorMessageExtended" in response_json:
            errormsg = f"{errormsg} See extended error message: {response_json["errorMessageExtended"]}"
            
        raise Exception(errormsg)

### GET GAMES LIST

    #TO-DO: Handle non-200 responses
    def get_games(self) -> list[Any]:
        url = f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/game"
        has_more = True
        games = []

        while has_more:
            query = {"offset": len(games)}
            response = requests.get(url, params=query, auth=self.auth)
            json_data = response.json()
            has_more = json_data["has_more"]
            games.extend(json_data["items"])

        return games

### CREATE GAME
        
    def create_game(self, payload: Any) -> Any:
        url = f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/game"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, auth=self.auth)
        if response.status_code != 201:
            self._raise_exc(response)
        response_json = response.json()
        return (response_json["item_id"], response_json["sku"])
            

### GET GAME DETAILS
    
    def _get_game(self, url) -> Any:
        response = requests.get(url, auth=self.auth)
    
        if response.status_code != 200:
            self._raise_exc(response)
        return response.json()            
        
    def get_game_by_id(self, id: int) -> Any:
        return self._get_game(f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/game/id/{id}")
    
    def get_game_by_sku(self, sku: str) -> Any:
        return self._get_game(f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/game/sku/{sku}")

### UPDATE GAME

    def _update_game(self, url, payload) -> None:
        if "periods" in payload and len(payload["periods"]) == 0:
            payload.pop("periods")

        response = requests.put(url, auth=self.auth, json=payload, headers={"Content-Type": "application/json"})
        if response.status_code != 204:
            self._raise_exc(response)            

    def update_game_by_id(self, game_id: int, payload) -> None:
        self._update_game(f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/game/id/{game_id}", payload)
                            
    def update_game_by_sku(self, sku: str, payload) -> None:
        self._update_game(f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/game/sku/{sku}", payload)

### DELETE GAME

    def _delete_game(self, url) -> None:
        response = requests.delete(url, auth=self.auth)
        if response.status_code != 204:
            self._raise_exc(response)            
    
    def delete_game_by_id(self, game_id: int) -> None:
        self._delete_game(f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/game/id/{game_id}")

    def delete_game_by_sku(self, sku: str) -> None:
        self._delete_game(f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/game/sku/{sku}")

### CREATE BUNDLE

    #TO-DO
    def create_bundle(self) -> None:
        pass

### GET BUNDLE

    def get_bundle(self, sku: str) -> Any:
        url = f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/bundle/sku/{sku}"
        response = requests.get(url, auth=self.auth)
        if response.status_code != 200:
            self._raise_exc(response)   
        return response.json()

### UPDATE BUNDLE

    def update_bundle(self, sku, payload) -> None:
        payload["groups"] = list([c["external_id"] for c in payload["groups"]])
        payload["content"] = list({ "sku": c["sku"], "quantity": c["quantity"] } for c in payload["content"])
        url = f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/bundle/sku/{sku}"
        response = requests.put(url, auth=self.auth, json=payload, headers={"Content-Type": "application/json"})
        if response.status_code != 204:
            self._raise_exc(response)
        return

### DELETE BUNDLE

    def delete_bundle(self, sku) -> None:
        url = f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/bundle/sku/{sku}"
        response = requests.delete(url, auth=self.auth)
        if response.status_code != 204:
            self._raise_exc(response)
        return

### GET VIRTUAL CURRENCY PACKAGE

    def get_virtual_currency_package(self, sku) -> None:
        url = f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/virtual_currency/package/sku/{sku}"
        response = requests.get(url, auth=self.auth)
        if response.status_code != 200:
            self._raise_exc(response)
        return response.json()

### GET VIRTUAL ITEM
    
    def get_virtual_item(self, sku) -> None:
        url = f"https://store.xsolla.com/api/v2/project/{self.project_id}/admin/items/virtual_items/sku/{sku}"
        response = requests.get(url, auth=self.auth)
        if response.status_code != 200:
            self._raise_exc(response)
        return response.json()

class XsollaMerchantAPI:
    def __init__(self, api_key: str, merchant_id: int):
        self.api_key = api_key
        self.merchant_id = merchant_id
        self.auth = (merchant_id, api_key)

    def get_projects(self) -> list[int]:
        url = f"https://store.xsolla.com/api/v2/merchant/{self.merchant_id}/projects"
        has_more = True
        projects = []
        
        while has_more:
            query = {"offset": len(projects)}
            response = requests.get(url, params=query, auth=self.auth)
            json_data = response.json()
            print(json_data)
            has_more = json_data["has_more"]
            projects.extend([i["project_id"] for i in json_data["items"]])
        
        return projects