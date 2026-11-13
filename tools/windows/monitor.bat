@echo off
rem Modo monitor do AoC Recomp: joga normalmente e o jogo guarda sozinho o que precisamos para investigar.
rem Copie para a pasta do jogo (ao lado do aoc.exe) e abra por aqui em vez do launcher.
rem
rem   - cada golpe (inicio de vibracao do controle): 8 imagens em tamanho cheio em logs\diag\hits\ (ate 40 golpes)
rem   - despejo de frame num golpe: acrescente set AOC_HIT_DUMP=<n> ou AOC_ATTACK_DUMP=<n> (conta desde o menu)
rem   - cada ataque (botao Y, um a cada 20 s): 12 imagens cheias em logs\diag\hits\a*.png
rem   - F8: marca o momento (imagem cheia em logs\diag\marks\, relatorio no log, despejo do frame)
rem   - cena escura ou preta por 15 s: relatorio + imagem + despejo, sem apertar nada
rem   - os comandos da sessao ficam em logs\sessions\ e o registro em logs\aoc.log
rem
rem Depois de jogar: python tools\diag_view.py  (na raiz do repositorio), ou mande a pasta logs.
cd /d "%~dp0"
set AOC_VK_RECORDER=0
set AOC_DUMP=arm
set AOC_DUMP_DIR=%~dp0logs\diag\dump
set AOC_DUMP_UBO=24
set AOC_DUMP_SKIP_RUNS=1
set AOC_DUMP_MAX=6
set AOC_HIT_SHOTS=40
set AOC_ATTACK_SHOTS=30
set AOC_MARK_DUMP=1
start "" "%~dp0aoc.exe"
