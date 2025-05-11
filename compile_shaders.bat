@echo off
echo Compiling shaders...

:: Folder with QSB compiler
set QSB="c:\Qt\6.9\6.9.0\mingw_64\bin\qsb.exe"
set SHADERS_DIR=shaders

:: Check for compiler existence
if not exist %QSB% (
    echo ERROR: QSB compiler not found at %QSB%
    echo Please adjust the path in compile_shaders.bat
    exit /b 1
)

:: Check if shaders directory exists
if not exist %SHADERS_DIR% (
    mkdir %SHADERS_DIR%
    echo Created shaders directory
)

:: Loop over all .frag and .vert files in the shaders folder and compile
for %%f in ("%SHADERS_DIR%\*.frag" "%SHADERS_DIR%\*.vert") do (
    %QSB% --glsl "440" --hlsl 50 --msl 22 -o "%%f.qsb" "%%f"
)

echo Compilation complete!
exit /b 0
