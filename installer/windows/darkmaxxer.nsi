; [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
; DarkMaxxer 2.0 Modern NSIS Administrator Installer with Authenticode Support

!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "DarkMaxxer"
OutFile "../../dist/DarkMaxxer-2.0.0-Setup.exe"
InstallDir "$PROGRAMFILES64\DarkMaxxer"
InstallDirRegKey HKLM "Software\DarkMaxxer" "Install_Dir"

; Require Administrator privileges for installation
RequestExecutionLevel admin

; Modern UI Configuration
!define MUI_ABORTWARNING
!define MUI_ICON "../../gui/logo_highres.ico"
!define MUI_UNICON "../../gui/logo_highres.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN "$INSTDIR\darkmaxxer.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch DarkMaxxer AI Workspace"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "DarkMaxxer Core" SecCore
    SetShellVarContext all
    SetOutPath "$INSTDIR"
    
    ; Certificate & Trust Utilities
    File "certs/DarkMaxxer.cer"
    File "Trust-Certificate.bat"
    
    ; Register Certificate with Windows Root and TrustedPublisher stores
    ExecWait 'certutil -addstore -f "ROOT" "$INSTDIR\DarkMaxxer.cer"'
    ExecWait 'certutil -addstore -f "TrustedPublisher" "$INSTDIR\DarkMaxxer.cer"'
    
    ; Signed Binaries
    File "../../target/x86_64-pc-windows-gnu/release/darkmaxxer.exe"
    File "../../target/x86_64-pc-windows-gnu/release/darkmaxxer-installer.exe"
    
    ; Python Engine scripts
    File "../../engine_runner.py"
    File "../../gguf_airllm.py"
    File "../../llm_engine.py"
    File "../../mcp_integration.py"
    File "../../memory_manager.py"
    File "../../requirements.txt"
    File "../../config.json"
    File "../../README.md"
    File "../../LICENSE"
    
    ; Windows scripts
    File "install.bat"
    File "install.ps1"
    
    ; GUI Assets
    SetOutPath "$INSTDIR\gui"
    File /r "../../gui\*.*"
    
    SetOutPath "$INSTDIR"
    
    ; Write Uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Registry Entries for Add / Remove Programs
    WriteRegStr HKLM "Software\DarkMaxxer" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DarkMaxxer" "DisplayName" "DarkMaxxer Local AI Workspace"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DarkMaxxer" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DarkMaxxer" "DisplayIcon" '"$INSTDIR\darkmaxxer.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DarkMaxxer" "Publisher" "Vikalp Sharma (DarkMaxxer Technologies)"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DarkMaxxer" "DisplayVersion" "2.0.0"
    
    ; Start Menu Shortcuts
    CreateDirectory "$SMPROGRAMS\DarkMaxxer"
    CreateShortcut "$SMPROGRAMS\DarkMaxxer\DarkMaxxer.lnk" "$INSTDIR\darkmaxxer.exe" "" "$INSTDIR\darkmaxxer.exe" 0
    CreateShortcut "$SMPROGRAMS\DarkMaxxer\GPU Configurator.lnk" "$INSTDIR\darkmaxxer-installer.exe" "" "$INSTDIR\darkmaxxer-installer.exe" 0
    CreateShortcut "$SMPROGRAMS\DarkMaxxer\Uninstall DarkMaxxer.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
    
    ; Desktop Shortcut
    CreateShortcut "$DESKTOP\DarkMaxxer.lnk" "$INSTDIR\darkmaxxer.exe" "" "$INSTDIR\darkmaxxer.exe" 0
SectionEnd

Section "Uninstall"
    SetShellVarContext all
    
    ; Remove Shortcuts
    Delete "$DESKTOP\DarkMaxxer.lnk"
    Delete "$SMPROGRAMS\DarkMaxxer\DarkMaxxer.lnk"
    Delete "$SMPROGRAMS\DarkMaxxer\GPU Configurator.lnk"
    Delete "$SMPROGRAMS\DarkMaxxer\Uninstall DarkMaxxer.lnk"
    RMDir "$SMPROGRAMS\DarkMaxxer"
    
    ; Remove Registry Entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DarkMaxxer"
    DeleteRegKey HKLM "Software\DarkMaxxer"
    
    ; Remove Installed Files
    RMDir /r "$INSTDIR\gui"
    RMDir /r "$INSTDIR\venv"
    Delete "$INSTDIR\*.*"
    RMDir "$INSTDIR"
SectionEnd
