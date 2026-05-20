# Cudy Router Integration for Home Assistant (Universal AC/AX)

vylad, oprav, vylepsi

This is an enhanced custom integration for Cudy routers, specifically optimized and tested for AC1200 (WR1200) and AX3000 (WR3000) models.

It features a smart parser.py that automatically detects the hardware version and adjusts data processing (scaling factors, JSON indexes, and HTML parsing) to provide accurate real-time statistics regardless of the router's architecture.

🚀 Enhanced Features & Sensors
Beyond basic device tracking, this integration provides dedicated entities for comprehensive network analysis:

Network Performance
Dynamic Bandwidth Scaling: Automatically detects if the router reports data in Bytes (AC series) or uses hardware-accelerated reporting (AX series).
Download/Upload Speed: Real-time aggregate throughput in Mbps.
Total Data: sensor.download_total & sensor.upload_total — Accumulative counters in GB.
Traffic Analysis
Top Downloader/Uploader: Identifies the device currently consuming the most bandwidth.
Detailed Device Tracker: Monitoring connection type (2.4G/5G/Wired), signal strength (
System Health & Info
Uptime: sensor.connected_time — How long the router has been running.
Hardware/Firmware Info: Version tracking and LAN IP monitoring.


---

## Guidelines for Behavior (Strict)

### 1. Think before you code
- Don't assume. If you're not sure, stop and ask.
- Explicitly emphasize trade-offs.
- If there are multiple interpretations, present them - don't silently choose.

### 2. Simplicity First
- Minimal code that solves the problem. No speculative functions.
- No abstractions for disposable code.
- "Would the lead engineer say this is too complicated?" If so, rewrite.

### 3. Surgical Changes
- Touch only what is necessary.
- Do not improve or refactor existing code unless it is an explicit task.
- Adapt existing style.
- Every changed line must directly reference the requirement.

### 4. Goal-Oriented Execution
- Before coding, provide a plan:
1. [Step] → verify: [check]
2. [Step] → verify: [check]
- Before implementing, write tests/checks that reproduce the goal.

---

**These guidelines work if:** fewer unnecessary changes, fewer reworked solutions, and questions come *before* implementation.
