# 验证记录

## N4MC-LAN v0.3 · 2026-11-09

- 55 项测试覆盖既有功能，以及房主和访客人数刷新、状态探测失败后清空人数、公共节点排除和中继丢包读数处理。
- 使用便携包内置的 EasyTier 2.6.4 在回环地址建立两个临时节点，实际 CLI 返回 2 台设备和直连路径。
- Qt 界面检查覆盖连接、掉线、恢复、复制诊断和 920×720 窗口。预览使用示例状态。尚未执行两地实机 Minecraft 联机测试。

日期：2026-11-06。

## 托管虚拟局域网更新

- 接入 Tailscale 只读 CLI 状态、本人 IP、在线设备选择、组网地址复制和显式 TCP 端口检查。登录/设备共享在官方客户端/控制台完成。
- 测试数据覆盖正常/未登录/异常 JSON、超时和 CLI 失败、IPv6、离线地址清理、房主/朋友地址、排序变化后按 IP 保持选择。真实 QML LAN 页面和地址绑定测试通过。
- 本机原先未安装 Tailscale。已从 pkgs.tailscale.com 下载 1.104.5 amd64 MSI，Authenticode 验证 Valid，签发者 Tailscale Inc.。使用原生路径安装返回 1603；日志明确“requires elevated privileges to install”。没有安装成功、没有登录账号、没有改变路由/防火墙。
- 需要用户完成 Windows 管理员授权安装及账号登录，并由另一台电脑完成授权组网，才能进行实际跨网 Minecraft 验证。测试样本截图不是已接入真实 tailnet 的证据。
- 独立源码审查完成。设备刷新后选择按 IP 跟踪，实际 QML 已验证顺序变化不会改指向其他房主；错误 JSON 原始类型也已补回归并修复。完整测试 47 项及真实 QML 检查通过。

## 房间加入版更新

- 支持 public / host / join 三种模式，STCP 房主和 loopback-only 朋友配置、房间邀请、角色切换、朋友端端口占用检查、双凭据日志隐藏。
- 邀请排除节点 Token、本地 CA 路径及可执行程序，导入时清空旧节点凭据与 CA；自定义 CA 要求保留并阻止静默降级。运行中复制邀请使用启动时捕获的房间配置。
- 目前完整回归 35 项通过，实际 QML 创建/加入切换与窗口检查通过。界面预览 build/join-preview.png。独立源码审查完成，跨模式隐藏字段校验与 visitor 名称严格导入均已补回归并修复。
- 已实际尝试 tests/stcp_integration.py（只使用回环地址），在启动官方 frpc 时仍得到 WinError 5，清理了本次测试进程。真实 STCP 数据往返及公网 MC 联机尚未通过；没有修改 Windows 安全策略。

## Material 版更新

- 新界面使用 PySide6 6.12 / Qt Quick Controls Material，已验证 QML 实际加载、控件双向数据流、切换页面保留字段、导入更新字段和 920×720 最小窗口下的主操作区。
- 当前完整测试 19 项通过，包含 Qt 控制器的离线保存、TLS/CA 导入、自选客户端路径、启动中取消和分享地址稳定性。
- 背景为用户指定 Wallpaper Engine scene.pkg 内的 2560×1440 JPEG。Qt 解码与离线资源路径通过检查；窗口截图见 build/material-preview.png。没有加载或执行场景 shader。
- 独立审查发现启动阶段编辑表单可能改变分享地址；回归测试已复现并修复。配置和真实 frp 运行限制仍与下文一致。
- 便携包首次发现 QtCore 加载失败，定位为打包器从 PATH 的 Poppler 目录复制了不兼容的 icuuc.dll（带 *_78 导出）。排除该错误副本、使用 Windows 系统 ICU 后，实际便携 EXE 的 Material/QML/背景自检通过，退出码 0。构建脚本已固定此处理；未更改系统 DLL 或 PATH。

## 已通过

- Python 3.13.9 / Tk 8.6：12 项 unittest 全部通过，涵盖 TOML 转义和往返、IPv6、非法端口、导入拒绝不支持的配置、TLS 配置保留、Token 保存选择、子进程重复启动和退出清理、日志隐藏认证信息；包含缺省随机端口导入与 DEL 特殊字符回归。
- Tkinter GUI smoke：真实原生窗口创建，默认尺寸下日志可读、离线保存、TLS 状态更新、干净退出。
- PyInstaller Windows 便携目录构建成功，包含 Python/Tcl/Tk 运行库，无需用户安装 Python。
- 已实际运行打包 EXE 自检，退出码 0，确认打包后的 Tkinter 和应用模块可加载。
- 独立代码审查已完成；固定端口导入语义、特殊字符 TOML 转义、启动检查卡住时的取消退出均已补回归并修复。正常退出也会取消 Tk 定时回调。

## 真实隧道测试受阻

已运行 tests/integration.py，测试使用本地回环 frps + frpc + 模拟 TCP 服务，不依赖公网服务器。frps 可启动；Windows 拒绝启动 frpc（WinError 5）。只读 Windows Defender 日志确认检测名 PUA:Win32/FRProxy，类别“潜在的垃圾软件”，路径对应官方 v0.72.0 frpc。没有修改 Defender、添加排除项或尝试绕过检测。

因此尚未通过真实 frp 数据往返测试；不能将进程管理单元测试视为真实隧道已通过。运行环境允许官方 frpc 后，可重新执行测试。真实 MC 世界和公网节点也尚未验证。

## 环境说明

普通工具沙箱下 tempfile.mkstemp 被权限限制并重复尝试；在正常用户权限下完整单元测试用时约 0.04 秒并通过。未修改应用逻辑以规避沙箱权限。
