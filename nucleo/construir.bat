@echo off
REM Compila o executavel do nucleo, gih-nucleo.exe (H53a, ADR-012).
REM
REM Rodar sempre por aqui, nunca chamando cl solto: o caminho do projeto tem
REM acento e o cmd quebra quando se encadeia comando com && numa linha so.
REM /utf-8 porque os fontes tem comentarios e mensagens em portugues: sem ele o
REM cl le os fontes na pagina de codigo do Windows e as mensagens saem trocadas.
REM
REM Em Linux (e na CI): g++ -O2 -std=c++17 -Wall -Wextra cpp/*.cpp -o bin/gih-nucleo

setlocal
cd /d "%~dp0"
call "%~dp0spike\ambiente.bat"
if not exist bin mkdir bin

cl /nologo /O2 /EHsc /std:c++17 /W4 /utf-8 cpp\*.cpp /Fe:bin\gih-nucleo.exe /Fo:bin\
if errorlevel 1 (
    echo FALHOU a compilacao do nucleo.
    exit /b 1
)
bin\gih-nucleo.exe versao
endlocal
