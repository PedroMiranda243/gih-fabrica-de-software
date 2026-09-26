@echo off
REM Compila o executavel do nucleo, gih-nucleo.exe (H53a, H53b, H54a, ADR-012).
REM
REM Rodar sempre por aqui, nunca chamando cl ou nvcc solto: o caminho do projeto
REM tem acento e o cmd quebra quando se encadeia comando com && numa linha so.
REM /utf-8 porque os fontes tem comentarios e mensagens em portugues: sem ele o
REM cl le os fontes na pagina de codigo do Windows e as mensagens saem trocadas.
REM
REM /openmp liga o modo openmp (H53b); o OpenMP do MSVC e o 2.0, e o codigo
REM foi escrito dentro dele.
REM
REM Com o CUDA Toolkit instalado, o nvcc compila tudo - os .cpp pelo cl, e o
REM gpu.cu - e o executavel sai com a GPU (H54a). Sem ele, so o cl: o
REM executavel diz que foi compilado sem CUDA e roda igual, em CPU (RNF06).
REM -arch=native gera codigo para a placa desta maquina. /wd4211 cala um aviso do
REM codigo que o proprio nvcc gera para o gpu.cu (o stub), e nao do nosso.
REM
REM O nvcc nao expande cpp\*.cpp como o cl: a lista de fontes e montada aqui.
REM
REM Uso: construir.bat          com CUDA, se houver
REM      construir.bat cpu      so a CPU, mesmo com o CUDA instalado
REM
REM Em Linux (e na CI): g++ -O2 -fopenmp -std=c++17 -Wall -Wextra cpp/*.cpp -o bin/gih-nucleo
REM Com CUDA em Linux: ver nucleo/Dockerfile.

setlocal
cd /d "%~dp0"
call "%~dp0spike\ambiente.bat"
if not exist bin mkdir bin

if /i "%~1"=="cpu" goto cpu
where nvcc >nul 2>nul
if errorlevel 1 goto cpu

set "FONTES="
for %%f in (cpp\*.cpp) do call set "FONTES=%%FONTES%% %%f"
nvcc -O2 -std=c++17 -arch=native -DGIH_COM_CUDA -Xcompiler=/openmp,/EHsc,/W4,/wd4211,/utf-8 %FONTES% cpp\gpu.cu -o bin\gih-nucleo.exe
if errorlevel 1 goto falhou
goto pronto

:cpu
cl /nologo /O2 /openmp /EHsc /std:c++17 /W4 /utf-8 cpp\*.cpp /Fe:bin\gih-nucleo.exe /Fo:bin\
if errorlevel 1 goto falhou

:pronto
bin\gih-nucleo.exe versao
endlocal
exit /b 0

:falhou
echo FALHOU a compilacao do nucleo.
endlocal
exit /b 1
