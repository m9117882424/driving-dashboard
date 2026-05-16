from __future__ import annotations

import hmac
import os
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from dashboard_core import (
    clear_database,
    get_db_stats,
    get_import_history,
    get_sheet_names,
    import_events_to_db,
    init_db,
    newest_xlsx_bytes,
    parse_excel_bytes,
)
from localization import col_label, default_language, language_selector, t
from wialon_client import (
    DEFAULT_BASE_URL,
    WialonAPIError,
    WialonClient,
    date_bounds_to_unix,
    env_value,
    parse_id_list,
    read_env_file,
)

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "driving_dashboard.sqlite"
REPORTS_DIR = BASE_DIR / "data" / "wialon_reports"
ENV_PATH = BASE_DIR / ".env"

for k, v in read_env_file(ENV_PATH).items():
    os.environ.setdefault(k, v)

initial_lang = default_language(ENV_PATH)
st.set_page_config(
    page_title=t("admin_page_title", initial_lang),
    page_icon="🔐",
    layout="wide",
)

lang = language_selector(ENV_PATH)

st.markdown(
    """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
.admin-box {background:#f8fafc; border:1px solid #dbeafe; border-radius:14px; padding:16px 18px;}
.small-muted {font-size:13px; color:#64748b;}
</style>
""",
    unsafe_allow_html=True,
)

init_db(DB_PATH)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@st.cache_data(show_spinner=False)
def cached_sheet_names(file_bytes: bytes):
    return get_sheet_names(file_bytes)


@st.cache_data(show_spinner=False)
def cached_parse(file_bytes: bytes, sheet_name: str | None):
    return parse_excel_bytes(file_bytes, sheet_name)


def get_admin_password() -> str:
    return env_value("ADMIN_PASSWORD", "admin", ENV_PATH).strip() or "admin"


def check_admin_password() -> bool:
    if st.session_state.get("admin_authenticated"):
        return True

    st.title(t("admin_login_title", lang))
    st.caption(t("admin_login_caption", lang))

    configured_password = get_admin_password()
    if configured_password == "admin":
        st.warning(t("default_password_warning", lang))

    password = st.text_input(t("admin_password", lang), type="password")
    col1, _col2 = st.columns([1, 4])
    with col1:
        login = st.button(t("login", lang), type="primary", use_container_width=True)

    if login:
        if hmac.compare_digest(password, configured_password):
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error(t("bad_password", lang))
    return False


def get_wialon_token(token_input: str | None = None) -> str:
    return (token_input or "").strip() or env_value("WIALON_TOKEN", "", ENV_PATH).strip()


def wialon_connect(token: str, base_url: str, tz_hours: float) -> WialonClient:
    client = WialonClient(token=token, base_url=base_url)
    # Язык API Wialon синхронизируем с языком интерфейса.
    client.login(tz_offset_hours=tz_hours, language="tr" if lang == "tr" else "ru")
    return client


if not check_admin_password():
    st.stop()

st.title(t("admin_title", lang))
st.caption(t("admin_caption", lang))

if st.button(t("logout", lang)):
    st.session_state["admin_authenticated"] = False
    st.rerun()

admin_tab1, admin_tab2, admin_tab3 = st.tabs([t("tab_wialon", lang), t("tab_manual", lang), t("tab_db", lang)])

with admin_tab1:
    st.subheader(t("wialon_subheader", lang))
    left, right = st.columns([1, 1])

    with left:
        token_from_env = bool(env_value("WIALON_TOKEN", "", ENV_PATH).strip())
        token_input = st.text_input(
            "Wialon token",
            value="",
            type="password",
            help=t("token_help", lang),
            placeholder=t("token_placeholder_env", lang) if token_from_env else t("token_placeholder", lang),
        )
        base_url = st.text_input(t("api_url", lang), value=env_value("WIALON_API_URL", DEFAULT_BASE_URL, ENV_PATH) or DEFAULT_BASE_URL)
        tz_hours = st.number_input(t("timezone", lang), value=float(env_value("WIALON_TZ_HOURS", "3", ENV_PATH)), step=0.5)

    with right:
        template_mask = st.text_input(
            t("template_mask", lang),
            value=env_value("WIALON_REPORT_TEMPLATE_MASK", "*Качество*", ENV_PATH) or "*Качество*",
        )
        object_mask = st.text_input(
            t("object_mask", lang),
            value=env_value("WIALON_OBJECT_MASK", "*АВТОБУС*", ENV_PATH) or "*АВТОБУС*",
        )
        if st.button(t("find_templates", lang), use_container_width=True):
            token = get_wialon_token(token_input)
            if not token:
                st.error(t("token_missing", lang))
            else:
                try:
                    with wialon_connect(token, base_url, tz_hours) as client:
                        st.session_state["wialon_templates"] = client.search_report_templates(template_mask or "*")
                        st.session_state["wialon_groups"] = client.search_objects("avl_unit_group", object_mask or "*")
                        st.session_state["wialon_units"] = client.search_objects("avl_unit", object_mask or "*")
                    st.success(
                        t(
                            "found_wialon",
                            lang,
                            templates=len(st.session_state.get("wialon_templates", [])),
                            groups=len(st.session_state.get("wialon_groups", [])),
                        )
                    )
                except Exception as exc:
                    st.error(t("wialon_refs_error", lang, error=exc))

    st.divider()

    templates = st.session_state.get("wialon_templates", [])
    groups = st.session_state.get("wialon_groups", [])
    units = st.session_state.get("wialon_units", [])

    manual_resource_id = int(env_value("WIALON_REPORT_RESOURCE_ID", "0", ENV_PATH) or 0)
    manual_template_id = int(env_value("WIALON_REPORT_TEMPLATE_ID", "0", ENV_PATH) or 0)
    manual_object_id = int(env_value("WIALON_REPORT_OBJECT_ID", "0", ENV_PATH) or 0)
    manual_object_list = env_value("WIALON_REPORT_OBJECT_ID_LIST", "", ENV_PATH)

    c1, c2 = st.columns(2)
    with c1:
        if templates:
            template_choice = st.selectbox(t("report_template", lang), templates, format_func=lambda x: x.label)
            report_resource_id = template_choice.resource_id
            report_template_id = template_choice.template_id
            st.caption(f"resourceId={report_resource_id}, templateId={report_template_id}")
        else:
            st.caption(t("templates_empty", lang))
            report_resource_id = st.number_input("reportResourceId", min_value=0, value=manual_resource_id, step=1)
            report_template_id = st.number_input("reportTemplateId", min_value=0, value=manual_template_id, step=1)

    with c2:
        object_options = ["Группа ТС", "Отдельное ТС", "ID вручную"]
        object_labels = {
            "Группа ТС": t("object_group", lang),
            "Отдельное ТС": t("object_unit", lang),
            "ID вручную": t("object_manual", lang),
        }
        object_source = st.radio(t("report_object", lang), object_options, horizontal=True, format_func=lambda x: object_labels[x])
        if object_source == "Группа ТС" and groups:
            object_choice = st.selectbox(t("object_group", lang), groups, format_func=lambda x: x.label)
            report_object_id = object_choice.object_id
            object_id_list_text = ""
        elif object_source == "Отдельное ТС" and units:
            object_choice = st.selectbox(t("object_unit", lang), units, format_func=lambda x: x.label)
            report_object_id = object_choice.object_id
            object_id_list_text = ""
        else:
            report_object_id = st.number_input("reportObjectId", min_value=0, value=manual_object_id, step=1)
            object_id_list_text = st.text_input(t("object_id_list", lang), value=manual_object_list)

    today = date.today()
    default_from = today - timedelta(days=7)
    wialon_period = st.date_input(
        t("wialon_period", lang),
        value=(default_from, today),
        key="wialon_period_admin",
    )
    if isinstance(wialon_period, tuple) and len(wialon_period) == 2:
        wialon_from, wialon_to = wialon_period
    else:
        wialon_from = wialon_to = wialon_period

    import_button = st.button(t("run_wialon_import", lang), type="primary", use_container_width=True)
    if import_button:
        token = get_wialon_token(token_input)
        if not token:
            st.error(t("token_missing", lang))
        elif not int(report_resource_id) or not int(report_template_id) or not int(report_object_id):
            st.error(t("ids_missing", lang))
        else:
            try:
                time_from, time_to = date_bounds_to_unix(wialon_from, wialon_to, tz_hours)
                output_base_name = f"wialon_driving_{wialon_from}_{wialon_to}"
                object_id_list = parse_id_list(object_id_list_text)
                with st.spinner(t("wialon_spinner", lang)):
                    with wialon_connect(token, base_url, tz_hours) as client:
                        downloaded_bytes, _meta = client.run_report_to_xlsx(
                            report_resource_id=int(report_resource_id),
                            report_template_id=int(report_template_id),
                            report_object_id=int(report_object_id),
                            object_id_list=object_id_list or None,
                            time_from=time_from,
                            time_to=time_to,
                            output_file_name=output_base_name,
                            timeout_sec=int(env_value("WIALON_REPORT_TIMEOUT_SEC", "420", ENV_PATH) or 420),
                        )
                    save_path = REPORTS_DIR / f"{output_base_name}.xlsx"
                    save_path.write_bytes(downloaded_bytes)
                    events, _vehicles, sheet = parse_excel_bytes(downloaded_bytes)
                    result = import_events_to_db(
                        DB_PATH,
                        events,
                        source_file=save_path.name,
                        source_sheet=sheet,
                        file_bytes=downloaded_bytes,
                    )
                st.success(
                    t(
                        "wialon_imported",
                        lang,
                        inserted=result["inserted_events"],
                        duplicates=result["duplicate_events"],
                        parsed=result["parsed_events"],
                    )
                )
                st.rerun()
            except WialonAPIError as exc:
                st.error(t("wialon_error", lang, error=exc))
            except Exception as exc:
                st.error(t("wialon_import_error", lang, error=exc))

with admin_tab2:
    st.subheader(t("manual_subheader", lang))
    uploaded = st.file_uploader(t("upload_excel", lang), type=["xlsx"])
    use_local = st.checkbox(t("use_latest_file", lang), value=False)

    file_bytes = None
    file_name = None
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        file_name = uploaded.name
    elif use_local:
        local = newest_xlsx_bytes(BASE_DIR)
        if local:
            file_bytes, file_name = local

    if file_bytes:
        sheet_names = cached_sheet_names(file_bytes)
        preferred_index = sheet_names.index("Качество вождения") if "Качество вождения" in sheet_names else 0
        selected_sheet_input = st.selectbox(t("data_sheet", lang), sheet_names, index=preferred_index)
        with st.spinner(t("wialon_spinner", lang)):
            parsed_events, _parsed_vehicles, selected_sheet = cached_parse(file_bytes, selected_sheet_input)
        st.success(t("file_parsed", lang, events=len(parsed_events), sheet=selected_sheet))

        if st.button(t("import_file", lang), type="primary", use_container_width=True):
            result = import_events_to_db(
                DB_PATH,
                parsed_events,
                source_file=file_name or "uploaded.xlsx",
                source_sheet=selected_sheet or selected_sheet_input,
                file_bytes=file_bytes,
            )
            st.success(
                t(
                    "manual_imported",
                    lang,
                    inserted=result["inserted_events"],
                    duplicates=result["duplicate_events"],
                    parsed=result["parsed_events"],
                )
            )
            st.rerun()
    else:
        st.info(t("manual_hint", lang))

with admin_tab3:
    st.subheader(t("db_subheader", lang))
    db_stats = get_db_stats(DB_PATH)
    c1, c2, c3 = st.columns(3)
    c1.metric(t("db_events", lang), db_stats["events_count"])
    c2.metric(t("db_vehicles", lang), db_stats["vehicles_count"])
    period_text = "—"
    if db_stats["min_dt"] and db_stats["max_dt"]:
        period_text = f"{db_stats['min_dt'][:10]} — {db_stats['max_dt'][:10]}"
    c3.metric(t("db_period", lang), period_text)
    st.caption(f"{t('db_file', lang)}: `{DB_PATH}`")

    st.markdown(f"### {t('import_history', lang)}")
    history = get_import_history(DB_PATH)
    if history.empty:
        st.caption(t("no_imports", lang))
    else:
        hist = history.rename(
            columns={
                "imported_at": col_label("import", lang),
                "source_file": col_label("source_file", lang),
                "source_sheet": col_label("source_sheet", lang),
                "parsed_events": col_label("parsed_events", lang),
                "inserted_events": col_label("inserted_events", lang),
                "duplicate_events": col_label("duplicate_events", lang),
                "min_dt": col_label("min_dt", lang),
                "max_dt": col_label("max_dt", lang),
            }
        )
        st.dataframe(hist, use_container_width=True, hide_index=True, height=360)

    st.markdown(f"### {t('danger_zone', lang)}")
    st.warning(t("clear_warning", lang))
    confirm_clear = st.checkbox(t("confirm_clear", lang))
    if st.button(t("clear_db", lang), disabled=not confirm_clear, use_container_width=True):
        clear_database(DB_PATH)
        st.success(t("db_cleared", lang))
        st.rerun()
