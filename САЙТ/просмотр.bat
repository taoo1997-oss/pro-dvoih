@echo off
rem Локальный просмотр витрины. Адреса на сайте абсолютные (/styles.css),
rem поэтому просто открыть файл нельзя — нужен маленький локальный сервер.
cd /d "%~dp0dist"
start "" http://localhost:5500
python -m http.server 5500
