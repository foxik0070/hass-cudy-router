"""Provides the backend for a Cudy router"""
import hashlib
import time
import json
import logging
import requests
from typing import Any
from http.cookies import SimpleCookie
from bs4 import BeautifulSoup
import homeassistant.util.dt as dt_util

from .const import (
    MODULE_DEVICES, MODULE_LAN, MODULE_BANDWIDTH, MODULE_SYSTEM,
    MODULE_SYSTEM_STATUS, MODULE_WAN, MODULE_WIRELESS, OPTIONS_DEVICELIST,
)
from .parser import (
    parse_devices, parse_lan_info, parse_bandwidth_json, parse_system_info,
    parse_system_status, parse_wan_info, parse_wireless_info,
)

_LOGGER = logging.getLogger(__name__)

class CudyRouter:
    def __init__(self, hass, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.hass = hass
        self.auth_cookie = None

    def get_cookie_header(self, force_auth: bool) -> str:
        if not force_auth and self.auth_cookie:
            return f"sysauth={self.auth_cookie}"
        if self.authenticate():
            return f"sysauth={self.auth_cookie}"
        return ""

    def authenticate(self) -> bool:
        login_url = f"http://{self.host}/cgi-bin/luci"
        try:
            resp = requests.get(login_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            def extract(name):
                tag = soup.find("input", {"name": name})
                return tag["value"] if tag and tag.has_attr("value") else ""
            _csrf = extract("_csrf")
            token = extract("token")
            salt = extract("salt")
        except Exception as e:
            _LOGGER.error("Error retrieving login page: %s", e)
            return False

        zonename = str(dt_util.DEFAULT_TIME_ZONE)
        timeclock = str(int(time.time()))
        
        if salt:
            hashed = hashlib.sha256((self.password + salt).encode()).hexdigest()
            if token:
                hashed = hashlib.sha256((hashed + token).encode()).hexdigest()
            luci_password = hashed
        else:
            luci_password = self.password

        body = {"_csrf": _csrf, "token": token, "salt": salt, "zonename": zonename, 
                "timeclock": timeclock, "luci_language": "en", "luci_username": self.username, 
                "luci_password": luci_password}
        body = {k: v for k, v in body.items() if v}

        try:
            response = requests.post(login_url, timeout=30, data=body, allow_redirects=False)
            if response.ok:
                cookie = SimpleCookie()
                cookie.load(response.headers.get("set-cookie"))
                if cookie.get("sysauth"):
                     self.auth_cookie = cookie.get("sysauth").value
                     return True
        except Exception:
            pass
        return False

    def get(self, url: str) -> str:
        retries = 2
        while retries > 0:
            retries -= 1
            data_url = f"http://{self.host}/cgi-bin/luci/{url}"
            headers = {"Cookie": self.get_cookie_header(False)}
            try:
                response = requests.get(data_url, timeout=30, headers=headers, allow_redirects=False)
                if response.status_code == 403:
                    if self.authenticate(): continue
                    else: break
                if response.ok: return response.text
            except Exception:
                pass
        return ""

    async def get_data(self, hass, options: dict[str, Any], previous_data: dict[str, Any] = None) -> dict[str, Any]:
        data = {}

        raw_system_page = await hass.async_add_executor_job(self.get, "admin/system/system")
        data[MODULE_SYSTEM] = parse_system_info(raw_system_page)
        hw_version = data[MODULE_SYSTEM].get("hardware", "")
        raw_status = await hass.async_add_executor_job(self.get, "admin/system/status")
        raw_lan_status = await hass.async_add_executor_job(self.get, "admin/network/lan/status")
        combined_html = (raw_status or "") + (raw_lan_status or "")
        data[MODULE_LAN] = parse_lan_info(combined_html)
        data[MODULE_SYSTEM_STATUS] = parse_system_status(raw_status or "")

        raw_wan = await hass.async_add_executor_job(self.get, "admin/network/wan/status")
        data[MODULE_WAN] = parse_wan_info(raw_wan or "")

        raw_wifi_24 = await hass.async_add_executor_job(self.get, "admin/network/wireless/status?iface=wlan00")
        raw_wifi_5 = await hass.async_add_executor_job(self.get, "admin/network/wireless/status?iface=wlan10")
        data[MODULE_WIRELESS] = parse_wireless_info(raw_wifi_24 or "", raw_wifi_5 or "")

        raw_dev = await hass.async_add_executor_job(self.get, "admin/network/devices/devlist?detail=1")
        data[MODULE_DEVICES] = parse_devices(raw_dev, self.host)

        try:
            raw_bw = await hass.async_add_executor_job(self.get, "admin/status/bandwidth?iface=eth0")
            if raw_bw:
                data[MODULE_BANDWIDTH] = parse_bandwidth_json(json.loads(raw_bw), hw_version)
            else:
                data[MODULE_BANDWIDTH] = {}
        except Exception:
            data[MODULE_BANDWIDTH] = {}

        return data
