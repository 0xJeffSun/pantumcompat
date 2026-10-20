# PantumCompat

面向 Apple Silicon Mac 的奔图 P3305DN 社区兼容打印组件。

它将 macOS CUPS 提供的 PostScript 转成字形轮廓 PDF，再生成单色 PCL XL，
对整份输出逐字节执行 XOR `0xA5`，交给 CUPS 的网络后端发送。
本项目独立维护，不是奔图官方驱动，也不隶属于打印机厂商。

## 当前状态

- 私有前身 0.2.0 已有 P3305DN 从 WPS 经 CUPS 正常出纸的使用者反馈。
- 本公开版为 0.2.1：保留转换算法，去除预设打印机地址，增加通用构建与配置工具。
- 当前构建目标为 macOS / arm64；开发验证环境为 macOS 26.4.1、Ghostscript 10.08.0。
- 尚未承诺 Intel Mac、其他型号、所有应用、字体严格一致或全部打印选项均可用。
- 支持的配置包括 600 dpi 黑白、A4/A5/Letter/Legal、单面及双面选项。
  页面范围、份数、合版由上游 CUPS 处理；具体实机覆盖范围见 [测试说明](docs/TESTING.md)。

## 源码包与本机安装包

这个公开发行物只有源码、PPD、无个人信息的单页测试样例和构建工具。
它不包含 Ghostscript 二进制、依赖库、字体、历史安装包或任何真实打印文稿。
构建工具只使用使用者已安装的 Homebrew 依赖，生成供本机安装的包。
公开分发带 Ghostscript 的二进制包前，还需完成 [第三方分发说明](docs/REDISTRIBUTION.md)。

## 本机构建

需要 Apple Silicon Mac、Xcode Command Line Tools、Python 3.9 或更新版本，
以及通过 Homebrew 安装的 Ghostscript。
构建过程会复制并重定位 Ghostscript 的依赖，创建独立运行环境；
安装后的打印过滤器不依赖直接访问 Homebrew 目录。

在项目文件夹中运行：

```sh
python3 tools/build.py
```

工具会输出一个新的 `build/local-*` 目录与 `LOCAL-USE.pkg` 安装包。
每次构建使用新目录，不覆盖旧输出、不安装软件、不调整打印队列、不发送打印任务。
当前工具只支持 Homebrew Cellar 布局；若某个依赖或许可证缺失，会停止构建。
构建工具不会自动下载或安装依赖。

可选的无纸离线检查：

```sh
python3 tools/test.py build/本次构建目录
```

## 安装与填写打印机地址

打开本机构建的安装包并按系统提示输入管理员密码。
包仅作本机临时队列的 CUPS 自检，接收端固定为本机回环地址，不会让实际打印机出纸。
它不会修改全局 CUPS 沙箱配置，也不会修改已有打印机队列。
本地安装包仅作临时签名，没有 Developer ID 签名和 Apple 公证。

安装完成后，使用下面的工具创建或更新 `P3305DN_Compat` 队列。
将示例中的 `printer.example` 换成你自己的打印机 IPv4 地址或 DNS 主机名：

```sh
sudo /Library/Printers/PantumCompat/Tools/configure-printer printer.example
```

该步骤保存目标地址，不发送测试页，不更改默认打印机；默认设置为 A4、600 dpi、单面。
工具仅处理这一条指定队列；若队列有未完成任务会停止，避免重配后意外重发。
当前配置工具接受 IPv4 地址或 DNS 主机名，不接受 IPv6、带端口或路径的 URI。
确认配置正确后，在应用中选择 **Pantum P3305DN (Compatible)**，先打印一页。
遇到异常先查看任务状态，避免反复提交同一份文稿。

## 工作原理与限制

```text
应用 → macOS CUPS PostScript → Ghostscript 字形轮廓 PDF
    → Ghostscript pxlmono → 整体 XOR 0xA5 → CUPS socket 后端 → 打印机
```

过滤器完成全部转换并检查输出边界后，才向后端释放打印数据。
它本身不连接打印机，不下载依赖，也不采集或上传文稿。
字形轮廓转换不能补回输入阶段已经缺失或被替换的字体。
RAW 9100 传输没有加密或服务端身份验证，应只在可信网络中使用。
需要驱动的传统 CUPS 过滤器接口可能随未来 macOS 版本变化。

## 隐私与问题反馈

详见 [隐私说明](docs/PRIVACY.md)。请不要上传整份打印日志、文稿、打印数据、
屏幕截图或未脱敏的系统信息。可以先用 `resources/selfcheck.ps` 复现，
只提供型号、系统版本、架构、组件版本和脱敏后的错误信息。

## 许可

本项目原始代码、脚本、兼容 PPD 和公开样例采用 **AGPL-3.0-or-later**，见 [LICENSE](LICENSE)。
第三方组件保留各自许可，见 [NOTICE](NOTICE)。
Ghostscript 的官方许可说明见 [官方发行页](https://ghostscript.com/releases/gsdnld.html)。
