# PantumCompat：国内版奔图 P3305DN 的 macOS 兼容打印组件

[English](README.md) | 简体中文

**本项目面向国内版、信创配置的奔图 P3305DN，目标是解决打印机网络可达、UOS 驱动能够打印，但测试中的 Mac 原驱动不出纸的问题。** 它提供 Apple Silicon 原生 CUPS 过滤器，将文稿转成经过编码的 PCL XL；此前组件已在最初的国内版设备上完成 WPS 实机打印。

> **先确认国内版与海外版。** 国内官网列示 31 页/分钟、800 MHz，海外官网的同名型号列示另一套配置。不能仅凭 P3305DN 型号名认定驱动通用。详细参数和官方出处见[版本对照](docs/COMPATIBILITY.md)。

## 适用范围

- 目标设备：国内版 / 信创配置 P3305DN；不是所有地区、所有批次同名机器的通用驱动。
- Mac：Apple Silicon / arm64；开发环境为 macOS 26.4.1、Ghostscript 10.08.0。Intel Mac 未验证。
- 打印链路：macOS CUPS → 单色 PCL XL → 整体 XOR `0xA5` → 有线网络 RAW 9100。
- 本地构建时封装独立 Ghostscript 环境，解决过滤器在 CUPS 沙箱内无法直接访问 Homebrew 中 `gs` 的问题。
- 实机依据：此前 0.2.0 在最初的国内版设备上获得 WPS 正常出纸反馈。公开版通过了构建与无纸转换检查，安装配置修订尚未单独完成实机验收。

配置中提供 600 dpi、A4/A5/Letter/Legal 和单双面选项；份数、页面范围、合版由上游 CUPS 处理。字体完全一致、复杂表格、图片、多页和双面等需按实际文档验收，不能由单页成功推导为全部兼容。参见[测试边界](docs/TESTING.md)。

## 本机构建与安装

公开发行物只有源码、PPD、通用样例及构建工具，不含厂商专有驱动、第三方二进制、字体或真实打印文稿。

需要 Apple Silicon Mac、Xcode Command Line Tools、Python 3.9 或更新版本，以及已经通过 Homebrew 安装的 Ghostscript。在项目目录运行：

```sh
python3 tools/build.py
```

工具会输出新的 `build/local-*` 目录和 `LOCAL-USE.pkg` 安装包，不自动安装、不连接实际打印机。可选的无纸检查如下，将示例替换为本次输出目录：

```sh
python3 tools/test.py build/local-YOUR-BUILD-DIRECTORY
```

打开本机构建的安装包并按系统提示输入管理员密码。安装会经过真正的 CUPS 做本机回环自检，不让实体打印机出纸，不修改全局沙箱配置或现有队列。安装包只有临时签名，没有 Developer ID 签名或 Apple 公证。

完成后，把 `printer.example` 换成自己的打印机 IPv4 地址或 DNS 主机名：

```sh
sudo /Library/Printers/PantumCompat/Tools/configure-printer printer.example
```

应用内选择 **Pantum P3305DN China (Compatible)**，先试一页。默认 A4、600 dpi、单面；配置工具不发送测试页、不修改默认打印机。RAW 9100 没有传输加密，仅应在可信网络使用。

## 常见问题

**海外版 P3305DN 能用吗？** 不在已验证范围内，应先匹配当地官方驱动。相同型号名不足以证明协议和固件兼容。

**能保证所有 WPS、表格和 PDF 都能打印吗？** 不能。已有实机结果只覆盖具体设备与文稿，仍需检查字体、排版、双面等实际效果。

**这是 AirPrint 服务器、固件破解或 UOS 虚拟机方案吗？** 都不是。这是运行在 Mac 上的 CUPS 转换组件，不新增打印机固件功能，不运行 UOS/Linux 二进制，也不解决网络离线或输入字体缺失。

**反馈时能上传什么？** 优先使用公开样例，只提供型号、国内/海外版本判断、系统和组件版本、脱敏错误信息。不要上传真实文稿、打印数据、完整配置页、姓名、邮箱、序列号、MAC/IP 地址或未脱敏日志。详见[隐私说明](docs/PRIVACY.md)。

本项目独立维护，非奔图官方驱动。采用 **AGPL-3.0-or-later**；第三方保持各自许可。发布本机构建的二进制包前，需完成[再分发要求](docs/REDISTRIBUTION.md)。
