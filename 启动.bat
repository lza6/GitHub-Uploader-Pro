@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title GitHub Uploader Pro: 智能启动器

:: ==========================================
:: GitHub Uploader Pro - Smart Launcher
:: 功能:
::   - 自动检测/下载 Python (嵌入式支持)
::   - 自动创建虚拟环境 (venv)
::   - 实时依赖库检查与安装
::   - 极速启动模式 (Marker File)
:: ==========================================

cd /d "%~dp0"

:: 配置
set "APP_NAME=GitHub Uploader Pro"
set "PYTHON_VERSION=3.11.9"
set "PYTHON_DIR=%~dp0python_env"
set "VENV_DIR=%~dp0venv"
set "MARKER_FILE=%~dp0.env_ready"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

:: 显示标题
echo.
echo ==========================================
echo    %APP_NAME% - 智能启动器 v2.0
echo ==========================================
echo.

:: 极速检查 - 如果标记文件存在，跳过完整检查
if "%~1"=="--force-check" (
    echo [*] 强制模式: 重新验证环境...
    del "%MARKER_FILE%" 2>nul
)

if exist "%MARKER_FILE%" (
    echo [*] 极速模式: 环境已就绪，正在启动...
    goto :run_app
)

echo [*] 初次运行或环境配置变更，正在检查...
echo.

:: ==========================================
:: 步骤 1: 检查 Python 环境
:: ==========================================
echo [1/4] 正在检查 Python 环境...

set "PYTHON_EXE="
set "USE_EMBEDDED=0"

:: 优先级 1: 检查是否存在本地 python_env
if exist "%PYTHON_DIR%\python.exe" (
    set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
    set "USE_EMBEDDED=1"
    echo      [+] 发现嵌入式 Python 环境
    goto :python_found
)

:: 优先级 2: 检查系统 Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "SYSTEM_PY_VER=%%v"
    echo      [+] 发现系统 Python: !SYSTEM_PY_VER!
    
    :: 检查版本 >= 3.9
    for /f "tokens=1,2 delims=." %%a in ("!SYSTEM_PY_VER!") do (
        set /a "MAJOR=%%a"
        set /a "MINOR=%%b"
        if !MAJOR! geq 3 (
            if !MINOR! geq 9 (
                set "PYTHON_EXE=python"
                echo      [+] 版本符合要求 (需 3.9+)
                goto :python_found
            )
        )
    )
    echo      [-] 系统版本过低，将下载嵌入式版本...
)

:: 没有找到合适的 Python，下载嵌入式版本
echo      [-] 未找到合适的 Python，即将下载 Python %PYTHON_VERSION%...
goto :download_python

:python_found
echo      [OK] Python 环境满足要求
echo.
goto :check_venv

:: ==========================================
:: 步骤 2: 下载嵌入式 Python
:: ==========================================
:download_python
echo.
echo [*] 正在下载 Python %PYTHON_VERSION% 嵌入版...
echo     地址: %PYTHON_URL%
echo.

if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

set "PYTHON_ZIP=%PYTHON_DIR%\python.zip"
echo     [↓] 正在下载 (请耐心等待)...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%' -UseBasicParsing}"

if not exist "%PYTHON_ZIP%" (
    echo.
    echo [错误] 下载失败！请检查网络或手动安装 Python 3.10+
    pause
    exit /b 1
)

echo     [📦] 正在解压环境...
powershell -Command "& {Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force}"
del "%PYTHON_ZIP%" 2>nul

:: 修正 .pth 文件以启用 pip 和 site-packages
for /f "delims=" %%f in ('dir /b "%PYTHON_DIR%\python*._pth"') do set "PTH_FILE=%PYTHON_DIR%\%%f"
if defined PTH_FILE (
    echo     [🔧] 正在配置 Python 路径...
    (
        echo python311.zip
        echo .
        echo Lib\site-packages
        echo import site
    ) > "!PTH_FILE!"
)

:: 安装 pip
echo     [🚀] 正在安装包管理器 (pip)...
set "GET_PIP=%PYTHON_DIR%\get-pip.py"
powershell -Command "& {Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%GET_PIP%' -UseBasicParsing}"
"%PYTHON_DIR%\python.exe" "%GET_PIP%" --no-warn-script-location
del "%GET_PIP%" 2>nul

set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "USE_EMBEDDED=1"
echo      [OK] 嵌入式 Python 部署完成
echo.

:: ==========================================
:: 步骤 3: 检查/创建虚拟环境
:: ==========================================
:check_venv
echo [2/4] 正在配置运行环境...

if "%USE_EMBEDDED%"=="1" (
    echo      [+] 独占模式: 直接使用内置环境
    set "PIP_CMD=%PYTHON_EXE% -m pip"
    goto :check_deps
)

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo      [OK] 虚拟环境 venv 已就绪
    set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
    goto :check_deps
)

echo      [+] 正在创建虚拟环境 (首次运行可能较慢)...
python -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo [错误] 虚拟环境创建失败
    pause
    exit /b 1
)

set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
echo      [OK] 虚拟环境创建成功
echo.

:: ==========================================
:: 步骤 4: 检查并安装依赖库
:: ==========================================
:check_deps
echo [3/4] 正在核对依赖库...

:: 检查 requirements.txt
if not exist "requirements.txt" (
    echo [警告] 未找到 requirements.txt，尝试直接启动...
    goto :create_marker
)

:: 尝试运行导入测试，加快启动速度
!PYTHON_EXE! -c "import PyQt6, github, git, keyring, httpx, loguru, qasync" 2>nul
if %errorlevel% equ 0 (
    echo      [OK] 依赖库校验通过
    goto :create_marker
)

echo      [-] 发现依赖缺失，正在拉取最新依赖 (实时日志)...
echo      ------------------------------------------
"!PYTHON_EXE!" -m pip install -r requirements.txt --no-warn-script-location
if %errorlevel% neq 0 (
    echo.
    echo [错误] 依赖安装过程中出现异常
    echo 请检查网络连接或尝试: pip install -r requirements.txt
    pause
    exit /b 1
)
echo      ------------------------------------------
echo      [OK] 依赖库更新完成
echo.

:: ==========================================
:: 步骤 5: 最终就绪
:: ==========================================
:create_marker
echo [4/4] 正在收尾...
echo 环境就绪于 %date% %time% > "%MARKER_FILE%"
echo 执行路径: %PYTHON_EXE% >> "%MARKER_FILE%"
echo.

:: ==========================================
:: 启动应用
:: ==========================================
:run_app
:: 此时需要确保 PYTHON_EXE 变量在极速模式下也正确
if not defined PYTHON_EXE (
    if exist "%PYTHON_DIR%\python.exe" (
        set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
    ) else if exist "%VENV_DIR%\Scripts\python.exe" (
        set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
    ) else (
        set "PYTHON_EXE=python"
    )
)

echo [*] 正在唤起 GitHub Uploader Pro v4.0...
echo.

:: 直接运行（非后台），以便捕获所有错误
"!PYTHON_EXE!" main.py

set APP_EXIT_CODE=%errorlevel%
if %APP_EXIT_CODE% neq 0 (
    echo.
    echo ==========================================
    echo [错误] 程序异常退出 (Exit Code: %APP_EXIT_CODE%)
    echo ==========================================
    echo.
    echo 可能的原因:
    echo   1. Python 依赖库缺失或版本不兼容
    echo   2. main.py 代码存在语法或运行时错误
    echo   3. 配置文件损坏
    echo.
    echo 解决方案: 尝试运行 "启动.bat --force-check" 重新检查环境
    echo.
    del "%MARKER_FILE%" 2>nul
    pause
    exit /b %APP_EXIT_CODE%
)
exit /b 0
