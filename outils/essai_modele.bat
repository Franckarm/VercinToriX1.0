@echo off
rem Vercintorix @V@ : @TITRE@
rem Les trois a chaque essai : le C++ (le processeur), vtx au processeur, Taranis (la carte) ; puis le Druide.
rem Le journal : essai-@V@.log (le meme texte qu'a l'ecran).
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
set ICI=%~dp0
set LOG=%~dp0essai-@V@.log
set TMPS=%~dp0essai-@V@.tmp
echo Vercintorix @V@ > "%LOG%"
echo Vercintorix @V@
if exist essai-@V@ rmdir /s /q essai-@V@
powershell -NoProfile -Command "Expand-Archive -Force 'vtx-@V@.zip' 'essai-@V@'"
if errorlevel 1 goto :sanszip
cd /d "%~dp0essai-@V@\vtx-0.6"
set NEMC=%USERPROFILE%\.vercintorix\nemeton\gergovie_etages

call :titre "1. la machine (lugus, vtx64) et Ogmios"
pushd vtx-rs
cargo build --release --bin lugus --bin vtx64 --bin ogmios > "%TMPS%" 2>&1
findstr /i /c:"error" /c:"Finished" "%TMPS%" > "%TMPS%.2"
type "%TMPS%.2"
type "%TMPS%.2" >> "%LOG%"
set EXE=%CD%\target\release\ogmios.exe
if not exist "%EXE%" goto :sansogmios
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell; foreach($d in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))){ $s=$w.CreateShortcut((Join-Path $d 'Ogmios.lnk')); $s.TargetPath=$env:EXE; $s.WorkingDirectory=(Split-Path $env:EXE); $s.Description='Ogmios, Vercintorix'; $s.Save() }"
echo Ogmios : %EXE% (raccourci "Ogmios" sur le Bureau et dans le menu Demarrer)
echo Ogmios : %EXE% >> "%LOG%"
goto :suite1
:sansogmios
echo ogmios.exe n'est pas construit (voir les erreurs ci-dessus)
echo ogmios.exe n'est pas construit >> "%LOG%"
:suite1
popd

call :titre "2. le temoin C++ (le processeur)"
call :cpp

call :titre "3. vtx au processeur (lugus forger : la forge en vtx, sans Python)"
vtx-rs\target\release\lugus.exe forger belenos\gergovie.vtx -o gergovie.exe > "%TMPS%" 2>&1
type "%TMPS%"
type "%TMPS%" >> "%LOG%"
call :jouer gergovie.exe

call :titre "4. Taranis (la carte), le noyau unique"
set VTX_EPISSAGE=rapide
vtx-rs\target\release\lugus.exe forger belenos\gergovie_carte.vtx -o gergovie_carte.exe > "%TMPS%" 2>&1
vtx-rs\target\release\lugus.exe forger belenos\gergovie_etages.vtx -o gergovie_etages.exe > "%TMPS%.3" 2>&1
set VTX_EPISSAGE=
type "%TMPS%"
type "%TMPS%" >> "%LOG%"
call :jouer gergovie_carte.exe

call :titre "5. Taranis, les etages : le Vergobret mesure ses lots, puis apprend"
type "%TMPS%.3"
type "%TMPS%.3" >> "%LOG%"
set VTX_REGLAGE=1
call :jouer gergovie_etages.exe
set VTX_REGLAGE=
echo %NEMC%> "%TMPS%.in"
vtx-rs\target\release\lugus.exe vergobret\vergobret.vtx < "%TMPS%.in" > "%TMPS%" 2>&1
type "%TMPS%"
type "%TMPS%" >> "%LOG%"

call :titre "6. le Druide sur Gergovie (il lit aussi ce qu'elle importe)"
call :jouer "vtx-rs\target\release\lugus.exe druide belenos\gergovie.vtx"
@EXTRA@
call :titre "fini : envoyer essai-@V@.log"
del "%TMPS%" "%TMPS%.2" "%TMPS%.3" "%TMPS%.in" >nul 2>&1
pause
exit /b 0

:sanszip
echo le zip vtx-@V@.zip manque a cote de ce fichier >> "%LOG%"
echo le zip vtx-@V@.zip manque a cote de ce fichier
pause
exit /b 1

rem ---- le temoin C++ : un compilateur dans la console, sinon Visual Studio (vswhere), sinon un gergovie_ref.exe deja la
:cpp
set REF=
where g++ >nul 2>&1
if not errorlevel 1 goto :gpp
where clang++ >nul 2>&1
if not errorlevel 1 goto :clang
where cl >nul 2>&1
if not errorlevel 1 goto :msvc
set VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe
if not exist "%VSWHERE%" goto :cppdeja
set VSDIR=
for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set VSDIR=%%i
if "%VSDIR%"=="" goto :cppdeja
if not exist "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" goto :cppdeja
echo Visual Studio : %VSDIR%
echo Visual Studio : %VSDIR% >> "%LOG%"
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
goto :msvc
:gpp
g++ -O2 -fopenmp -o gergovie_ref.exe belenos\gergovie_ref.cpp > "%TMPS%" 2>&1
goto :cppjouer
:clang
clang++ -O2 -fopenmp -o gergovie_ref.exe belenos\gergovie_ref.cpp > "%TMPS%" 2>&1
goto :cppjouer
:msvc
cl /nologo /O2 /openmp /EHsc /TP belenos\gergovie_ref.cpp /Fegergovie_ref.exe > "%TMPS%" 2>&1
goto :cppjouer
:cppdeja
if exist "%ICI%gergovie_ref.exe" copy /y "%ICI%gergovie_ref.exe" gergovie_ref.exe >nul
if exist gergovie_ref.exe echo pas de compilateur trouve : le gergovie_ref.exe deja construit, a cote de ce fichier
if exist gergovie_ref.exe echo pas de compilateur trouve : le gergovie_ref.exe deja construit >> "%LOG%"
:cppjouer
type "%TMPS%" >> "%LOG%" 2>nul
if exist gergovie_ref.exe goto :cppok
echo le temoin C++ n'a pas pu etre construit : ni g++, ni clang++, ni Visual Studio, ni gergovie_ref.exe a cote de ce fichier
echo le temoin C++ n'a pas pu etre construit >> "%LOG%"
exit /b 0
:cppok
call :jouer gergovie_ref.exe
exit /b 0

:titre
echo.>> "%LOG%"
echo ==== %~1 >> "%LOG%"
echo.
echo ==== %~1
exit /b 0

:jouer
echo -- %~1 >> "%LOG%"
echo -- %~1
%~1 > "%TMPS%" 2>&1
type "%TMPS%"
type "%TMPS%" >> "%LOG%"
exit /b 0
