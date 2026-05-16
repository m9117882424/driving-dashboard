from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from dashboard_core import enrich_missing_geo_for_period, import_events_to_db, init_db, parse_excel_bytes
from wialon_client import (
    DEFAULT_BASE_URL,
    WialonClient,
    date_bounds_to_unix,
    env_value,
    parse_id_list,
    read_env_file,
)

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
DB_PATH = BASE_DIR / "data" / "driving_dashboard.sqlite"
REPORTS_DIR = BASE_DIR / "data" / "wialon_reports"

for k, v in read_env_file(ENV_PATH).items():
    os.environ.setdefault(k, v)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> int:
    parser = argparse.ArgumentParser(description="Получить XLSX-отчёт Wialon и импортировать события в SQLite без дублей.")
    parser.add_argument("--from-date", help="Дата начала YYYY-MM-DD. По умолчанию: сегодня - WIALON_SYNC_DAYS.")
    parser.add_argument("--to-date", help="Дата окончания YYYY-MM-DD. По умолчанию: сегодня.")
    parser.add_argument("--days", type=int, default=int(env_value("WIALON_SYNC_DAYS", "7", ENV_PATH) or 7), help="Сколько последних дней брать, если даты не заданы.")
    args = parser.parse_args()

    token = env_value("WIALON_TOKEN", "", ENV_PATH).strip()
    if not token:
        raise SystemExit("Не указан WIALON_TOKEN в .env")

    base_url = env_value("WIALON_API_URL", DEFAULT_BASE_URL, ENV_PATH) or DEFAULT_BASE_URL
    tz_hours = float(env_value("WIALON_TZ_HOURS", "3", ENV_PATH) or 3)
    report_resource_id = int(env_value("WIALON_REPORT_RESOURCE_ID", "0", ENV_PATH) or 0)
    report_template_id = int(env_value("WIALON_REPORT_TEMPLATE_ID", "0", ENV_PATH) or 0)
    report_object_id = int(env_value("WIALON_REPORT_OBJECT_ID", "0", ENV_PATH) or 0)
    object_id_list = parse_id_list(env_value("WIALON_REPORT_OBJECT_ID_LIST", "", ENV_PATH))

    missing = [
        name for name, value in [
            ("WIALON_REPORT_RESOURCE_ID", report_resource_id),
            ("WIALON_REPORT_TEMPLATE_ID", report_template_id),
            ("WIALON_REPORT_OBJECT_ID", report_object_id),
        ] if not value
    ]
    if missing:
        raise SystemExit("Не заполнены параметры в .env: " + ", ".join(missing))

    today = date.today()
    date_to = parse_date(args.to_date) if args.to_date else today
    date_from = parse_date(args.from_date) if args.from_date else date_to - timedelta(days=max(args.days, 1) - 1)
    if date_from > date_to:
        raise SystemExit("from-date не может быть больше to-date")

    init_db(DB_PATH)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    time_from, time_to = date_bounds_to_unix(date_from, date_to, tz_hours)
    output_base_name = f"wialon_driving_{date_from}_{date_to}"

    print(f"[WIALON] Период: {date_from} — {date_to}")
    print(f"[WIALON] Ресурс={report_resource_id}, шаблон={report_template_id}, объект={report_object_id}")

    with WialonClient(token=token, base_url=base_url) as client:
        # __enter__ логинится с дефолтным UTC+3. Ниже явно переустановим, если в .env другое значение.
        client.set_locale(tz_offset_hours=tz_hours, language="ru")
        xlsx_bytes, _meta = client.run_report_to_xlsx(
            report_resource_id=report_resource_id,
            report_template_id=report_template_id,
            report_object_id=report_object_id,
            object_id_list=object_id_list or None,
            time_from=time_from,
            time_to=time_to,
            output_file_name=output_base_name,
            timeout_sec=int(env_value("WIALON_REPORT_TIMEOUT_SEC", "420", ENV_PATH) or 420),
        )

    save_path = REPORTS_DIR / f"{output_base_name}.xlsx"
    save_path.write_bytes(xlsx_bytes)
    print(f"[OK] XLSX сохранён: {save_path}")

    events_df, _vehicles_df, sheet_name = parse_excel_bytes(xlsx_bytes)
    result = import_events_to_db(
        DB_PATH,
        events_df,
        source_file=save_path.name,
        source_sheet=sheet_name,
        file_bytes=xlsx_bytes,
    )

    print(
        "[OK] Импорт завершён: "
        f"в файле={result['parsed_events']}, "
        f"добавлено={result['inserted_events']}, "
        f"дублей={result['duplicate_events']}"
    )

    geo_enabled = str(env_value("WIALON_GEO_ENRICH", "1", ENV_PATH)).strip().lower() not in {"0", "false", "no", "off"}
    if geo_enabled:
        geo_limit = int(env_value("WIALON_GEO_LIMIT", "500", ENV_PATH) or 500)
        geo_window = int(env_value("WIALON_GEO_WINDOW_SEC", "180", ENV_PATH) or 180)
        geo_load_count = int(env_value("WIALON_GEO_LOAD_COUNT", "50", ENV_PATH) or 50)
        print(f"[GEO] Дозаполнение координат: limit={geo_limit}, window={geo_window}s")
        with WialonClient(token=token, base_url=base_url) as client:
            client.set_locale(tz_offset_hours=tz_hours, language="ru")
            geo = enrich_missing_geo_for_period(
                DB_PATH,
                client,
                date_from=f"{date_from} 00:00:00",
                date_to=f"{date_to} 23:59:59",
                tz_offset_hours=tz_hours,
                window_sec=geo_window,
                limit=geo_limit,
                load_count=geo_load_count,
            )
        print(
            "[GEO] Готово: "
            f"проверено={geo['checked']}, "
            f"обновлено={geo['updated']}, "
            f"нет_ТС={geo['no_unit']}, "
            f"нет_сообщений={geo['no_message']}, "
            f"api_ошибок={geo['api_errors']}, "
            f"ТС_загружено={geo['units_loaded']}"
        )
    else:
        print("[GEO] Дозаполнение координат отключено: WIALON_GEO_ENRICH=0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
