@echo off
tasklist /FI "IMAGENAME eq python2.exe" /NH | find /I /N "python2.exe" >NUL 
if "%ERRORLEVEL%"=="1" (cd smiths_micrologix_data
C:/python27/python2 connector.py)