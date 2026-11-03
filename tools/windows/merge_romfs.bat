@echo off
rem Mescla base 1.0.0 + update 1.3.0 (veja merge_romfs.ps1)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0merge_romfs.ps1"
pause
