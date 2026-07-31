# 安装与启动

## 千问视觉依赖

千问视觉通过 `openai` Python SDK 调用阿里云百炼兼容接口。升级已有环境后需要重新安装依赖并重启 Maidie：

```powershell
python -m pip install -r requirements.txt
```

如果界面提示网络或模型服务失败，而日志中出现 `No module named 'openai'`，说明启动 Maidie 的 Python 环境尚未安装新依赖。应在同一个虚拟环境中执行安装和启动。配置与连通测试见[千问视觉与屏幕理解](VISION.md)。

## 环境要求

- Windows 10 或 Windows 11
- Python 3.10 或更高版本
- 推荐使用独立虚拟环境
- 可选：Tesseract OCR 及中英文语言包

## 快速启动

双击项目目录中的：

```text
start_maidie.bat
```

脚本会在首次启动时创建 `.venv` 并安装 `requirements.txt` 中的依赖。
后续启动会直接使用该虚拟环境；依赖文件更新后，请手动重新执行安装命令。

## 手动启动

在 `maidie_desktop_pet` 目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

主要依赖：

- `PyQt6`：桌面窗口、动画和交互。
- `requests`：AI API、SSE 流和联网工具请求。
- `Pillow`：动作条导入和图像处理。
- `pytesseract`：可选的本地 OCR 调用。

## OCR 安装

OCR 默认关闭；不使用屏幕识别时无需安装 Tesseract。

Maidie 会自动识别默认安装路径：

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

语言包目录应至少包含：

```text
C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata
C:\Program Files\Tesseract-OCR\tessdata\chi_sim.traineddata
```

检查安装和语言包：

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

启用 OCR 前，请阅读[隐私与安全边界](PRIVACY_AND_SAFETY.md)，再在设置界面开启屏幕理解。

## 构建 Windows 发布包

先激活用于构建的 conda 或其他 Python 3.10+ x64 环境，并安装
[Inno Setup 6](https://jrsoftware.org/isinfo.php)，然后使用唯一推荐入口：

```powershell
python scripts/build.py beta
python scripts/build.py stable
```

脚本读取根目录 `version.json`，根据参数设置发布渠道，清理旧 `build/` 和
`dist/`，再使用现有 `maidie.spec` 构建 one-folder 程序并调用
`installer/MaidieSetup.iss`。以 `v0.9.0 beta` 为例，输出为：

```text
release\Maidie-v0.9.0-beta-win64\
release\Maidie_Setup_v0.9.0_beta.exe
```

发布时必须保留整个 `Maidie-v版本-channel-win64` 目录，不能只拿走 EXE。
`build_exe.bat` 和 `build_installer.bat` 仅保留为旧 beta 调用的兼容转发，
不再包含独立打包逻辑。完整发布规范见[发布流程](release.md)。

构建包使用 `packaging/config.json`，其中不应出现真实 Key。首次运行后可通过设置界面修改 `%APPDATA%\Maidie\config.json`，也可以使用环境变量。

安装包需要管理员权限，默认安装到 `C:\Program Files\Maidie`，并创建开始菜单快捷方式。桌面快捷方式由用户在安装界面选择。

配置、日志、记忆和宠物状态统一写入 `%APPDATA%\Maidie`，安装器不创建、覆盖或卸载该目录。安装目录中的 `config\config.json` 只是首次启动使用的只读默认模板，不是用户配置。若 Inno Setup 安装在自定义位置，可设置：

```powershell
$env:INNO_SETUP_COMPILER = "D:\Tools\Inno Setup 6\ISCC.exe"
python scripts/build.py beta
```

安装程序默认创建开始菜单快捷方式，桌面快捷方式由用户在安装界面选择。`packaging/maidie.ico` 同时用于应用 EXE、安装程序和快捷方式；透明图标源文件为 `packaging/maidie-icon.png`。

## 启动问题排查

- 无法创建虚拟环境：确认 `python --version` 可用且版本不低于 3.10。
- 缺少模块：激活 `.venv` 后重新执行 `python -m pip install -r requirements.txt`。
- OCR 不可用：检查可执行文件路径和 `eng`、`chi_sim` 语言包。
- API 请求失败：检查 Base URL、模型名称和 Key，详见[配置说明](CONFIG.md)。
- 打包失败：确认当前环境为 Python 3.10+，并检查 PyInstaller 输出；不要只复制生成的 EXE。
- 安装包失败：确认已安装 Inno Setup 6，或设置 `INNO_SETUP_COMPILER`。
