@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo == Поиск клиентов: свадебные лендинги ==
echo Проверяю зависимости (первый запуск может занять минуту)...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo.
  echo Не удалось установить зависимости. Проверьте, что установлен Python 3.10+.
  pause
  exit /b 1
)
echo Запускаю. Откроется браузер: http://127.0.0.1:5017
echo Чтобы остановить — закройте это окно или нажмите Ctrl+C.
echo.
python app.py
pause
