@echo off
REM Carrega o ambiente do MSVC e do CUDA. No Windows o nvcc usa o cl.exe como
REM compilador hospedeiro, então vcvars64 precisa vir antes.
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set "CUDA_PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.4"
set "PATH=%CUDA_PATH%\bin;%PATH%"
