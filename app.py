from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from dashboard_core import (
    compute_metrics,
    filter_events,
    init_db,
    load_events_from_db,
    prepare_dynamic,
    to_excel_bytes,
)
from localization import (
    col_label,
    label_action,
    label_any,
    label_group,
    label_priority,
    label_severity,
    label_violation,
    default_language,
    language_selector,
    localize_event_values,
    t,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "driving_dashboard.sqlite"
ENV_PATH = BASE_DIR / ".env"

# APP_LANGUAGE в .env задаёт язык по умолчанию. Пользователь может переключить язык в сайдбаре.
initial_lang = default_language(ENV_PATH)

st.set_page_config(
    page_title=t("page_title", initial_lang),
    page_icon="🚌",
    layout="wide",
)

lang = language_selector(ENV_PATH)

st.markdown(
    """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
.kpi-card {background:#f8fafc; border:1px solid #dbeafe; border-radius:14px; padding:16px 18px; min-height:104px;}
.kpi-label {font-size:13px; color:#475569; font-weight:700; margin-bottom:8px;}
.kpi-value {font-size:28px; color:#0f172a; font-weight:800; line-height:1.05;}
.kpi-sub {font-size:13px; color:#64748b; margin-top:6px;}
.section-title {font-size:18px; font-weight:800; color:#0f172a; margin:14px 0 8px 0;}
.small-muted {font-size:13px; color:#64748b;}
[data-testid="stMetric"] {background:#f8fafc; border:1px solid #dbeafe; border-radius:14px; padding:14px 16px;}
</style>
""",
    unsafe_allow_html=True,
)

init_db(DB_PATH)


def kpi(label: str, value, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{html.escape(str(label))}</div>
            <div class="kpi-value">{html.escape(str(value))}</div>
            <div class="kpi-sub">{html.escape(str(sub))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def _has_valid_coords(row) -> bool:
    try:
        return pd.notna(row.get("start_lat")) and pd.notna(row.get("start_lon"))
    except Exception:
        return False


def _event_short_label(row) -> str:
    dt = row.get("dt")
    dt_text = pd.to_datetime(dt).strftime("%d.%m.%Y %H:%M:%S") if pd.notna(dt) else "—"
    return f"{dt_text} · {row.get('plate', '—')} · {row.get('violation', '—')} · {row.get('start_pos', '—')}"


def _render_event_geo(row, lang: str) -> None:
    title = "Карта события" if lang == "ru" else "Olay haritası"
    st.subheader(title)

    dt = row.get("dt")
    dt_text = pd.to_datetime(dt).strftime("%d.%m.%Y %H:%M:%S") if pd.notna(dt) else "—"
    info_rows = [
        ("ТС" if lang == "ru" else "Araç", row.get("plate", "—")),
        ("Нарушение" if lang == "ru" else "İhlal", label_violation(row.get("violation", ""), lang)),
        ("Класс" if lang == "ru" else "Sınıf", label_severity(row.get("severity", ""), lang)),
        ("Дата/время" if lang == "ru" else "Tarih/saat", dt_text),
        ("Нач. положение" if lang == "ru" else "Başlangıç konumu", row.get("start_pos", "—")),
        ("Значение" if lang == "ru" else "Değer", row.get("value", "—")),
    ]
    for key, value in info_rows:
        st.markdown(f"**{html.escape(str(key))}:** {html.escape(str(value))}")

    lat = row.get("start_lat")
    lon = row.get("start_lon")
    map_url = row.get("start_map_url") or row.get("end_map_url")

    if pd.notna(lat) and pd.notna(lon):
        lat_f = float(lat)
        lon_f = float(lon)
        embed_url = f"https://maps.google.com/maps?q={lat_f},{lon_f}&z=16&t=h&output=embed"
        components.html(
            f"""
            <iframe
                width="100%"
                height="420"
                frameborder="0"
                style="border:0; border-radius: 14px;"
                src="{embed_url}"
                allowfullscreen
                loading="lazy"
                referrerpolicy="no-referrer-when-downgrade">
            </iframe>
            """,
            height=430,
        )
        if map_url:
            st.link_button("Открыть в Google Maps" if lang == "ru" else "Google Maps’te aç", str(map_url))
    else:
        st.warning("У события нет координат. Нужно переимпортировать Wialon-отчёт с гиперссылками в локациях." if lang == "ru" else "Bu olayda koordinat yok. Konum bağlantıları olan Wialon raporunu yeniden içe aktarın.")


def _open_event_geo(row, lang: str) -> None:
    if hasattr(st, "dialog"):
        @st.dialog("Гео события" if lang == "ru" else "Olay konumu", width="large")
        def _dialog():
            _render_event_geo(row, lang)
        _dialog()
    else:
        with st.expander("Гео события" if lang == "ru" else "Olay konumu", expanded=True):
            _render_event_geo(row, lang)


st.title(t("dashboard_title", lang))
st.caption(t("dashboard_caption", lang))

events_df = load_events_from_db(DB_PATH)
if events_df.empty:
    st.info(t("db_empty", lang))
    st.stop()

min_dt = events_df["dt"].min()
max_dt = events_df["dt"].max()
min_date = min_dt.date() if pd.notna(min_dt) else pd.Timestamp.today().date()
max_date = max_dt.date() if pd.notna(max_dt) else pd.Timestamp.today().date()

all_severities = [x for x in ["Критическое", "Опасное", "Среднее", "Резкое", "Прочее"] if x in set(events_df["severity"].dropna())]
all_actions = sorted(events_df["action"].dropna().unique().tolist())
all_violations = sorted(events_df["violation"].dropna().unique().tolist())
all_vehicles = sorted(events_df["plate"].dropna().unique().tolist())

with st.sidebar:
    st.header(t("filters", lang))
    period = st.date_input(
        t("report_period", lang),
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(period, (tuple, list)):
        if len(period) >= 2:
            date_start, date_end = period[0], period[1]
        elif len(period) == 1:
            date_start = date_end = period[0]
        else:
            date_start, date_end = min_date, max_date
    else:
        date_start = date_end = period

    if date_start is None:
        date_start = min_date
    if date_end is None:
        date_end = date_start
    if date_start > date_end:
        date_start, date_end = date_end, date_start

    severities = st.multiselect(
        t("severity_filter", lang),
        all_severities,
        default=all_severities,
        format_func=lambda x: label_severity(x, lang),
    )
    actions = st.multiselect(
        t("action_filter", lang),
        all_actions,
        default=[],
        format_func=lambda x: label_action(x, lang),
    )
    violations = st.multiselect(
        t("violation_filter", lang),
        all_violations,
        default=[],
        format_func=lambda x: label_violation(x, lang),
    )
    vehicles = st.multiselect(t("vehicle_filter", lang), all_vehicles, default=[])
    location_text = st.text_input(t("location_search", lang))

filtered = filter_events(
    events_df,
    date_start=date_start,
    date_end=date_end,
    severities=severities,
    violations=violations,
    vehicles=vehicles,
    actions=actions,
    location_text=location_text,
)
metrics = compute_metrics(filtered)

period_len = (pd.Timestamp(date_end) - pd.Timestamp(date_start)).days + 1
prev_start = pd.Timestamp(date_start) - pd.Timedelta(days=period_len)
prev_end = pd.Timestamp(date_start) - pd.Timedelta(days=1)
prev = filter_events(
    events_df,
    date_start=prev_start.date(),
    date_end=prev_end.date(),
    severities=severities,
    violations=violations,
    vehicles=vehicles,
    actions=actions,
    location_text=location_text,
)
prev_total = len(prev)
delta_total = metrics["total_events"] - prev_total
if prev_total > 0:
    pct = delta_total / prev_total
    sign = "+" if pct >= 0 else ""
    delta_text = t("previous_delta", lang, sign=sign, pct=pct)
else:
    delta_text = t("previous_empty", lang)

st.markdown(
    f"<div class='small-muted'>{t('source_line', lang, events=metrics['total_events'], min_date=min_date, max_date=max_date)}</div>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    kpi(t("kpi_vehicles", lang), metrics["total_vehicles"])
with c2:
    kpi(t("kpi_total", lang), metrics["total_events"], delta_text)
with c3:
    kpi(t("kpi_dangerous", lang), metrics["dangerous"], f"{metrics['danger_share']:.1%}" if metrics["total_events"] else "0%")
with c4:
    kpi(t("kpi_sharp", lang), metrics["sharp"], f"{metrics['sharp'] / metrics['total_events']:.1%}" if metrics["total_events"] else "0%")
with c5:
    kpi(t("kpi_avg", lang), metrics["avg_per_vehicle"])
with c6:
    kpi(t("kpi_leader", lang), metrics["top_vehicle"], f"{metrics['top_vehicle_count']} {t('pcs', lang)}")

if filtered.empty:
    st.warning(t("empty_filter", lang))
    st.stop()

st.markdown(f"<div class='section-title'>{t('key_charts', lang)}</div>", unsafe_allow_html=True)
left, right = st.columns(2)

with left:
    top = metrics["top_count"].sort_values("violations", ascending=True)
    fig = px.bar(
        top,
        x="violations",
        y="plate",
        orientation="h",
        text="violations",
        title=t("top10_count_title", lang),
        labels={"violations": t("violations_axis", lang), "plate": t("vehicle_axis", lang)},
    )
    fig.update_traces(marker_color="#4F81BD", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, height=430, margin=dict(l=20, r=40, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)

with right:
    viol = metrics["violation_counts"].head(10).copy()
    if not viol.empty:
        viol["violation_label"] = viol["violation"].map(lambda x: label_violation(x, lang))
    fig = px.bar(
        viol,
        x="violation_label" if "violation_label" in viol.columns else "violation",
        y="count",
        text="count",
        title=t("violations_structure_title", lang),
        labels={"violation_label": t("violation_axis", lang), "violation": t("violation_axis", lang), "count": t("count_axis", lang)},
    )
    fig.update_traces(marker_color="#4F81BD", textposition="outside", cliponaxis=False)
    fig.update_xaxes(tickangle=-35)
    fig.update_layout(showlegend=False, height=430, margin=dict(l=20, r=30, t=55, b=110))
    st.plotly_chart(fig, use_container_width=True)

st.markdown(f"<div class='section-title'>{t('dynamic_title', lang)}</div>", unsafe_allow_html=True)
d1, d2 = st.columns([2, 1])
with d2:
    dynamic_type = st.selectbox(
        t("dynamic_violation_type", lang),
        ["Все"] + all_violations,
        format_func=lambda x: t("all", lang) if x == "Все" else label_violation(x, lang),
    )
    group_options = ["День", "Час", "Неделя"]
    dynamic_group = st.radio(
        t("dynamic_group", lang),
        group_options,
        horizontal=True,
        format_func=lambda x: label_group(x, lang),
    )
with d1:
    dynamic_df = prepare_dynamic(filtered, dynamic_type, dynamic_group)
    if dynamic_df.empty:
        st.info(t("dynamic_empty", lang))
    else:
        dynamic_name = t("all", lang) if dynamic_type == "Все" else label_violation(dynamic_type, lang)
        fig = px.line(
            dynamic_df,
            x="period",
            y="count",
            markers=True,
            title=t("dynamic_chart_title", lang, violation=dynamic_name.lower(), group=label_group(dynamic_group, lang).lower()),
            labels={"period": t("period_axis", lang), "count": t("violations_axis", lang)},
        )
        fig.update_traces(line_color="#4F81BD", marker_color="#4F81BD")
        fig.update_layout(height=420, margin=dict(l=20, r=30, t=55, b=40))
        st.plotly_chart(fig, use_container_width=True)

st.markdown(f"<div class='section-title'>{t('priority_title', lang)}</div>", unsafe_allow_html=True)
r1, r2 = st.columns(2)
with r1:
    risk = metrics["top_risk"].sort_values("risk_score", ascending=True)
    fig = px.bar(
        risk,
        x="risk_score",
        y="plate",
        orientation="h",
        text="risk_score",
        title=t("top10_risk_title", lang),
        labels={"risk_score": t("risk_axis", lang), "plate": t("vehicle_axis", lang)},
    )
    fig.update_traces(marker_color="#4F81BD", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, height=410, margin=dict(l=20, r=40, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)
with r2:
    sev = metrics["severity_counts"].copy()
    if not sev.empty:
        sev["severity_label"] = sev["severity"].map(lambda x: label_severity(x, lang))
    fig = px.pie(sev, names="severity_label" if "severity_label" in sev.columns else "severity", values="count", title=t("severity_pie_title", lang), hole=0.45)
    fig.update_layout(height=410, margin=dict(l=20, r=20, t=55, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.markdown(f"<div class='section-title'>{t('tables', lang)}</div>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs([t("tab_top_vehicles", lang), t("tab_top_violations", lang), t("tab_locations", lang), t("tab_events", lang)])

with tab1:
    top_display = metrics["top_count"].copy()
    if not top_display.empty:
        top_display["priority"] = top_display["priority"].map(lambda x: label_priority(x, lang))
        top_display = top_display.rename(
            columns={
                "plate": col_label("plate", lang),
                "violations": col_label("violations", lang),
                "dangerous": col_label("dangerous", lang),
                "sharp": col_label("sharp", lang),
                "risk_score": col_label("risk_score", lang),
                "priority": col_label("priority", lang),
            }
        )[[col_label("plate", lang), col_label("violations", lang), col_label("dangerous", lang), col_label("sharp", lang), col_label("risk_score", lang), col_label("priority", lang)]]
    st.dataframe(top_display, use_container_width=True, hide_index=True)

with tab2:
    viol_display = metrics["violation_counts"].copy()
    if not viol_display.empty:
        viol_display["share"] = viol_display["share"].map(lambda x: f"{x:.1%}")
        viol_display["violation"] = viol_display["violation"].map(lambda x: label_violation(x, lang))
        viol_display = viol_display.rename(columns={"violation": col_label("violation", lang), "count": col_label("count", lang), "share": col_label("share", lang)})
    st.dataframe(viol_display, use_container_width=True, hide_index=True)

with tab3:
    loc_display = metrics["location_counts"].copy()
    if not loc_display.empty:
        loc_display = loc_display.rename(columns={"location": col_label("location", lang), "count": col_label("violations", lang)})
    st.dataframe(loc_display, use_container_width=True, hide_index=True)

with tab4:
    base_events = filtered.sort_values("dt", ascending=False).reset_index(drop=True).copy()
    base_events["Карта" if lang == "ru" else "Harita"] = base_events.apply(lambda r: "📍" if _has_valid_coords(r) else "", axis=1)

    events_display = localize_event_values(base_events.copy(), lang)
    events_display = events_display.rename(
        columns={
            "vehicle": col_label("vehicle", lang),
            "plate": col_label("plate", lang),
            "route": col_label("route", lang),
            "violation": col_label("violation", lang),
            "action": col_label("action", lang),
            "severity": col_label("severity", lang),
            "risk": col_label("risk", lang),
            "dt": col_label("dt", lang),
            "hour": col_label("hour", lang),
            "start_pos": col_label("start_pos", lang),
            "end_pos": col_label("end_pos", lang),
            "value": col_label("value", lang),
            "value_num": col_label("value_num", lang),
            "source_file": col_label("source_file", lang),
            "imported_at": col_label("imported_at", lang),
        }
    )
    map_col = "Карта" if lang == "ru" else "Harita"
    visible_cols = [map_col, col_label("dt", lang), col_label("plate", lang), col_label("violation", lang), col_label("severity", lang), col_label("risk", lang), col_label("hour", lang), col_label("start_pos", lang), col_label("value", lang)]
    if col_label("source_file", lang) in events_display.columns:
        visible_cols.append(col_label("source_file", lang))

    hint = "Выбери строку события, затем нажми кнопку «Открыть карту события»." if lang == "ru" else "Olay satırını seç, ardından «Olay haritasını aç» düğmesine bas."
    st.caption(hint)

    selected_idx = None
    table_data = events_display[visible_cols]

    try:
        selection = st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
            height=520,
            on_select="rerun",
            selection_mode="single-row",
        )
        if getattr(selection, "selection", None) and selection.selection.rows:
            selected_idx = int(selection.selection.rows[0])
    except TypeError:
        # Fallback for older Streamlit versions without row selection support.
        st.dataframe(table_data, use_container_width=True, hide_index=True, height=520)
        labels = [_event_short_label(row) for _, row in base_events.iterrows()]
        chosen = st.selectbox(
            "Открыть событие на карте" if lang == "ru" else "Olayı haritada aç",
            [""] + labels,
        )
        if chosen:
            selected_idx = labels.index(chosen)

    if selected_idx is not None and 0 <= selected_idx < len(base_events):
        row = base_events.iloc[selected_idx]

        has_geo = _has_valid_coords(row)
        btn_label = "🗺️ Открыть карту события" if lang == "ru" else "🗺️ Olay haritasını aç"

        if has_geo:
            if st.button(btn_label, type="primary", use_container_width=False):
                _open_event_geo(row, lang)
        else:
            st.warning(
                "У выбранного события пока нет координат. Дождись GEO-дозаполнения или запусти синхронизацию."
                if lang == "ru"
                else "Seçilen olayda henüz koordinat yok. GEO zenginleştirmeyi bekle veya senkronizasyonu çalıştır."
            )

export_bytes = to_excel_bytes(filtered, metrics, lang=lang)
st.download_button(
    t("download_excel", lang),
    data=export_bytes,
    file_name="driving_dashboard_filtered.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
