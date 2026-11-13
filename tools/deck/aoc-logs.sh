#!/bin/bash
# Registros do AoC Recomp no Steam Deck: lista e resume as sessões jogadas, acompanha a sessão em andamento e junta um
# pacote para mandar. Fica na pasta do jogo (tools/build.py dist); roda no Konsole ou por SSH.
#
#   ./aoc-logs.sh                    resumo da última sessão (o mesmo que "resumo 1")
#   ./aoc-logs.sh lista [N]          uma linha por sessão, as N mais recentes (padrão 15): data, minutos, fps, watts
#                                    da APU (média e pico), bateria, temperatura máxima de CPU e GPU, erros
#   ./aoc-logs.sh resumo [K] [--rows]  resumo da K-ésima sessão mais recente (1 = a última); --rows lista as linhas
#                                    "sys:" de 10 em 10 s
#   ./aoc-logs.sh ao-vivo            segue a sessão em andamento (linhas sys:, fps:, frametime:, erros); Ctrl+C sai
#   ./aoc-logs.sh sistema            estado da máquina agora: TDP, watts, temperaturas, ventoinha, clocks, bateria
#   ./aoc-logs.sh detalhado on|off   liga/desliga o traço de desempenho (AOC_TRACE=perf) nas próximas sessões: GPU por
#                                    frame, sombra dos pools, write-watch; custa pouco, mas o log cresce
#   ./aoc-logs.sh diag [K]           relatórios do gravador de estado (travada, tela preta ou escura) da K-ésima
#                                    sessão, lidos por ferramentas/diag_view.py (tools/diag_view.py no repositório)
#   ./aoc-logs.sh pacote             logs/pacote-<data>.tar.gz com as sessões, o aoc.ini, o estado da máquina e as
#                                    imagens dos dois últimos relatórios (logs/diag/)
#
# As sessões: logs/aoc.log é a última; o aoc.sh guarda cada sessão anterior comprimida em logs/sessoes/ ao abrir o jogo
# (as 60 mais recentes). O resumo vem de ferramentas/logsum.py (tools/deck/logsum.py no repositório).
here="$(cd "$(dirname "$0")" && pwd)"
L="$here/logs"
S="$L/sessoes"
PY="$here/ferramentas/logsum.py"
INI="$here/aoc.ini"

# The sessions, newest first: logs/aoc.log, then logs/sessoes/*.log.gz by name (the name is the start time).
sessions() {
    [ -f "$L/aoc.log" ] && echo "$L/aoc.log"
    ls -1 "$S"/*.log.gz 2>/dev/null | sort -r
}

need_python() {
    command -v python3 >/dev/null || { echo "python3 não encontrado"; exit 1; }
    [ -f "$PY" ] || { echo "falta $PY"; exit 1; }
}

# One sysfs value from the hwmon whose name is $1 ($2 = file); empty when absent.
hw() {
    for d in /sys/class/hwmon/hwmon*; do
        [ "$(cat "$d/name" 2>/dev/null)" = "$1" ] && cat "$d/$2" 2>/dev/null && return
    done
}

machine() {
    w() { [ -n "$1" ] && awk -v v="$1" -v d="$2" 'BEGIN { printf "%.1f", v / d }' || printf -- '-'; }
    echo "data: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "sistema: $(. /etc/os-release 2>/dev/null; echo "$PRETTY_NAME $VERSION_ID") · kernel $(uname -r)"
    echo "APU: $(w "$(hw amdgpu power1_average)" 1000000) W agora; limite (TDP) $(w "$(hw amdgpu power1_cap)" 1000000) W" \
         "(máx $(w "$(hw amdgpu power1_cap_max)" 1000000) W)"
    echo "temperaturas: CPU $(w "$(hw k10temp temp1_input)" 1000) °C, GPU $(w "$(hw amdgpu temp1_input)" 1000) °C;" \
         "ventoinha $(hw steamdeck_hwmon fan1_input) rpm"
    echo "clocks: GPU $(w "$(hw amdgpu freq1_input)" 1000000) MHz; CPU" \
         "$(for c in /sys/devices/system/cpu/cpu[0-7]/cpufreq/scaling_cur_freq; do w "$(cat "$c")" 1000; printf ' '; done) MHz;" \
         "governador $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)"
    echo "GPU ocupada: $(cat /sys/class/drm/card*/device/gpu_busy_percent 2>/dev/null | head -1) %;" \
         "nível de desempenho: $(cat /sys/class/drm/card*/device/power_dpm_force_performance_level 2>/dev/null | head -1)"
    for b in /sys/class/power_supply/*; do
        [ "$(cat "$b/type" 2>/dev/null)" = Battery ] || continue
        v=$(cat "$b/voltage_now" 2>/dev/null); i=$(cat "$b/current_now" 2>/dev/null)
        p=$( [ -n "$v" ] && [ -n "$i" ] && awk -v v="$v" -v i="$i" 'BEGIN { printf "%.1f", v * i / 1e12 }' )
        echo "bateria: $(cat "$b/capacity")% $(cat "$b/status"), ${p:--} W"
    done
    echo "memória: $(free -m | awk '/^Mem:/ { print $3 " de " $2 " MiB em uso" }')"
    pgrep -a aoc | grep -v aoc-logs | sed 's/^/processo: /'
}

cmd=${1:-resumo}
case "$cmd" in
lista)
    need_python
    n=${2:-15}
    files=$(sessions | head -n "$n")
    [ -n "$files" ] || { echo "nenhuma sessão em $L"; exit 0; }
    # oldest first, so the table reads top to bottom in time
    python3 "$PY" --list $(echo "$files" | tac)
    ;;
resumo)
    need_python
    shift
    k=1
    case "$1" in [0-9]*) k=$1; shift ;; esac
    f=$(sessions | sed -n "${k}p")
    [ -n "$f" ] || { echo "não há a sessão $k (./aoc-logs.sh lista)"; exit 1; }
    echo "== $f"
    python3 "$PY" "$f" "$@"
    ;;
ao-vivo)
    [ -f "$L/aoc.log" ] || { echo "sem logs/aoc.log"; exit 1; }
    tail -n 20 -F "$L/aoc.log" | grep --line-buffered -E '^\[host\] (sys:|fps:|frametime:|resolution:)|FATAL|hang:|device lost'
    ;;
sistema)
    machine
    ;;
detalhado)
    case "$2" in
    on)
        if grep -qiE '^[[:space:]]*trace[[:space:]]*=' "$INI" 2>/dev/null; then
            sed -i -E 's/^[[:space:]]*[Tt][Rr][Aa][Cc][Ee][[:space:]]*=.*/trace = perf/' "$INI"
        else
            printf '\n[diagnostics]\ntrace = perf\n' >> "$INI"
        fi
        echo "traço de desempenho ligado nas próximas sessões (aoc.ini: trace = perf)"
        ;;
    off)
        sed -i -E '/^[[:space:]]*[Tt][Rr][Aa][Cc][Ee][[:space:]]*=/d' "$INI" 2>/dev/null
        echo "traço de desempenho desligado (só as linhas sys: e o resumo de frametime)"
        ;;
    *)
        grep -iE '^[[:space:]]*trace[[:space:]]*=' "$INI" 2>/dev/null || echo "desligado"
        ;;
    esac
    ;;
diag)
    command -v python3 >/dev/null || { echo "python3 não encontrado"; exit 1; }
    [ -f "$here/ferramentas/diag_view.py" ] || { echo "falta $here/ferramentas/diag_view.py"; exit 1; }
    f=$(sessions | sed -n "${2:-1}p")
    [ -n "$f" ] || { echo "sem sessão ${2:-1}"; exit 1; }
    case "$f" in
    *.gz) t=$(mktemp); gzip -dc "$f" > "$t"; python3 "$here/ferramentas/diag_view.py" "$t" --threads; rm -f "$t" ;;
    *) python3 "$here/ferramentas/diag_view.py" "$f" --threads ;;
    esac
    ;;
pacote)
    ts=$(date +%Y%m%d-%H%M%S)
    tmp=$(mktemp -d)
    machine > "$tmp/maquina.txt" 2>&1
    cp "$INI" "$tmp/" 2>/dev/null
    mkdir -p "$tmp/logs"
    sessions | head -n 10 | while read -r f; do cp "$f" "$tmp/logs/"; done
    # the picture copies of the two newest recorder reports (320x180, small); not hits/, marks/ or dump/ (large)
    ls -1d "$L"/diag/2*-* 2>/dev/null | sort -r | head -n 2 | while read -r d; do
        mkdir -p "$tmp/logs/diag" && cp -r "$d" "$tmp/logs/diag/"
    done
    out="$L/pacote-$ts.tar.gz"
    tar -czf "$out" -C "$tmp" .
    rm -rf "$tmp"
    echo "$out ($(du -h "$out" | cut -f1))"
    ;;
*)
    sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
