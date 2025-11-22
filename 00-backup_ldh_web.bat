@echo off
REM Backup completo del proyecto LDH_Web
REM Este script crea un archivo ZIP con fecha y hora

setlocal enabledelayedexpansion

REM Obtener fecha y hora en formato YYYY-MM-DD_HH-MM-SS
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set FECHA=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2%
set HORA=%datetime:~8,2%-%datetime:~10,2%-%datetime:~12,2%

REM Nombre del archivo de backup
set BACKUP_FILE=backups\backup_LDH_Web_%FECHA%_%HORA%.zip

REM Crear carpeta backups si no existe
if not exist "backups" mkdir backups

echo ================================================================================
echo BACKUP DEL PROYECTO LDH WEB
echo ================================================================================
echo.
echo Fecha: %FECHA%
echo Hora: %HORA%
echo.
echo Creando backup...

REM Usar PowerShell para crear el ZIP (disponible en Windows 10+)
powershell -command "Compress-Archive -Path '*.py','*.md','*.txt','*.bat','models','routes','templates','static','migrations','docs','ldh_database.db' -DestinationPath '%BACKUP_FILE%' -Force"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================================
    echo BACKUP COMPLETADO EXITOSAMENTE
    echo ================================================================================
    echo.
    echo Archivo: %BACKUP_FILE%
    for %%A in ("%BACKUP_FILE%") do (
        set size=%%~zA
        set /a sizeMB=!size! / 1048576
        echo Tamaño: !sizeMB! MB
    )
    echo.
) else (
    echo.
    echo ================================================================================
    echo ERROR AL CREAR EL BACKUP
    echo ================================================================================
    echo.
)

pause

