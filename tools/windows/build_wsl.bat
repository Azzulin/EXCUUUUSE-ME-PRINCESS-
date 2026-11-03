@echo off
setlocal
rem Build do AoC Recomp pelo WSL, em qualquer maquina com o repositorio clonado.
rem 1) prepara o WSL (clang, lld, ninja, venv Python) - pode pedir a senha do sudo do Ubuntu na primeira vez
rem 2) extrai o codigo do jogo de "Game Files\" se ainda nao foi extraido
rem 3) gera o C e compila em ~/aoc-build (disco do Linux)
rem O log completo fica em build\build-wsl.log.
cd /d "%~dp0..\.."

where wsl >nul 2>nul
if errorlevel 1 (
    echo ERRO: o WSL nao esta instalado.
    echo No PowerShell como administrador: wsl --install -d Ubuntu-24.04
    goto :fim
)
wsl -e true >nul 2>nul
if errorlevel 1 (
    echo ERRO: o WSL nao conseguiu abrir a distro Linux padrao.
    echo Veja as distros com:          wsl -l -v
    echo Instale um Ubuntu novo com:   wsl --install -d Ubuntu-24.04
    echo Ou escolha outra como padrao: wsl --set-default NOME
    goto :fim
)
if not exist "build\v130\exefs\main" if not exist "Game Files\prod.keys" (
    echo ERRO: faltam os arquivos do jogo.
    echo Coloque em "%CD%\Game Files\" os NSPs da base, do update 1.3.0 e dos DLCs, e o seu prod.keys.
    goto :fim
)

wsl -e bash -lc "cd \"$(wslpath '%CD%')\" && bash tools/setup_wsl.sh && . ~/.venvs/aoc/bin/activate && mkdir -p build && python3 -u tools/build.py --work ~/aoc-build 2>&1 | tee build/build-wsl.log; exit ${PIPESTATUS[0]}"
if errorlevel 1 (
    echo.
    echo O build falhou. Veja build\build-wsl.log
) else (
    echo.
    echo Build concluido. Log em build\build-wsl.log
)

:fim
echo.
pause
