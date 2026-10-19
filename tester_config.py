# =============================================================================
# URTC Tester - Configuration, language/translation loading, and shared
# constants used by every other module in this project
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
from urtc_ui import DEFAULT_LANGUAGE, LANGUAGES, parse_bitrate
import sys
import os
import json
import re

from urtc_can import protocol

try:
    import serial  # noqa: F401  (availability check only)
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False


TESTER_VERSION = "0.3.6"
TESTER_AUTHOR = "JuanenRac"

# THIS_HARDWARE_ID matches bootloader_common.h/firmware_common.h's own constant - used
# here only to flag a mismatch after connecting (a different board/rig
# answering than the one this was set up for), never to gate anything.
THIS_HARDWARE_ID = protocol.HARDWARE_ID_MAIN

BITRATE_500K_SLCAN_CODE = "6"  # SLCAN's "Sx" bitrate codes: 6 = 500 kbit/s
SLCAN_BITRATES = [
    ("10 kbit/s", "0"), ("20 kbit/s", "1"), ("50 kbit/s", "2"),
    ("100 kbit/s", "3"), ("125 kbit/s", "4"), ("250 kbit/s", "5"),
    ("500 kbit/s", "6"), ("800 kbit/s", "7"), ("1 Mbit/s", "8"),
]


def bitrate_bps_for_label(label):
    """Bits per second of a bitrate label such as "500 kbit/s" or "1 Mbit/s" (500000 when it is not recognised)."""
    try:
        return parse_bitrate(str(label))
    except ValueError:
        return 500000


if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
LOGS_FOLDER = os.path.normpath(os.path.join(base_dir, "logs"))
CUSTOM_IDS_PATH = os.path.normpath(os.path.join(base_dir, "urtc_custom_ids.json"))
LANGUAGE_FOLDER = os.path.normpath(os.path.join(base_dir, "language"))
CONFIG_PATH = os.path.normpath(os.path.join(base_dir, "config.json"))
AVAILABLE_LANGUAGES = list(LANGUAGES)  # the list every URTC program shares (urtc_ui)


def load_config():
    """Reads config.json next to this tool - currently just the language
    preference, but a plain dict so future settings can be added here
    without needing a new file or a schema migration. Missing file (first
    run) or a broken one (manual edit gone wrong) both fall back to an
    empty dict rather than crashing the tool - every read of a key from
    this uses .get() with a sensible default anyway."""
    if not os.path.isfile(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def save_config(updates):
    """Merges updates into whatever's already in config.json and writes
    the result back - merges rather than overwrites wholesale, so saving
    one setting (e.g. language) never clobbers some other setting a
    future version of this tool might have already written there.
    Failure to write (read-only filesystem, permissions) is logged by the
    caller if it wants to, not raised here - a missing saved preference
    is a minor inconvenience, not worth crashing over. Written atomically
    (temp file + os.replace()) - a plain open(..., "w") would leave the
    real file truncated or half-written if the process was interrupted
    mid-write."""
    current = load_config()
    current.update(updates)
    tmp_path = CONFIG_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        os.replace(tmp_path, CONFIG_PATH)
        return True
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def load_language(name):
    """Reads language/<name>.lng - a plain UTF-8 KEY=Value text file, one
    entry per line, '#' - prefixed lines and blank lines ignored, and a
    literal two-character \\n inside a value unescaped into a real
    newline (for the handful of multi-line messagebox strings). Falls
    back to an empty dict if the file is missing or unreadable, so the
    caller's own fallback-to-key-itself behavior in _() takes over rather
    than crashing the tool over a missing/corrupt translation file."""
    path = os.path.join(LANGUAGE_FOLDER, f"{name}.lng")
    # name comes from urtc_config.json - not sanitized before this point,
    # so a manipulated config file could otherwise smuggle in a path
    # separator or "../" sequence and make this read a file outside
    # LANGUAGE_FOLDER entirely. Restricting to a plain filename-safe
    # character set closes that off regardless of what's actually in the
    # AVAILABLE_LANGUAGES list.
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return {}
    result = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n").rstrip("\r")
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _sep, value = line.partition("=")
                result[key.strip()] = value.replace("\\n", "\n")
    except (OSError, UnicodeDecodeError):
        return {}
    return result


_config = load_config()
_current_language = _config.get("language", DEFAULT_LANGUAGE)
_translations = load_language(_current_language)
if not _translations and _current_language != DEFAULT_LANGUAGE:
    # Saved preference pointed at a language file that's now missing/broken
    # (moved, deleted, hand-edited badly) - falls back to English rather
    # than showing raw translation keys throughout the entire UI.
    _current_language = DEFAULT_LANGUAGE
    _translations = load_language(DEFAULT_LANGUAGE)


def _(key, **kwargs):
    """Looks up key in the currently loaded language file and applies any
    keyword substitutions (e.g. _("GREETING", name=x) for a string
    containing {name}). Falls back to the key itself, visibly
    un-translated, if the key is missing from the file entirely - a
    visible wrong string in the UI is far easier to notice and report
    than a silent KeyError crashing the tool."""
    text = _translations.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def _load_custom_id_names():
    """Optional, not included by default: urtc_custom_ids.json next to
    this script, mapping hex ID strings to friendly names - e.g.
    {"0x199": "My Expansion Sensor"}. Lets someone testing a custom
    expansion board or addition give their own IDs a readable name in the
    Raw Bus Monitor without needing to modify this tool's source at all.
    Missing file is silent (this is opt-in); a present-but-broken file is
    logged and ignored rather than crashing the tool over a typo."""
    if not os.path.isfile(CUSTOM_IDS_PATH):
        return {}
    try:
        with open(CUSTOM_IDS_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        result = {}
        for key, name in raw.items():
            try:
                result[int(key, 0)] = str(name)
            except (ValueError, TypeError):
                continue  # one bad entry doesn't invalidate the rest of the file
        return result
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


CUSTOM_ID_NAMES = _load_custom_id_names()

if getattr(sys, "frozen", False):
    ICON_IMAGE_PATH = os.path.normpath(os.path.join(sys._MEIPASS, "assets", "urtc_icon.png"))
else:
    ICON_IMAGE_PATH = os.path.normpath(os.path.join(base_dir, "assets", "urtc_icon.png"))


def list_serial_ports():
    ports = []
    if HAVE_SERIAL:
        import serial.tools.list_ports
        ports = [p.device for p in serial.tools.list_ports.comports()]
    return ports

# CAN protocol constants - every ID this tool can send or receive, matching
# CANBUS.TXT exactly (kept as one flat block here rather than split per
# tool, since several - like 0x100 and 0x110/0x111 - are global and used
# regardless of which tool profile is active).
# =============================================================================
CAN_ID_IMPACT_EVENT      = protocol.CAN_ID_IMPACT_EVENT  # Scan probe - max priority, event-driven
CAN_ID_GLOBAL_STATUS     = protocol.CAN_ID_GLOBAL_STATUS  # Status LED + ring LED + OLED night mode - any tool
CAN_ID_QUERY_ACTIVE_TOOL = protocol.CAN_ID_QUERY_ACTIVE_TOOL  # Query which tool profile is active + quick state
CAN_ID_ACTIVE_TOOL_RESP  = protocol.CAN_ID_ACTIVE_TOOL_RESP  # Answers CAN_ID_QUERY_ACTIVE_TOOL
CAN_ID_MOTION_CMD        = protocol.CAN_ID_MOTION_CMD  # Stepper dir+steps - dispensers/screwdriver/grippers, and (doc #16) the soldering iron's own wire feeder
CAN_ID_SOLDER_SETPOINT   = protocol.CAN_ID_SOLDER_SETPOINT  # T12 setpoint temperature
# The firmware refuses a setpoint above this (soldering iron, hot air) and declares a latched CRITICAL ERROR (firmware_control_thermal.c): no screen offers more.
SETPOINT_MAX_C = 445
CAN_ID_SOLDER_FEEDER_RESET = protocol.CAN_ID_SOLDER_FEEDER_RESET  # Reset wire feeder's own open-loop position to 0 - magic payload, see CANBUS.TXT
CAN_ID_SOLDER_FEEDER_POS   = protocol.CAN_ID_SOLDER_FEEDER_POS  # Query/response: wire feeder's own current position (signed steps)
CAN_ID_SOLDER_TELEMETRY  = protocol.CAN_ID_SOLDER_TELEMETRY  # T12 actual temperature only (DLC 2, no endstop byte), see CANBUS.TXT's own 0x135 note
CAN_ID_DRILL_CMD         = protocol.CAN_ID_DRILL_CMD  # BL4260 speed + direction
CAN_ID_VACUUM_TELEMETRY  = protocol.CAN_ID_VACUUM_TELEMETRY  # ADC reading + digital detect
CAN_ID_DRILL_TELEMETRY   = protocol.CAN_ID_DRILL_TELEMETRY  # Actual RPM + endstop
CAN_ID_AOI_CMD           = protocol.CAN_ID_AOI_CMD  # Ring mode + strobe period
CAN_ID_AOI_TELEMETRY     = protocol.CAN_ID_AOI_TELEMETRY  # Endstop only
CAN_ID_LASER_CMD         = protocol.CAN_ID_LASER_CMD  # Power + interlock
CAN_ID_LASER_TELEMETRY   = protocol.CAN_ID_LASER_TELEMETRY  # Endstop only
CAN_ID_3DP_THERMAL_MOTION = protocol.CAN_ID_PRINTER_THERMAL_MOTION  # Nozzle setpoint + extruder direction/steps
CAN_ID_3DP_LAYER_FAN_CMD  = protocol.CAN_ID_PRINTER_LAYERFAN_CMD  # Layer fan PWM
CAN_ID_3DP_HOTEND_TELEM   = protocol.CAN_ID_PRINTER_HOTEND_TELEMETRY  # Hotend actual temperature
CAN_ID_3DP_LAYER_FAN_RPM  = protocol.CAN_ID_PRINTER_LAYERFAN_RPM  # Layer fan actual RPM
CAN_ID_3DP_HOTEND_FAN_CMD = protocol.CAN_ID_PRINTER_HOTENDFAN_CMD  # Hotend fan PWM
CAN_ID_3DP_HOTEND_FAN_RPM = protocol.CAN_ID_PRINTER_HOTENDFAN_RPM  # Hotend fan actual RPM
CAN_ID_ELECTROMAGNET_CMD  = protocol.CAN_ID_ELECTROMAGNET_CMD  # Coil energize/release (nonzero=on)
CAN_ID_SPOT_WELD_CMD      = protocol.CAN_ID_SPOT_WELD_CMD  # Timed pulse, gated on the contact sensor
CAN_ID_UV_CURING_CMD      = protocol.CAN_ID_UV_CURING_CMD  # LED driver duty cycle, 0-255
CAN_ID_HOTAIR_CMD         = protocol.CAN_ID_HOTAIR_CMD  # Setpoint temp + blower duty (shares 0x135 telemetry with the soldering iron)
CAN_ID_CRIMPING_CMD       = protocol.CAN_ID_CRIMPING_CMD  # Same byte layout as 0x120, drives the expansion board's own driver instead
CAN_ID_ULTRASONIC_WELD_CMD = protocol.CAN_ID_ULTRASONIC_WELD_CMD  # Timed pulse, same as Spot Welder but no contact-sensor gate
CAN_ID_ADS1115_CONFIG     = protocol.CAN_ID_ADS1115_CONFIG  # Functional Testing Head - ADS1115 16-bit config register [BIG-ENDIAN]
CAN_ID_ADS1115_TRIGGER    = protocol.CAN_ID_ADS1115_TRIGGER  # Functional Testing Head - trigger a single-shot conversion
CAN_ID_ADS1115_RESULT     = protocol.CAN_ID_ADS1115_RESULT  # Functional Testing Head - query (empty payload), or the 2-byte raw result
CAN_ID_FLYING_PROBE_BASIC = protocol.CAN_ID_FLYING_PROBE_BASIC  # Functional Testing Head - basic onboard-ADC reading, automatic telemetry
CAN_ID_PASTE_JETTING_CONFIG = protocol.CAN_ID_PASTE_JETTING_CONFIG  # Local PWM channel + frequency config
CAN_ID_PASTE_JETTING_PULSE  = protocol.CAN_ID_PASTE_JETTING_PULSE  # Local PWM channel + duty + duration pulse
CAN_ID_THERMAL_TRIGGER    = protocol.CAN_ID_THERMAL_TRIGGER  # PCB Advanced Inspection - trigger a new capture
CAN_ID_THERMAL_STATUS     = protocol.CAN_ID_THERMAL_STATUS  # PCB Advanced Inspection - query (empty payload), or the 1-byte status
CAN_ID_THERMAL_RAW_CHUNK_REQ = protocol.CAN_ID_THERMAL_RAW_CHUNK_REQ  # PCB Advanced Inspection - request a raw pixel chunk (1 byte, chunk index)
CAN_ID_THERMAL_RAW_CHUNK  = protocol.CAN_ID_THERMAL_RAW_CHUNK  # PCB Advanced Inspection - raw pixel chunk data, 4 frames of 8 bytes
CAN_ID_THERMAL_CALIB_CHUNK_REQ = protocol.CAN_ID_THERMAL_CAL_CHUNK_REQ  # PCB Advanced Inspection - request a calibrated temperature chunk
CAN_ID_THERMAL_CALIB_CHUNK = protocol.CAN_ID_THERMAL_CAL_CHUNK  # PCB Advanced Inspection - calibrated temperature chunk data, 4 frames of 8 bytes
CAN_ID_EXP_SPI_CMD        = protocol.CAN_ID_EXPANSION_SPI_REQ  # Generic SPI passthrough request, for CONN_EXPANSION
CAN_ID_EXP_SPI_RESP       = protocol.CAN_ID_EXPANSION_SPI_RESP  # Answers CAN_ID_EXP_SPI_CMD
CAN_ID_QUERY_DIAG0        = protocol.CAN_ID_EXPANSION_DIAG0_REQ  # Query TMC_DIAG0's current level
CAN_ID_DIAG0_RESP         = protocol.CAN_ID_EXPANSION_DIAG0_RESP  # Answers CAN_ID_QUERY_DIAG0
CAN_ID_QUERY_FRAM_STATE = protocol.CAN_ID_FRAM_QUERY  # Query the FM24CL64B's recovered state
CAN_ID_FRAM_STATE_RESP  = protocol.CAN_ID_FRAM_STATE_RESP  # Answers CAN_ID_QUERY_FRAM_STATE, also sent after an erase
CAN_ID_QUERY_THERMAL_STATS = protocol.CAN_ID_THERMAL_STATS_QUERY  # Query lifetime thermal counters (URTC firmware 0.3.3+)
CAN_ID_THERMAL_STATS_RESP  = protocol.CAN_ID_THERMAL_STATS_RESP  # Answers CAN_ID_QUERY_THERMAL_STATS
CAN_ID_ERASE_FRAM       = protocol.CAN_ID_ERASE_FRAM  # Magic-payload erase - see ERASE_FRAM_MAGIC below
CAN_ID_EXPANSION_TYPE_RESP = protocol.CAN_ID_EXPANSION_TYPE_RESP  # Query (empty payload), or the response - see EXPANSION.TXT
CAN_ID_FREE_TOOL_CONFIG_RESP = protocol.CAN_ID_FREE_TOOL_CONFIG_RESP  # Query (empty payload), or the response - see EEPROM.TXT section 5
CAN_ID_PERIPHERAL_INFO_RESP = protocol.CAN_ID_PERIPHERAL_INFO_RESP  # Query (empty payload), or the response - see EEPROM.TXT section 6
CAN_ID_MLX_VARIANT_RESP = protocol.CAN_ID_MLX_VARIANT_RESP  # Query (empty payload), or the response - see CANBUS.TXT

# Same 7 configurations as the flasher's own list (flasher_config.py) - kept in sync manually
# since these two tools don't share a module.
EXPANSION_BOARD_TYPES = [
    "0 - None installed",
    "1 - Basic, TMC2209",
    "2 - Basic, TMC5160A",
    "3 - Advanced, TMC2209 + STM32F303CBT6",
    "4 - Advanced, TMC5160A + STM32F303CBT6",
    "5 - Basic, ADS1115 only (direct connection)",
    "6 - Basic, MLX9064x only (direct connection)",
]

# Same list as urtc_flasher.py's own MLX_SENSOR_VARIANTS - see that
# file's own comment for what this controls. 0 deliberately means "no
# sensor configured" rather than defaulting to any real sensor.
MLX_SENSOR_VARIANTS = [
    "0 - None installed",
    "1 - MLX90640 (32x24)",
    "2 - MLX90641 (16x12)",
    "3 - MLX90642 (32x24, onboard calc)",
]
# The ring light's strobe period is in MILLISECONDS and the firmware limits it to 1..500.
AOI_STROBE_MAX_MS = 500
AOI_STROBE_DEFAULT_MS = 5
ERASE_FRAM_MAGIC = protocol.MAGIC_ERASE_FRAM
SOLDER_FEEDER_RESET_MAGIC = protocol.MAGIC_SOLDER_FEEDER_RESET  # ASCII "RSP0": reset the wire feeder position to 0
CAN_ID_QUERY_VERSION     = protocol.CAN_ID_QUERY_VERSION  # Answered by app or bootloader, whichever's running
CAN_ID_VERSION_RESPONSE  = protocol.CAN_ID_VERSION_RESPONSE
CAN_ID_VERSION_PATCH_RESPONSE = protocol.CAN_ID_VERSION_PATCH_RESPONSE  # companion of 0x7F9: patch number of the installed application (URTC firmware 0.3.5+)
VERSION_PATCH_GRACE_S = protocol.VERSION_PATCH_GRACE_MS / 1000.0  # how long after 0x7F9 the companion frame is waited for

# Layers built-in names (derived from every CAN_ID_* constant just above,
# via globals() - not a separately hand-maintained list that could drift)
# underneath whatever urtc_custom_ids.json already loaded into
# CUSTOM_ID_NAMES above. setdefault leaves any custom override already
# present alone - so a custom file that deliberately renames a standard ID
# still wins, and everything else gets a sensible built-in name instead of
# nothing at all.
for _name, _value in list(globals().items()):
    if _name.startswith("CAN_ID_") and isinstance(_value, int):
        CUSTOM_ID_NAMES.setdefault(_value, _name[len("CAN_ID_"):].replace("_", " ").title())
del _name, _value

TOOL_NAMES = {
    0: "Soldering Iron", 1: "Paste Dispenser", 2: "Liquid Dispenser",
    3: "Screwdriver", 4: "Vacuum Pickup", 5: "Drill",
    6: "Gripper (Gimbal)", 7: "Gripper (NEMA)", 8: "AOI Inspection",
    9: "Laser Engraver", 10: "3D Printer", 11: "Scan Probe",
    12: "SMT Pick & Place", 13: "Electromagnet", 14: "Spot Welder",
    15: "Conformal Coating", 16: "Vacuum Gripper (LG)", 17: "Flying Probe",
    18: "UV Curing", 19: "Hot Air Rework", 20: "Press-Fit Inserter",
    21: "Crimping Actuator", 22: "Thermal Inspection", 23: "Paste Jetting",
    24: "Ultrasonic Welder",
}
# 7 tool IDs all share the exact same motion command (0x120) - a plain
# stepper with direction + step count, differing only in what's physically
# attached, not in the protocol.
MOTION_TOOL_IDS = {1, 2, 3, 6, 7, 12, 16}



def format_thermal_stats(stats):
    """Display text for a decode_thermal_stats() result (None = no answer)."""
    if stats is None:
        return _("LBL_THERMAL_STATS_NO_RESPONSE")
    hours = stats["heater_on_seconds"] / 3600.0
    text = _("LBL_THERMAL_STATS_TEXT", faults=stats["fault_count"], hours=f"{hours:.2f}",
             last=stats["last_fault_name"] or _("VAL_NONE"))
    if not stats["persisted"]:
        text += "\n" + _("LBL_THERMAL_STATS_NOT_PERSISTED")
    return text
