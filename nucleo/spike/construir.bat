@echo off
REM Compila e roda os dois testes de toolchain do nucleo (historia H47).
REM
REM Rodar sempre por aqui, nunca chamando cl/nvcc solto: o caminho do projeto
REM tem acento e o cmd quebra quando se encadeia comando com && numa linha so.
REM
REM Uso:  construir.bat            compila e roda os dois
REM       construir.bat openmp     so o teste de CPU
REM       construir.bat cuda       so o teste de GPU

setlocal
cd /d "%~dp0"

call "%~dp0ambiente.bat"

set "ALVO=%~1"
if "%ALVO%"=="" set "ALVO=tudo"

echo === Versoes do toolchain ===
REM O cl responde no idioma do sistema, entao filtrar por "Version" nao
REM funciona em maquina em portugues. A primeira linha ja tem a versao.
cl 2>&1 | findstr /C:"C/C++"
nvcc --version | findstr /C:"release"
echo.

if not exist bin mkdir bin

if "%ALVO%"=="cuda" goto cuda

REM ------------------------------------------------------------------ OpenMP
echo === Compilando teste_openmp.cpp ===
cl /nologo /O2 /openmp /EHsc /std:c++17 teste_openmp.cpp /Fe:bin\teste_openmp.exe /Fo:bin\
if errorlevel 1 (
    echo FALHOU a compilacao do teste de OpenMP.
    exit /b 1
)
echo.
echo === Rodando teste de OpenMP ===
bin\teste_openmp.exe
if errorlevel 1 (
    echo FALHOU a execucao do teste de OpenMP.
    exit /b 1
)
echo.

if "%ALVO%"=="openmp" goto fim

REM -------------------------------------------------------------------- CUDA
:cuda
echo === Compilando teste_cuda.cu ===
REM -arch=native gera para a GPU desta maquina; evita chutar a capacidade.
nvcc -O2 -arch=native -o bin\teste_cuda.exe teste_cuda.cu
if errorlevel 1 (
    echo FALHOU a compilacao do teste de CUDA.
    exit /b 1
)
echo.
echo === Rodando teste de CUDA ===
bin\teste_cuda.exe
if errorlevel 1 (
    echo FALHOU a execucao do teste de CUDA.
    exit /b 1
)

:fim
echo.
echo === Toolchain validado ===
endlocal
