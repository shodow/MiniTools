@echo off
chcp 65001 >nul
set SDK=%LOCALAPPDATA%\Android\Sdk
"%SDK%\emulator\emulator.exe" -avd Medium_Phone_API_36 -no-audio -no-boot-anim -gpu swiftshader_indirect > "%TEMP%\emu_win_out.txt" 2>&1
