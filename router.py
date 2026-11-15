"""Provides the backend for a Cudy router"""
import base64
import hashlib
import time
import json
import logging
import requests
import threading
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
# firmware 2.5.4x: kazde POST admin/login vyda novy nonce a predchozi zneplatni -> soubezna prihlaseni
# (vic SyncWorkeru po startu HA) se navzajem shazuji na 403; prihlasovat po jednom
_LOGIN_LOCK = threading.Lock()

class CudyRouter:
    def __init__(self, hass, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.hass = hass
        self.auth_cookie = None
        self.cookie_name = "sysauth"

    def get_cookie_header(self, force_auth: bool) -> str:
        if not force_auth and self.auth_cookie:
            return f"{self.cookie_name}={self.auth_cookie}"
        if self.authenticate():
            return f"{self.cookie_name}={self.auth_cookie}"
        return ""

    def _login_v2(self) -> bool | None:
        """Prihlaseni firmwaru 2.5.4x (Cudy WR3000E, 10/2026): POST admin/login vrati salt, nonce a RSA klic;
        heslo = sha256(sha256(heslo+salt)+nonce) (pri kdfiter > 0 PBKDF2), sifrovane RSA-OAEP (SHA-256), base64.
        Vraci None, kdyz router tento zpusob nezna (stary firmware) -> puvodni prihlaseni."""
        login_url = f"http://{self.host}/cgi-bin/luci"
        try:
            ses = requests.Session()
            page = ses.get(login_url, timeout=10)
            r = ses.post(f"{login_url}/admin/login", data={"username": self.username}, timeout=10)
            d = r.json()
        except Exception:
            return None
        if not isinstance(d, dict) or not d.get("key") or not d.get("salt"):
            return None
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        def phash(pwd, salt, kdf):
            if kdf > 0:
                return hashlib.pbkdf2_hmac("sha256", pwd.encode(), bytes.fromhex(salt), kdf, 32).hex()
            return hashlib.sha256((pwd + salt).encode()).hexdigest()

        kdf = int(d.get("kdfiter") or 0)
        h = phash(self.password, d["salt"], kdf)
        if d.get("nonce"):
            h = phash(h, d["nonce"], 0)
        else:
            h += ":" + phash(self.password, d["salt"], 1000000)
        key = serialization.load_pem_public_key(base64.b64decode(d["key"]))
        enc = base64.b64encode(key.encrypt(h.encode(), padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))).decode()
        soup = BeautifulSoup(page.text, "html.parser")
        tag = soup.find("input", {"name": "_csrf"})
        body = {"_csrf": tag["value"] if tag and tag.has_attr("value") else "",
                "zonename": str(dt_util.DEFAULT_TIME_ZONE), "timeclock": str(int(time.time())),
                "luci_language": "en", "luci_username": self.username, "luci_password": enc}
        try:
            resp = ses.post(login_url + "/", data={k: v for k, v in body.items() if v}, timeout=30, allow_redirects=False)
        except Exception:
            return False
        for c in list(resp.cookies) + list(ses.cookies):
            if c.name.startswith("sysauth") and c.value:
                self.cookie_name, self.auth_cookie = c.name, c.value
                return True
        _LOGGER.warning("Cudy %s: prihlaseni (firmware 2.5.4x) se nepovedlo, HTTP %s", self.host, resp.status_code)
        return False

    def authenticate(self) -> bool:
        with _LOGIN_LOCK:
            v2 = self._login_v2()
        if v2 is not None:
            return v2
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
            is_ax = any(m in hw_version for m in ("WR3000", "WR3000E", "AX3000", "AX1800", "AX6000"))
            bw_iface = "eth1" if is_ax else "eth0"
            raw_bw = await hass.async_add_executor_job(self.get, f"admin/status/bandwidth?iface={bw_iface}")
            bw_json = json.loads(raw_bw) if raw_bw else []
            if bw_json:
                data[MODULE_BANDWIDTH] = parse_bandwidth_json(bw_json, hw_version)
            else:
                # firmware 2.5.4x v rezimu AP (11/2026): ethX vraci [], provoz jen na Wi-Fi rozhranich ra0 (2,4 GHz)
                # a rax0 (5 GHz); mereni se musi rozbehnout pres checkbandwidth. Pro klienty je stahovani = vysilani AP (tx).
                await hass.async_add_executor_job(self.get, "admin/status/checkbandwidth")
                souhrn = {"download_mbps": 0.0, "upload_mbps": 0.0, "download_total_gb": 0.0, "upload_total_gb": 0.0}
                for wif in ("ra0", "rax0"):
                    raw = await hass.async_add_executor_job(self.get, f"admin/status/bandwidth?iface={wif}")
                    b = parse_bandwidth_json(json.loads(raw) if raw else [], hw_version)
                    souhrn["download_mbps"] += b.get("upload_mbps", 0.0)
                    souhrn["upload_mbps"] += b.get("download_mbps", 0.0)
                    souhrn["download_total_gb"] += b.get("upload_total_gb", 0.0)
                    souhrn["upload_total_gb"] += b.get("download_total_gb", 0.0)
                data[MODULE_BANDWIDTH] = {k: round(v, 2) for k, v in souhrn.items()}
        except Exception:
            data[MODULE_BANDWIDTH] = {}

        return data
