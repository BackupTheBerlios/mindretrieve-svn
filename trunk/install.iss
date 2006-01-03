; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
AppId=MindRetrieve
AppName=MindRetrieve
AppVerName=MindRetrieve 0.6.1
AppPublisher=MindRetrieve
AppPublisherURL=http://mindretrieve.berlios.de/
AppSupportURL=http://mindretrieve.berlios.de/
AppUpdatesURL=http://mindretrieve.berlios.de/
DefaultDirName={pf}\MindRetrieve
DefaultGroupName=MindRetrieve
DisableProgramGroupPage=yes
Compression=lzma
SolidCompression=yes
OutputDir=.
OutputBaseFilename=mindretrieve0.6.1win32

[Files]
Source: "g:\bin\py_repos\mindretrieve\trunk\dist\MindRetrieve.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "g:\bin\py_repos\mindretrieve\trunk\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

;[InstallDelete]
;Filename: "{sys}\net.exe"; Parameters: "stop MindRetrieve"; RunOnceId: "StopService"


[InstallDelete]
Name: {app}\MindRetrieve.exe; Type: files; Check: StopAndRemoveService

[Run]
Filename: "{app}\MindRetrieve.exe"; Description: "Register I-identd service"; Parameters: "-install -auto";
Filename: "{sys}\net.exe"; Parameters: "start MindRetrieve"
Filename: "{app}\run.exe"; Parameters: "--run minds.weblib.win32.context_menu --register";
Filename: {app}\docs\readme.html; Flags: shellexec

[UninstallRun]
Filename: "{app}\run.exe"; Parameters: "--run minds.weblib.win32.context_menu --unregister";
Filename: "{sys}\net.exe"; Parameters: "stop MindRetrieve"; RunOnceId: "StopService"
Filename: "{app}\MindRetrieve.exe"; Parameters: "-remove"; RunOnceId: "RemoveService"

[Code]
function StopAndRemoveService(): Boolean;
var
  ErrorCode: Integer;
begin
  if RegValueExists(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Services\MindRetrieve', 'ImagePath') or
    RegValueExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\RunServices', 'MyService') then
    begin
      InstExec(ExpandConstant('{sys}\net.exe'), 'stop MindRetrieve', '', True, False, SW_SHOWNORMAL, ErrorCode);
      InstExec(ExpandConstant('{app}\MindRetrieve.exe'), '-remove', '', True, False, SW_SHOWNORMAL, ErrorCode);
      BringToFrontAndRestore();
    end;
  Result := True;
end;
