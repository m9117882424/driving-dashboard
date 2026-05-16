DEPLOY: Driving Safety Dashboard / Güvenli Sürüş Dashboard
=========================================================

Рекомендуемый вариант: отдельный поддомен, например:
  safety.equippulse.com
  drive.equippulse.com

Так мы не трогаем текущий сайт/дашборд на основном домене.

1. Загрузить архив на сервер
----------------------------
С локального компьютера:

scp driving_dashboard_server_v7.zip root@SERVER_IP:/root/

На сервере:

apt update && apt install -y unzip
cd /root
rm -rf driving_dashboard_server_v7
unzip driving_dashboard_server_v7.zip -d driving_dashboard_server_v7
cd driving_dashboard_server_v7

2. Установить приложение
------------------------
Для домена/поддомена:

sudo DOMAIN=safety.equippulse.com bash deploy/install_server.sh

Для проверки просто по IP:

sudo DOMAIN=_ bash deploy/install_server.sh

Установка создаст:
  /opt/driving-dashboard
  /opt/driving-dashboard/data/driving_dashboard.sqlite
  systemd service: driving-dashboard
  systemd timer: driving-dashboard-sync.timer
  nginx config: /etc/nginx/sites-available/driving-dashboard

3. Настроить .env
-----------------

nano /opt/driving-dashboard/.env

Минимально заполнить:

APP_LANGUAGE=ru
ADMIN_PASSWORD=сложный_пароль
WIALON_TOKEN=твой_токен
WIALON_REPORT_RESOURCE_ID=...
WIALON_REPORT_TEMPLATE_ID=...
WIALON_REPORT_OBJECT_ID=...
WIALON_TZ_HOURS=3
WIALON_SYNC_DAYS=7

После изменения:

systemctl restart driving-dashboard

4. Проверить работу
-------------------

systemctl status driving-dashboard --no-pager
journalctl -u driving-dashboard -f

Открыть:

http://safety.equippulse.com

Админка будет отдельной страницей Streamlit:
  /Admin

5. HTTPS
--------
Если DNS уже смотрит на сервер:

apt install -y certbot python3-certbot-nginx
certbot --nginx -d safety.equippulse.com

6. Автосинхронизация Wialon
---------------------------
Таймер установлен по умолчанию каждый день в 06:10 серверного времени.

Проверить таймер:

systemctl status driving-dashboard-sync.timer --no-pager
systemctl list-timers | grep driving-dashboard

Запустить синхронизацию вручную:

systemctl start driving-dashboard-sync
journalctl -u driving-dashboard-sync -n 100 --no-pager

Изменить расписание:

nano /etc/systemd/system/driving-dashboard-sync.timer
systemctl daemon-reload
systemctl restart driving-dashboard-sync.timer

Примеры OnCalendar:
  каждый день 06:10:      OnCalendar=*-*-* 06:10:00
  каждые 3 часа:          OnCalendar=*-*-* 00/3:10:00
  каждый час:             OnCalendar=hourly

7. Обновление версии
--------------------
Загрузить новый архив, распаковать и выполнить:

cd /root/driving_dashboard_server_v7
sudo bash deploy/update_server.sh

Скрипт сохранит текущую базу и .env, сделает backup SQLite перед обновлением.

8. Важные команды
-----------------

Перезапуск приложения:
  systemctl restart driving-dashboard

Логи приложения:
  journalctl -u driving-dashboard -f

Логи синхронизации:
  journalctl -u driving-dashboard-sync -f

Проверка nginx:
  nginx -t
  systemctl reload nginx

База данных:
  /opt/driving-dashboard/data/driving_dashboard.sqlite
