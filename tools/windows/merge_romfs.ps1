# Mescla o RomFS da base 1.0.0 com o patch BKTR do update 1.3.0 usando o hactool.exe, no Windows.
#
# Por que no Windows: no ambiente Linux do Cowork a escrita no disco D e lenta (~11 MB/s); nativo e muito mais rapido.
#
# Antes (uma vez): python tools/extract.py hactool-home
#   (cria build\v130\tmp\hactool-home\.switch\prod.keys e title.keys; nada disso vai para o git)
#
# Uso, na raiz do repositorio (ou clique duas vezes em merge_romfs.bat):
#   powershell -ExecutionPolicy Bypass -File tools\windows\merge_romfs.ps1
#
# Resultado: build\v130\romfs.bin (imagem RomFS 1.3.0 completa) e build\v130\merge.log.
# Arquivo deste script so com ASCII de proposito (PowerShell 5.1 le .ps1 sem BOM como ANSI).

$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Hactool = Join-Path $Repo 'toolchain\hactool-1.4.0-win\hactool.exe'
$Work = Join-Path $Repo 'build\v130'
$Tmp = Join-Path $Work 'tmp'
$HacHome = Join-Path $Tmp 'hactool-home'
$Out = Join-Path $Work 'romfs.bin'
$Log = Join-Path $Work 'merge.log'

function Fail($msg) { Write-Host "ERRO: $msg" -ForegroundColor Red; exit 1 }

if (-not (Test-Path -LiteralPath $Hactool)) { Fail "hactool.exe nao encontrado em $Hactool" }
if (-not (Test-Path -LiteralPath (Join-Path $HacHome '.switch\title.keys'))) {
    Fail "rode antes: python tools/extract.py hactool-home" }
if (Test-Path -LiteralPath $Out) { Fail "$Out ja existe; apague-o para refazer" }

$GameDir = Join-Path $Repo 'Game Files'
$BaseNsp = Get-ChildItem -LiteralPath $GameDir -Recurse -File -Filter '*.nsp' |
    Where-Object { $_.Name -match '01002B00111A2000' -and $_.Name -match 'Base' } | Select-Object -First 1
$UpdNsp = Get-ChildItem -LiteralPath $GameDir -Recurse -File -Filter '*.nsp' |
    Where-Object { $_.Name -match '01002B00111A2800' } | Select-Object -First 1
if (-not $BaseNsp) { Fail 'NSP da base (01002B00111A2000) nao encontrado em Game Files' }
if (-not $UpdNsp) { Fail 'NSP do update (01002B00111A2800) nao encontrado em Game Files' }

# Hardlinks com nomes ASCII: o hactool 1.4.0 do Windows nao abre caminhos com caracteres Unicode (ex.: o sinal de
# dois-pontos dos nomes dos NSP). Hardlink no mesmo disco nao copia nada.
$In = Join-Path $Tmp 'in'
New-Item -ItemType Directory -Force -Path $In | Out-Null
foreach ($pair in @(@($BaseNsp, 'base.nsp'), @($UpdNsp, 'update.nsp'))) {
    $link = Join-Path $In $pair[1]
    if (-not (Test-Path -LiteralPath $link)) {
        # mklink em vez de New-Item: o -Target do New-Item trata [ ] dos nomes como curinga.
        cmd /c mklink /H "$link" "$($pair[0].FullName)" | Out-Null
        if (-not (Test-Path -LiteralPath $link)) {
            Write-Host "Hardlink falhou; copiando $($pair[1]) (pode demorar) ..."
            Copy-Item -LiteralPath $pair[0].FullName -Destination $link
        }
    }
}

# Extrai os NCAs dos dois NSP (a base tem ~11 GB).
foreach ($name in @('base', 'update')) {
    $dir = Join-Path $Tmp $name
    if (-not (Test-Path -LiteralPath $dir)) {
        Write-Host "Extraindo $name.nsp ..."
        & $Hactool -t pfs0 --outdir="$dir" (Join-Path $In "$name.nsp") | Out-Null
        if ($LASTEXITCODE -ne 0) { Fail "hactool falhou ao abrir $name.nsp" }
    }
}
$BaseNca = Get-ChildItem -LiteralPath (Join-Path $Tmp 'base') -Filter '*.nca' | Sort-Object Length -Descending | Select-Object -First 1
$UpdNca = Get-ChildItem -LiteralPath (Join-Path $Tmp 'update') -Filter '*.nca' | Sort-Object Length -Descending | Select-Object -First 1
Write-Host "NCA de programa da base:   $($BaseNca.Name)"
Write-Host "NCA de programa do update: $($UpdNca.Name)"

# Mescla: a secao 1 do NCA do update e um patch BKTR sobre a base. Para secao BKTR o hactool ignora --romfs; so
# --section1 grava a imagem (o nivel RomFS final, sem os niveis de hash). -y verifica os seis niveis IVFC.
$env:HOME = $HacHome
Write-Host 'Mesclando o RomFS (base + 1.3.0) ...'
& $Hactool -x -y --disablekeywarns --suppresskeys -k (Join-Path $HacHome '.switch\prod.keys') `
    --basenca="$($BaseNca.FullName)" --section1="$Out" $UpdNca.FullName *> $Log
$code = $LASTEXITCODE
$text = Get-Content -LiteralPath $Log -Raw
# Sem as chaves publicas da Nintendo, o hactool sempre marca as assinaturas como FAIL: nao e erro de dados.
$checked = ($text -split "`r?`n" | Where-Object { $_ -notmatch '(Fixed-Key Signature|NPDM Signature) \(FAIL\)' }) -join "`n"
$levels = (0..5 | Where-Object { $text -match "Level $_ \(GOOD\)" }).Count
if ($code -ne 0 -or $checked -match '\(FAIL\)|\(INVALID\)|Failed to|Error:' -or $levels -ne 6) {
    Fail "a mesclagem nao verificou (codigo $code, niveis IVFC bons: $levels/6). Veja $Log"
}
# Os NCAs temporarios so sao apagados se a imagem existir de fato.
if (-not (Test-Path -LiteralPath $Out) -or (Get-Item -LiteralPath $Out).Length -lt 1GB) {
    Fail "o hactool verificou mas nao gravou $Out. NCAs mantidos em $Tmp para nova tentativa. Veja $Log"
}

# Limpa os NCAs temporarios e as chaves copiadas.
Remove-Item -Recurse -Force -LiteralPath (Join-Path $Tmp 'base'), (Join-Path $Tmp 'update'), $In, $HacHome
$size = (Get-Item -LiteralPath $Out).Length
Write-Host ("OK: {0} ({1:N2} GiB), seis niveis IVFC verificados." -f $Out, ($size / 1GB)) -ForegroundColor Green
