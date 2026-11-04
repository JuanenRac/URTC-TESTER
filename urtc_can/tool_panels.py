"""GENERATED from spec/tools.json by tools/generate_tools.py - do not edit by hand.

The panels of the tool profiles (controls, readings, commands) as data (standard library only).
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

_BY_NAME: dict[str, dict] = {
 "0": {
  "sections": [
   {
    "title": {
     "key": "testertool.soldering_heater_title",
     "default": "Heater (0x130 / telemetry 0x135)"
    },
    "controls": [
     {
      "id": "temp",
      "type": "number",
      "label": {
       "key": "testertool.setpoint_0_445",
       "default": "Setpoint (0-445 C)"
      },
      "min": 0,
      "max": 445,
      "default": 220
     }
    ],
    "actions": [
     {
      "type": "keepalive",
      "message": "SOLDER_SETPOINT",
      "canId": 304,
      "encoder": "solderSetpoint",
      "args": [
       "temp"
      ],
      "off_encoder": "solderOff",
      "description": "Soldering iron setpoint",
      "off_description": "Soldering iron off",
      "confirm": "heater",
      "confirm_value": "temp",
      "watchdog_ms": 250
     }
    ],
    "telemetry": [
     {
      "id": "live",
      "label": {
       "key": "testertool.live_label",
       "default": "Live:"
      },
      "message": "SOLDER_TELEMETRY",
      "canId": 309,
      "offset": 0,
      "width": 2,
      "unit": "C",
      "graph_max": 450
     }
    ]
   },
   {
    "title": {
     "key": "testertool.wire_feeder_title",
     "default": "Wire Feeder (0x120 motion, 0x131/0x132 position)"
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move feeder",
      "confirm": "motion"
     },
     {
      "type": "query",
      "label": {
       "key": "testertool.query",
       "default": "Query"
      },
      "message": "SOLDER_FEEDER_POS",
      "canId": 306,
      "timeout_ms": 1500,
      "description": "Query feeder position",
      "auto": True,
      "result": {
       "label": {
        "key": "testertool.position_label",
        "default": "Position:"
       },
       "offset": 0,
       "width": 4,
       "signed": True
      }
     },
     {
      "type": "send",
      "label": {
       "key": "testertool.reset",
       "default": "Reset"
      },
      "message": "SOLDER_FEEDER_RESET",
      "canId": 305,
      "encoder": "feederReset",
      "description": "Reset feeder position",
      "confirm": "feeder_reset"
     }
    ]
   }
  ]
 },
 "1": {
  "sections": [
   {
    "title": {
     "text": "{tool} (0x120)"
    },
    "subtitle": {
     "key": "testertool.motion_subtitle",
     "default": "One-shot move, no telemetry, no comms watchdog."
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move",
      "confirm": "motion"
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionStop",
      "args": [
       "dir"
      ],
      "description": "Stop"
     }
    ]
   }
  ]
 },
 "2": {
  "sections": [
   {
    "title": {
     "text": "{tool} (0x120)"
    },
    "subtitle": {
     "key": "testertool.motion_subtitle",
     "default": "One-shot move, no telemetry, no comms watchdog."
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move",
      "confirm": "motion"
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionStop",
      "args": [
       "dir"
      ],
      "description": "Stop"
     }
    ]
   }
  ]
 },
 "3": {
  "sections": [
   {
    "title": {
     "text": "{tool} (0x120)"
    },
    "subtitle": {
     "key": "testertool.motion_subtitle",
     "default": "One-shot move, no telemetry, no comms watchdog."
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move",
      "confirm": "motion"
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionStop",
      "args": [
       "dir"
      ],
      "description": "Stop"
     }
    ]
   }
  ]
 },
 "4": {
  "sections": [
   {
    "title": {
     "key": "testertool.vacuum_title",
     "default": "Vacuum Pickup (0x145, telemetry only)"
    },
    "subtitle": {
     "key": "testertool.vacuum_subtitle",
     "default": "Passively pushed by the firmware - no command to send."
    },
    "telemetry": [
     {
      "id": "adc",
      "label": {
       "key": "testertool.adc_label",
       "default": "ADC:"
      },
      "message": "VACUUM_TELEMETRY",
      "canId": 325,
      "offset": 0,
      "width": 2
     },
     {
      "id": "part",
      "label": {
       "key": "testertool.part_detected_label",
       "default": "Part detected:"
      },
      "message": "VACUUM_TELEMETRY",
      "canId": 325,
      "offset": 2,
      "width": 1,
      "format": "yes_no"
     }
    ]
   }
  ]
 },
 "5": {
  "sections": [
   {
    "title": {
     "key": "testertool.drill_title",
     "default": "Drill (0x140 / telemetry 0x147)"
    },
    "subtitle": {
     "key": "testertool.drill_subtitle",
     "default": "The command is resent while Active is checked; the board stops the drill 250 ms after the last one."
    },
    "controls": [
     {
      "id": "speed",
      "type": "range",
      "label": {
       "key": "testertool.speed_label",
       "default": "Speed ({{speed}})",
       "param": "speed"
      },
      "min": 0,
      "max": 255,
      "default": 0
     },
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "cw",
      "options": [
       {
        "value": "cw",
        "label": {
         "key": "testertool.clockwise",
         "default": "Clockwise"
        }
       },
       {
        "value": "ccw",
        "label": {
         "key": "testertool.counter_clockwise",
         "default": "Counter-clockwise"
        }
       }
      ]
     }
    ],
    "actions": [
     {
      "type": "keepalive",
      "message": "DRILL_CMD",
      "canId": 320,
      "encoder": "drillCommand",
      "args": [
       "speed",
       "dir"
      ],
      "off_encoder": "drillStop",
      "description": "Drill command",
      "off_description": "Drill stop",
      "confirm": "drill",
      "watchdog_ms": 250
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "DRILL_CMD",
      "canId": 320,
      "encoder": "drillStop",
      "description": "Drill stop",
      "reset": [
       "speed"
      ]
     }
    ],
    "telemetry": [
     {
      "id": "rpm",
      "label": {
       "key": "testertool.rpm_label",
       "default": "RPM:"
      },
      "message": "DRILL_TELEMETRY",
      "canId": 327,
      "offset": 0,
      "width": 2
     },
     {
      "id": "endstop",
      "label": {
       "key": "testertool.endstop_label",
       "default": "Endstop:"
      },
      "message": "DRILL_TELEMETRY",
      "canId": 327,
      "offset": 2,
      "width": 1
     }
    ]
   }
  ]
 },
 "6": {
  "sections": [
   {
    "title": {
     "text": "{tool} (0x120)"
    },
    "subtitle": {
     "key": "testertool.motion_subtitle",
     "default": "One-shot move, no telemetry, no comms watchdog."
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move",
      "confirm": "motion"
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionStop",
      "args": [
       "dir"
      ],
      "description": "Stop"
     }
    ]
   }
  ]
 },
 "7": {
  "sections": [
   {
    "title": {
     "text": "{tool} (0x120)"
    },
    "subtitle": {
     "key": "testertool.motion_subtitle",
     "default": "One-shot move, no telemetry, no comms watchdog."
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move",
      "confirm": "motion"
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionStop",
      "args": [
       "dir"
      ],
      "description": "Stop"
     }
    ]
   }
  ]
 },
 "8": {
  "sections": [
   {
    "title": {
     "key": "testertool.aoi_title",
     "default": "AOI Inspection (0x150 / telemetry 0x155)"
    },
    "subtitle": {
     "key": "testertool.aoi_subtitle",
     "default": "Ring color comes from the global 0x100 command - this only sets mode/strobe."
    },
    "controls": [
     {
      "id": "mode",
      "type": "select",
      "label": {
       "key": "testertool.ring_mode_label",
       "default": "Ring Mode"
      },
      "default": 0,
      "options": [
       {
        "value": 0,
        "label": {
         "key": "testertool.mode_off",
         "default": "Off"
        }
       },
       {
        "value": 1,
        "label": {
         "key": "testertool.mode_sync",
         "default": "Synchronous strobe"
        }
       },
       {
        "value": 2,
        "label": {
         "key": "testertool.mode_fixed",
         "default": "Fixed continuous"
        }
       }
      ]
     },
     {
      "id": "period",
      "type": "number",
      "label": {
       "key": "testertool.strobe_period_label",
       "default": "Strobe period (ms)"
      },
      "min": 1,
      "max": 500,
      "default": 100
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.send",
       "default": "Send"
      },
      "message": "AOI_CMD",
      "canId": 336,
      "encoder": "aoiRingCommand",
      "args": [
       "mode",
       "period"
      ],
      "description": "AOI ring command"
     }
    ],
    "telemetry": [
     {
      "id": "endstop",
      "label": {
       "key": "testertool.endstop_label",
       "default": "Endstop:"
      },
      "message": "AOI_TELEMETRY",
      "canId": 341,
      "offset": 0,
      "width": 1
     }
    ]
   }
  ]
 },
 "9": {
  "sections": [
   {
    "title": {
     "key": "testertool.laser_title",
     "default": "Laser Engraver (0x160 / telemetry 0x165)"
    },
    "notice": {
     "key": "testertool.laser_interlock_notice",
     "default": "Interlock must be armed for power to actually do anything (firmware-side gate)."
    },
    "controls": [
     {
      "id": "power",
      "type": "range",
      "label": {
       "key": "testertool.power_label",
       "default": "Power ({{power}})",
       "param": "power"
      },
      "min": 0,
      "max": 255,
      "default": 0
     },
     {
      "id": "interlock",
      "type": "checkbox",
      "label": {
       "key": "testertool.interlock_armed",
       "default": "Interlock Armed"
      },
      "default": False
     }
    ],
    "actions": [
     {
      "type": "keepalive",
      "message": "LASER_CMD",
      "canId": 352,
      "encoder": "laserCommand",
      "args": [
       "power",
       "interlock"
      ],
      "off_encoder": "laserOff",
      "description": "Laser power command",
      "off_description": "Laser off",
      "confirm": "laser",
      "watchdog_ms": 250
     }
    ],
    "telemetry": [
     {
      "id": "endstop",
      "label": {
       "key": "testertool.endstop_label",
       "default": "Endstop:"
      },
      "message": "LASER_TELEMETRY",
      "canId": 357,
      "offset": 0,
      "width": 1
     }
    ]
   }
  ]
 },
 "10": {
  "sections": [
   {
    "title": {
     "key": "testertool.printer3d_nozzle_title",
     "default": "Nozzle Heater + Extruder (0x170, combined)"
    },
    "controls": [
     {
      "id": "temp",
      "type": "number",
      "label": {
       "key": "testertool.setpoint_0_300",
       "default": "Setpoint (0-300 C)"
      },
      "min": 0,
      "max": 300,
      "default": 200
     },
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.extruder_direction_label",
       "default": "Extruder Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "retract",
        "label": {
         "key": "testertool.retract",
         "default": "Retract"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_24bit_label",
       "default": "Steps (24-bit)"
      },
      "min": 0,
      "max": 16777215,
      "default": 0
     }
    ],
    "actions": [
     {
      "type": "keepalive",
      "message": "PRINTER_THERMAL_MOTION",
      "canId": 368,
      "encoder": "thermalMotion",
      "args": [
       "temp",
       "dir",
       0
      ],
      "off_encoder": "thermalMotionOff",
      "description": "3D printer nozzle+extruder command",
      "off_description": "3D printer nozzle+extruder command",
      "confirm": "heater",
      "confirm_value": "temp",
      "watchdog_ms": 250,
      "reset": [
       "steps"
      ]
     },
     {
      "type": "send",
      "label": {
       "key": "testertool.move_extruder_once",
       "default": "Move Extruder Once"
      },
      "message": "PRINTER_THERMAL_MOTION",
      "canId": 368,
      "encoder": "thermalMotion",
      "args": [
       "temp",
       "dir",
       "steps"
      ],
      "gate_first": True,
      "description": "3D printer nozzle+extruder command",
      "confirm": "motion"
     }
    ],
    "telemetry": [
     {
      "id": "hotend",
      "label": {
       "key": "testertool.hotend_label",
       "default": "Hotend:"
      },
      "message": "PRINTER_HOTEND_TELEMETRY",
      "canId": 373,
      "offset": 0,
      "width": 2,
      "unit": "C",
      "graph_max": 300
     }
    ]
   },
   {
    "title": {
     "key": "testertool.layer_fan_title",
     "default": "Layer fan (0x173 / telemetry 0x177)"
    },
    "controls": [
     {
      "id": "layer",
      "type": "range",
      "label": {
       "key": "testertool.layer_fan_label",
       "default": "Layer fan ({{power}})",
       "param": "power"
      },
      "min": 0,
      "max": 255,
      "default": 0
     }
    ],
    "actions": [
     {
      "type": "keepalive",
      "message": "PRINTER_LAYERFAN_CMD",
      "canId": 371,
      "encoder": "powerByte",
      "args": [
       "layer"
      ],
      "off_encoder": "powerOff",
      "description": "Layer fan power",
      "off_description": "Layer fan off",
      "watchdog_ms": 1000,
      "interval_ms": 400
     }
    ],
    "telemetry": [
     {
      "id": "layer_rpm",
      "label": {
       "key": "testertool.rpm_label",
       "default": "RPM:"
      },
      "message": "PRINTER_LAYERFAN_RPM",
      "canId": 375,
      "offset": 0,
      "width": 2
     }
    ]
   },
   {
    "title": {
     "key": "testertool.hotend_fan_title",
     "default": "Hotend fan (0x178 / telemetry 0x179)"
    },
    "subtitle": {
     "key": "testertool.no_watchdog_note",
     "default": "One-shot, no watchdog (stall detector)."
    },
    "controls": [
     {
      "id": "hotend_fan",
      "type": "range",
      "label": {
       "key": "testertool.hotend_fan_label",
       "default": "Hotend fan ({{power}})",
       "param": "power"
      },
      "min": 0,
      "max": 255,
      "default": 0
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.send",
       "default": "Send"
      },
      "message": "PRINTER_HOTENDFAN_CMD",
      "canId": 376,
      "encoder": "powerByte",
      "args": [
       "hotend_fan"
      ],
      "description": "Hotend fan power"
     }
    ],
    "telemetry": [
     {
      "id": "hotend_rpm",
      "label": {
       "key": "testertool.rpm_label",
       "default": "RPM:"
      },
      "message": "PRINTER_HOTENDFAN_RPM",
      "canId": 377,
      "offset": 0,
      "width": 2
     }
    ]
   }
  ]
 },
 "11": {
  "sections": [
   {
    "title": {
     "key": "testertool.scan_probe_title",
     "default": "Scan Probe (0x095, event-driven)"
    },
    "subtitle": {
     "key": "testertool.scan_probe_subtitle",
     "default": "Max-priority ID - purely passive, no command to send."
    },
    "telemetry": [
     {
      "id": "impacts",
      "label": {
       "key": "testertool.impacts_label",
       "default": "Impacts this session:"
      },
      "message": "IMPACT_EVENT",
      "canId": 149,
      "offset": 0,
      "width": 1,
      "format": "count",
      "match": 1
     },
     {
      "id": "last",
      "label": {
       "key": "testertool.last_impact_label",
       "default": "Last impact:"
      },
      "message": "IMPACT_EVENT",
      "canId": 149,
      "offset": 0,
      "width": 1,
      "format": "last_seen",
      "match": 1
     }
    ]
   }
  ]
 },
 "12": {
  "sections": [
   {
    "title": {
     "text": "{tool} (0x120)"
    },
    "subtitle": {
     "key": "testertool.motion_subtitle",
     "default": "One-shot move, no telemetry, no comms watchdog."
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move",
      "confirm": "motion"
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionStop",
      "args": [
       "dir"
      ],
      "description": "Stop"
     }
    ]
   }
  ]
 },
 "13": {
  "sections": [
   {
    "title": {
     "key": "testertool.electromagnet_title",
     "default": "Electromagnet (0x1B0)"
    },
    "subtitle": {
     "key": "testertool.electromagnet_subtitle",
     "default": "Latched digital command - no comms watchdog by design (see CANBUS.TXT note on 0x1B0)."
    },
    "actions": [
     {
      "type": "latched",
      "label": {
       "key": "testertool.energize",
       "default": "Energize"
      },
      "message": "ELECTROMAGNET_CMD",
      "canId": 432,
      "encoder": "electromagnetCommand",
      "description_on": "Electromagnet ON",
      "description_off": "Electromagnet OFF"
     }
    ]
   }
  ]
 },
 "14": {
  "sections": [
   {
    "title": {
     "text": "Spot Welder (0x1C0)"
    },
    "subtitle": {
     "key": "testertool.weld_subtitle_gated",
     "default": "Requires the contact sensor to be satisfied (firmware-side gate)."
    },
    "controls": [
     {
      "id": "ms",
      "type": "number",
      "label": {
       "key": "testertool.pulse_duration_label",
       "default": "Pulse duration (1-{{max}} ms)"
      },
      "min": 1,
      "max": 2000,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.fire_pulse",
       "default": "Fire Pulse"
      },
      "message": "SPOT_WELD_CMD",
      "canId": 448,
      "encoder": "weldFire",
      "args": [
       "ms"
      ],
      "description": "Spot Welder (0x1C0) fire",
      "confirm": "weld"
     }
    ]
   }
  ]
 },
 "16": {
  "sections": [
   {
    "title": {
     "text": "{tool} (0x120)"
    },
    "subtitle": {
     "key": "testertool.motion_subtitle",
     "default": "One-shot move, no telemetry, no comms watchdog."
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move",
      "confirm": "motion"
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "MOTION_CMD",
      "canId": 288,
      "encoder": "motionStop",
      "args": [
       "dir"
      ],
      "description": "Stop"
     }
    ]
   }
  ]
 },
 "17": {
  "sections": [
   {
    "title": {
     "key": "testertool.flying_probe_basic_title",
     "default": "Basic (0x243, onboard ADC)"
    },
    "subtitle": {
     "key": "testertool.flying_probe_basic_subtitle",
     "default": "Passive telemetry, no command."
    },
    "telemetry": [
     {
      "id": "raw",
      "label": {
       "key": "testertool.raw_label",
       "default": "Raw:"
      },
      "message": "FLYING_PROBE_BASIC",
      "canId": 579,
      "offset": 0,
      "width": 2
     }
    ]
   },
   {
    "title": {
     "key": "testertool.flying_probe_advanced_title",
     "default": "Advanced (ADS1115, 0x240/0x241/0x242)"
    },
    "controls": [
     {
      "id": "config",
      "type": "hex",
      "label": {
       "key": "testertool.config_register_label",
       "default": "Config register (hex)"
      },
      "default": "8583"
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.send",
       "default": "Send"
      },
      "message": "ADS1115_CONFIG",
      "canId": 576,
      "encoder": "adsConfig",
      "args": [
       "config"
      ],
      "description": "ADS1115 config"
     },
     {
      "type": "send",
      "label": {
       "key": "testertool.trigger_conversion",
       "default": "Trigger Conversion"
      },
      "message": "ADS1115_TRIGGER",
      "canId": 577,
      "encoder": "emptyFrame",
      "description": "Trigger conversion"
     },
     {
      "type": "query",
      "label": {
       "key": "testertool.read_result",
       "default": "Read Result"
      },
      "message": "ADS1115_RESULT",
      "canId": 578,
      "timeout_ms": 1000,
      "description": "Read ADS1115 result",
      "result": {
       "offset": 0,
       "width": 2,
       "signed": True
      }
     }
    ]
   }
  ]
 },
 "18": {
  "sections": [
   {
    "title": {
     "key": "testertool.uv_curing_title",
     "default": "UV Curing (0x1D0)"
    },
    "subtitle": {
     "key": "testertool.uv_curing_subtitle",
     "default": "Shares TIM1_CH1 with the laser - same 250ms watchdog."
    },
    "controls": [
     {
      "id": "power",
      "type": "range",
      "label": {
       "key": "testertool.power_label",
       "default": "Power ({{power}})",
       "param": "power"
      },
      "min": 0,
      "max": 255,
      "default": 0
     }
    ],
    "actions": [
     {
      "type": "keepalive",
      "message": "UV_CURING_CMD",
      "canId": 464,
      "encoder": "powerByte",
      "args": [
       "power"
      ],
      "off_encoder": "powerOff",
      "description": "UV curing power",
      "off_description": "UV curing off",
      "confirm": "uv",
      "watchdog_ms": 250
     }
    ]
   }
  ]
 },
 "19": {
  "sections": [
   {
    "title": {
     "key": "testertool.hotair_title",
     "default": "Hot Air Rework (0x1E0, telemetry shared with 0x135)"
    },
    "controls": [
     {
      "id": "temp",
      "type": "number",
      "label": {
       "key": "testertool.setpoint_0_445",
       "default": "Setpoint (0-445 C)"
      },
      "min": 0,
      "max": 445,
      "default": 200
     },
     {
      "id": "blower",
      "type": "range",
      "label": {
       "key": "testertool.blower_label",
       "default": "Blower ({{power}})",
       "param": "power"
      },
      "min": 0,
      "max": 255,
      "default": 0
     }
    ],
    "actions": [
     {
      "type": "keepalive",
      "message": "HOTAIR_CMD",
      "canId": 480,
      "encoder": "hotAirCommand",
      "args": [
       "temp",
       "blower"
      ],
      "off_encoder": "hotAirOff",
      "description": "Hot air rework command",
      "off_description": "Hot air rework off",
      "confirm": "heater",
      "confirm_value": "temp",
      "watchdog_ms": 250
     }
    ],
    "telemetry": [
     {
      "id": "live",
      "label": {
       "key": "testertool.live_label",
       "default": "Live:"
      },
      "message": "SOLDER_TELEMETRY",
      "canId": 309,
      "offset": 0,
      "width": 2,
      "unit": "C",
      "graph_max": 450
     }
    ]
   }
  ]
 },
 "21": {
  "sections": [
   {
    "title": {
     "text": "{tool} (0x1F0)"
    },
    "subtitle": {
     "key": "testertool.motion_subtitle",
     "default": "One-shot move, no telemetry, no comms watchdog."
    },
    "controls": [
     {
      "id": "dir",
      "type": "select",
      "label": {
       "key": "testertool.direction_label",
       "default": "Direction"
      },
      "default": "fwd",
      "options": [
       {
        "value": "fwd",
        "label": {
         "key": "testertool.forward",
         "default": "Forward"
        }
       },
       {
        "value": "rev",
        "label": {
         "key": "testertool.reverse",
         "default": "Reverse"
        }
       }
      ]
     },
     {
      "id": "steps",
      "type": "number",
      "label": {
       "key": "testertool.steps_label",
       "default": "Steps"
      },
      "min": 1,
      "max": 4294967295,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.move",
       "default": "Move"
      },
      "message": "CRIMPING_CMD",
      "canId": 496,
      "encoder": "motionMove",
      "args": [
       "dir",
       "steps"
      ],
      "description": "Move",
      "confirm": "motion"
     },
     {
      "type": "stop",
      "label": {
       "key": "testertool.stop",
       "default": "Stop"
      },
      "message": "CRIMPING_CMD",
      "canId": 496,
      "encoder": "motionStop",
      "args": [
       "dir"
      ],
      "description": "Stop"
     }
    ]
   }
  ]
 },
 "22": {
  "sections": [
   {
    "title": {
     "key": "testertool.thermal_title",
     "default": "Thermal Inspection (0x250/0x251/0x254/0x255)"
    },
    "subtitle": {
     "key": "testertool.thermal_subtitle",
     "default": "32x24 calibrated thermal image, pulled 48 chunks x 4 frames sequentially - no streaming mode."
    },
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.trigger_capture",
       "default": "Trigger Capture"
      },
      "message": "THERMAL_TRIGGER",
      "canId": 592,
      "encoder": "emptyFrame",
      "description": "Trigger thermal capture"
     },
     {
      "type": "query",
      "label": {
       "key": "testertool.check_status",
       "default": "Check Status"
      },
      "message": "THERMAL_STATUS",
      "canId": 593,
      "timeout_ms": 1000,
      "description": "Query thermal status",
      "result": {
       "offset": 0,
       "width": 1,
       "states": [
        {
         "value": 0,
         "label": {
          "key": "testertool.status_idle",
          "default": "Idle"
         }
        },
        {
         "value": 1,
         "label": {
          "key": "testertool.status_busy",
          "default": "Busy"
         }
        },
        {
         "value": 2,
         "label": {
          "key": "testertool.status_ready",
          "default": "Ready"
         }
        },
        {
         "value": 255,
         "label": {
          "key": "testertool.status_error",
          "default": "Error"
         }
        }
       ]
      }
     },
     {
      "type": "image",
      "label": {
       "key": "testertool.read_thermal_image",
       "default": "Read Thermal Image"
      },
      "message": "THERMAL_CAL_CHUNK_REQ",
      "canId": 596,
      "response": "THERMAL_CAL_CHUNK",
      "respCanId": 597,
      "timeout_ms": 300,
      "description": "Request thermal chunk",
      "chunks": 48,
      "frames_per_chunk": 4,
      "columns": 32,
      "scale": 100,
      "max_value": 100,
      "progress": {
       "key": "testertool.reading_progress",
       "default": "Reading... {{pct}}%"
      },
      "error": {
       "key": "testertool.thermal_read_failed",
       "default": "Reading the thermal image failed: {{message}}"
      }
     }
    ]
   }
  ]
 },
 "23": {
  "sections": [
   {
    "title": {
     "key": "testertool.paste_pwm_title",
     "default": "PWM Config (0x230)"
    },
    "controls": [
     {
      "id": "channel",
      "type": "number",
      "label": {
       "key": "testertool.channel_label",
       "default": "Channel (0-3)"
      },
      "min": 0,
      "max": 3,
      "default": 0
     },
     {
      "id": "freq",
      "type": "number",
      "label": {
       "key": "testertool.frequency_label",
       "default": "Frequency (Hz)"
      },
      "min": 1,
      "max": 65535,
      "default": 1000
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.configure",
       "default": "Configure"
      },
      "message": "PASTE_JETTING_CONFIG",
      "canId": 560,
      "encoder": "pasteJettingConfig",
      "args": [
       "channel",
       "freq"
      ],
      "description": "Paste jetting config"
     }
    ]
   },
   {
    "title": {
     "key": "testertool.paste_fire_title",
     "default": "Fire Pulse (0x231)"
    },
    "subtitle": {
     "key": "testertool.paste_fire_subtitle",
     "default": "Reuses the last-configured channel."
    },
    "controls": [
     {
      "id": "duty",
      "type": "number",
      "label": {
       "key": "testertool.duty_label",
       "default": "Duty (%)"
      },
      "min": 0,
      "max": 100,
      "default": 50
     },
     {
      "id": "pulse",
      "type": "number",
      "label": {
       "key": "testertool.duration_ms_label",
       "default": "Duration (ms)"
      },
      "min": 1,
      "max": 255,
      "default": 50
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.fire_pulse",
       "default": "Fire Pulse"
      },
      "message": "PASTE_JETTING_PULSE",
      "canId": 561,
      "encoder": "pasteJettingPulse",
      "args": [
       "channel",
       "duty",
       "pulse"
      ],
      "description": "Paste jetting pulse",
      "confirm": "paste"
     }
    ]
   }
  ]
 },
 "24": {
  "sections": [
   {
    "title": {
     "text": "Ultrasonic Welder (0x200)"
    },
    "subtitle": {
     "key": "testertool.weld_subtitle_ungated",
     "default": "No contact-sensor gate."
    },
    "controls": [
     {
      "id": "ms",
      "type": "number",
      "label": {
       "key": "testertool.pulse_duration_label",
       "default": "Pulse duration (1-{{max}} ms)"
      },
      "min": 1,
      "max": 2000,
      "default": 200
     }
    ],
    "actions": [
     {
      "type": "send",
      "label": {
       "key": "testertool.fire_pulse",
       "default": "Fire Pulse"
      },
      "message": "ULTRASONIC_WELD_CMD",
      "canId": 512,
      "encoder": "weldFire",
      "args": [
       "ms"
      ],
      "description": "Ultrasonic Welder (0x200) fire",
      "confirm": "weld"
     }
    ]
   }
  ]
 }
}

PANELS: dict[int, dict] = {int(key): value for key, value in _BY_NAME.items()}
