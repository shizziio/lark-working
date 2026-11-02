@echo off
rem Windows launcher: tries the py launcher, then python.
where py >nul 2>nul && (py -3 "%~dp0lark_setup.py" %* & exit /b %errorlevel%)
python "%~dp0lark_setup.py" %*
