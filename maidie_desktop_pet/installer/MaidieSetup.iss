#ifndef MyAppVersion
  #error "MyAppVersion must be supplied from version.json"
#endif
#ifndef MyAppChannel
  #error "MyAppChannel must be supplied from version.json"
#endif
#ifndef MyAppBuild
  #error "MyAppBuild must be supplied from version.json"
#endif
#ifndef MyAppSourceDir
  #error "MyAppSourceDir must be supplied by scripts/build.py"
#endif
#ifndef MyOutputDir
  #error "MyOutputDir must be supplied by scripts/build.py"
#endif
#ifndef MyOutputBaseFilename
  #error "MyOutputBaseFilename must be supplied by scripts/build.py"
#endif

#define MyAppName "Maidie"
#define MyAppPublisher "Maidie"
#define MyAppExeName "Maidie.exe"

[Setup]
AppId={{DF6C28A8-C3FC-49A7-AB97-415B162A87C3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion} {#MyAppChannel} (Build {#MyAppBuild})
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}.{#MyAppBuild}
VersionInfoProductVersion={#MyAppVersion}.{#MyAppBuild}
VersionInfoTextVersion={#MyAppVersion}.{#MyAppBuild}
VersionInfoProductTextVersion={#MyAppVersion}-{#MyAppChannel} (Build {#MyAppBuild})
DefaultDirName={autopf}\Maidie
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
UsePreviousAppDir=no
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\packaging\maidie.ico

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: unchecked

[Files]
; config\config.json 是首次启动所需的只读默认模板；真正的用户配置位于 %APPDATA%\Maidie。
; 仅排除明确的用户数据、构建杂项和 Qt release 运行时不会使用的 debug 资源副本。
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Excludes: "logs\*,memory\*,database\*,skins\*,memory.db,pet_state.db,scheduled_tasks.json,*.log,*.tmp,*.bak,*.pdb,*.pyc,*.pyo,__pycache__\*,*\__pycache__\*,tests\*,*\tests\*,.pytest_cache\*,*\.pytest_cache\*,PyQt6\Qt6\resources\*.debug.pak,PyQt6\Qt6\resources\*.debug.bin"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Maidie"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Maidie"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 Maidie"; Flags: nowait postinstall skipifsilent
