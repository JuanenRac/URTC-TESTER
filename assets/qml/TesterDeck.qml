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

    header: ToolBar {
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
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
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
                Text { text: testerBackend.uiText("QT_ACTIVITY_LOG"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: testerBackend.logs
                    clip: true
                    spacing: 4
                    delegate: Text { required property string modelData; text: modelData; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10; width: parent.width; wrapMode: Text.WrapAnywhere }
                }
            }
        }
    }
}
