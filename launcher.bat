@echo off
setlocal
rem Abre o launcher (launcher\launcher.cpp): escolha a pasta com a sua copia do jogo e forje o port para o Deck
rem e/ou o Windows. Na primeira vez compila o launcher no MSYS2 UCRT64 (tools\build_launcher.py).
rem Precisa do MSYS2 em C:\msys64 com clang, SDL3 e python (docs\building.md, secao "Launcher").
cd /d "%~dp0"
set "EXE=%~dp0build\launcher\aoc-launcher.exe"
if exist "%EXE%" goto :abrir

if not exist "C:\msys64\usr\bin\bash.exe" (
    echo ERRO: MSYS2 nao encontrado em C:\msys64. Veja docs\building.md, secao "Launcher".
    pause
    exit /b 1
)
echo Compilando o launcher (so na primeira vez)...
set MSYSTEM=UCRT64
set CHERE_INVOKING=1
C:\msys64\usr\bin\bash.exe -lc "python3 tools/build_launcher.py"
if not exist "%EXE%" (
    echo ERRO: o launcher nao compilou. Veja as mensagens acima.
    pause
    exit /b 1
)

:abrir
start "" "%EXE%"
