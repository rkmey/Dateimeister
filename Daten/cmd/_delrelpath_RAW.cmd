@REM  generated by dateimeister 20240108-15:23:01
@set OUTDIR=E:\Arbeit\python\Dateimeister\Daten\NAS\photo\RAW

@exit /b  
 
:DeleteIfEmpty 
@call :CheckFolder "%~f1" 
@set RESULT=%ERRORLEVEL% 
@if %RESULT% equ 999 @echo Folder doesn't exist 
@if %RESULT% equ 1   @echo Not empty!
@if %RESULT% equ 0   rd %1 
@exit /b  
 
:CheckFolder 
@if not exist "%~f1" @exit /b 999 
@for %%I in ("%~f1\*.*") do @exit /b 1 
@exit /b 0 

