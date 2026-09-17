@echo off
REM AbletonMCP MCP Server Launcher
REM Starts the Python MCP server that Claude uses to control Ableton

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ========================================
echo  AbletonMCP MCP Server (APC40 Mk2)
echo ========================================
echo.
echo Bridge target: localhost:9877 (Ableton Remote Script)
echo Full log file: %~dp0mcp_server.log
echo.
echo Requirements:
echo   1. Ableton Live is running
echo   2. AbletonMCP is selected as Control Surface
echo   3. APC40 Mk2 is connected and configured
echo.

REM Activate venv and run server (live log streams to this window via stderr)
call .venv\Scripts\activate.bat
python mcp_server.py
set EXITCODE=%ERRORLEVEL%

echo.
echo ========================================
echo  Server exited with code %EXITCODE%
echo ========================================
echo.
echo ---- Last 60 log lines (full log: mcp_server.log) ----
powershell -NoProfile -Command "Get-Content -Tail 60 'mcp_server.log'" 2>nul
echo -------------------------------------------------------
echo.
echo Press any key to open the FULL log in Notepad, or close this window.
pause >nul
start notepad "%~dp0mcp_server.log"
