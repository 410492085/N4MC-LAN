# N4MC-LAN · Minecraft Java 局域网联机助手

Windows 中文桌面工具，支持 EasyTier 房间和 Tailscale 虚拟局域网，让异地朋友加入房主电脑上的 Minecraft Java 单人世界。

## EasyTier 房间（新版默认入口）

1. 双方完整解压同一新版助手，打开 `N4MC-LAN.exe`，进入「EasyTier 房间」。便携包已包含 EasyTier 2.6.4 的 Windows x64 组件，助手校验后直接使用，首次联机也无需下载组件。
2. 房主在 Minecraft Java 单人世界选「对局域网开放」，点助手里的「检测局域网端口」。检测到一个世界会填入端口，检测到多个可以选择，也可以手动填端口。点击「创建房间」，再私发 `N4E1-` 开头的短码。重新创建房间会生成新短码。
3. 朋友切换到「加入房间」，粘贴短码并提交。连接成功后，助手在朋友本机发布「N4MC-LAN 房间」。在游戏的「多人游戏」里点击该房间，或复制助手提供的 `127.0.0.1:端口` 用「直接连接」。
4. 保持两边助手运行，房主也需保持世界开启。停止房间或离开会关闭助手启动的 EasyTier 进程。

房主和访客都可以在「房间概览」看到 Minecraft 状态查询返回的世界描述（MOTD）、版本、在线玩家数和上限，以及 EasyTier 发现的组网设备数（含本机）。两种数字独立统计。游戏探测没有返回人数时显示 `—`。

掉线时，在「掉线排查」对照双方的游戏探测、直连或中继路径、链路延迟和最近异常。延迟来自 EasyTier。房主侧显示可用读数中的最高延迟，访客侧显示到房主的链路延迟。丢包只显示可用的直连读数。「本次联机记录」保留最近 30 条关键事件，开始下一次联机时清空。「复制诊断」会带上事件记录，摘要里没有短码和 IP。

短暂掉线时，保持双方助手开启。连接恢复后，朋友可以用原房间重新进入游戏。如果使用「仅中继」时反复掉线，可以让双方取消勾选后重建房间，对比默认组网模式是否更稳定。

房间使用 [EasyTier 社区公共节点](https://github.com/Xocio/Campfire/blob/v1.1.31/NETWORK.md) `et.chinokou.cn`、`225284.xyz` 和 `easytier.weiai.org.cn` 发现对方，尝试直连，必要时经节点中继。防火墙限制入站时，可勾选「仅中继」重试，该选项使用出站公共节点连接并关闭直连监听和打洞。双方无需自建服务器、注册账号或单独安装客户端。EasyTier 使用无虚拟网卡模式，房主仅向房间开放指定 TCP 游戏端口，朋友的转发和 LAN 通告只在本机回环地址上。

## 新增：免自建服务器联机（Tailscale）

侧栏的「Tailscale 联机」通过官方 Tailscale 组网。双方必须安装并登录 Tailscale，再由房主在官方控制台邀请朋友加入网络，或共享房主设备给朋友自己的 Tailscale 账号。助手不代办账号、不发送邀请、不修改路由或系统防火墙。

1. 从 [Tailscale 官方下载页](https://tailscale.com/download/windows) 安装 Windows 客户端。
2. 双方打开官方 Tailscale 客户端并各自登录，在官方设备管理页面完成成员邀请或设备共享。不同账号分别登录，不需共享密码。设备出现在列表且获得访问权限后继续。
3. 房主在 N4MC-LAN 的「Tailscale 联机」页刷新状态，选择「创建房间」，再在 MC 单人世界开放局域网并填入游戏显示的端口，例如 51234。
4. 点击“检查游戏连接”，然后把生成的组网 IP:端口（例如 100.x.x.x:51234）发给朋友。
5. 朋友在同一页面刷新状态，选择「加入房间」，从列表选择房主设备，填写房主的游戏端口，检查连接后复制地址到 MC「多人游戏 → 直接连接」。也可直接在 MC 使用房主发来的组网地址。

这个模式不需要自购服务器，但依赖 Tailscale 的托管协调/中继服务、双方账号访问权限和网络可达性。服务自动尝试直连，必要时使用中继；助手不根据“设备在线”虚报已连通游戏。测试 TCP 端口可连接也不证明 MC 版本或模组兼容。

Java 防火墙需允许 Tailscale 网络上的游戏访问，网络访问策略也需允许该端口。应用不会自动放行防火墙。组网不提供 MC 局域网自动发现，请使用直接连接。关闭 N4MC-LAN 不会退出或停止系统 Tailscale 服务。

官方资料：https://tailscale.com/docs/install/windows 、https://tailscale.com/docs/features/sharing 、https://tailscale.com/docs/reference/connection-types 。免费个人方案的额度以 https://tailscale.com/pricing 为准。

新版便携包入口为 `N4MC-LAN/N4MC-LAN.exe`，通过 `build-lan.ps1` 构建。

## 打开

新版使用 PySide6 / Qt Quick Material 控件，搭配黑粉配色、纯色背景和侧边导航。

新版解压后，双击 `N4MC-LAN/N4MC-LAN.exe`。请保留整个目录，包含 `bin`、`_internal` 和 `licenses`。无需安装 Python。

源码运行：Python 3.11+ 并安装 PySide6，执行 `python material_app.py`。本项目开发依赖装在 `.build-deps` 时，需要把该目录加入 PYTHONPATH。原 Tkinter 界面源码保留在 app.py 便于回退。

## frp 联机记录（v0.4 及更早版本）

以下 frp 操作说明适用于旧版便携包。

### 新增：双方安装助手的房间模式（STCP 中转）

这不是免服务器 P2P：双方仍连接同一个公网 frps。房主电脑运行 MC，frps 转发连接；此模式不需要为每个房间开放公网游戏端口。需要放行节点控制端口，例如 TCP 7000。第三方服务商是否允许 STCP 及朋友账户接入，取决于节点权限。

房主：
1. 联机方式选择“我是房主 · 创建房间”。首次会自动生成房间 ID 和密钥，也可点“生成新房间”。
2. 填写中转节点、控制端口、节点 Token，并按节点要求配置证书。
3. MC 单人世界开放局域网，把游戏显示的端口填入助手。
4. 点击“启动房间”，等隧道注册后点“复制房间邀请”，私下发给朋友。

朋友：
1. 安装同版本助手，联机方式选择“我是朋友 · 加入房间”。
2. 点击“粘贴房间邀请”，确认邀请中的节点地址。载入邀请不会自动启动连接。
3. 单独填写有权限使用该节点的 Token。邀请不包含节点 Token，也不包含房主电脑上的 CA 文件。导入邀请会清空旧节点 Token 与 CA 路径，避免把旧凭据发送到新节点。
4. 房主使用自定义 CA 时，需要单独获取可信 CA 文件并在安全设置中选中；否则不允许降级启动。保持证书服务器名与节点一致。
5. 本地入口端口默认 25566，被占用时可更换。点击“加入房间”。朋友无需开放自己的 MC 单人世界。
6. 本地入口就绪后复制下方 MC 地址，例如 `127.0.0.1:25566`，在游戏“多人游戏 → 直接连接”粘贴。

“本地加入入口已就绪”仅说明本地监听启动，不证明房主在线、房间密钥有效或游戏已连通；实际访问房主时的错误会显示在日志。

邀请以 `N4ROOM1:` 开头，是带房间密钥的编码文本，不是加密文件或公开邀请码。只发给朋友，不要公开。停止房间后可重新生成密钥撤销旧邀请。默认保存设置时不保存房间密钥，重新打开助手后需重新输入或载入邀请；勾选保存凭据则明文保存节点 Token 和房间密钥。

### 保留：公网端口模式

1. 打开 Minecraft Java 单人世界，Esc → 对局域网开放 → 创建局域网世界。
2. 记下游戏聊天区显示的端口。例如 51234，重新开放后可能变化。
3. 填写节点 IP/域名、控制端口、Token、服务端允许的公网游戏端口。自建 frps 常用控制端口 7000、游戏端口 25565。也可导入服务商的单隧道标准 TOML。
4. 本地地址通常保持 127.0.0.1；填写游戏刚显示的局域网端口，点击“检查游戏端口”。
5. 根据节点证书配置系统 CA 或可信 CA 文件与 TLS 服务器名。没有配置 CA 时仍使用 TLS 加密，但不验证节点身份，界面会明确显示。
6. 点击“启动联机”，等待“隧道已注册”。复制地址给朋友。注册成功不代表公网防火墙已放行，需要朋友实际连接确认。
7. 保持游戏、助手和电脑开启。结束后点击“停止”或关闭助手，工具会停止自己创建的 frpc 子进程。

## 朋友操作

多人游戏 → 直接连接 → 粘贴 `公网IP或域名:游戏端口`。朋友无需安装本工具。Java 游戏版本、模组与模组版本需兼容。异地世界不会自动出现在局域网发现列表。

## 使用 frp 模式且现在没有服务器

可以先打开界面、熟悉操作，并保存不完整设置。MC 端口暂时不知道时保持 0，之后填入游戏端口。只在启动、导出或复制地址时要求完整有效配置。

待有服务器后，在公网 Linux 服务器部署同版本 frps。例如：

```toml
bindPort = 7000
auth.method = "token"
auth.token = "换成随机长密码"
auth.additionalScopes = ["HeartBeats", "NewWorkConns"]
transport.tls.force = true
allowPorts = [{ single = 25565 }]
```

执行 `./frps -c ./frps.toml`。安全组和防火墙放行 TCP 7000、TCP 25565。此基础示例没有自定义证书；正式部署时增加服务端证书，客户端配置匹配的可信 CA / 系统 CA 和 TLS 服务器名。公网中转配置不修改 MC 账户认证。

## 配置和凭据

- 设置文件：`%LOCALAPPDATA%/MC-Link/settings.json`。默认不保存 Token；勾选保存后是本机明文存储。
- 启动时临时生成含 Token 的 TOML，正常停止/退出后删除。强制结束程序、断电或系统崩溃可能留下 `%TEMP%/mc-link-*` 文件夹，请按需清理自己这次生成的配置。
- 导出 TOML 含 Token，界面会先确认；不要将其当作联机地址发送给朋友。
- 导入接受一个普通 TCP 隧道、STCP 房主或 STCP 朋友配置，Token 鉴权、TLS 和指定 CA 选项。朋友入口强制只监听本机 127.0.0.1。OIDC、插件、多隧道、KCP/QUIC、未知配置项会明确拒绝。
- 玩家连接地址可与控制节点地址不同，请填写服务商实际提供的地址；不包含 `:端口`。
- 自选 frpc 程序会在本机执行，请只选择自己信任的官方或服务商程序。工具不会修改 Windows 安全设置。

## 常见问题

- 本地端口不通：重新开放局域网，核对游戏显示的端口；检查本机防火墙和 Java 网络权限。
- 节点连接失败：核对 IP、7000 端口、Token 和服务器是否在线。
- 代理注册失败：检查远程端口占用、服务端 allowPorts 和服务商端口授权。
- 好友连不上：核对公网 IP、TCP 游戏端口安全组/防火墙，双方版本与模组；公网 25565 与本地随机端口不同是正常的。
- 证书验证失败：核对 CA、TLS 服务器名和服务端证书。不要盲目启用系统 CA 去连接自签名节点。
- 系统拒绝执行 frpc：本机实际检测到 Windows Defender `PUA:Win32/FRProxy`。查看 Windows 安全中心保护历史记录，并按自己的安全策略处理；本工具不会绕过拦截。未解除执行限制前无法建立隧道。

## 开发与验证

```
python -m unittest discover -s tests -v
python tests/integration.py
```

integration.py 使用回环地址、本机官方 frps/frpc 和 TCP echo 服务验证真实数据往返，不连接公网。需要系统允许 frp 程序运行。tests/gui_smoke.py 验证界面构造与离线操作。

新增 `python tests/stcp_integration.py` 用于本地真实 STCP 房主/朋友数据往返。当前机器仍因 Defender 阻止 frpc 执行而无法通过；单元测试和界面测试不能替代真实 MC 联机验证。

Material 验证需要 PySide6：`python tests/qt_gui_smoke.py` 检查真正 QML 控件、页面切换与小窗口布局。`python material_app.py --capture build/material-preview.png` 导出当前界面截图。

### 从源码构建 Windows x64 便携包

发布版使用 Windows x64 版 Python 3.13.9。先安装构建依赖。

```powershell
python -m pip install --target .build-deps -r requirements-build.txt
```

1. 下载 EasyTier v2.6.4 的 `easytier-windows-x86_64-v2.6.4.zip`。 [官方发行页](https://github.com/EasyTier/EasyTier/releases/tag/v2.6.4)
2. 下载 WinPcap 4.1.3 安装包，用 7-Zip 提取 `Packet.dll`，保留重名文件以便对照。选 SHA-256 为 `ab3cce674f5216895fd26a073771f82b05d4c8b214a89f0f288a59774a06b14b` 的 64 位文件。 [WinPcap 官网](https://www.winpcap.org/install/) · [7-Zip 官网](https://www.7-zip.org/)
3. 运行下面的命令，替换为刚下载或解压的实际路径。脚本先核对发行 ZIP 和 DLL 的哈希，再将依赖写入 `bin/easytier/`。

```powershell
python packaging/prepare-easytier.py "easytier-windows-x86_64-v2.6.4.zip" "解压路径/Packet_2.dll"
./build-lan.ps1
```

Windows 便携 ZIP 生成在 `dist/`，公开发行时可作为 GitHub Release 附件。源码仓库提交构建脚本、测试、资源和许可文件。 `bin/`、`test-tools/`、`build/` 和 `dist/` 由本地构建或测试准备。

本次验证状态见 VALIDATION.md。未有真实公网节点和运行中的 MC 世界，因此不声称已验证真实跨网 MC 联机。

## 第三方许可

N4MC-LAN 自有源码采用 [MIT 许可证](LICENSE)。便携包随附 [第三方声明](THIRD-PARTY-NOTICES.md) 和 `licenses/` 中的许可文件。
