@echo off
md temp

cp -a execjs 				temp 
cp -a cc_*.py 				temp 
cp -a comiccrawler.py 		temp 
cp -a comiccrawlergui.py 	temp 
cp -a safeprint.py			temp 
cp -a readme.txt 			temp 
cp -a zip.bat 				temp 
cp -a winlaunch.pyw			temp 

cd temp
ddate +%%Y%%m%%d-%%H%%M > _tv_
set /P d= < _tv_
del _tv_
7z a -tzip "../build/comiccrawler_v%d%.zip" *
cd ..
rd /S /Q temp
echo.
echo.
pause