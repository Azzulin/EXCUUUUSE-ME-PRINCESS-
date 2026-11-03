@echo off
rem Prepara o WSL (uma vez) e compila o codigo do jogo. Pode pedir a senha do sudo do Ubuntu na primeira vez.
rem O log completo fica em build\build-wsl.log (o Claude le esse arquivo).
cd /d "%~dp0..\.."
wsl -e bash -lc "cd \"$(wslpath '%CD%')\" && bash tools/setup_wsl.sh && . ~/.venvs/aoc/bin/activate && mkdir -p build && python3 -u tools/build.py --work ~/aoc-build 2>&1 | tee build/build-wsl.log"
echo.
echo Terminado. Veja build\build-wsl.log
pause
