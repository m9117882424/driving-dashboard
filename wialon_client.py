from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_BASE_URL = "https://hst-api.wialon.com"
DEFAULT_TZ_OFFSET_HOURS = 3.0
DST_NONE_MASK = 0x08000000
TZ_MASK = 0xF000FFFF


class WialonAPIError(RuntimeError):
    """Ошибка Remote API Wialon с сохранением кода и ответа."""

    def __init__(self, message: str, code: int | None = None, payload: Any | None = None):
        self.code = code
        self.payload = payload
        super().__init__(message)


@dataclass(frozen=True)
class WialonTemplate:
    resource_id: int
    resource_name: str
    template_id: int
    template_name: str
    calc_type: str = ""

    @property
    def label(self) -> str:
        suffix = f" · {self.calc_type}" if self.calc_type else ""
        return f"{self.resource_name} / {self.template_name} (res={self.resource_id}, rep={self.template_id}{suffix})"


@dataclass(frozen=True)
class WialonObject:
    object_id: int
    name: str
    item_type: str

    @property
    def label(self) -> str:
        return f"{self.name} (id={self.object_id})"


def read_env_file(path: str | Path) -> dict[str, str]:
    """Минимальный .env reader без дополнительной магии."""
    result: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return result
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        result[key.strip()] = value
    return result


def env_value(key: str, default: str = "", env_path: str | Path | None = None) -> str:
    if os.getenv(key):
        return os.getenv(key, "")
    if env_path:
        return read_env_file(env_path).get(key, default)
    return default


def parse_id_list(value: str | None) -> list[int]:
    if not value:
        return []
    result: list[int] = []
    for part in str(value).replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        result.append(int(part))
    return result


def make_wialon_tz_offset(offset_hours: float = DEFAULT_TZ_OFFSET_HOURS, dst_mask: int = DST_NONE_MASK) -> int:
    """Собирает значение tzOffset для render/set_locale.

    Для UTC+3 без DST получается 134228528.
    """
    offset_seconds = int(float(offset_hours) * 3600)
    return (offset_seconds & TZ_MASK) | int(dst_mask)


def date_bounds_to_unix(date_from: date, date_to: date, tz_offset_hours: float = DEFAULT_TZ_OFFSET_HOURS) -> tuple[int, int]:
    """Преобразует локальный календарный период в Unix timestamps для Wialon."""
    tz = timezone(timedelta(hours=float(tz_offset_hours)))
    start = datetime.combine(date_from, dt_time.min, tzinfo=tz)
    end = datetime.combine(date_to, dt_time(23, 59, 59), tzinfo=tz)
    return int(start.timestamp()), int(end.timestamp())


def _json_dumps(params: dict[str, Any]) -> str:
    return json.dumps(params, ensure_ascii=False, separators=(",", ":"))


class WialonClient:
    def __init__(self, token: str, base_url: str = DEFAULT_BASE_URL, timeout: int = 120):
        self.token = token.strip()
        self.base_url = base_url.rstrip("/")
        self.ajax_url = f"{self.base_url}/wialon/ajax.html"
        self.timeout = timeout
        self.sid: str | None = None

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.logout()
        return False

    def call(self, svc: str, params: dict[str, Any] | None = None, *, expect_json: bool = True) -> Any:
        query: dict[str, Any] = {
            "svc": svc,
            "params": _json_dumps(params or {}),
        }
        if self.sid:
            query["sid"] = self.sid

        response = requests.get(self.ajax_url, params=query, timeout=self.timeout)
        response.raise_for_status()

        if not expect_json:
            content = response.content
            stripped = content.strip()[:1]
            if stripped in {b"{", b"["}:
                try:
                    payload = response.json()
                except Exception:
                    payload = content[:500].decode("utf-8", errors="replace")
                self._raise_if_error(payload, svc)
                raise WialonAPIError(f"Wialon вернул JSON вместо файла для {svc}", payload=payload)
            return content

        try:
            payload = response.json()
        except Exception as exc:
            text = response.text[:1000]
            raise WialonAPIError(f"Wialon вернул не-JSON ответ для {svc}: {text}") from exc

        self._raise_if_error(payload, svc)
        return payload

    @staticmethod
    def _raise_if_error(payload: Any, svc: str) -> None:
        if isinstance(payload, dict) and "error" in payload:
            code = payload.get("error")
            if code not in (None, 0, "0"):
                raise WialonAPIError(f"Ошибка Wialon API в {svc}: code={code}", code=int(code), payload=payload)

    def login(self, *, tz_offset_hours: float = DEFAULT_TZ_OFFSET_HOURS, language: str = "ru") -> dict[str, Any]:
        if not self.token:
            raise WialonAPIError("Не указан Wialon token")
        payload = self.call("token/login", {"token": self.token})
        sid = payload.get("eid") if isinstance(payload, dict) else None
        if not sid:
            raise WialonAPIError("Wialon не вернул session id (eid)", payload=payload)
        self.sid = sid
        # Локаль нужна, чтобы время в отчётах совпадало с интерфейсом, а не уезжало в GMT+0.
        self.set_locale(tz_offset_hours=tz_offset_hours, language=language)
        return payload

    def set_locale(self, *, tz_offset_hours: float = DEFAULT_TZ_OFFSET_HOURS, language: str = "ru") -> dict[str, Any]:
        return self.call("render/set_locale", {
            "tzOffset": make_wialon_tz_offset(tz_offset_hours),
            "language": language,
            "flags": 0,
            "formatDate": "%d.%m.%Y %H:%M:%S",
        })

    def logout(self) -> None:
        if not self.sid:
            return
        try:
            self.call("core/logout", {})
        except Exception:
            pass
        finally:
            self.sid = None

    def cleanup_report_result(self) -> None:
        self.call("report/cleanup_result", {})

    def search_report_templates(self, mask: str = "*", limit: int = 0) -> list[WialonTemplate]:
        payload = self.call("core/search_items", {
            "spec": {
                "itemsType": "avl_resource",
                "propType": "propitemname",
                "propName": "reporttemplates",
                "propValueMask": mask or "*",
                "sortType": "sys_name",
            },
            "force": 1,
            "flags": 8193,
            "from": 0,
            "to": limit,
        })
        templates: list[WialonTemplate] = []
        for item in payload.get("items", []) if isinstance(payload, dict) else []:
            resource_id = int(item.get("id"))
            resource_name = str(item.get("nm", resource_id))
            reps = item.get("rep") or {}
            if isinstance(reps, dict):
                iterable = reps.values()
            else:
                iterable = reps
            for rep in iterable:
                if not isinstance(rep, dict):
                    continue
                templates.append(WialonTemplate(
                    resource_id=resource_id,
                    resource_name=resource_name,
                    template_id=int(rep.get("id")),
                    template_name=str(rep.get("n", rep.get("name", rep.get("id")))),
                    calc_type=str(rep.get("ct", "")),
                ))
        templates.sort(key=lambda x: (x.resource_name.lower(), x.template_name.lower()))
        return templates

    def search_objects(self, item_type: str = "avl_unit_group", mask: str = "*", limit: int = 0) -> list[WialonObject]:
        payload = self.call("core/search_items", {
            "spec": {
                "itemsType": item_type,
                "propName": "sys_name",
                "propValueMask": mask or "*",
                "sortType": "sys_name",
            },
            "force": 1,
            "flags": 1,
            "from": 0,
            "to": limit,
        })
        objects: list[WialonObject] = []
        for item in payload.get("items", []) if isinstance(payload, dict) else []:
            objects.append(WialonObject(
                object_id=int(item.get("id")),
                name=str(item.get("nm", item.get("id"))),
                item_type=item_type,
            ))
        objects.sort(key=lambda x: x.name.lower())
        return objects

    def search_units(self, mask: str = "*", limit: int = 0) -> list[WialonObject]:
        """Return available Wialon units for matching events to GPS messages."""
        return self.search_objects(item_type="avl_unit", mask=mask or "*", limit=limit)

    def unload_messages(self) -> None:
        """Clear Wialon message loader. Safe to call before/after interval loads."""
        try:
            self.call("messages/unload", {})
        except Exception:
            pass

    def load_messages_interval(self, *, item_id: int, time_from: int, time_to: int, load_count: int = 100) -> list[dict[str, Any]]:
        """Load unit messages around a short interval and return raw messages.

        Wialon installations differ slightly: some return messages directly from
        messages/load_interval, while others require messages/get_messages after
        loading into the message loader. This method supports both variants.
        """
        self.unload_messages()
        payload = self.call("messages/load_interval", {
            "itemId": int(item_id),
            "timeFrom": int(time_from),
            "timeTo": int(time_to),
            "flags": 0,
            "flagsMask": 0,
            "loadCount": int(load_count),
        })

        messages: list[dict[str, Any]] = []
        if isinstance(payload, dict):
            raw_messages = payload.get("messages")
            if isinstance(raw_messages, list):
                messages = [m for m in raw_messages if isinstance(m, dict)]
            else:
                count = int(payload.get("count") or 0)
                if count > 0:
                    got = self.call("messages/get_messages", {
                        "indexFrom": 0,
                        "indexTo": max(0, min(count, int(load_count)) - 1),
                        "timeFrom": int(time_from),
                        "timeTo": int(time_to),
                        "filter": "",
                        "flags": 0,
                        "flagsMask": 0,
                        "loadCount": int(load_count),
                    })
                    if isinstance(got, list):
                        messages = [m for m in got if isinstance(m, dict)]
                    elif isinstance(got, dict) and isinstance(got.get("messages"), list):
                        messages = [m for m in got.get("messages", []) if isinstance(m, dict)]
        elif isinstance(payload, list):
            messages = [m for m in payload if isinstance(m, dict)]

        self.unload_messages()
        return messages

    def execute_report(self,
                       *,
                       report_resource_id: int,
                       report_template_id: int,
                       report_object_id: int,
                       time_from: int,
                       time_to: int,
                       object_id_list: list[int] | None = None,
                       remote_exec: int = 1,
                       timeout_sec: int = 300,
                       poll_interval_sec: float = 2.0) -> dict[str, Any]:
        self.cleanup_report_result()
        params: dict[str, Any] = {
            "reportResourceId": int(report_resource_id),
            "reportTemplateId": int(report_template_id),
            "reportObjectId": int(report_object_id),
            "reportObjectSecId": 0,
            "interval": {"from": int(time_from), "to": int(time_to), "flags": 0},
            "remoteExec": int(remote_exec),
        }
        if object_id_list:
            params["reportObjectIdList"] = [int(x) for x in object_id_list]

        result = self.call("report/exec_report", params)
        if not remote_exec:
            return result if isinstance(result, dict) else {"result": result}

        deadline = time.monotonic() + timeout_sec
        last_status: Any = None
        while time.monotonic() < deadline:
            status_payload = self.call("report/get_report_status", {})
            last_status = status_payload.get("status") if isinstance(status_payload, dict) else status_payload
            if int(last_status) == 4:
                applied = self.call("report/apply_report_result", {})
                return applied if isinstance(applied, dict) else {"result": applied}
            if int(last_status) in {8, 16}:
                raise WialonAPIError(f"Отчёт Wialon не выполнен, status={last_status}", payload=status_payload)
            time.sleep(poll_interval_sec)

        raise WialonAPIError(f"Истёк timeout ожидания отчёта Wialon, последний status={last_status}")

    def export_current_report_xlsx(self, output_file_name: str = "driving_quality_report") -> bytes:
        return self.call("report/export_result", {
            "format": 8,
            "compress": "0",
            "hideGoogleLinks": 1,
            "outputFileName": output_file_name,
        }, expect_json=False)

    def run_report_to_xlsx(self,
                           *,
                           report_resource_id: int,
                           report_template_id: int,
                           report_object_id: int,
                           time_from: int,
                           time_to: int,
                           object_id_list: list[int] | None = None,
                           output_file_name: str = "driving_quality_report",
                           timeout_sec: int = 300) -> tuple[bytes, dict[str, Any]]:
        result_meta = self.execute_report(
            report_resource_id=report_resource_id,
            report_template_id=report_template_id,
            report_object_id=report_object_id,
            object_id_list=object_id_list,
            time_from=time_from,
            time_to=time_to,
            timeout_sec=timeout_sec,
        )
        file_bytes = self.export_current_report_xlsx(output_file_name=output_file_name)
        self.cleanup_report_result()
        return file_bytes, result_meta
