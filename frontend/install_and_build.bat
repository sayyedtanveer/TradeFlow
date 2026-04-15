@echo off
cd /d "c:\Users\sayye\source\repos\MedTrack\frontend"
echo Installing recharts...
call npm install recharts --save
echo.
echo Checking build status...
call npm run build
