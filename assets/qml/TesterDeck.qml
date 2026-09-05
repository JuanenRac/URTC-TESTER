// =============================================================================
// URTC Tester - Qt Quick live CAN diagnostics command deck
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.VectorImage

ApplicationWindow {
    id: window
    width: 1440
    height: 900
    minimumWidth: 1080
    minimumHeight: 680
    visible: true
    title: "URTC Tester"
    color: "#07111e"

    property color panel: "#101d30"
    property color panelAlt: "#14253b"
    property color panelBorder: "#294965"
    property color textPrimary: "#edf7ff"
    property color muted: "#91a8bd"
    property color cyan: "#38d4e6"
    property var pendingAdvancedAction: null

    component Card: Rectangle {
        color: window.panel
        radius: 16
        border.width: 1
        border.color: window.panelBorder
    }

    component GameButton: Button {
        id: control
        property color accent: window.cyan
        implicitHeight: 42
        hoverEnabled: true
        font.family: "Bahnschrift"
        font.bold: true
        contentItem: Text {
            text: control.text
            color: control.enabled ? "#f5fbff" : "#6d8294"
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 10
            color: !control.enabled ? "#122031" : (control.down ? Qt.darker(control.accent, 1.35) : (control.hovered ? Qt.lighter(control.accent, 1.13) : control.accent))
            border.width: 1
            border.color: control.enabled ? Qt.lighter(control.accent, 1.12) : "#25384b"
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: "#9eeeff"
                opacity: control.enabled ? 0.6 : 0.15
            }
        }
    }

    Dialog {
        id: motionConfirm
        modal: true
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 510)
        title: testerBackend.uiText("QT_CONFIRM_MOTION")
        standardButtons: Dialog.NoButton
        background: Rectangle {
            color: window.panel
            radius: 16
            border.width: 1
            border.color: window.cyan
        }
        contentItem: ColumnLayout {
            spacing: 12
            Text {
                Layout.fillWidth: true
                text: testerBackend.uiText("QT_CONFIRM_MOTION_HELP")
                color: window.textPrimary
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: "PROFILE #" + testerBackend.selectedToolId
                    + "  •  " + motionDirection.currentText.toUpperCase()
                    + "  •  " + motionSteps.text + " STEPS"
                color: window.cyan
                font.family: "Cascadia Mono"
                font.bold: true
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                GameButton {
                    text: testerBackend.uiText("QT_CANCEL")
                    accent: "#24465e"
                    Layout.preferredWidth: 126
                    onClicked: motionConfirm.close()
                }
                GameButton {
                    text: testerBackend.uiText("QT_CONFIRM")
                    accent: "#b86a35"
                    Layout.preferredWidth: 126
                    onClicked: {
                        motionConfirm.close()
                        testerBackend.sendMotion(motionDirection.currentText, motionSteps.text)
                    }
                }
            }
        }
    }

    Dialog {
        id: advancedConfirm
        modal: true
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 510)
        title: testerBackend.uiText("QT_CONFIRM_ACTION")
        standardButtons: Dialog.NoButton
        background: Rectangle {
            color: window.panel
            radius: 16
            border.width: 1
            border.color: "#f7b955"
        }
        contentItem: ColumnLayout {
            spacing: 12
            Text {
                Layout.fillWidth: true
                text: testerBackend.uiText("QT_CONFIRM_ACTION_HELP")
                color: window.textPrimary
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                text: "PROFILE #" + testerBackend.selectedToolId + "  •  " + testerBackend.activeTool
                color: "#f7b955"
                font.family: "Cascadia Mono"
                font.bold: true
                wrapMode: Text.WrapAnywhere
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                GameButton {
                    text: testerBackend.uiText("QT_CANCEL")
                    accent: "#24465e"
                    Layout.preferredWidth: 126
                    onClicked: advancedConfirm.close()
                }
                GameButton {
                    text: testerBackend.uiText("QT_CONFIRM")
                    accent: "#b86a35"
                    Layout.preferredWidth: 126
                    onClicked: {
                        advancedConfirm.close()
                        if (window.pendingAdvancedAction !== null) {
                            window.pendingAdvancedAction()
                            window.pendingAdvancedAction = null
                        }
                    }
                }
            }
        }
    }

    function requestAdvanced(action) {
        if (!testerBackend.canActuateSelectedProfile)
            return
        pendingAdvancedAction = action
        advancedConfirm.open()
    }

    // Same real shared confirmation dialog as requestAdvanced above, for
    // the one real destructive tool-independent utility action (F-RAM
    // erase) - gated on canUseUtilityPanels instead of
    // canActuateSelectedProfile, since this isn't a per-tool-profile
    // action at all.
    function requestUtilityAction(action) {
        if (!testerBackend.canUseUtilityPanels)
            return
        pendingAdvancedAction = action
        advancedConfirm.open()
    }

    header: ToolBar {
        // Explicit, not left implicit - a real on-screen check showed this
        // ToolBar's own Basic-style implicit sizing collapsing to 0 height
        // for this window (branding/status text all overlapping at the
        // top-left corner instead of laid out in a row), the same real bug
        // HYDRA-UMC-SUITE's own Qt Quick shell already found and fixed the
        // same way - never propagated back to this sibling app until now.
        // Sized to comfortably fit the 50px icon box plus this Card's own
        // 7px and this RowLayout's own 10px margins top and bottom
        // (50 + 2*7 + 2*10).
        height: 84
        background: Rectangle { color: "#07111e" }
        Card {
            anchors.fill: parent
            anchors.margins: 7
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Rectangle {
                    Layout.preferredWidth: 50
                    Layout.preferredHeight: 50
                    radius: 12
                    color: "#0e3045"
                    border.width: 1
                    border.color: "#2d7695"
                    VectorImage { anchors.fill: parent; anchors.margins: 7; source: testerBackend.iconSource }
                }
                ColumnLayout {
                    Layout.preferredWidth: 275
                    spacing: 0
                    Text { text: "URTC"; color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 10 }
                    Text { text: "TESTER"; color: textPrimary; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 19 }
                    Text { text: "LIVE CAN DIAGNOSTICS - SAFE TEST CONTROL"; color: muted; font.family: "Bahnschrift"; font.pixelSize: 8 }
                }
                Item { Layout.fillWidth: true }
                Text { text: testerBackend.status; color: testerBackend.connected ? "#43db9b" : muted; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 11 }
                Text { text: "v" + testerBackend.version; color: muted; font.family: "Bahnschrift"; font.pixelSize: 10 }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14
        Card {
            Layout.preferredWidth: 410
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 11
                Text { text: testerBackend.uiText("QT_TRANSPORT_GATE"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text { text: testerBackend.uiText("QT_TRANSPORT_HELP"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                ComboBox {
                    id: ports
                    Layout.fillWidth: true
                    model: testerBackend.ports
                    enabled: !testerBackend.connected && !testerBackend.busy
                    onActivated: testerBackend.selectPort(currentText)
                }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: testerBackend.uiText("BTN_REFRESH"); accent: "#24465e"; Layout.fillWidth: true; enabled: !testerBackend.connected && !testerBackend.busy; onClicked: testerBackend.scanPorts() }
                    GameButton { text: testerBackend.connected ? testerBackend.uiText("BTN_DISCONNECT") : testerBackend.uiText("BTN_CONNECT"); Layout.fillWidth: true; enabled: !testerBackend.busy; onClicked: testerBackend.toggleConnection() }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_SAFETY_MODE"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Switch {
                    id: listenOnly
                    text: checked ? testerBackend.uiText("QT_LISTEN_ONLY") : testerBackend.uiText("QT_ACTIVE_CHECKS_ARMED")
                    checked: testerBackend.listenOnly
                    enabled: !testerBackend.connected && !testerBackend.busy
                    onToggled: testerBackend.setListenOnly(checked)
                }
                Text {
                    Layout.fillWidth: true
                    color: listenOnly.checked ? "#43db9b" : "#f7b955"
                    wrapMode: Text.WordWrap
                    text: listenOnly.checked
                        ? testerBackend.uiText("QT_PASSIVE_HELP")
                        : testerBackend.uiText("QT_ACTIVE_HELP")
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_TOOL_PROFILE"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text { text: testerBackend.uiText("QT_PROFILE_GUARD"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 9 }
                ListView {
                    id: profiles
                    Layout.fillWidth: true
                    Layout.preferredHeight: 210
                    clip: true
                    model: testerBackend.toolProfiles
                    spacing: 3
                    delegate: Rectangle {
                        required property var modelData
                        width: profiles.width
                        height: 34
                        radius: 8
                        color: testerBackend.selectedToolId === modelData.id ? "#1a4967" : panelAlt
                        border.width: 1
                        border.color: testerBackend.activeToolId === modelData.id ? "#43db9b" : panelBorder
                        Row {
                            anchors.fill: parent
                            anchors.margins: 7
                            spacing: 7
                            Text { text: "#" + modelData.id; color: cyan; font.family: "Cascadia Mono"; font.bold: true; width: 26 }
                            Text { text: modelData.name; color: textPrimary; font.bold: true; width: 190; elide: Text.ElideRight }
                            Text { text: modelData.kind.toUpperCase(); color: muted; font.pixelSize: 9 }
                        }
                        MouseArea { anchors.fill: parent; enabled: !testerBackend.busy; onClicked: testerBackend.selectToolProfile(modelData.id) }
                    }
                }
                Text { text: testerBackend.uiText("QT_STAGED_LIMIT"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
            }
        }
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            // Real scroll wrapper - added alongside the new Global
            // Controls/Expansion Board/F-RAM sections below (see their
            // own header comment), since this card's real content no
            // longer reliably fits the window's own minimumHeight: 680.
            ScrollView {
                anchors.fill: parent
                anchors.margins: 16
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: parent.width
                spacing: 12
                Text { text: testerBackend.uiText("QT_IDENTITY_CHECKPOINTS"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 14 }
                Text { text: testerBackend.uiText("QT_CHECKPOINTS"); color: muted; font.family: "Bahnschrift"; font.pixelSize: 12; lineHeight: 1.55 }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_PASSIVE_WINDOW"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text { text: testerBackend.uiText("QT_PASSIVE_HELP"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                GameButton {
                    text: testerBackend.uiText("QT_CAPTURE_PASSIVE")
                    accent: "#24465e"
                    Layout.fillWidth: true
                    enabled: testerBackend.canCapturePassive
                    onClicked: testerBackend.capturePassiveWindow()
                }
                Text {
                    text: testerBackend.hasPassiveSnapshot ? testerBackend.passiveSummary : testerBackend.uiText("QT_NO_PASSIVE_FRAMES")
                    color: testerBackend.hasPassiveSnapshot ? "#43db9b" : muted
                    font.family: "Cascadia Mono"
                    font.pixelSize: 10
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(contentHeight, 70)
                    visible: testerBackend.passiveFrames.length > 0
                    model: testerBackend.passiveFrames
                    clip: true
                    spacing: 2
                    delegate: Text {
                        required property var modelData
                        text: modelData.id + "  " + modelData.data
                        color: muted
                        font.family: "Cascadia Mono"
                        font.pixelSize: 9
                        width: parent.width
                        elide: Text.ElideRight
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_ADVANCED_CONTROL"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text {
                    visible: testerBackend.activeWatchdogs.length === 0
                    text: testerBackend.uiText("QT_NO_ACTIVE_WATCHDOGS")
                    color: muted
                    font.family: "Cascadia Mono"
                    font.pixelSize: 9
                }
                Text {
                    visible: testerBackend.activeWatchdogs.length > 0
                    text: testerBackend.uiText("QT_ACTIVE_WATCHDOGS") + ": " + testerBackend.activeWatchdogs.join(", ").toUpperCase()
                    color: "#43db9b"
                    font.family: "Cascadia Mono"
                    font.bold: true
                    font.pixelSize: 9
                }
                Text {
                    visible: testerBackend.advancedControlKind === "unavailable"
                    text: testerBackend.uiText("QT_ADVANCED_UNAVAILABLE")
                    color: muted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    font.pixelSize: 10
                }
                ColumnLayout {
                    visible: testerBackend.advancedControlKind === "drill"
                    Layout.fillWidth: true
                    spacing: 7
                    Text { text: testerBackend.uiText("QT_DRILL_SPEED"); color: muted; font.pixelSize: 10 }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: drillSpeed; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        ComboBox { id: drillDirection; model: ["clockwise", "counter-clockwise"]; Layout.preferredWidth: 170 }
                        GameButton { text: testerBackend.uiText("QT_SEND_MOTION"); accent: "#b86a35"; Layout.preferredWidth: 145; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.sendDrill(drillSpeed.text, drillDirection.currentText) }) }
                    }
                }
                ColumnLayout {
                    visible: testerBackend.advancedControlKind === "aoi"
                    Layout.fillWidth: true
                    spacing: 7
                    Text { text: testerBackend.uiText("QT_AOI_MODE"); color: muted; font.pixelSize: 10 }
                    RowLayout {
                        Layout.fillWidth: true
                        ComboBox { id: aoiMode; model: ["off", "strobe", "continuous"]; Layout.preferredWidth: 150 }
                        TextField { id: aoiPeriod; text: "1000"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_SEND_MOTION"); accent: "#b86a35"; Layout.preferredWidth: 145; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.sendAoi(aoiMode.currentText, aoiPeriod.text) }) }
                    }
                }
                RowLayout {
                    visible: testerBackend.advancedControlKind === "magnet"
                    Layout.fillWidth: true
                    GameButton { text: testerBackend.uiText("QT_ENERGIZE"); accent: "#b86a35"; Layout.fillWidth: true; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.setElectromagnet(true) }) }
                    GameButton { text: testerBackend.uiText("QT_RELEASE"); accent: "#24465e"; Layout.fillWidth: true; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.setElectromagnet(false) }) }
                }
                RowLayout {
                    visible: testerBackend.advancedControlKind === "pulse"
                    Layout.fillWidth: true
                    TextField { id: weldDuration; text: "100"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_PULSE_DURATION"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton { text: testerBackend.uiText("QT_FIRE_PULSE"); accent: "#b86a35"; Layout.preferredWidth: 170; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.fireWeldPulse(weldDuration.text) }) }
                }
                ColumnLayout {
                    visible: testerBackend.advancedControlKind === "paste"
                    Layout.fillWidth: true
                    spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: pasteChannel; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_PASTE_CHANNEL"); Layout.preferredWidth: 150; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        TextField { id: pasteFrequency; text: "100"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_PASTE_FREQUENCY"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_CONFIGURE"); accent: "#24465e"; Layout.preferredWidth: 150; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.configurePasteJetting(pasteChannel.text, pasteFrequency.text) }) }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: pasteDuty; text: "50"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_PASTE_DUTY"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        TextField { id: pasteDuration; text: "10"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_PULSE_DURATION"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_FIRE_PULSE"); accent: "#b86a35"; Layout.preferredWidth: 150; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.firePastePulse(pasteChannel.text, pasteDuty.text, pasteDuration.text) }) }
                    }
                }
                ColumnLayout {
                    visible: testerBackend.advancedControlKind === "flying"
                    Layout.fillWidth: true
                    spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: adsConfig; text: "8583"; color: textPrimary; placeholderText: testerBackend.uiText("QT_ADS_CONFIG"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_CONFIGURE"); accent: "#24465e"; Layout.preferredWidth: 150; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.configureFlyingProbe(adsConfig.text) }) }
                        GameButton { text: testerBackend.uiText("QT_TRIGGER"); accent: "#24465e"; Layout.preferredWidth: 140; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.triggerFlyingProbe() }) }
                        GameButton { text: testerBackend.uiText("QT_READ_RESULT"); accent: "#b86a35"; Layout.preferredWidth: 160; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.readFlyingProbe() }) }
                    }
                    Text { text: testerBackend.flyingProbeResult; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                }
                ColumnLayout {
                    visible: testerBackend.advancedControlKind === "thermal"
                    Layout.fillWidth: true
                    spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: testerBackend.thermalSummary; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                        GameButton { text: testerBackend.uiText("QT_THERMAL_CAPTURE"); accent: "#b86a35"; Layout.preferredWidth: 230; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.captureThermalFrame() }) }
                    }
                    GridView {
                        id: thermalGrid
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(240, Math.ceil(count / 32) * 8)
                        visible: count > 0
                        model: testerBackend.thermalCells
                        cellWidth: width / 32
                        cellHeight: 8
                        clip: true
                        delegate: Rectangle {
                            required property var modelData
                            width: thermalGrid.cellWidth
                            height: thermalGrid.cellHeight
                            color: modelData.color
                            ToolTip.visible: thermalMouse.containsMouse
                            ToolTip.text: (modelData.temperature / 100.0).toFixed(2) + " C"
                            MouseArea { id: thermalMouse; anchors.fill: parent; hoverEnabled: true }
                        }
                    }
                    Text { visible: testerBackend.thermalCells.length === 0; text: testerBackend.uiText("QT_NO_THERMAL_FRAME"); color: muted; font.pixelSize: 10 }
                }
                ColumnLayout {
                    // Real, continuous telemetry - Vacuum Pickup and Scan
                    // Probe have no commands at all (see
                    // tester_tool_panels.py's own _build_vacuum_panel/
                    // _build_scan_probe_panel), so this is the one
                    // advanced-control panel with no requestAdvanced()
                    // confirmation anywhere in it - nothing here can ever
                    // transmit a real CAN frame.
                    visible: testerBackend.advancedControlKind === "vacuum" || testerBackend.advancedControlKind === "scan_probe"
                    Layout.fillWidth: true
                    spacing: 7
                    Text {
                        text: testerBackend.advancedControlKind === "vacuum" ? testerBackend.uiText("TITLE_VACUUM_TELEMETRY") : testerBackend.uiText("TITLE_SCAN_PROBE_TELEMETRY")
                        color: textPrimary; font.bold: true; font.pixelSize: 12
                    }
                    RowLayout {
                        visible: testerBackend.advancedControlKind === "vacuum"
                        Layout.fillWidth: true
                        spacing: 20
                        ColumnLayout {
                            spacing: 2
                            Text { text: testerBackend.uiText("LBL_ANALOG_READING"); color: muted; font.pixelSize: 10 }
                            Text { text: testerBackend.isWatchingTelemetry ? String(testerBackend.vacuumAdc) : "--"; color: textPrimary; font.bold: true; font.pixelSize: 14 }
                        }
                        ColumnLayout {
                            spacing: 2
                            Text { text: testerBackend.uiText("LBL_PART_DETECTED_LM393"); color: muted; font.pixelSize: 10 }
                            Text {
                                text: testerBackend.isWatchingTelemetry ? (testerBackend.vacuumDetected ? testerBackend.uiText("VAL_PART_PICKED_UP") : testerBackend.uiText("VAL_PART_NOT_DETECTED")) : "--"
                                color: testerBackend.isWatchingTelemetry && testerBackend.vacuumDetected ? "#43db9b" : textPrimary
                                font.bold: true; font.pixelSize: 14
                            }
                        }
                    }
                    RowLayout {
                        visible: testerBackend.advancedControlKind === "scan_probe"
                        Layout.fillWidth: true
                        spacing: 20
                        ColumnLayout {
                            spacing: 2
                            Text { text: testerBackend.uiText("LBL_IMPACTS_DETECTED_SESSION"); color: muted; font.pixelSize: 10 }
                            Text { text: String(testerBackend.scanProbeImpactCount); color: textPrimary; font.bold: true; font.pixelSize: 14 }
                        }
                        ColumnLayout {
                            spacing: 2
                            Text { text: testerBackend.uiText("LBL_LAST_IMPACT"); color: muted; font.pixelSize: 10 }
                            Text { text: testerBackend.scanProbeLastImpact || "--"; color: textPrimary; font.bold: true; font.pixelSize: 14 }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        GameButton {
                            text: testerBackend.uiText("QT_WATCH_TELEMETRY")
                            accent: "#24465e"
                            Layout.preferredWidth: 220
                            visible: !testerBackend.isWatchingTelemetry
                            enabled: testerBackend.canWatchTelemetry
                            onClicked: testerBackend.watchTelemetry()
                        }
                        GameButton {
                            text: testerBackend.uiText("QT_STOP_WATCHING_TELEMETRY")
                            accent: "#b86a35"
                            Layout.preferredWidth: 220
                            visible: testerBackend.isWatchingTelemetry
                            enabled: true
                            onClicked: testerBackend.stopTelemetryWatch()
                        }
                    }
                }
                RowLayout {
                    visible: testerBackend.advancedControlKind === "solder"
                    Layout.fillWidth: true
                    TextField { id: solderSetpoint; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_HEATER_SETPOINT"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton { text: testerBackend.uiText("QT_WATCHDOG_ENABLE"); accent: "#b86a35"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.setWatchdogOutput("solder", true, solderSetpoint.text, "0") }) }
                    GameButton { text: testerBackend.uiText("QT_WATCHDOG_DISABLE"); accent: "#24465e"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: testerBackend.setWatchdogOutput("solder", false, solderSetpoint.text, "0") }
                }
                ColumnLayout {
                    visible: testerBackend.advancedControlKind === "laser"
                    Layout.fillWidth: true
                    spacing: 7
                    Text { text: testerBackend.uiText("QT_INTERLOCK_ARMED"); color: "#f7b955"; font.bold: true; font.pixelSize: 10 }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: laserPower; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_LASER_POWER"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        CheckBox { id: laserInterlock; text: testerBackend.uiText("QT_INTERLOCK_ARMED"); checked: false }
                        GameButton { text: testerBackend.uiText("QT_WATCHDOG_ENABLE"); accent: "#b86a35"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile && laserInterlock.checked; onClicked: window.requestAdvanced(function() { testerBackend.setWatchdogOutput("laser", true, laserPower.text, laserInterlock.checked ? "1" : "0") }) }
                        GameButton { text: testerBackend.uiText("QT_WATCHDOG_DISABLE"); accent: "#24465e"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: testerBackend.setWatchdogOutput("laser", false, laserPower.text, "0") }
                    }
                }
                ColumnLayout {
                    visible: testerBackend.advancedControlKind === "printer"
                    Layout.fillWidth: true
                    spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: printerHeater; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_HEATER_SETPOINT"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_WATCHDOG_ENABLE"); accent: "#b86a35"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.setWatchdogOutput("printer_heater", true, printerHeater.text, "0") }) }
                        GameButton { text: testerBackend.uiText("QT_WATCHDOG_DISABLE"); accent: "#24465e"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: testerBackend.setWatchdogOutput("printer_heater", false, printerHeater.text, "0") }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: layerFanPower; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_LAYER_FAN_POWER"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_WATCHDOG_ENABLE"); accent: "#b86a35"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.setWatchdogOutput("layer_fan", true, layerFanPower.text, "0") }) }
                        GameButton { text: testerBackend.uiText("QT_WATCHDOG_DISABLE"); accent: "#24465e"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: testerBackend.setWatchdogOutput("layer_fan", false, layerFanPower.text, "0") }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: hotendFanPower; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_HOTEND_FAN_POWER"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_SEND_MOTION"); accent: "#b86a35"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.sendPrinterOneShot("hotend_fan", hotendFanPower.text, "0") }) }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: extruderSteps; text: "200"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_STEPS"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_SEND_MOTION"); accent: "#b86a35"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.sendPrinterOneShot("extruder", extruderSteps.text, printerHeater.text) }) }
                    }
                }
                RowLayout {
                    visible: testerBackend.advancedControlKind === "uv"
                    Layout.fillWidth: true
                    TextField { id: uvPower; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_LASER_POWER"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton { text: testerBackend.uiText("QT_WATCHDOG_ENABLE"); accent: "#b86a35"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.setWatchdogOutput("uv", true, uvPower.text, "0") }) }
                    GameButton { text: testerBackend.uiText("QT_WATCHDOG_DISABLE"); accent: "#24465e"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: testerBackend.setWatchdogOutput("uv", false, uvPower.text, "0") }
                }
                RowLayout {
                    visible: testerBackend.advancedControlKind === "hotair"
                    Layout.fillWidth: true
                    TextField { id: hotairSetpoint; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_HEATER_SETPOINT"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    TextField { id: hotairBlower; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: testerBackend.uiText("QT_BLOWER_POWER"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton { text: testerBackend.uiText("QT_WATCHDOG_ENABLE"); accent: "#b86a35"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.setWatchdogOutput("hotair", true, hotairSetpoint.text, hotairBlower.text) }) }
                    GameButton { text: testerBackend.uiText("QT_WATCHDOG_DISABLE"); accent: "#24465e"; Layout.preferredWidth: 200; enabled: testerBackend.canActuateSelectedProfile; onClicked: testerBackend.setWatchdogOutput("hotair", false, hotairSetpoint.text, hotairBlower.text) }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                GameButton { text: testerBackend.uiText("QT_PROBE"); Layout.fillWidth: true; enabled: testerBackend.canProbe; onClicked: testerBackend.probeIdentity() }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 104
                    radius: 10
                    color: panelAlt
                    border.width: 1
                    border.color: panelBorder
                    Column {
                        anchors.fill: parent
                        anchors.margins: 11
                        spacing: 5
                        Text { text: testerBackend.uiText("QT_ACTIVE_TOOL"); color: cyan; font.bold: true; font.pixelSize: 10 }
                        Text { text: testerBackend.activeTool; color: textPrimary; width: parent.width; wrapMode: Text.WordWrap }
                        Text { text: testerBackend.boardVersion; color: muted; width: parent.width; elide: Text.ElideRight; font.pixelSize: 11 }
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_MOTION_CONTROL"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text {
                    text: testerBackend.canSendMotion ? testerBackend.uiText("QT_PROFILE_GUARD") : testerBackend.uiText("QT_PROFILE_NOT_MATCHED")
                    color: testerBackend.canSendMotion ? "#43db9b" : "#f7b955"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    font.pixelSize: 9
                }
                RowLayout {
                    Layout.fillWidth: true
                    ComboBox { id: motionDirection; model: ["forward", "reverse"]; Layout.preferredWidth: 120; enabled: testerBackend.canSendMotion }
                    TextField {
                        id: motionSteps
                        text: "200"
                        inputMethodHints: Qt.ImhDigitsOnly
                        color: textPrimary
                        placeholderText: testerBackend.uiText("QT_STEPS")
                        Layout.fillWidth: true
                        enabled: testerBackend.canSendMotion
                        background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder }
                    }
                    GameButton {
                        text: testerBackend.uiText("QT_SEND_MOTION")
                        accent: "#b86a35"
                        Layout.preferredWidth: 145
                        enabled: testerBackend.canSendMotion
                        onClicked: motionConfirm.open()
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }

                // -- Global Controls / Expansion Board / F-RAM - real,
                // tool-independent utility panels (Status LED/ring/OLED,
                // CONN_EXPANSION's raw SPI passthrough + TMC_DIAG0, and
                // the FM24CL64B's recovered state + read-only EEPROM
                // fields), matching the 3 real Tkinter tabs of the same
                // names. Always shown - unlike everything above, none of
                // this depends on which tool profile is selected at all
                // (see tester_common_panels.py's own CommonPanelsMixin).
                Text { text: testerBackend.uiText("QT_GLOBAL_CONTROLS"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    TextField { id: statusR; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: "R"; Layout.preferredWidth: 60; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    TextField { id: statusG; text: "255"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: "G"; Layout.preferredWidth: 60; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    TextField { id: statusB; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: "B"; Layout.preferredWidth: 60; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    Text { text: testerBackend.uiText("LBL_STATUS_LED_OVERRIDE"); color: muted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    TextField { id: ringR; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: "R"; Layout.preferredWidth: 60; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    TextField { id: ringG; text: "0"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: "G"; Layout.preferredWidth: 60; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    TextField { id: ringB; text: "255"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; placeholderText: "B"; Layout.preferredWidth: 60; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    CheckBox { id: ringOn; text: testerBackend.uiText("CHK_RING_ON"); contentItem: Text { text: ringOn.text; color: muted; leftPadding: ringOn.indicator.width + 4; verticalAlignment: Text.AlignVCenter; font.pixelSize: 9 } }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    ComboBox { id: oledMode; model: ["standard", "night", "standby"]; Layout.preferredWidth: 130 }
                    GameButton {
                        text: testerBackend.uiText("BTN_SEND")
                        accent: "#24465e"
                        Layout.fillWidth: true
                        enabled: testerBackend.canUseUtilityPanels
                        onClicked: testerBackend.sendGlobalStatus(statusR.text, statusG.text, statusB.text, oledMode.currentText, ringR.text, ringG.text, ringB.text, ringOn.checked)
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_EXPANSION_BOARD"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    TextField { id: spiBytes; text: "01 02 03 04"; color: textPrimary; placeholderText: testerBackend.uiText("LBL_SPI_BYTES_TO_SEND"); Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton { text: testerBackend.uiText("BTN_SEND"); accent: "#24465e"; Layout.preferredWidth: 130; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.sendExpansionSpi(spiBytes.text) }
                }
                Text { text: testerBackend.spiResponseText; visible: testerBackend.spiResponseText !== ""; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY_DIAG0"); accent: "#24465e"; Layout.preferredWidth: 170; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryDiag0() }
                    Text { text: testerBackend.diag0Text; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_FRAM_PANEL"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY_STATE"); accent: "#24465e"; Layout.preferredWidth: 160; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryFramState() }
                    GameButton {
                        text: testerBackend.uiText("BTN_ERASE_FRAM")
                        accent: "#b86a35"
                        Layout.preferredWidth: 160
                        enabled: testerBackend.canUseUtilityPanels
                        onClicked: window.requestUtilityAction(function() { testerBackend.eraseFram() })
                    }
                }
                Text { text: testerBackend.framStateText; visible: testerBackend.framStateText !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY") + " " + testerBackend.uiText("LBL_EXPANSION_BOARD_TYPE"); accent: "#24465e"; Layout.preferredWidth: 220; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryExpansionBoardType() }
                    Text { text: testerBackend.expansionBoardTypeText; color: muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY") + " " + testerBackend.uiText("LBL_MLX_SENSOR_VARIANT"); accent: "#24465e"; Layout.preferredWidth: 220; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryMlxSensorVariant() }
                    Text { text: testerBackend.mlxSensorVariantText; color: muted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY") + " " + testerBackend.uiText("LBL_FREE_TOOL_CONFIG"); accent: "#24465e"; Layout.preferredWidth: 220; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryFreeToolConfig() }
                    Text { text: testerBackend.freeToolConfigText; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY") + " " + testerBackend.uiText("LBL_PERIPHERAL_INFO"); accent: "#24465e"; Layout.preferredWidth: 220; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryPeripheralInfo() }
                    Text { text: testerBackend.peripheralInfoText; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                // -- Custom CAN Frame - the one real tool-independent
                // action with no validation beyond frame shape (see
                // HELP_SENDS_RAW_FRAME's own real text below): whatever
                // is typed goes on the bus exactly as typed, unlike
                // every other GameButton in this deck which only ever
                // sends a specific, already-known-safe frame. Periodic
                // re-send is a real QML Timer, not a Python thread - see
                // testerBackend.customFramePeriodicActive's own comment
                // in qt_tester.py for why.
                Text { text: testerBackend.uiText("TAB_CUSTOM_FRAME"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text { text: testerBackend.uiText("LBL_CAN_ID_HEX"); color: muted; font.pixelSize: 10 }
                    TextField { id: customId; text: "100"; color: textPrimary; Layout.preferredWidth: 80; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    Text { text: testerBackend.uiText("LBL_DATA_BYTES_HEX"); color: muted; font.pixelSize: 10 }
                    TextField { id: customData; text: ""; color: textPrimary; Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    GameButton {
                        text: testerBackend.uiText("BTN_SEND_ONCE")
                        accent: "#24465e"
                        Layout.preferredWidth: 130
                        enabled: testerBackend.canUseUtilityPanels
                        onClicked: testerBackend.sendCustomFrame(customId.text, customData.text)
                    }
                    CheckBox {
                        id: customPeriodic
                        text: testerBackend.uiText("LBL_REPEAT_EVERY")
                        checked: testerBackend.customFramePeriodicActive
                        enabled: testerBackend.canUseUtilityPanels
                        contentItem: Text { text: customPeriodic.text; color: muted; leftPadding: customPeriodic.indicator.width + 4; verticalAlignment: Text.AlignVCenter; font.pixelSize: 10 }
                        onToggled: {
                            testerBackend.setCustomFramePeriodic(checked, customId.text, customData.text, customInterval.text)
                            // Explicit re-sync rather than relying on the
                            // checked: binding above surviving user
                            // interaction (QML breaks a property binding
                            // on direct/interactive assignment) - this is
                            // what makes a backend rejection (not
                            // connected, bad hex) visibly revert the box,
                            // matching the legacy panel's own
                            // custom_periodic_var.set(False).
                            checked = testerBackend.customFramePeriodicActive
                        }
                    }
                    TextField { id: customInterval; text: "100"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; Layout.preferredWidth: 60; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    Text { text: testerBackend.uiText("LBL_MS_UNIT"); color: muted; font.pixelSize: 10 }
                }
                Timer {
                    id: customFrameTimer
                    interval: Math.max(10, parseInt(customInterval.text) || 100)
                    running: testerBackend.customFramePeriodicActive
                    repeat: true
                    onTriggered: testerBackend.sendCustomFramePeriodicTick(customId.text, customData.text)
                }
                Text {
                    text: testerBackend.uiText("HELP_SENDS_RAW_FRAME")
                    color: "#f7b955"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    font.pixelSize: 9
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_ACTIVITY_LOG"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                ListView {
                    Layout.fillWidth: true
                    // Was Layout.fillHeight: true - meaningless now that
                    // this whole ColumnLayout lives inside a ScrollView
                    // (see this Card's own comment above) rather than a
                    // fixed-height parent; a real, generous fixed
                    // viewport instead, matching the passive-frames
                    // ListView just above in this same file.
                    Layout.preferredHeight: 220
                    model: testerBackend.logs
                    clip: true
                    spacing: 4
                    delegate: Text { required property string modelData; text: modelData; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10; width: parent.width; wrapMode: Text.WrapAnywhere }
                }
            }
            }
        }
    }
}
