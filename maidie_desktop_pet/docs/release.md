# Windows 发布流程

Maidie 只有一个真实构建入口：

```powershell
python scripts/build.py beta
python scripts/build.py stable
```

`build_exe.bat` 和 `build_installer.bat` 仅用于兼容旧调用，都会转发到
`python scripts/build.py beta`，不再维护独立构建逻辑。

## 构建前准备

- Windows 10/11 x64
- 64 位 Python 3.10 或更高版本
- Inno Setup 6
- 根目录 `version.json` 中维护 SemVer 版本号和 Build 编号

如果 Inno Setup 不在默认位置，可设置：

```powershell
$env:INNO_SETUP_COMPILER = "D:\Tools\Inno Setup 6\ISCC.exe"
```

## 自动执行步骤

构建脚本会依次：

1. 检查 Python 与 Windows x64 环境。
2. 读取并校验 `version.json`。
3. 将命令行渠道写入 `version.json`，使其继续作为唯一版本来源。
4. 检查并安装运行/构建依赖。
5. 仅清理根目录下的 `build/` 和 `dist/`。
6. 使用现有 `maidie.spec` 执行 PyInstaller。
7. 生成标准 one-folder 发布目录。
8. 使用 `installer/MaidieSetup.iss` 生成 Inno Setup 安装器。

## 输出结构

以 `python scripts/build.py beta`、版本 `0.9.0` 为例：

```text
release/
├── Maidie-v0.9.0-beta-win64/
│   ├── Maidie.exe
│   ├── assets/
│   ├── docs/
│   ├── README.txt
│   ├── version.json
│   └── 其他运行时 DLL 与依赖
└── Maidie_Setup_v0.9.0_beta.exe
```

不要单独复制 `Maidie.exe`；发布时必须保留完整 one-folder 目录。

## 版本发布

确认 `version.json` 的版本和 Build 编号后运行对应渠道命令。构建成功并完成
安装/启动检查后再提交版本文件和发布配置，然后创建 Git 标签：

```powershell
git tag v0.9.0
git push origin v0.9.0
```

用户配置、日志和数据库位于 `%APPDATA%\Maidie`，不属于 `build/`、`dist/`
或 `release/`，构建清理和安装升级不得修改这些数据。

正式安装器需要管理员权限，默认安装到 `C:\Program Files\Maidie`。安装器只管理
程序文件、静态资源、快捷方式和卸载项，不创建、覆盖或删除
`%APPDATA%\Maidie`。安装目录中的 `config\config.json` 是首次启动所需的
只读默认模板，不是用户配置。

为降低安装包体积，Inno Setup 保留 `lzma2` 和固实压缩，并仅排除 Qt WebEngine
同时提供 release 版本的 `.debug.pak`、`.debug.bin` 资源副本。禁止继续裁剪未知
DLL、Qt/Python runtime 或改变 PyInstaller one-folder 目录结构。
