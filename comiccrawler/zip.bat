REM 7z path
set zip="C:\Program Files\7-Zip\7z.exe"

REM	move to mission directory
cd /D %1

REM run 7z command to compress to zip file
%zip% a -tzip "../%~n1.zip" *

REM exit if failed to compress
if ERRORLEVEL 1 goto exit

REM move to parent directory then delete folder
cd ..
rd /S /Q "%~1"

exit:
REM pause