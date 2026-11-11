import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    width: 1200; height: 850
    minimumWidth: 920; minimumHeight: 720
    visible: true
    title: Qt.application.displayName + " v" + Qt.application.version + " · Java 局域网联机助手"
    color: "#19151d"
    Material.theme: Material.Dark
    Material.accent: "#f4a3bf"
    Material.primary: "#412c3b"
    Material.foreground: "#f8edf3"
    font.family: "Microsoft YaHei UI"
    font.pixelSize: 13
    property string page: "easy"

    component Card: Pane {
        padding: 20
        Layout.fillWidth: true
        background: Rectangle { color: "#27222e"; radius: 16; border.color: "#4b3d4d"; border.width: 1 }
    }
    component Hint: Label {
        color: "#bdb0c0"
        font.pixelSize: 12
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
    component Heading: Label { font.pixelSize: 17; font.weight: Font.DemiBold; color: "#f8edf3" }
    component Metric: ColumnLayout {
        property string caption
        property string value
        property string valueName
        spacing: 4
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        Hint { text: parent.caption }
        Label {
            objectName: parent.valueName
            text: parent.value
            color: "#ffcade"
            font.pixelSize: 21
            font.weight: Font.DemiBold
        }
    }
    component Action: Button {
        implicitHeight: 44
        leftPadding: 20; rightPadding: 20
        Material.roundedScale: Material.FullScale
        Material.accent: "#953b60"
        font.weight: Font.DemiBold
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.preferredWidth: 210
            Layout.fillHeight: true
            color: "#1b1721"
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 8
                Label { text: Qt.application.displayName; font.pixelSize: 25; font.bold: true; color: "#ffcade"; Layout.topMargin: 12 }
                Label { text: "MINECRAFT JAVA / LAN"; font.pixelSize: 10; font.letterSpacing: 1.3; color: "#bdb0c0" }
                Rectangle { Layout.fillWidth: true; height: 1; color: "#4b3d4d"; Layout.topMargin: 22; Layout.bottomMargin: 18 }
                Button {
                    Layout.fillWidth: true; implicitHeight: 48
                    text: "EasyTier 房间"
                    highlighted: window.page === "easy"; flat: window.page !== "easy"
                    Material.accent: "#953b60"
                    Material.roundedScale: Material.FullScale
                    onClicked: window.page = "easy"
                }
                Button {
                    Layout.fillWidth: true; implicitHeight: 48
                    objectName: "lanNav"
                    text: "Tailscale 联机"
                    highlighted: window.page === "tailscale"; flat: window.page !== "tailscale"
                    Material.accent: "#953b60"
                    Material.roundedScale: Material.FullScale
                    onClicked: window.page = "tailscale"
                }
                Item { Layout.fillHeight: true }
                Label { text: "Minecraft Java 联机助手"; color: "#ead2df"; font.pixelSize: 12 }
                Label { text: "v" + Qt.application.version; color: "#bdb0c0"; font.pixelSize: 11 }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.margins: 28
            spacing: 16
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 5
                Label {
                    text: window.page === "easy" ? "EasyTier 房间" : "Tailscale 联机"
                    font.pixelSize: 26
                    font.weight: Font.DemiBold
                }
                Hint {
                    text: window.page === "easy" ? "用短码邀请朋友加入 Minecraft Java 的局域网世界"
                                                 : "通过 Tailscale 连接房主，在 Minecraft 中直接加入"
                }
            }

            ScrollView {
                id: scroller
                Layout.fillWidth: true; Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout {
                    width: scroller.availableWidth
                    spacing: 16

                    Card {
                        objectName: "easyPage"
                        visible: window.page === "easy"
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 12
                            RowLayout {
                                visible: !easyBridge.busy
                                Action { text: "创建房间"; highlighted: easyBridge.host; enabled: !easyBridge.busy; onClicked: easyBridge.setHost(true) }
                                Action { objectName: "easyGuestButton"; text: "加入房间"; highlighted: !easyBridge.host; enabled: !easyBridge.busy; onClicked: easyBridge.setHost(false) }
                            }
                            Label {
                                visible: !easyBridge.busy
                                text: easyBridge.host ? "游戏显示的局域网端口" : "房主发来的短码"
                                color: "#edc8dd"
                            }
                            RowLayout {
                                visible: easyBridge.host && !easyBridge.busy
                                Layout.fillWidth: true
                                TextField {
                                    id: easyPort
                                    objectName: "easyPortField"
                                    Layout.fillWidth: true
                                    selectByMouse: true
                                    placeholderText: "例如 51234"
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    Material.containerStyle: Material.Outlined
                                    onAccepted: if (startRoom.enabled) startRoom.clicked()
                                }
                                Action {
                                    id: scanButton
                                    property string portBeforeScan
                                    text: easyBridge.scanBusy ? "正在检测…" : "检测局域网端口"
                                    enabled: !easyBridge.scanBusy
                                    onClicked: {
                                        portBeforeScan = easyPort.text
                                        easyBridge.scanLan()
                                    }
                                }
                                Connections {
                                    target: easyBridge
                                    function onScanFinished(port) {
                                        if (easyPort.text === scanButton.portBeforeScan)
                                            easyPort.text = port
                                    }
                                }
                            }
                            Hint {
                                visible: easyBridge.host && !easyBridge.busy && text.length > 0
                                text: easyBridge.scanHint
                            }
                            ComboBox {
                                objectName: "easyWorldPicker"
                                visible: easyBridge.host && !easyBridge.busy && count > 0
                                         && (count > 1 || easyPort.text !== String(easyBridge.worlds[0].port))
                                Layout.fillWidth: true
                                model: easyBridge.worlds
                                textRole: "label"
                                currentIndex: -1
                                displayText: currentIndex < 0 ? "选择检测到的世界" : currentText
                                onActivated: function(index) {
                                    easyPort.text = String(easyBridge.worlds[index].port)
                                }
                            }
                            TextField {
                                id: easyInvite
                                objectName: "easyInviteField"
                                visible: !easyBridge.host && !easyBridge.busy
                                enabled: !easyBridge.busy
                                Layout.fillWidth: true
                                selectByMouse: true
                                placeholderText: "N4E1-…"
                                Material.containerStyle: Material.Outlined
                                onAccepted: if (startRoom.enabled) startRoom.clicked()
                            }
                            CheckBox {
                                id: easyRelayOnly
                                visible: !easyBridge.busy
                                text: "仅中继"
                                enabled: !easyBridge.busy
                                ToolTip.visible: hovered
                                ToolTip.text: "默认尝试直连。网络限制入站时，可以试试仅中继。"
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Heading {
                                    visible: easyBridge.busy
                                    text: easyBridge.host ? "我创建的房间" : "我加入的房间"
                                }
                                Label {
                                    visible: easyBridge.busy
                                    text: easyBridge.gameCheck === "无响应" ? "○ 正在重试" : (easyBridge.ready ? "● 已就绪" : "○ 检测中")
                                    color: easyBridge.ready && easyBridge.gameCheck !== "无响应" ? "#ffbdd5" : "#efc792"
                                }
                                Action {
                                    id: startRoom
                                    objectName: "easyStartButton"
                                    visible: !easyBridge.busy
                                    text: easyBridge.host ? "创建房间" : "加入房间"
                                    highlighted: true
                                    enabled: !easyBridge.busy && (easyBridge.host ? easyPort.text.trim().length : easyInvite.text.trim().length) > 0
                                    onClicked: easyBridge.start(easyBridge.host ? easyPort.text : easyInvite.text, easyRelayOnly.checked)
                                }
                                Item { Layout.fillWidth: true }
                                Action { text: easyBridge.host ? "停止房间" : "离开房间"; flat: true; visible: easyBridge.busy; onClicked: easyBridge.stop() }
                            }
                            Hint { text: easyBridge.message; color: easyBridge.ready ? "#ffbdd5" : "#d0bccc" }
                            RowLayout {
                                visible: easyBridge.ready
                                Layout.fillWidth: true
                                TextField {
                                    Layout.fillWidth: true; readOnly: true; selectByMouse: true
                                    text: easyBridge.share
                                    font.family: "Consolas"
                                    Accessible.name: easyBridge.host ? "房间短码" : "本地连接地址"
                                }
                                Action { text: easyBridge.host ? "复制短码" : "复制直连地址"; onClicked: easyBridge.copy() }
                            }
                        }
                    }

                    Card {
                        objectName: "easyPlayersCard"
                        visible: window.page === "easy"
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10
                            Heading { text: "房间概览" }
                            RowLayout {
                                visible: easyBridge.gameCheck === "有响应"
                                Layout.fillWidth: true
                                Label {
                                    objectName: "easyWorldName"
                                    Layout.fillWidth: true
                                    text: easyBridge.worldName || "世界未提供名称"
                                    textFormat: Text.PlainText
                                    elide: Text.ElideRight
                                    font.bold: true
                                    color: "#ffcade"
                                }
                                Label {
                                    objectName: "easyWorldVersion"
                                    Layout.maximumWidth: 220
                                    text: easyBridge.worldVersion || "版本未知"
                                    textFormat: Text.PlainText
                                    elide: Text.ElideRight
                                    color: "#bdb0c0"
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 20
                                Metric {
                                    caption: "游戏在线 / 上限"
                                    valueName: "easyPlayerCount"
                                    value: easyBridge.onlinePlayers < 0 ? "—" : easyBridge.onlinePlayers + " / " + (easyBridge.playerLimit < 0 ? "—" : easyBridge.playerLimit)
                                }
                                Metric {
                                    caption: "已发现的组网设备（含本机）"
                                    value: easyBridge.network.devices === undefined ? "—" : easyBridge.network.devices + " 台"
                                }
                            }
                            Hint { text: "玩家数由 Minecraft 返回，设备数由 EasyTier 发现。" }
                        }
                    }

                    Card {
                        objectName: "easyDiagnostics"
                        visible: window.page === "easy"
                        ColumnLayout {
                            anchors.fill: parent; spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                Heading { text: "掉线排查" }
                                Item { Layout.fillWidth: true }
                                Action {
                                    objectName: "easyCopyDiagnostics"
                                    flat: true
                                    text: "复制诊断"
                                    enabled: easyBridge.busy || easyBridge.history.length > 0
                                    onClicked: {
                                        easyBridge.copyDiagnostics()
                                        diagnosticCopied.restart()
                                    }
                                    ToolTip.visible: diagnosticCopied.running
                                    ToolTip.text: "诊断已复制"
                                    Timer { id: diagnosticCopied; interval: 1800 }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 14
                                Metric { caption: "游戏探测"; value: easyBridge.gameCheck; valueName: "easyGameCheck" }
                                Metric { caption: "EasyTier 路径"; value: easyBridge.network.path || "—"; valueName: "easyNetworkPath" }
                                Metric { caption: easyBridge.host ? "最高延迟" : "房主链路延迟"; value: easyBridge.network.latency || "—" }
                                Metric { caption: "直连丢包"; value: easyBridge.network.loss || "—" }
                            }
                            Hint { objectName: "easyLastIssue"; text: "最近异常 · " + (easyBridge.lastIssue || "暂无记录"); color: "#efc792" }
                            Hint { text: easyBridge.diagnosticHint }
                            RowLayout {
                                visible: easyBridge.history.length > 0
                                Layout.fillWidth: true
                                Label { text: "本次联机记录"; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Action {
                                    id: historyToggle
                                    visible: easyBridge.history.length > 3
                                    text: checked ? "收起" : "查看全部"
                                    checkable: true
                                    flat: true
                                }
                            }
                            Repeater {
                                model: easyBridge.history.slice(historyToggle.checked ? 0 : -3).reverse()
                                delegate: Hint {
                                    required property string modelData
                                    text: modelData
                                    textFormat: Text.PlainText
                                }
                            }
                        }
                    }

                    Card {
                        objectName: "lanPage"
                        visible: window.page === "tailscale"
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                Heading { text: "01  Tailscale 网络" }
                                Label {
                                    text: lanBridge.ready ? "● 已连接" : "○ 尚未连接"
                                    color: lanBridge.ready ? "#ffbdd5" : "#efc792"
                                }
                                Item { Layout.fillWidth: true }
                                Action {
                                    text: "刷新状态"
                                    enabled: !lanBridge.busy
                                    onClicked: lanBridge.refresh()
                                }
                            }
                            Hint {
                                text: lanBridge.ready ? "本机组网 IP  " + lanBridge.ip
                                                      : "双方先安装并登录 Tailscale，再加入同一网络或由房主共享设备。"
                                textFormat: Text.PlainText
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Action { text: "打开 / 登录 Tailscale"; flat: true; onClicked: lanBridge.openClient() }
                                Action { text: "设备共享与成员管理"; flat: true; onClicked: lanBridge.openAdmin() }
                                Item { Layout.fillWidth: true }
                                Action {
                                    objectName: "lanDownloadButton"
                                    text: "官方下载"
                                    flat: true
                                    onClicked: lanBridge.download()
                                }
                            }
                            RowLayout {
                                visible: !lanBridge.ready
                                Layout.fillWidth: true
                                TextField {
                                    id: tailscaleDownloadAddress
                                    Layout.fillWidth: true
                                    text: "https://tailscale.com/download/windows"
                                    readOnly: true
                                    selectByMouse: true
                                    Accessible.name: "Tailscale Windows 官方下载地址"
                                }
                                Action {
                                    text: "复制下载地址"
                                    flat: true
                                    onClicked: {
                                        tailscaleDownloadAddress.selectAll()
                                        tailscaleDownloadAddress.copy()
                                        tailscaleDownloadAddress.deselect()
                                    }
                                }
                            }
                        }
                    }

                    Card {
                        visible: window.page === "tailscale"
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 14
                            Heading { text: "02  Minecraft 房间" }
                            RowLayout {
                                Action {
                                    objectName: "lanHostButton"
                                    text: "创建房间"
                                    highlighted: lanBridge.role === "host"
                                    flat: !highlighted
                                    onClicked: lanBridge.setRole("host")
                                }
                                Action {
                                    objectName: "lanGuestButton"
                                    text: "加入房间"
                                    highlighted: lanBridge.role === "friend"
                                    flat: !highlighted
                                    onClicked: lanBridge.setRole("friend")
                                }
                            }
                            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#4b3d4d" }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 1
                                    Layout.minimumWidth: 0
                                    Layout.alignment: Qt.AlignTop
                                    spacing: 8
                                    Label { text: lanBridge.role === "host" ? "开放世界" : "选择房主"; font.bold: true }
                                    Hint {
                                        text: lanBridge.role === "host" ? "在单人世界开放局域网，把游戏显示的端口填在下方。"
                                                                         : "选择在线房主，并填入房主在游戏中看到的端口。"
                                    }
                                    ComboBox {
                                        objectName: "lanPeers"
                                        visible: lanBridge.role === "friend"
                                        enabled: lanBridge.ready && count > 0
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        model: lanBridge.peers
                                        textRole: "name"
                                        currentIndex: lanBridge.selectedIndex
                                        displayText: currentIndex >= 0 ? (lanBridge.peers[currentIndex].name + " · " + lanBridge.peers[currentIndex].ip
                                                                          + (lanBridge.peers[currentIndex].online ? " · 在线" : " · 离线"))
                                                                         : (count > 0 ? "选择房主设备" : "暂无设备，请完成共享并刷新")
                                        onActivated: lanBridge.setTarget(lanBridge.peers[currentIndex].ip)
                                    }
                                    TextField {
                                        objectName: "lanPort"
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        placeholderText: "游戏端口，例如 51234"
                                        Accessible.name: "Minecraft 局域网端口"
                                        Material.containerStyle: Material.Outlined
                                        inputMethodHints: Qt.ImhDigitsOnly
                                        onTextEdited: lanBridge.setPort(text)
                                    }
                                }
                                Rectangle { Layout.fillHeight: true; implicitWidth: 1; color: "#4b3d4d" }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 1
                                    Layout.minimumWidth: 0
                                    Layout.alignment: Qt.AlignTop
                                    spacing: 8
                                    Label { text: lanBridge.role === "host" ? "分享连接地址" : "在游戏内直接连接"; font.bold: true }
                                    Hint {
                                        text: lanBridge.role === "host" ? "先检查游戏端口，再把组网地址发给朋友。"
                                                                         : "检查通过后，去 Minecraft「多人游戏 → 直接连接」粘贴地址。"
                                    }
                                    TextField {
                                        objectName: "lanAddress"
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        text: lanBridge.address
                                        readOnly: true
                                        selectByMouse: true
                                        placeholderText: "连接地址"
                                        Accessible.name: "Minecraft 连接地址"
                                    }
                                    RowLayout {
                                        Action {
                                            objectName: "lanCheck"
                                            text: "检查游戏连接"
                                            highlighted: true
                                            enabled: !lanBridge.busy && lanBridge.address !== ""
                                            onClicked: lanBridge.checkConnection()
                                        }
                                        Action {
                                            text: "复制地址"
                                            flat: true
                                            enabled: lanBridge.address !== ""
                                            onClicked: lanBridge.copyAddress()
                                        }
                                    }
                                }
                            }
                            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#4b3d4d" }
                            Hint {
                                objectName: "lanMessage"
                                text: lanBridge.message
                                textFormat: Text.PlainText
                                color: "#f0c6db"
                            }
                        }
                    }
                }
            }

            Label { text: window.page === "easy" ? "保持世界与助手开启  ·  好友在 Minecraft「多人游戏」选择房间" : "保持世界与助手开启  ·  好友在 Minecraft「多人游戏 → 直接连接」加入"; color: "#baa6b9"; font.pixelSize: 10; Layout.alignment: Qt.AlignHCenter }
        }
    }

}
