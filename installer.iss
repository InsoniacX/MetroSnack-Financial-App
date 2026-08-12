[Setup]
AppName=MetroSnack
AppVersion=1.0.0
AppPublisher=MetroSnack
DefaultDirName={autopf}\MetroSnack
DefaultGroupName=MetroSnack
OutputDir=installer_output
OutputBaseFilename=MetroSnack_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
;Name: "indonesian"; MessagesFile: "compiler:Languages\Indonesian.isl"

[Files]
Source: "build\flutter\build\windows\x64\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MetroSnack"; Filename: "{app}\MetroSnack.exe"
Name: "{autodesktop}\MetroSnack"; Filename: "{app}\MetroSnack.exe"

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut tambahan:"

[Run]
Filename: "{app}\MetroSnack.exe"; Description: "Jalankan MetroSnack sekarang"; Flags: nowait postinstall skipifsilent