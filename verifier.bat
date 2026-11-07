@echo off
cd /d "%~dp0"
rem Vercintorix : la verification complete (environ trois quarts d heure). Le compte rendu va dans verifier.log.
rem Il faut Python et cargo (Rust) ; numpy, Node.js et gcc sont facultatifs (les etapes qui en ont besoin sont sautees).
set PYTHONIOENCODING=utf-8
chcp 65001 >nul
echo construction de la machine Rust ...
cd vtx-rs
cargo build --release > "%~dp0verifier.log" 2>&1
cd ..
echo verification en cours, compte rendu dans verifier.log ...
python verifier.py %* >> "%~dp0verifier.log" 2>&1
powershell -NoProfile -Command "Get-Content -Tail 4 -Encoding UTF8 verifier.log"
pause
