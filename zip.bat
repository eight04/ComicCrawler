REM	move to mission directory
cd /D %1

REM run 7z command to compress to zip file
7z a -tzip "../%~n1.zip" *
REM start /low /wait /b 

REM exit if failed to compress
if ERRORLEVEL 1 goto exit

REM move to parent directory then delete folder
cd ..
rd /S /Q "%~1"
REM echo %~1

exit:
REM pause