"""Helper methods to parse HTML returned by Cudy routers"""
import re
import logging
from typing import Any
from bs4 import BeautifulSoup
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

def _get_clean_text(element) -> str:
    if element is None:
        return "Unknown"
    p_tag = element.find("p")
    text = p_tag.get_text(strip=True) if p_tag else element.get_text(strip=True)
    if not text:
        return "Unknown"
    if len(text) > 1 and len(text) % 2 == 0:
        mid = len(text) // 2
        if text[:mid] == text[mid:]:
            return text[:mid]
    return text

def parse_speed(input_string: str) -> float:
    if not input_string:
        return 0.0
    if len(input_string) > 1 and len(input_string) % 2 == 0:
        mid = len(input_string) // 2
        if input_string[:mid] == input_string[mid:]:
            input_string = input_string[:mid]

    match = re.search(r"(\d+(?:\.\d+)?)\s*([kKmMgG]?)([bB])", input_string, re.IGNORECASE)
    if match:
        try:
            value = float(match.group(1))
            prefix = match.group(2).lower()
            unit_is_byte = match.group(3) == 'B'
            if prefix == 'k': value *= 1000
            elif prefix == 'm': value *= 1000000
            elif prefix == 'g': value *= 1000000000
            if unit_is_byte: value *= 8
            return round(value / 1000000.0, 2)
        except ValueError: pass
    return 0.0

def parse_lan_info(input_html: str) -> dict[str, Any]:
    if not input_html: return {}
    soup = BeautifulSoup(input_html, "html.parser")
    data = {"ip_address": "N/A", "connected_time": "N/A"}

    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        
        label = cells[0].get_text(strip=True)
        value = _get_clean_text(cells[1])
        
        if any(x in label for x in ["IP Address", "IPv4-Address", "Address"]):
            ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", value)
            if ip_match:
                data["ip_address"] = ip_match.group(1)
        
        if any(x in label for x in ["Uptime", "Connected", "Runtime", "Up Time"]):
            if ":" in value or "s" in value or "d" in value:
                data["connected_time"] = value
            
    return data

def parse_system_info(input_html: str) -> dict[str, Any]:
    data = {"firmware": "Unknown", "hardware": "Unknown"}
    if not input_html: return data
    
    soup = BeautifulSoup(input_html, "html.parser")
    footer = soup.find("footer")
    if footer:
        text = footer.get_text()
        hw_match = re.search(r"HW:\s*([^\s|]+(?:\s+V[\d\.]+)*)", text)
        if hw_match:
            data["hardware"] = hw_match.group(1).strip()
        
        fw_match = re.search(r"FW:\s*([^\s|]+)", text)
        if fw_match:
            data["firmware"] = fw_match.group(1).strip()
            
    return data

def parse_bandwidth_json(json_data: list, hw_version: str = "") -> dict[str, Any]:
    if not json_data or len(json_data) < 2:
        return {"upload_mbps": 0.0, "download_mbps": 0.0, "upload_total_gb": 0.0, "download_total_gb": 0.0}
    try:
        last, prev = json_data[-1], json_data[-2]
        delta_t = (last[0] - prev[0]) / 1000000.0
        if delta_t <= 0: delta_t = 1.0
        
        _hw = hw_version or ""
        is_ax = any(m in _hw for m in ("WR3000", "AX3000", "AX1800", "AX6000", "AX"))
        if is_ax:
            raw_rx_diff, raw_tx_diff = last[3] - prev[3], last[4] - prev[4]
            rx_mbps = round((raw_rx_diff * 8 * 45) / (delta_t * 10000.0), 2)
            tx_mbps = round((raw_tx_diff * 8 * 45) / (delta_t * 10000.0), 2)
            total_rx_gb, total_tx_gb = round(last[3] / 1024, 2), round(last[4] / 1024, 2)
        else:
            raw_rx_diff, raw_tx_diff = last[1] - prev[1], last[3] - prev[3]
            rx_mbps = round((raw_rx_diff * 8) / (delta_t * 1000000.0), 2)
            tx_mbps = round((raw_tx_diff * 8) / (delta_t * 1000000.0), 2)
            total_rx_gb, total_tx_gb = round(last[1] / (1024**3), 2), round(last[3] / (1024**3), 2)
            
        return {"download_mbps": max(0.0, rx_mbps), "upload_mbps": max(0.0, tx_mbps),
                "download_total_gb": max(0.0, total_rx_gb), "upload_total_gb": max(0.0, total_tx_gb)}
    except: return {"upload_mbps": 0.0, "download_mbps": 0.0, "upload_total_gb": 0.0, "download_total_gb": 0.0}

def _parse_ac1200_style(soup: BeautifulSoup) -> list[dict]:
    devices = []
    for br in soup.find_all("br"): br.replace_with("\n")
    rows = soup.find_all("tr", id=re.compile(r"^cbi-table-\d+"))
    for row in rows:
        try:
            ip, mac = "Unknown", "Unknown"
            ipmac_div = row.find("div", id=re.compile(r"-ipmac$"))
            if ipmac_div:
                parts = ipmac_div.get_text(strip=True, separator="\n").split("\n")
                if len(parts) >= 1: ip = _get_clean_text(BeautifulSoup(parts[0], "html.parser"))
                if len(parts) >= 2: mac = _get_clean_text(BeautifulSoup(parts[1], "html.parser"))
            
            hostname_raw = _get_clean_text(row.find("div", id=re.compile(r"-hostnamexs$")))
            hostname = ip if not hostname_raw or "Unknown" in hostname_raw else hostname_raw

            speed_div = row.find("div", id=re.compile(r"-speed$"))
            up_s, down_s = "0", "0"
            if speed_div:
                s_parts = speed_div.get_text(strip=True, separator="\n").split("\n")
                if len(s_parts) >= 2: up_s, down_s = s_parts[0], s_parts[1]

            conn_raw = _get_clean_text(row.find("div", id=re.compile(r"-iface$"))).upper()
            is_eth = "WIRED" in conn_raw or any(x in conn_raw for x in ["ETH", "LAN"])
            is_wifi = any(x in conn_raw for x in ["G", "WIFI", "WIRELESS"]) and not is_eth
            if not is_wifi and not is_eth: is_eth = True

            devices.append({
                "hostname": hostname, "ip": ip, "mac": mac,
                "upload_speed": parse_speed(up_s), "download_speed": parse_speed(down_s),
                "signal": _get_clean_text(row.find("div", id=re.compile(r"-signal$"))),
                "online_time": _get_clean_text(row.find("div", id=re.compile(r"-online$"))),
                "connection": conn_raw, "is_wifi": is_wifi, "is_eth": is_eth
            })
        except: continue
    return devices

def parse_devices(input_html: str, router_ip: str = "") -> dict[str, Any]:
    soup = BeautifulSoup(input_html, "html.parser")
    devices = _parse_ac1200_style(soup)
    
    router_ips = [router_ip, "127.0.0.1", "Unknown"]
    filtered_devices = [d for d in devices if d["ip"] not in router_ips and d["mac"] != "Unknown"]

    wifi_devs = [d for d in filtered_devices if d["is_wifi"]]
    eth_devs = [d for d in filtered_devices if d["is_eth"]]

    data = {
        "device_count": {"value": len(filtered_devices)},
        "wifi_device_count": {"value": len(wifi_devs)},
        "eth_device_count": {"value": len(eth_devs)}
    }
    
    data["connected_devices"] = {
        "value": len(filtered_devices), 
        "attributes": {
            "wifi_count": len(wifi_devs),
            "eth_count": len(eth_devs),
            "devices": filtered_devices, 
            "last_updated": datetime.now().isoformat()
        }
    }
    return data
