// =============================================================================
// URTC Tester - assets/qml/ToolPanelView.qml
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0-or-later - see LICENSE
// =============================================================================
// The panel of the selected tool drawn from its profile: one generic view for every control, button, check box, reading, query and
// picture. `model` is the ToolPanelController (qt_tool_panel.py); `ask` is the deck's confirmation (it runs the function it receives
// once the person confirms), so a command is never sent without it.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: view
    property var model
    property var ask: function(action) { action() }
    property bool canAct: false
    // A value that raises a tool that is on too far above the confirmed one goes through the deck's confirmation first.
    function setControl(id, value) {
        if (view.model.needsConfirm(id, value))
            view.ask(function() { view.model.setValueConfirmed(id, value) })
        else
            view.model.setValue(id, value)
    }
    property color panelColor: "#14253b"
    property color borderColor: "#294965"
    property color textColor: "#edf7ff"
    property color mutedColor: "#91a8bd"
    property color accentColor: "#b86a35"
    property color onColor: "#43db9b"
    property color offColor: "#6d8294"

    spacing: 10

    Repeater {
        model: view.model ? view.model.sections : []
        delegate: Rectangle {
            id: card
            required property var modelData
            property int sectionIndex: modelData.index
            Layout.fillWidth: true
            implicitHeight: body.implicitHeight + 24
            radius: 10
            color: view.panelColor
            border.width: 1
            border.color: view.borderColor

            ColumnLayout {
                id: body
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                Text { text: card.modelData.title; color: view.textColor; font.bold: true; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text { visible: card.modelData.notice !== ""; text: card.modelData.notice; color: "#f7b955"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }

                Flow {
                    Layout.fillWidth: true
                    spacing: 10
                    Repeater {
                        model: card.modelData.controls
                        delegate: ColumnLayout {
                            id: field
                            required property var modelData
                            spacing: 3
                            Text { text: field.modelData.label; color: view.mutedColor; font.pixelSize: 10 }
                            CheckBox {
                                visible: field.modelData.type === "checkbox"
                                checked: field.modelData.value === true
                                onToggled: view.model.setValue(field.modelData.id, checked)
                            }
                            ComboBox {
                                visible: field.modelData.type === "select"
                                objectName: "panelCombo"
                                textRole: "label"
                                valueRole: "value"
                                model: field.modelData.options ? field.modelData.options : []
                                currentIndex: {
                                    var options = field.modelData.options ? field.modelData.options : []
                                    for (var i = 0; i < options.length; i++)
                                        if (String(options[i].value) === String(field.modelData.value)) return i
                                    return 0
                                }
                                onActivated: view.model.setValue(field.modelData.id, String(currentValue))
                            }
                            RowLayout {
                                visible: field.modelData.type === "range"
                                Slider {
                                    from: field.modelData.min !== undefined ? field.modelData.min : 0
                                    to: field.modelData.max !== undefined ? field.modelData.max : 1
                                    stepSize: 1
                                    value: Number(field.modelData.value)
                                    implicitWidth: 140
                                    onMoved: view.setControl(field.modelData.id, Math.round(value))
                                }
                                Text { text: String(field.modelData.value); color: view.textColor; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                            }
                            TextField {
                                visible: field.modelData.type === "number" || field.modelData.type === "hex"
                                objectName: "panelField"
                                text: String(field.modelData.value)
                                implicitWidth: field.modelData.type === "hex" ? 90 : 110
                                color: field.modelData.valid === false ? "#ff7b7b" : view.textColor
                                onEditingFinished: view.setControl(field.modelData.id, text)
                            }
                        }
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 10
                    Repeater {
                        model: card.modelData.actions
                        delegate: RowLayout {
                            id: act
                            required property var modelData
                            spacing: 8
                            // a command that repeats while it is on, and a latched output: a check box
                            CheckBox {
                                visible: act.modelData.kind === "keepalive" || act.modelData.kind === "latched"
                                objectName: "panelToggle"
                                enabled: view.canAct
                                text: act.modelData.kind === "latched" ? act.modelData.label : view.model.uiActive
                                checked: act.modelData.kind === "latched" ? act.modelData.on : card.modelData.active
                                onToggled: {
                                    var on = checked
                                    var si = card.sectionIndex
                                    var ai = act.modelData.index
                                    if (on && act.modelData.confirm)
                                        view.ask(function() { view.model.toggle(si, ai, true) })
                                    else
                                        view.model.toggle(si, ai, on)
                                }
                            }
                            Button {
                                visible: act.modelData.kind === "send" || act.modelData.kind === "stop" || act.modelData.kind === "query" || act.modelData.kind === "image"
                                objectName: "panelButton"
                                text: act.modelData.label
                                enabled: (act.modelData.kind === "query" || act.modelData.kind === "image" ? view.model.canAsk : view.canAct)
                                    && (act.modelData.enabled === undefined || act.modelData.enabled)
                                onClicked: {
                                    var si = card.sectionIndex
                                    var ai = act.modelData.index
                                    if (act.modelData.confirm)
                                        view.ask(function() { view.model.run(si, ai) })
                                    else
                                        view.model.run(si, ai)
                                }
                            }
                            Text { visible: act.modelData.kind === "query"; text: act.modelData.resultLabel || ""; color: view.mutedColor; font.pixelSize: 10 }
                            Text { visible: act.modelData.kind === "query"; text: act.modelData.resultText || ""; color: view.textColor; font.family: "Cascadia Mono"; font.pixelSize: 11 }
                            Text { visible: act.modelData.kind === "image" && !!act.modelData.error; text: act.modelData.error || ""; color: "#ff7b7b"; font.pixelSize: 10 }
                        }
                    }
                }

                Repeater {
                    model: card.modelData.actions
                    delegate: Grid {
                        id: picture
                        required property var modelData
                        visible: modelData.kind === "image" && !!modelData.cells && modelData.cells.length > 0
                        columns: modelData.columns || 1
                        spacing: 1
                        Repeater {
                            model: picture.modelData.cells || []
                            delegate: Rectangle { required property string modelData; width: 12; height: 12; color: modelData }
                        }
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 18
                    visible: card.modelData.readings.length > 0
                    Repeater {
                        model: card.modelData.readings
                        delegate: Row {
                            id: reading
                            required property var modelData
                            spacing: 6
                            Text { text: reading.modelData.label; color: view.mutedColor; font.pixelSize: 10 }
                            Text {
                                text: reading.modelData.text
                                font.family: "Cascadia Mono"
                                font.pixelSize: 11
                                color: reading.modelData.tone === "on" ? view.onColor : (reading.modelData.tone === "off" ? view.offColor : view.textColor)
                            }
                        }
                    }
                }
            }
        }
    }

    Row {
        visible: view.model && view.model.hasReadings
        spacing: 8
        Button { text: view.model ? view.model.uiWatch : ""; objectName: "panelWatch"; enabled: view.model && view.model.canWatch; onClicked: view.model.watchReadings() }
        Button { text: view.model ? view.model.uiStopWatch : ""; objectName: "panelStopWatch"; enabled: view.model && view.model.watching; onClicked: view.model.stopReadings() }
    }
}
