// =============================================================================
// URTC Tester - Qt Quick live CAN diagnostics command deck
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0-or-later - see LICENSE
// =============================================================================
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
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
                        testerBackend.sendMotion(motionDirection.currentValue, motionSteps.text)
                    }
                }
            }
        }
    }

    FileDialog {
        id: saveLogDialog
        title: testerBackend.uiText("MENU_SAVE_LOGS")
        fileMode: FileDialog.SaveFile
        nameFilters: ["Text (*.txt)"]
        onAccepted: testerBackend.saveLogText(selectedFile.toString())
    }
    FileDialog {
        id: readoutCsvDialog
        title: testerBackend.uiText("BTN_EXPORT_CSV")
        fileMode: FileDialog.SaveFile
        nameFilters: ["CSV (*.csv)"]
        onAccepted: testerBackend.exportReadoutCsv(selectedFile.toString())
    }

    FileDialog {
        id: replayOpenDialog
        title: testerBackend.uiText("BTN_REPLAY_OPEN")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Bus traces (*.trc *.asc)", "All files (*)"]
        onAccepted: testerBackend.openReplay(selectedFile.toString())
    }
    FileDialog {
        id: blackBoxOpenDialog
        title: testerBackend.uiText("BTN_BLACKBOX_OPEN")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Black box records (*.json *.csv)", "All files (*)"]
        onAccepted: testerBackend.openBlackBox(selectedFile.toString())
    }

    HelpDialog {
        id: helpDialog
        objectName: "helpDialog"
        model: testerBackend.help
        panelColor: window.panel
        borderColor: window.panelBorder
        textColor: window.textPrimary
        mutedColor: window.muted
        accentColor: window.cyan
    }

    UpdateDialog {
        id: updateDialog
        objectName: "updateDialog"
        model: testerBackend.updates
        panelColor: window.panel
        borderColor: window.panelBorder
        textColor: window.textPrimary
        mutedColor: window.muted
        accentColor: window.cyan
    }

    Dialog {
        id: aboutDialog
        anchors.centerIn: parent
        modal: true
        width: Math.min(parent.width - 48, 640)
        height: Math.min(parent.height - 48, 560)
        title: testerBackend.uiText("TITLE_ABOUT")
        standardButtons: Dialog.Close
        property string shownText: ""
        onOpened: shownText = ""
        background: Rectangle { color: window.panel; radius: 16; border.width: 1; border.color: window.panelBorder }
        contentItem: ColumnLayout {
            spacing: 10
            Text { text: testerBackend.aboutText; color: window.textPrimary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                GameButton { text: testerBackend.uiText("MENU_README"); accent: "#24465e"; Layout.fillWidth: true; onClicked: aboutDialog.shownText = testerBackend.readmeText() }
                GameButton { text: testerBackend.uiText("MENU_LICENSE"); accent: "#24465e"; Layout.fillWidth: true; onClicked: aboutDialog.shownText = testerBackend.licenseText() }
                GameButton { text: testerBackend.uiText("MENU_GITHUB"); accent: "#24465e"; Layout.fillWidth: true; onClicked: Qt.openUrlExternally(testerBackend.githubUrl) }
            }
            ScrollView {
                visible: aboutDialog.shownText.length > 0
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                TextArea {
                    text: aboutDialog.shownText
                    readOnly: true
                    wrapMode: Text.WordWrap
                    color: window.textPrimary
                    font.family: "Cascadia Mono"
                    font.pixelSize: 10
                    background: Rectangle { color: window.panelAlt; radius: 8 }
                }
            }
        }
    }

    Dialog {
        id: selfTestConfirm
        modal: true
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 510)
        title: testerBackend.uiText("TITLE_RUN_SELF_TEST_Q")
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
                text: testerBackend.uiText("MSG_SELF_TEST_CONFIRM")
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
                    onClicked: selfTestConfirm.close()
                }
                GameButton {
                    text: testerBackend.uiText("QT_CONFIRM")
                    accent: "#b86a35"
                    Layout.preferredWidth: 126
                    onClicked: { selfTestConfirm.close(); testerBackend.runSelfTest() }
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
                Text { text: testerBackend.status; color: testerBackend.statusColor; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 11 }
                Text { visible: testerBackend.busHealthText.length > 0; text: testerBackend.busHealthText; color: "#ee6b80"; font.bold: true; font.pixelSize: 11; Layout.maximumWidth: 260; elide: Text.ElideRight }
                Text {
                    id: busStatsText
                    visible: testerBackend.connected
                    color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10
                    Timer {
                        interval: 1000; running: testerBackend.connected; repeat: true; triggeredOnStart: true
                        onTriggered: busStatsText.text = testerBackend.refreshBusStats()
                    }
                }
                ComboBox {
                    id: languageBox
                    model: testerBackend.languageNames
                    currentIndex: testerBackend.languageIndex
                    Layout.preferredWidth: 130
                    font.pixelSize: 11
                    onActivated: function(index) { languageNotice.text = testerBackend.selectLanguage(index) }
                }
                Text { id: languageNotice; visible: text !== ""; color: "#e0b04a"; font.pixelSize: 10; Layout.maximumWidth: 220; wrapMode: Text.WordWrap }
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
                ComboBox {
                    Layout.fillWidth: true
                    model: testerBackend.bitrates
                    currentIndex: Math.max(0, testerBackend.bitrates.indexOf(testerBackend.selectedBitrate))
                    enabled: !testerBackend.connected && !testerBackend.busy
                    onActivated: testerBackend.selectBitrate(currentText)
                }
                RowLayout {
                    Layout.fillWidth: true
                    GameButton { text: testerBackend.uiText("BTN_REFRESH"); accent: "#24465e"; Layout.fillWidth: true; enabled: !testerBackend.connected && !testerBackend.busy; onClicked: testerBackend.scanPorts() }
                    GameButton { text: testerBackend.uiText("BTN_AUTO_DETECT"); accent: "#24465e"; Layout.fillWidth: true; enabled: !testerBackend.connected && !testerBackend.busy; onClicked: testerBackend.autoDetectBitrate() }
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
                // Real-time-window CAN bus load indicator - the load
                // percentage itself comes from testerBackend's own real
                // frame count/size tracking during the passive capture
                // window (see qt_tester.py's _passive_capture_worker),
                // not a simulated or client-side-guessed value. Only
                // visible once a real window has actually been captured.
                RowLayout {
                    Layout.fillWidth: true
                    visible: testerBackend.hasPassiveSnapshot
                    spacing: 8
                    Text {
                        text: testerBackend.uiText("QT_BUS_LOAD")
                        color: muted
                        font.family: "Bahnschrift"
                        font.pixelSize: 9
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 10
                        radius: 5
                        color: window.panelAlt
                        border.width: 1
                        border.color: window.panelBorder
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            radius: 5
                            width: parent.width * Math.min(testerBackend.passiveLoadPercent / 100.0, 1.0)
                            color: testerBackend.passiveLoadPercent >= 80 ? "#e05252"
                                   : testerBackend.passiveLoadPercent >= 40 ? "#e0c552"
                                   : "#43db9b"
                        }
                    }
                    Text {
                        text: testerBackend.passiveLoadPercent.toFixed(1) + "%"
                        color: textPrimary
                        font.family: "Cascadia Mono"
                        font.bold: true
                        font.pixelSize: 10
                        Layout.preferredWidth: 44
                    }
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
                GameButton {
                    visible: testerBackend.connected && !testerBackend.listenOnly
                    text: testerBackend.uiText("QT_STOP_ALL_OUTPUTS")
                    accent: "#a33a3a"
                    Layout.preferredWidth: 200
                    onClicked: testerBackend.stopAllOutputs()
                }
                Text {
                    visible: testerBackend.advancedControlKind === "unavailable"
                    text: testerBackend.noHandlerText
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
                        ComboBox { id: drillDirection; textRole: "label"; valueRole: "value"; model: [{ value: "clockwise", label: testerBackend.uiText("OPT_CLOCKWISE") }, { value: "counter-clockwise", label: testerBackend.uiText("OPT_COUNTER_CLOCKWISE") }]; Layout.preferredWidth: 170 }
                        GameButton { text: testerBackend.uiText("QT_SEND_MOTION"); accent: "#b86a35"; Layout.preferredWidth: 145; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.sendDrill(drillSpeed.text, drillDirection.currentValue) }) }
                    }
                }
                ColumnLayout {
                    visible: testerBackend.advancedControlKind === "aoi"
                    Layout.fillWidth: true
                    spacing: 7
                    Text { text: testerBackend.uiText("QT_AOI_MODE"); color: muted; font.pixelSize: 10 }
                    RowLayout {
                        Layout.fillWidth: true
                        ComboBox { id: aoiMode; textRole: "label"; valueRole: "value"; model: [{ value: "off", label: testerBackend.uiText("OPT_OFF") }, { value: "strobe", label: testerBackend.uiText("OPT_SYNCHRONOUS_STROBE") }, { value: "continuous", label: testerBackend.uiText("OPT_FIXED_CONTINUOUS") }]; Layout.preferredWidth: 150 }
                        TextField { id: aoiPeriod; text: "5"; inputMethodHints: Qt.ImhDigitsOnly; color: textPrimary; Layout.fillWidth: true; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                        GameButton { text: testerBackend.uiText("QT_SEND_MOTION"); accent: "#b86a35"; Layout.preferredWidth: 145; enabled: testerBackend.canActuateSelectedProfile; onClicked: window.requestAdvanced(function() { testerBackend.sendAoi(aoiMode.currentValue, aoiPeriod.text) }) }
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
                        Layout.preferredHeight: Math.min(240, Math.ceil(count / testerBackend.thermalColumns) * 8)
                        visible: count > 0
                        model: testerBackend.thermalCells
                        cellWidth: width / testerBackend.thermalColumns
                        cellHeight: 8
                        clip: true
                        delegate: Rectangle {
                            required property var modelData
                            width: thermalGrid.cellWidth
                            height: thermalGrid.cellHeight
                            color: modelData.color
                            ToolTip.visible: thermalMouse.containsMouse
                            ToolTip.text: modelData.missing ? "--" : (modelData.temperature / 100.0).toFixed(2) + " C"
                            MouseArea { id: thermalMouse; anchors.fill: parent; hoverEnabled: true }
                        }
                    }
                    Text { visible: testerBackend.thermalCells.length === 0; text: testerBackend.uiText("QT_NO_THERMAL_FRAME"); color: muted; font.pixelSize: 10 }
                }
                ColumnLayout {
                    // Live readouts of the tool's own broadcasts (temperature, RPM, endstop). Nothing here transmits,
                    // so it works in listen-only mode and next to a running output.
                    visible: testerBackend.readoutsAvailable
                    Layout.fillWidth: true
                    spacing: 7
                    Repeater {
                        model: testerBackend.readoutItems
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 12
                            Text { text: modelData.label; color: muted; font.pixelSize: 11; Layout.preferredWidth: 200 }
                            Text { text: testerBackend.isWatchingReadouts ? modelData.text : "--"; color: textPrimary; font.bold: true; font.pixelSize: 14 }
                        }
                    }
                    Canvas {
                        id: readoutGraph
                        visible: testerBackend.readoutHasGraph
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        property var points: testerBackend.readoutGraphPoints
                        onPointsChanged: requestPaint()
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.fillStyle = "#07111e"
                            ctx.fillRect(0, 0, width, height)
                            ctx.strokeStyle = "#294965"
                            ctx.lineWidth = 1
                            for (var g = 0; g <= 2; g++) {
                                var gy = height - g * height / 2
                                ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(width, gy); ctx.stroke()
                            }
                            if (points.length < 2 || testerBackend.readoutGraphMax <= 0)
                                return
                            ctx.strokeStyle = "#38d4e6"
                            ctx.lineWidth = 2
                            ctx.beginPath()
                            for (var i = 0; i < points.length; i++) {
                                var x = i * width / 59
                                var y = height - Math.max(0, Math.min(testerBackend.readoutGraphMax, points[i])) / testerBackend.readoutGraphMax * height
                                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                            }
                            ctx.stroke()
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
                            onClicked: testerBackend.stopTelemetryWatch()
                        }
                        GameButton {
                            text: testerBackend.uiText("BTN_EXPORT_CSV")
                            accent: "#24465e"
                            Layout.preferredWidth: 160
                            visible: testerBackend.readoutHasGraph
                            onClicked: readoutCsvDialog.open()
                        }
                    }
                }
                ColumnLayout {
                    // Real, continuous telemetry - Vacuum Pickup and Scan
                    // Probe have no commands at all, so this is the one
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
                    Text { text: testerBackend.uiText("QT_EXTRUDER_KEEPALIVE_NOTE"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
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
                GameButton {
                    text: testerBackend.uiText("BTN_RUN_SELF_TEST")
                    Layout.fillWidth: true
                    accent: "#b86a35"
                    enabled: testerBackend.canSelfTest
                    onClicked: selfTestConfirm.open()
                }
                Repeater {
                    model: testerBackend.selfTestLines
                    delegate: Text {
                        required property var modelData
                        Layout.fillWidth: true
                        text: "[" + modelData.status + "] " + modelData.text
                        color: modelData.status === "PASS" ? "#43db9b" : (modelData.status === "FAIL" ? "#ee6b80" : muted)
                        font.family: "Cascadia Mono"
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
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
                    ComboBox { id: motionDirection; textRole: "label"; valueRole: "value"; model: [{ value: "forward", label: testerBackend.uiText("OPT_FORWARD") }, { value: "reverse", label: testerBackend.uiText("OPT_REVERSE") }]; Layout.preferredWidth: 120; enabled: testerBackend.canSendMotion }
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
                    GameButton {
                        text: testerBackend.uiText("QT_STOP_MOTION")
                        accent: "#a33a3a"
                        Layout.preferredWidth: 100
                        enabled: testerBackend.canSendMotion
                        onClicked: testerBackend.stopMotion()
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }

                // -- Global Controls / Expansion Board / F-RAM - real,
                // tool-independent utility panels (Status LED/ring/OLED,
                // CONN_EXPANSION's raw SPI passthrough + TMC_DIAG0, and
                // the FM24CL64B's recovered state + read-only EEPROM
                // fields). Always shown - unlike everything above, none of
                // this depends on which tool profile is selected at all.
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
                    ComboBox { id: oledMode; textRole: "label"; valueRole: "value"; model: [{ value: "standard", label: testerBackend.uiText("OPT_STANDARD") }, { value: "night", label: testerBackend.uiText("OPT_NIGHT") }, { value: "standby", label: testerBackend.uiText("OPT_STANDBY") }]; Layout.preferredWidth: 130 }
                    GameButton {
                        text: testerBackend.uiText("BTN_SEND")
                        accent: "#24465e"
                        Layout.fillWidth: true
                        enabled: testerBackend.canUseUtilityPanels
                        onClicked: testerBackend.sendGlobalStatus(statusR.text, statusG.text, statusB.text, oledMode.currentValue, ringR.text, ringG.text, ringB.text, ringOn.checked)
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
                    GameButton { text: testerBackend.uiText("BTN_QUERY_THERMAL_STATS"); accent: "#24465e"; Layout.preferredWidth: 190; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryThermalStats() }
                }
                Text { text: testerBackend.framStateText; visible: testerBackend.framStateText !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                Text { text: testerBackend.thermalStatsText; visible: testerBackend.thermalStatsText !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
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
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY") + " " + testerBackend.uiText("LBL_FEEDER_POSITION"); accent: "#24465e"; Layout.preferredWidth: 220; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryFeederPosition() }
                    GameButton {
                        text: testerBackend.uiText("BTN_RESET_FEEDER_POSITION")
                        accent: "#b86a35"
                        Layout.preferredWidth: 200
                        enabled: testerBackend.canUseUtilityPanels
                        onClicked: window.requestUtilityAction(function() { testerBackend.resetFeederPosition() })
                    }
                    Text { text: testerBackend.feederPositionText; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                }
                Text { text: testerBackend.uiText("HELP_FEEDER_POSITION_OPEN_LOOP"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                Text { text: testerBackend.uiText("QT_EXTRAS_PANEL"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_READ_BLACK_BOX"); accent: "#24465e"; Layout.preferredWidth: 190; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.readBlackBox() }
                    CheckBox { text: testerBackend.uiText("LBL_AUTO_BLACK_BOX"); checked: testerBackend.autoBlackBox; font.pixelSize: 11; onToggled: testerBackend.setAutoBlackBox(checked) }
                }
                Text { text: testerBackend.blackBoxText; visible: testerBackend.blackBoxText !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: testerBackend.uiText("TITLE_BLACKBOX_VIEW"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    GameButton { text: testerBackend.uiText("BTN_BLACKBOX_OPEN"); accent: "#24465e"; Layout.preferredWidth: 280; onClicked: blackBoxOpenDialog.open() }
                }
                Text { visible: testerBackend.blackBoxViewNotice !== ""; text: testerBackend.blackBoxViewNotice; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                Text { visible: !testerBackend.hasBlackBoxView; text: testerBackend.uiText("LBL_BLACKBOX_VIEW_EMPTY"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                Canvas {
                    id: blackBoxChart
                    visible: testerBackend.hasBlackBoxView
                    Layout.fillWidth: true
                    Layout.preferredHeight: 170
                    property var series: testerBackend.blackBoxSeries
                    onSeriesChanged: requestPaint()
                    onWidthChanged: requestPaint()
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        ctx.fillStyle = "#07131c"
                        ctx.fillRect(0, 0, width, height)
                        var s = series
                        if (!s || !s.ticks || s.ticks.length === 0) return
                        var padL = 34, padR = 8, padT = 8, padB = 8
                        var w = width - padL - padR, h = height - padT - padB
                        var span = Math.max(1, s.span_ms)
                        var range = Math.max(1, s.maximum - s.minimum)
                        function px(i) { return padL + (s.ticks[i] / span) * w }
                        function py(t) { return padT + h - ((t - s.minimum) / range) * h }
                        ctx.strokeStyle = "#1c3548"; ctx.fillStyle = "#91a8bd"; ctx.lineWidth = 1; ctx.font = "9px sans-serif"
                        for (var g = 0; g <= 4; g++) {
                            var value = s.minimum + (range * g) / 4
                            var y = py(value)
                            ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(width - padR, y); ctx.stroke()
                            ctx.fillText(String(Math.round(value)), 2, y + 3)
                        }
                        function line(values, color) {
                            ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath()
                            for (var i = 0; i < values.length; i++) {
                                if (i === 0) ctx.moveTo(px(i), py(values[i])); else ctx.lineTo(px(i), py(values[i]))
                            }
                            ctx.stroke()
                        }
                        line(s.target, "#f3ba55")
                        line(s.current, "#43db9b")
                        if (s.trigger >= 0) {
                            ctx.strokeStyle = "#ee6b80"; ctx.lineWidth = 2
                            ctx.beginPath(); ctx.moveTo(px(s.trigger), padT); ctx.lineTo(px(s.trigger), padT + h); ctx.stroke()
                        }
                    }
                }
                RowLayout {
                    visible: testerBackend.hasBlackBoxView
                    Layout.fillWidth: true
                    spacing: 12
                    Rectangle { width: 14; height: 3; color: "#43db9b" }
                    Text { text: testerBackend.uiText("LBL_BLACKBOX_LEGEND_CURRENT"); color: muted; font.pixelSize: 10 }
                    Rectangle { width: 14; height: 3; color: "#f3ba55" }
                    Text { text: testerBackend.uiText("LBL_BLACKBOX_LEGEND_TARGET"); color: muted; font.pixelSize: 10 }
                    Rectangle { width: 3; height: 12; color: "#ee6b80" }
                    Text { text: testerBackend.uiText("LBL_BLACKBOX_LEGEND_TRIGGER"); color: muted; font.pixelSize: 10 }
                    Item { Layout.fillWidth: true }
                    Text { text: testerBackend.blackBoxSpanText; color: muted; font.pixelSize: 10 }
                }
                Rectangle {
                    visible: testerBackend.hasBlackBoxView
                    Layout.fillWidth: true
                    Layout.preferredHeight: 110
                    color: "#07131c"; radius: 8; border.width: 1; border.color: panelBorder
                    ListView {
                        anchors.fill: parent; anchors.margins: 6; clip: true
                        model: testerBackend.blackBoxLines
                        delegate: Text { width: ListView.view.width; text: modelData; color: textPrimary; font.family: "Consolas"; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    CheckBox { id: featRamps; text: testerBackend.uiText("LBL_FEATURE_MOTION_RAMPS"); font.pixelSize: 10 }
                    CheckBox { id: featHealth; text: testerBackend.uiText("LBL_FEATURE_HEALTH_PROFILE"); font.pixelSize: 10 }
                    CheckBox { id: featHsi; text: testerBackend.uiText("LBL_FEATURE_HSI_AUTOTRIM"); font.pixelSize: 10 }
                    CheckBox { id: featPid; text: testerBackend.uiText("LBL_FEATURE_THERMAL_PID"); font.pixelSize: 10 }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY_FEATURES"); accent: "#24465e"; Layout.preferredWidth: 190; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryFeatures() }
                    GameButton {
                        text: testerBackend.uiText("BTN_WRITE_FEATURES")
                        accent: "#b86a35"
                        Layout.preferredWidth: 260
                        enabled: testerBackend.canUseUtilityPanels
                        onClicked: window.requestUtilityAction(function() { testerBackend.writeFeatures((featRamps.checked ? 1 : 0) + (featHealth.checked ? 2 : 0) + (featHsi.checked ? 4 : 0) + (featPid.checked ? 8 : 0)) })
                    }
                }
                Text { text: testerBackend.featuresText; visible: testerBackend.featuresText !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }

                Text { text: testerBackend.uiText("QT_PID_PANEL"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 12 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text { text: testerBackend.uiText("LBL_PID_KP"); color: muted; font.pixelSize: 10 }
                    TextField { id: pidKp; text: "8"; color: textPrimary; Layout.preferredWidth: 58; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    Text { text: testerBackend.uiText("LBL_PID_KI"); color: muted; font.pixelSize: 10 }
                    TextField { id: pidKi; text: "0.2"; color: textPrimary; Layout.preferredWidth: 58; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    Text { text: testerBackend.uiText("LBL_PID_KD"); color: muted; font.pixelSize: 10 }
                    TextField { id: pidKd; text: "1.5"; color: textPrimary; Layout.preferredWidth: 58; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_QUERY_PID"); accent: "#24465e"; Layout.preferredWidth: 190; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.queryPid() }
                    GameButton {
                        text: testerBackend.uiText("BTN_SET_PID_GAINS")
                        accent: "#b86a35"
                        Layout.preferredWidth: 190
                        enabled: testerBackend.canUseUtilityPanels
                        onClicked: window.requestUtilityAction(function() { testerBackend.writePidGains(pidKp.text, pidKi.text, pidKd.text) })
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton {
                        text: testerBackend.uiText("BTN_PID_AUTOTUNE")
                        accent: "#b86a35"
                        Layout.preferredWidth: 190
                        enabled: testerBackend.canUseUtilityPanels
                        onClicked: window.requestUtilityAction(function() { testerBackend.startPidAutotune() })
                    }
                    GameButton { text: testerBackend.uiText("BTN_PID_ABORT"); accent: "#8f2f3a"; Layout.preferredWidth: 190; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.abortPidAutotune() }
                }
                Text { text: testerBackend.uiText("HELP_PID_AUTOTUNE"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                Text { text: testerBackend.pidText; visible: testerBackend.pidText !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }

                Text { text: testerBackend.uiText("QT_RACK_BENCH"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 12 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text { text: testerBackend.uiText("LBL_SLOT"); color: muted; font.pixelSize: 10 }
                    TextField { id: benchSlot; text: "0"; color: textPrimary; Layout.preferredWidth: 46; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    Text { text: testerBackend.uiText("LBL_TOOL_ID"); color: muted; font.pixelSize: 10 }
                    TextField { id: benchTool; text: "0"; color: textPrimary; Layout.preferredWidth: 46; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    Text { text: testerBackend.uiText("LBL_SERIAL"); color: muted; font.pixelSize: 10 }
                    TextField { id: benchSerial; text: "0"; color: textPrimary; Layout.preferredWidth: 46; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton { text: testerBackend.uiText("BTN_RACK_IT"); accent: "#24465e"; Layout.fillWidth: true; onClicked: testerBackend.rackBenchRack(parseInt(benchSlot.text) || 0, parseInt(benchTool.text) || 0, parseInt(benchSerial.text) || 0) }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text { text: testerBackend.uiText("LBL_TARGET_C"); color: muted; font.pixelSize: 10 }
                    TextField { id: benchTarget; text: "200"; color: textPrimary; Layout.preferredWidth: 60; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton { text: testerBackend.uiText("BTN_SEND_PREHEAT"); accent: "#24465e"; Layout.preferredWidth: 190; onClicked: testerBackend.rackBenchPreheat(parseInt(benchTool.text) || 0, parseInt(benchTarget.text) || 0) }
                    TextField { id: benchAdvance; text: "1000"; color: textPrimary; Layout.preferredWidth: 70; background: Rectangle { radius: 8; color: panelAlt; border.width: 1; border.color: panelBorder } }
                    GameButton { text: testerBackend.uiText("BTN_ADVANCE_TIME"); accent: "#24465e"; Layout.fillWidth: true; onClicked: testerBackend.rackBenchAdvance(parseInt(benchAdvance.text) || 0) }
                }
                GameButton { text: testerBackend.uiText("BTN_EXPORT_RACK_STATUS"); accent: "#24465e"; Layout.preferredWidth: 220; onClicked: testerBackend.rackBenchExport() }
                Text { text: testerBackend.rackBenchText; visible: testerBackend.rackBenchText !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.family: "Cascadia Mono"; font.pixelSize: 10 }

                Text { text: testerBackend.uiText("QT_THERMAL_VIEW"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 12 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_THERMAL_SIMULATED"); accent: "#24465e"; Layout.preferredWidth: 220; onClicked: testerBackend.showSimulatedThermal() }
                    GameButton { text: testerBackend.uiText("BTN_THERMAL_READ"); accent: "#24465e"; Layout.preferredWidth: 200; enabled: testerBackend.canUseUtilityPanels; onClicked: testerBackend.readThermalImage() }
                }
                Image { source: testerBackend.thermalViewSource; visible: testerBackend.thermalViewSource !== ""; fillMode: Image.PreserveAspectFit; smooth: false; Layout.preferredWidth: 384; Layout.preferredHeight: 288 }
                Text { text: testerBackend.thermalViewText; visible: testerBackend.thermalViewText !== ""; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }

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
                Text { text: testerBackend.uiText("TITLE_RAW_BUS_MONITOR"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton {
                        text: testerBackend.isMonitoring ? testerBackend.uiText("QT_MONITOR_STOP") : testerBackend.uiText("QT_MONITOR_START")
                        accent: testerBackend.isMonitoring ? "#7a2f2f" : "#24465e"
                        Layout.fillWidth: true
                        enabled: testerBackend.isMonitoring || testerBackend.canMonitorBus
                        onClicked: testerBackend.isMonitoring ? testerBackend.stopBusMonitor() : testerBackend.startBusMonitor()
                    }
                    GameButton { text: testerBackend.uiText("BTN_CLEAR"); accent: "#24465e"; Layout.fillWidth: true; onClicked: testerBackend.clearBusMonitor() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: testerBackend.uiText("LBL_FILTER_IDS"); color: muted; font.pixelSize: 11 }
                    TextField { id: monitorIds; Layout.fillWidth: true; placeholderText: "1A0 110 7F8"; font.pixelSize: 11; onTextEdited: testerBackend.setMonitorIds(text) }
                    CheckBox { text: testerBackend.uiText("BTN_ONLY_CHANGES"); font.pixelSize: 11; onToggled: testerBackend.setMonitorOnlyChanges(checked) }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 150
                    color: "#07131c"; radius: 8; border.width: 1; border.color: panelBorder
                    ListView {
                        anchors.fill: parent; anchors.margins: 6; clip: true
                        model: testerBackend.monitorLines
                        delegate: Text { width: ListView.view.width; text: modelData; color: textPrimary; font.family: "Consolas"; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: String(testerBackend.monitorCount); color: muted; font.pixelSize: 10 }
                    GameButton { text: testerBackend.uiText("BTN_EXPORT_TRC"); accent: "#24465e"; Layout.fillWidth: true; enabled: testerBackend.monitorCount > 0; onClicked: testerBackend.exportMonitor("trc") }
                    GameButton { text: testerBackend.uiText("BTN_EXPORT_ASC"); accent: "#24465e"; Layout.fillWidth: true; enabled: testerBackend.monitorCount > 0; onClicked: testerBackend.exportMonitor("asc") }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: testerBackend.uiText("TITLE_REPLAY"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Rectangle {
                        visible: testerBackend.replayLoaded
                        radius: 6; color: "#5a4a22"; border.width: 1; border.color: "#f3ba55"
                        implicitWidth: replayBadgeText.implicitWidth + 14; implicitHeight: 20
                        Text { id: replayBadgeText; anchors.centerIn: parent; text: testerBackend.replayBadge; color: "#f3ba55"; font.bold: true; font.pixelSize: 10 }
                    }
                }
                Text { text: testerBackend.uiText("HELP_REPLAY"); color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    GameButton { text: testerBackend.uiText("BTN_REPLAY_OPEN"); accent: "#24465e"; Layout.fillWidth: true; onClicked: replayOpenDialog.open() }
                    GameButton {
                        text: testerBackend.replayPlaying ? testerBackend.uiText("BTN_REPLAY_PAUSE") : testerBackend.uiText("BTN_REPLAY_PLAY")
                        accent: "#24465e"
                        Layout.fillWidth: true
                        enabled: testerBackend.replayLoaded
                        onClicked: testerBackend.replayPlaying ? testerBackend.pauseReplay() : testerBackend.playReplay()
                    }
                    GameButton { text: testerBackend.uiText("BTN_REPLAY_STOP"); accent: "#7a2f2f"; Layout.fillWidth: true; enabled: testerBackend.replayLoaded; onClicked: testerBackend.stopReplay() }
                    GameButton { text: testerBackend.uiText("BTN_CLEAR"); accent: "#24465e"; Layout.fillWidth: true; onClicked: testerBackend.clearReplay() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: testerBackend.uiText("LBL_REPLAY_SPEED"); color: muted; font.pixelSize: 11 }
                    ComboBox {
                        id: replaySpeedBox
                        model: testerBackend.replaySpeeds
                        Layout.preferredWidth: 90
                        font.pixelSize: 11
                        displayText: String(currentValue) + "x"
                        currentIndex: Math.max(0, testerBackend.replaySpeeds.indexOf(testerBackend.replaySpeed))
                        onActivated: testerBackend.setReplaySpeed(currentValue)
                    }
                    CheckBox { text: testerBackend.uiText("LBL_REPLAY_LOOP"); checked: testerBackend.replayLoop; font.pixelSize: 11; onToggled: testerBackend.setReplayLoop(checked) }
                    Text { text: testerBackend.replayProgressText; color: muted; font.pixelSize: 10; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                }
                ProgressBar { visible: testerBackend.replayLoaded; Layout.fillWidth: true; from: 0; to: 100; value: testerBackend.replayPercent }
                Text { visible: testerBackend.replayNotice !== ""; text: testerBackend.replayNotice; color: "#f3ba55"; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    color: "#07131c"; radius: 8; border.width: 1; border.color: panelBorder
                    ListView {
                        anchors.fill: parent; anchors.margins: 6; clip: true
                        model: testerBackend.replayLines
                        delegate: Text { width: ListView.view.width; text: modelData; color: "#f3ba55"; font.family: "Consolas"; font.pixelSize: 10; elide: Text.ElideRight }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: panelBorder }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: testerBackend.uiText("QT_ACTIVITY_LOG"); color: cyan; font.family: "Bahnschrift"; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true }
                    Rectangle {
                        id: copyIconButton
                        property bool copied: false
                        Layout.preferredWidth: 36
                        Layout.preferredHeight: 30
                        radius: 8
                        color: copyIconMouse.containsMouse ? "#1b3c52" : "#102a3b"
                        border.width: 1
                        border.color: copyIconButton.copied ? "#5df0c4" : "#264966"
                        Item {
                            anchors.centerIn: parent
                            width: 18; height: 18
                            Rectangle { x: 6; y: 0; width: 11; height: 12; radius: 2; color: "transparent"; border.width: 1.6; border.color: copyIconButton.copied ? "#5df0c4" : "#9fd8e3" }
                            Rectangle { x: 1; y: 5; width: 11; height: 12; radius: 2; color: copyIconMouse.containsMouse ? "#1b3c52" : "#102a3b"; border.width: 1.6; border.color: copyIconButton.copied ? "#5df0c4" : "#9fd8e3" }
                        }
                        TextEdit { id: copyHelper; visible: false }
                        Timer { id: copiedTimer; interval: 1400; onTriggered: copyIconButton.copied = false }
                        MouseArea {
                            id: copyIconMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                copyHelper.text = testerBackend.logs.join("\n"); copyHelper.selectAll(); copyHelper.copy(); copyHelper.deselect()
                                copyIconButton.copied = true; copiedTimer.restart()
                            }
                        }
                    }
                }
                GameButton { text: testerBackend.uiText("QT_EXPORT_SESSION"); accent: "#24465e"; Layout.preferredWidth: 260; onClicked: testerBackend.exportSession() }
                GameButton { text: testerBackend.uiText("MENU_SAVE_LOGS"); accent: "#24465e"; Layout.preferredWidth: 260; onClicked: saveLogDialog.open() }
                GameButton { text: testerBackend.updates.t("UPD_BTN_CHECK"); accent: "#24465e"; Layout.preferredWidth: 260; onClicked: updateDialog.open() }
                GameButton { text: testerBackend.help.title; accent: "#24465e"; Layout.preferredWidth: 260; onClicked: helpDialog.open() }
                GameButton { text: testerBackend.uiText("TITLE_ABOUT"); accent: "#24465e"; Layout.preferredWidth: 260; onClicked: aboutDialog.open() }
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
