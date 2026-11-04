# =============================================================================
# URTC Tester - tests/test_tool_panel_model_copy.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The model of a tool panel is a copy from the shared repository (tested there in full); here it is checked that the copy in use works
with this program's own bus view and covers every tool this program shows."""
from urtc_can import tool_panel_model as model
from urtc_can import tools_catalog
from urtc_can.tool_panels import PANELS


class Bus:
    def __init__(self, answers):
        self.answers, self.sent = answers, []

    def send_frame(self, can_id, data, description=""):
        self.sent.append((can_id, list(data)))

    def wait_for_frame(self, can_id, timeout_ms):
        return None

    def request(self, can_id, data, response_id, timeout_ms, description=""):
        self.sent.append((can_id, list(data)))
        return self.answers.get(response_id)

    def flush_frames(self, can_id=None):
        pass


def test_every_panel_belongs_to_a_tool_of_the_catalog_and_starts_with_valid_values():
    known = {tool["id"] for tool in tools_catalog.TOOLS}
    assert PANELS and set(PANELS) <= known
    for tool_id, panel in PANELS.items():
        values = model.initial_values(panel)
        for control in model.panel_controls(panel):
            assert model.clamp_control(control, values[control["id"]]) == values[control["id"]], (tool_id, control["id"])


def test_the_drill_panel_gives_the_frame_the_firmware_expects():
    panel = model.panel_of(5)
    action = panel["sections"][0]["actions"][0]
    values = {"speed": 300, "dir": "ccw"}
    values.update({k: v for k, v in model.initial_values(panel).items() if k not in values})
    assert action["canId"] == 0x140
    assert model.encode_action(action["encoder"], values, action["args"])[1] == 1


def test_a_query_goes_over_the_bus_of_this_program():
    query = next(a for p in PANELS.values() for s in p["sections"] for a in s.get("actions", []) if a["type"] == "query")
    bus = Bus({query.get("respCanId", query["canId"]): [0, 0, 1, 0]})
    assert model.ask_value(bus, query) == 256 and bus.sent[0][0] == query["canId"]
