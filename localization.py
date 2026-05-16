from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

LANG_LABELS = {
    "ru": "Русский",
    "tr": "Türkçe",
}

LANG_BY_LABEL = {v: k for k, v in LANG_LABELS.items()}

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "language_label": "Язык / Dil",
        "page_title": "Дашборд качества вождения",
        "dashboard_title": "Дашборд качества вождения автобусов",
        "dashboard_caption": "Рабочая страница: только просмотр, фильтры, аналитика и экспорт. Импорт Wialon и управление базой вынесены в защищённую админку.",
        "db_empty": "База пока пустая. Открой страницу «Admin» в меню слева, выполни импорт из Wialon или загрузи Excel-файл.",
        "filters": "Фильтры",
        "report_period": "Период отчётности",
        "severity_filter": "Класс нарушения",
        "action_filter": "Тип действия",
        "violation_filter": "Конкретные нарушения",
        "vehicle_filter": "ТС",
        "location_search": "Поиск по локации",
        "previous_empty": "предыдущий период пустой",
        "previous_delta": "{sign}{pct:.1%} к предыдущему периоду",
        "source_line": "Источник: <b>SQLite база</b> · событий после фильтра: <b>{events}</b> · период базы: <b>{min_date} — {max_date}</b>",
        "kpi_vehicles": "ТС с нарушениями",
        "kpi_total": "Всего нарушений",
        "kpi_dangerous": "Опасных",
        "kpi_sharp": "Резких",
        "kpi_avg": "Среднее количество нарушений наТС",
        "kpi_leader": "Лидер",
        "pcs": "шт.",
        "empty_filter": "По текущим фильтрам событий нет. Ослабь фильтр периода, ТС или типа нарушения.",
        "key_charts": "Ключевые графики",
        "top10_count_title": "Топ-10 нарушителей по количеству",
        "violations_structure_title": "Структура нарушений",
        "violations_axis": "Нарушений",
        "vehicle_axis": "ТС",
        "violation_axis": "Нарушение",
        "count_axis": "Кол-во",
        "dynamic_title": "Динамика изменений количества нарушений",
        "dynamic_violation_type": "Тип нарушения для динамики",
        "dynamic_group": "Группировка",
        "dynamic_empty": "Нет данных для построения динамики по выбранному типу.",
        "dynamic_chart_title": "Динамика: {violation} / {group}",
        "period_axis": "Период",
        "priority_title": "Приоритет на разбор",
        "top10_risk_title": "Топ-10 по риск-баллу",
        "risk_axis": "Риск-балл",
        "severity_pie_title": "Опасные / резкие / прочие",
        "tables": "Таблицы",
        "tab_top_vehicles": "Топ нарушителей",
        "tab_top_violations": "Топ нарушений",
        "tab_locations": "Горячие локации",
        "tab_events": "Реестр событий",
        "download_excel": "Скачать отфильтрованный отчёт в Excel",
        "all": "Все",
        "day": "День",
        "hour": "Час",
        "week": "Неделя",
        "admin_page_title": "Админка · Дашборд качества вождения",
        "admin_login_title": "🔐 Админка",
        "admin_login_caption": "Импорт Wialon, ручная загрузка Excel, история импортов и обслуживание базы.",
        "default_password_warning": "Используется пароль по умолчанию `admin`. Для рабочей эксплуатации задай ADMIN_PASSWORD в файле .env.",
        "admin_password": "Пароль администратора",
        "login": "Войти",
        "bad_password": "Неверный пароль.",
        "admin_title": "🔐 Админка дашборда качества вождения",
        "admin_caption": "Сюда вынесены все операции, которые меняют данные: Wialon API, импорт Excel, история импортов и очистка базы.",
        "logout": "Выйти из админки",
        "tab_wialon": "Wialon автоотчёт",
        "tab_manual": "Ручной импорт Excel",
        "tab_db": "База данных",
        "wialon_subheader": "Получить отчёт из Wialon и импортировать в базу",
        "token_help": "Можно не вводить здесь, если токен указан в .env как WIALON_TOKEN.",
        "token_placeholder_env": "используется .env",
        "token_placeholder": "вставь токен Wialon",
        "api_url": "API URL",
        "timezone": "Часовой пояс отчёта, UTC+",
        "template_mask": "Маска имени шаблона отчёта",
        "object_mask": "Маска группы/объекта",
        "find_templates": "Найти шаблоны и группы",
        "token_missing": "Не указан Wialon token. Добавь его в .env или вставь в поле выше.",
        "found_wialon": "Найдено шаблонов: {templates}, групп: {groups}.",
        "wialon_refs_error": "Не удалось получить справочники Wialon: {error}",
        "report_template": "Шаблон отчёта",
        "templates_empty": "Шаблоны не загружены — можно указать ID вручную.",
        "report_object": "Объект отчёта",
        "object_group": "Группа ТС",
        "object_unit": "Отдельное ТС",
        "object_manual": "ID вручную",
        "object_id_list": "reportObjectIdList, если нужен список",
        "wialon_period": "Период для отчёта Wialon",
        "run_wialon_import": "Получить из Wialon и импортировать в базу",
        "ids_missing": "Не хватает ID: reportResourceId / reportTemplateId / reportObjectId.",
        "wialon_spinner": "Wialon выполняет отчёт, скачиваю XLSX и импортирую в базу...",
        "wialon_imported": "Отчёт получен и импортирован: добавлено {inserted}, дублей пропущено {duplicates} из {parsed}.",
        "wialon_error": "Ошибка Wialon: {error}",
        "wialon_import_error": "Не удалось получить или импортировать отчёт: {error}",
        "manual_subheader": "Ручная загрузка Excel Wialon",
        "upload_excel": "Загрузить Excel Wialon",
        "use_latest_file": "Взять самый свежий .xlsx из папки приложения",
        "data_sheet": "Лист с данными",
        "file_parsed": "Файл распознан: {events} событий · лист: {sheet}",
        "import_file": "Импортировать файл в базу",
        "manual_imported": "Импорт завершён: добавлено {inserted}, дублей пропущено {duplicates} из {parsed}.",
        "manual_hint": "Загрузи Excel или включи режим выбора самого свежего файла из папки приложения.",
        "db_subheader": "Состояние базы данных",
        "db_events": "Событий в базе",
        "db_vehicles": "ТС в базе",
        "db_period": "Период в базе",
        "db_file": "Файл БД",
        "import_history": "История импортов",
        "no_imports": "Импортов пока нет.",
        "danger_zone": "Опасная зона",
        "clear_warning": "Очистка удалит все события и историю импортов из локальной SQLite-базы.",
        "confirm_clear": "Подтверждаю очистку базы",
        "clear_db": "Очистить базу",
        "db_cleared": "База очищена.",
    },
    "tr": {
        "language_label": "Dil / Язык",
        "page_title": "Sürüş Kalitesi Panosu",
        "dashboard_title": "Otobüs Sürüş Kalitesi Panosu",
        "dashboard_caption": "Çalışma sayfası: yalnızca görüntüleme, filtreler, analiz ve dışa aktarma. Wialon içe aktarma ve veritabanı yönetimi şifreli yönetici sayfasına taşındı.",
        "db_empty": "Veritabanı boş. Sol menüden «Admin» sayfasını açıp Wialon’dan veri içe aktar veya Excel dosyası yükle.",
        "filters": "Filtreler",
        "report_period": "Rapor dönemi",
        "severity_filter": "İhlal sınıfı",
        "action_filter": "Hareket tipi",
        "violation_filter": "İhlal türü",
        "vehicle_filter": "Araç",
        "location_search": "Konuma göre ara",
        "previous_empty": "önceki dönem boş",
        "previous_delta": "önceki döneme göre {sign}{pct:.1%}",
        "source_line": "Kaynak: <b>SQLite veritabanı</b> · filtre sonrası olay: <b>{events}</b> · veri dönemi: <b>{min_date} — {max_date}</b>",
        "kpi_vehicles": "İhlalli araç",
        "kpi_total": "Toplam ihlal",
        "kpi_dangerous": "Tehlikeli",
        "kpi_sharp": "Sert",
        "kpi_avg": "Araç başına ortalama ihlal",
        "kpi_leader": "Lider",
        "pcs": "adet",
        "empty_filter": "Seçili filtrelerde olay yok. Dönem, araç veya ihlal türü filtresini genişlet.",
        "key_charts": "Ana grafikler",
        "top10_count_title": "İhlal sayısına göre top-10 araç",
        "violations_structure_title": "İhlal dağılımı",
        "violations_axis": "İhlal",
        "vehicle_axis": "Araç",
        "violation_axis": "İhlal türü",
        "count_axis": "Adet",
        "dynamic_title": "İhlal sayısı değişim dinamiği",
        "dynamic_violation_type": "Dinamik için ihlal türü",
        "dynamic_group": "Gruplama",
        "dynamic_empty": "Seçili ihlal türü için dinamik grafiği oluşturulacak veri yok.",
        "dynamic_chart_title": "Dinamik: {violation} / {group}",
        "period_axis": "Dönem",
        "priority_title": "Öncelikli inceleme",
        "top10_risk_title": "Risk puanına göre top-10",
        "risk_axis": "Risk puanı",
        "severity_pie_title": "Tehlikeli / sert / diğer",
        "tables": "Tablolar",
        "tab_top_vehicles": "Top ihlalciler",
        "tab_top_violations": "Top ihlaller",
        "tab_locations": "Sıcak lokasyonlar",
        "tab_events": "Olay kaydı",
        "download_excel": "Filtrelenmiş raporu Excel olarak indir",
        "all": "Tümü",
        "day": "Gün",
        "hour": "Saat",
        "week": "Hafta",
        "admin_page_title": "Yönetim · Sürüş Kalitesi Panosu",
        "admin_login_title": "🔐 Yönetim",
        "admin_login_caption": "Wialon içe aktarma, manuel Excel yükleme, içe aktarma geçmişi ve veritabanı bakımı.",
        "default_password_warning": "Varsayılan `admin` parolası kullanılıyor. Canlı kullanım için .env dosyasında ADMIN_PASSWORD değerini değiştir.",
        "admin_password": "Yönetici parolası",
        "login": "Giriş",
        "bad_password": "Parola hatalı.",
        "admin_title": "🔐 Sürüş kalitesi panosu yönetimi",
        "admin_caption": "Veriyi değiştiren tüm işlemler burada: Wialon API, Excel içe aktarma, içe aktarma geçmişi ve veritabanı temizliği.",
        "logout": "Yönetimden çık",
        "tab_wialon": "Wialon otomatik rapor",
        "tab_manual": "Manuel Excel içe aktarma",
        "tab_db": "Veritabanı",
        "wialon_subheader": "Wialon’dan rapor al ve veritabanına aktar",
        "token_help": "Token .env içinde WIALON_TOKEN olarak tanımlandıysa buraya girmek gerekmez.",
        "token_placeholder_env": ".env kullanılıyor",
        "token_placeholder": "Wialon token gir",
        "api_url": "API URL",
        "timezone": "Rapor saat dilimi, UTC+",
        "template_mask": "Rapor şablonu adı maskesi",
        "object_mask": "Grup/obje maskesi",
        "find_templates": "Şablonları ve grupları bul",
        "token_missing": "Wialon token belirtilmedi. .env dosyasına ekle veya yukarıdaki alana gir.",
        "found_wialon": "Bulunan şablon: {templates}, grup: {groups}.",
        "wialon_refs_error": "Wialon referansları alınamadı: {error}",
        "report_template": "Rapor şablonu",
        "templates_empty": "Şablonlar yüklenmedi — ID manuel girilebilir.",
        "report_object": "Rapor objesi",
        "object_group": "Araç grubu",
        "object_unit": "Tek araç",
        "object_manual": "Manuel ID",
        "object_id_list": "Gerekirse reportObjectIdList",
        "wialon_period": "Wialon rapor dönemi",
        "run_wialon_import": "Wialon’dan al ve veritabanına aktar",
        "ids_missing": "Eksik ID: reportResourceId / reportTemplateId / reportObjectId.",
        "wialon_spinner": "Wialon raporu çalıştırıyor, XLSX indiriliyor ve veritabanına aktarılıyor...",
        "wialon_imported": "Rapor alındı ve aktarıldı: eklenen {inserted}, atlanan kopya {duplicates}, toplam {parsed}.",
        "wialon_error": "Wialon hatası: {error}",
        "wialon_import_error": "Rapor alınamadı veya içe aktarılamadı: {error}",
        "manual_subheader": "Wialon Excel manuel yükleme",
        "upload_excel": "Wialon Excel yükle",
        "use_latest_file": "Uygulama klasöründeki en yeni .xlsx dosyasını kullan",
        "data_sheet": "Veri sayfası",
        "file_parsed": "Dosya okundu: {events} olay · sayfa: {sheet}",
        "import_file": "Dosyayı veritabanına aktar",
        "manual_imported": "İçe aktarma tamamlandı: eklenen {inserted}, atlanan kopya {duplicates}, toplam {parsed}.",
        "manual_hint": "Excel yükle veya uygulama klasöründeki en yeni dosyayı seçme modunu aç.",
        "db_subheader": "Veritabanı durumu",
        "db_events": "Veritabanındaki olay",
        "db_vehicles": "Veritabanındaki araç",
        "db_period": "Veri dönemi",
        "db_file": "DB dosyası",
        "import_history": "İçe aktarma geçmişi",
        "no_imports": "Henüz içe aktarma yok.",
        "danger_zone": "Tehlikeli alan",
        "clear_warning": "Temizleme, yerel SQLite veritabanındaki tüm olayları ve içe aktarma geçmişini siler.",
        "confirm_clear": "Veritabanı temizliğini onaylıyorum",
        "clear_db": "Veritabanını temizle",
        "db_cleared": "Veritabanı temizlendi.",
    },
}

SEVERITY_LABELS = {
    "ru": {"Критическое": "Критическое", "Опасное": "Опасное", "Среднее": "Среднее", "Резкое": "Резкое", "Прочее": "Прочее"},
    "tr": {"Критическое": "Kritik", "Опасное": "Tehlikeli", "Среднее": "Orta", "Резкое": "Sert", "Прочее": "Diğer"},
}

PRIORITY_LABELS = {
    "ru": {"Красная зона": "Красная зона", "Жёлтая зона": "Жёлтая зона", "Норма": "Норма"},
    "tr": {"Красная зона": "Kırmızı bölge", "Жёлтая зона": "Sarı bölge", "Норма": "Normal"},
}

ACTION_LABELS = {
    "ru": {"Поворот": "Поворот", "Торможение": "Торможение", "Ускорение": "Ускорение", "Превышение скорости": "Превышение скорости"},
    "tr": {"Поворот": "Dönüş", "Торможение": "Frenleme", "Ускорение": "Hızlanma", "Превышение скорости": "Hız aşımı"},
}

GROUP_LABELS = {
    "ru": {"День": "День", "Час": "Час", "Неделя": "Неделя"},
    "tr": {"День": "Gün", "Час": "Saat", "Неделя": "Hafta"},
}

COLUMN_LABELS = {
    "ru": {
        "vehicle": "ТС",
        "plate": "Госномер",
        "route": "Маршрут / привязка",
        "violation": "Нарушение",
        "action": "Тип",
        "severity": "Класс",
        "risk": "Риск-балл",
        "dt": "Дата/время",
        "hour": "Час",
        "start_pos": "Нач. положение",
        "end_pos": "Кон. положение",
        "value": "Значение",
        "value_num": "Значение число",
        "source_file": "Источник",
        "imported_at": "Дата импорта",
        "violations": "Нарушений",
        "dangerous": "Опасных",
        "sharp": "Резких",
        "risk_score": "Риск-балл",
        "priority": "Зона",
        "count": "Кол-во",
        "share": "Доля",
        "location": "Локация",
        "import": "Импорт",
        "source_sheet": "Лист",
        "parsed_events": "Событий в файле",
        "inserted_events": "Добавлено",
        "duplicate_events": "Дублей",
        "min_dt": "С даты",
        "max_dt": "По дату",
    },
    "tr": {
        "vehicle": "Araç",
        "plate": "Plaka",
        "route": "Rota / bağlama",
        "violation": "İhlal",
        "action": "Tip",
        "severity": "Sınıf",
        "risk": "Risk puanı",
        "dt": "Tarih/saat",
        "hour": "Saat",
        "start_pos": "Başlangıç konumu",
        "end_pos": "Bitiş konumu",
        "value": "Değer",
        "value_num": "Sayısal değer",
        "source_file": "Kaynak",
        "imported_at": "İçe aktarma tarihi",
        "violations": "İhlal",
        "dangerous": "Tehlikeli",
        "sharp": "Sert",
        "risk_score": "Risk puanı",
        "priority": "Bölge",
        "count": "Adet",
        "share": "Pay",
        "location": "Lokasyon",
        "import": "İçe aktarma",
        "source_sheet": "Sayfa",
        "parsed_events": "Dosyadaki olay",
        "inserted_events": "Eklenen",
        "duplicate_events": "Kopya",
        "min_dt": "Başlangıç",
        "max_dt": "Bitiş",
    },
}


def _read_env_value(env_path: str | Path | None, key: str, default: str = "") -> str:
    if not env_path:
        return os.environ.get(key, default)
    path = Path(env_path)
    if not path.exists():
        return os.environ.get(key, default)
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return os.environ.get(key, default)


def normalize_lang(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"tr", "turkish", "türkçe", "turkce"}:
        return "tr"
    return "ru"


def default_language(env_path: str | Path | None = None) -> str:
    return normalize_lang(os.environ.get("APP_LANGUAGE") or _read_env_value(env_path, "APP_LANGUAGE", "ru"))


def language_selector(env_path: str | Path | None = None, *, key: str = "ui_language", in_sidebar: bool = True) -> str:
    if key not in st.session_state:
        st.session_state[key] = default_language(env_path)
    current = normalize_lang(st.session_state[key])
    labels = [LANG_LABELS["ru"], LANG_LABELS["tr"]]
    index = 1 if current == "tr" else 0
    target = st.sidebar if in_sidebar else st
    selected = target.selectbox(_TRANSLATIONS[current]["language_label"], labels, index=index, key=f"{key}_select")
    lang = LANG_BY_LABEL.get(selected, "ru")
    st.session_state[key] = lang
    return lang


def t(key: str, lang: str = "ru", **kwargs: Any) -> str:
    lang = normalize_lang(lang)
    value = _TRANSLATIONS.get(lang, _TRANSLATIONS["ru"]).get(key, _TRANSLATIONS["ru"].get(key, key))
    return value.format(**kwargs) if kwargs else value


def label_severity(value: Any, lang: str = "ru") -> str:
    text = str(value or "")
    return SEVERITY_LABELS.get(normalize_lang(lang), SEVERITY_LABELS["ru"]).get(text, text)


def label_priority(value: Any, lang: str = "ru") -> str:
    text = str(value or "")
    return PRIORITY_LABELS.get(normalize_lang(lang), PRIORITY_LABELS["ru"]).get(text, text)


def label_action(value: Any, lang: str = "ru") -> str:
    text = str(value or "")
    return ACTION_LABELS.get(normalize_lang(lang), ACTION_LABELS["ru"]).get(text, text)


def label_group(value: Any, lang: str = "ru") -> str:
    text = str(value or "")
    return GROUP_LABELS.get(normalize_lang(lang), GROUP_LABELS["ru"]).get(text, text)


def label_violation(value: Any, lang: str = "ru") -> str:
    text = str(value or "")
    if normalize_lang(lang) != "tr":
        return text
    replacements = [
        ("Поворот", "Dönüş"),
        ("Торможение", "Frenleme"),
        ("Ускорение", "Hızlanma"),
        ("Превышение скорости", "Hız aşımı"),
        ("опасный", "tehlikeli"),
        ("опасное", "tehlikeli"),
        ("опасная", "tehlikeli"),
        ("резкий", "sert"),
        ("резкое", "sert"),
        ("резкая", "sert"),
        ("среднее", "orta"),
        ("критическое", "kritik"),
    ]
    result = text
    for src, dst in replacements:
        result = result.replace(src, dst)
    return result


def label_any(value: Any, lang: str = "ru") -> str:
    text = str(value or "")
    if text in SEVERITY_LABELS["ru"]:
        return label_severity(text, lang)
    if text in PRIORITY_LABELS["ru"]:
        return label_priority(text, lang)
    if text in ACTION_LABELS["ru"]:
        return label_action(text, lang)
    return label_violation(text, lang)


def col_label(key: str, lang: str = "ru") -> str:
    return COLUMN_LABELS.get(normalize_lang(lang), COLUMN_LABELS["ru"]).get(key, key)


def localize_event_values(df, lang: str = "ru"):
    out = df.copy()
    if normalize_lang(lang) == "ru" or out.empty:
        return out
    if "violation" in out.columns:
        out["violation"] = out["violation"].map(lambda x: label_violation(x, lang))
    if "action" in out.columns:
        out["action"] = out["action"].map(lambda x: label_action(x, lang))
    if "severity" in out.columns:
        out["severity"] = out["severity"].map(lambda x: label_severity(x, lang))
    if "priority" in out.columns:
        out["priority"] = out["priority"].map(lambda x: label_priority(x, lang))
    return out
