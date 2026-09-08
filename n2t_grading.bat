@echo off
setlocal EnableDelayedExpansion

set "VERBOSE=0"
set "PROJECT_DIR="

:parse_args
if "%~1"=="" goto args_done

if /i "%~1"=="-v" (
    set "VERBOSE=1"
    shift
    goto parse_args
)
if /i "%~1"=="--verbose" (
    set "VERBOSE=1"
    shift
    goto parse_args
)
if /i "%~1"=="-h" (
    call :usage
    exit /b 0
)
if /i "%~1"=="--help" (
    call :usage
    exit /b 0
)

set "ARG=%~1"
if "%ARG:~0,1%"=="-" (
    echo Unknown option: %ARG%
    call :usage
    exit /b 1
)

if defined PROJECT_DIR (
    echo Error: Multiple project folders provided
    call :usage
    exit /b 1
)
set "PROJECT_DIR=%~1"
shift
goto parse_args

:args_done

if not defined PROJECT_DIR (
    set "PROJECT_DIR=%CD%"
    echo No project directory provided. Using current directory
)

rem Strip a trailing slash, if any
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
if "%PROJECT_DIR:~-1%"=="/" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

rem Extract the project folder's name
for %%A in ("%PROJECT_DIR%") do set "PROJECT_NAME=%%~nxA"

rem Must be all digits
echo %PROJECT_NAME%| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo Error: Unrecognized project format
    exit /b 1
)

rem Strip leading zeros, then zero-pad back to 2 digits
set "NUM=%PROJECT_NAME%"
:strip_zero
if "%NUM:~0,1%"=="0" if not "%NUM%"=="0" (
    set "NUM=%NUM:~1%"
    goto strip_zero
)
if "%NUM%"=="" set "NUM=0"

set "PROJ_NUM=%NUM%"
if "%NUM:~1,1%"=="" set "PROJ_NUM=0%NUM%"

rem Select the emulator/simulator for this project
set "RUNNER="
if "%PROJ_NUM%"=="01" set "RUNNER=HardwareSimulator"
if "%PROJ_NUM%"=="02" set "RUNNER=HardwareSimulator"
if "%PROJ_NUM%"=="03" set "RUNNER=HardwareSimulator"
if "%PROJ_NUM%"=="05" set "RUNNER=HardwareSimulator"
if "%PROJ_NUM%"=="07" set "RUNNER=VMEmulator"
if "%PROJ_NUM%"=="08" set "RUNNER=VMEmulator"
if "%PROJ_NUM%"=="04" set "RUNNER=CPUEmulator"
if "%PROJ_NUM%"=="12" set "RUNNER=CPUEmulator"

if "%PROJ_NUM%"=="06" (
    echo Project %PROJ_NUM% requires testing compiler/assembler outputs directly
    exit /b 0
)
if "%PROJ_NUM%"=="10" (
    echo Project %PROJ_NUM% requires testing compiler/assembler outputs directly
    exit /b 0
)
if "%PROJ_NUM%"=="11" (
    echo Project %PROJ_NUM% requires testing compiler/assembler outputs directly
    exit /b 0
)
if "%PROJ_NUM%"=="09" (
    echo Project %PROJ_NUM% has no tests
    exit /b 0
)

if not defined RUNNER (
    echo Error: Project %PROJ_NUM% test runner not found
    exit /b 1
)

set "RUNNER=%RUNNER%.bat"

if "%VERBOSE%"=="1" echo Using %RUNNER% test runner

cd /d "%PROJECT_DIR%" || exit /b 1

echo ================================
echo  Testing Nand2Tetris Project %PROJ_NUM%
echo ================================

set /a TOTAL=0
set /a PASSED=0
set /a FAILED=0
set /a SKIPPED=0

for /r %%F in (*.tst) do (
    set "FULL=%%~fF"
    set "REL=!FULL:%CD%\=!"

    set "SKIP="
    if /i "!REL!"=="fill\Fill.tst" set "SKIP=1"
    if /i "!REL!"=="Memory.tst" set "SKIP=1"

    if defined SKIP (
        echo [SKIP] !REL!
        set /a SKIPPED+=1
    ) else (
        set /a TOTAL+=1

        set "TMPFILE=%TEMP%\test_project_!RANDOM!.txt"
       
		call %RUNNER% !FULL! >"!TMPFILE!" 2>&1

        findstr "success" "!TMPFILE!" >nul
        if errorlevel 1 (
            echo [FAIL] !REL!
            findstr /i "failure" "!TMPFILE!"
            set /a FAILED+=1
        ) else (
            echo [PASS] !REL!
            set /a PASSED+=1
        )

        del "!TMPFILE!" >nul 2>&1
    )
)

echo ================================
echo           %PASSED% / %TOTAL% passed
if %SKIPPED% gtr 0 echo            %SKIPPED% skipped
echo ================================

if %FAILED% equ 0 (
    exit /b 0
) else (
    exit /b 1
)

:usage
echo Usage: %~nx0 [options] [\path\to\project\folder]
echo If no project folder is specified, the current folder is used
echo Options:
echo   -v, --verbose       Enable verbose mode
echo   -h, --help          Display this help message
goto :eof

