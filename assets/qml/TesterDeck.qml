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
                Text { text: "TRANSPORT GATE"; color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Text { text: "Select a serial SLCAN port or a Linux SocketCAN interface."; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                ComboBox {
                    id: ports
                    Layout.fillWidth: true
                    model: testerBackend.ports
                    enabled: !testerBackend.connected && !testerBackend.busy
                    onActivated: testerBackend.selectPort(currentText)
                }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: "REFRESH"; accent: "#24465e"; Layout.fillWidth: true; enabled: !testerBackend.connected && !testerBackend.busy; onClicked: testerBackend.scanPorts() }
                    GameButton { text: testerBackend.connected ? "DISCONNECT" : "CONNECT"; Layout.fillWidth: true; enabled: !testerBackend.busy; onClicked: testerBackend.toggleConnection() }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: "SAFETY MODE"; color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                Switch {
                    id: listenOnly
                    text: checked ? "LISTEN-ONLY (NO CAN TX)" : "ACTIVE CHECKS ARMED"
                    checked: testerBackend.listenOnly
                    enabled: !testerBackend.connected && !testerBackend.busy
                    onToggled: testerBackend.setListenOnly(checked)
                }
                Text {
                    Layout.fillWidth: true
                    color: listenOnly.checked ? "#43db9b" : "#f7b955"
                    wrapMode: Text.WordWrap
                    text: listenOnly.checked
                        ? "Passive transport mode. Probe commands are blocked."
                        : "Identity probe transmits only documented queries 0x110 and 0x7F8."
                }
                Item { Layout.fillHeight: true }
                Text { text: "This staged deck does not expose any tool actuator controls."; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
            }
        }
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                Text { text: "IDENTITY & HEALTH CHECKPOINTS"; color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 14 }
                Text { text: "1  Connect to the selected production transport\n2  Explicitly arm active checks, if required\n3  Query active tool and board version\n4  Preserve a transparent session log"; color: muted; font.family: "Bahnschrift"; font.pixelSize: 12; lineHeight: 1.55 }
                GameButton { text: "PROBE ACTIVE TOOL + VERSION"; Layout.fillWidth: true; enabled: testerBackend.canProbe; onClicked: testerBackend.probeIdentity() }
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
                        Text { text: "ACTIVE TOOL"; color: cyan; font.bold: true; font.pixelSize: 10 }
                        Text { text: testerBackend.activeTool; color: textPrimary; width: parent.width; wrapMode: Text.WordWrap }
                        Text { text: testerBackend.boardVersion; color: muted; width: parent.width; elide: Text.ElideRight; font.pixelSize: 11 }
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: "ACTIVITY LOG"; color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
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
