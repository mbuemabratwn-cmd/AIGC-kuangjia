import base64
import binascii
import concurrent.futures
import hashlib
import http.client
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


def load_local_env() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())


load_local_env()

app = FastAPI(title="AIGC Local Studio API")
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "app.db"
GENERATED_DIR = Path(__file__).resolve().parents[2] / "data" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_ASSET_DIR = Path(__file__).resolve().parents[2] / "data" / "reference-assets"
REFERENCE_ASSET_DIR.mkdir(parents=True, exist_ok=True)
APIYI_BASE_URL = "https://api.apiyi.com"
APIYI_NATIVE_BASE_URL = f"{APIYI_BASE_URL}/v1beta/models"
LOCAL_API_BASE_URL = os.environ.get("AIGC_LOCAL_API_BASE_URL", "http://127.0.0.1:38381")
PROVIDER_TIMEOUT_SECONDS = 300
SUPABASE_SIGNED_URL_TTL_SECONDS = 3600
GPT_MODEL = "gpt-image-2"
GPT_VIP_MODEL = "gpt-image-2-vip"
GEMINI_MODEL = "gemini-3-pro-image-preview"
GPT_MODELS = {GPT_MODEL, GPT_VIP_MODEL}
LEGACY_MODEL_ALIASES = {
    "gpt-image-2-official": GPT_MODEL,
    "gemini-3-pro-image-preview-official": GEMINI_MODEL,
}
DEFAULT_SETTINGS = {
    "api_key": "",
    "api_key_gpt_image_2": "",
    "api_key_gpt_image_2_vip": "",
    "api_key_nano_banana_pro": "",
    "default_model": GPT_MODEL,
    "default_ratio": "1:1",
    "default_resolution": "1K",
    "output_dir": str(GENERATED_DIR),
    "project_dirs": [],
}
GPT_RATIO_OPTIONS = {
    "auto",
    "1:1",
    "3:2",
    "2:3",
    "4:3",
    "3:4",
    "5:4",
    "4:5",
    "16:9",
    "9:16",
    "2:1",
    "1:2",
    "21:9",
    "9:21",
}
GPT_4K_RATIO_OPTIONS = {"16:9", "9:16", "2:1", "1:2", "21:9", "9:21"}
GEMINI_RATIO_OPTIONS = {
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
}
GPT_VIP_RATIO_OPTIONS = {
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
}
QUALITY_OPTIONS = {"auto", "low", "medium", "high"}
BACKGROUND_OPTIONS = {"auto", "opaque", "transparent"}
OUTPUT_FORMAT_OPTIONS = {"png", "jpeg", "webp"}
GPT_IMAGE_SIZE_MAP = {
    "1K": {
        "1:1": "1024x1024",
        "3:2": "1536x1024",
        "2:3": "1024x1536",
        "4:3": "1024x768",
        "3:4": "768x1024",
        "5:4": "1280x1024",
        "4:5": "1024x1280",
        "16:9": "1536x864",
        "9:16": "864x1536",
        "2:1": "2048x1024",
        "1:2": "1024x2048",
        "21:9": "2016x864",
        "9:21": "864x2016",
    },
    "2K": {
        "1:1": "2048x2048",
        "3:2": "2048x1360",
        "2:3": "1360x2048",
        "4:3": "2048x1536",
        "3:4": "1536x2048",
        "5:4": "2560x2048",
        "4:5": "2048x2560",
        "16:9": "2048x1152",
        "9:16": "1152x2048",
        "2:1": "2688x1344",
        "1:2": "1344x2688",
        "21:9": "2688x1152",
        "9:21": "1152x2688",
    },
    "4K": {
        "16:9": "3840x2160",
        "9:16": "2160x3840",
        "2:1": "3840x1920",
        "1:2": "1920x3840",
        "21:9": "3840x1648",
        "9:21": "1648x3840",
    },
}
GPT_VIP_SIZE_MAP = {
    "1K": {
        "1:1": "1280x1280",
        "2:3": "848x1280",
        "3:2": "1280x848",
        "3:4": "960x1280",
        "4:3": "1280x960",
        "4:5": "1024x1280",
        "5:4": "1280x1024",
        "9:16": "720x1280",
        "16:9": "1280x720",
        "21:9": "1280x544",
    },
    "2K": {
        "1:1": "2048x2048",
        "2:3": "1360x2048",
        "3:2": "2048x1360",
        "3:4": "1536x2048",
        "4:3": "2048x1536",
        "4:5": "1632x2048",
        "5:4": "2048x1632",
        "9:16": "1152x2048",
        "16:9": "2048x1152",
        "21:9": "2048x864",
    },
    "4K": {
        "1:1": "2880x2880",
        "2:3": "2336x3520",
        "3:2": "3520x2336",
        "3:4": "2480x3312",
        "4:3": "3312x2480",
        "4:5": "2560x3216",
        "5:4": "3216x2560",
        "9:16": "2160x3840",
        "16:9": "3840x2160",
        "21:9": "3840x1632",
    },
}

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^http://(127\.0\.0\.1|localhost):\d+$"
        r"|^https://[a-z0-9-]+\.onrender\.com$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectDirPayload(BaseModel):
    name: str
    path: str


class SettingsPayload(BaseModel):
    api_key: str
    api_key_gpt_image_2: str = ""
    api_key_gpt_image_2_vip: str = ""
    api_key_nano_banana_pro: str = ""
    default_model: str
    default_ratio: str
    default_resolution: str
    output_dir: str = ""
    project_dirs: list[ProjectDirPayload] = Field(default_factory=list)


class ProjectSavePayload(BaseModel):
    source_path: str
    project_name: str


class JobCreatePayload(BaseModel):
    prompt: str
    model: str = GPT_MODEL
    size: str = "1:1"
    resolution: str = "1K"
    quality: str = "auto"
    moderation: str = "auto"
    background: str = "auto"
    output_format: str = "png"
    output_compression: Optional[int] = None
    n: int = 1
    image_urls: list[str] = Field(default_factory=list)
    mask_url: Optional[str] = None


class ProviderError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def normalize_model_identifier(model: str) -> str:
    return LEGACY_MODEL_ALIASES.get(model, model)


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_ASSET_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                api_key TEXT NOT NULL,
                api_key_gpt_image_2 TEXT NOT NULL DEFAULT '',
                api_key_gpt_image_2_vip TEXT NOT NULL DEFAULT '',
                api_key_nano_banana_pro TEXT NOT NULL DEFAULT '',
                default_model TEXT NOT NULL,
                default_ratio TEXT NOT NULL,
                default_resolution TEXT NOT NULL,
                output_dir TEXT NOT NULL,
                project_dirs TEXT NOT NULL
            )
            """
        )
        setting_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(settings)").fetchall()
        }
        if "output_dir" not in setting_columns:
            connection.execute(
                "ALTER TABLE settings ADD COLUMN output_dir TEXT NOT NULL DEFAULT ''"
            )
            connection.execute(
                "UPDATE settings SET output_dir = ? WHERE output_dir = ''",
                (DEFAULT_SETTINGS["output_dir"],),
            )
        if "project_dirs" not in setting_columns:
            connection.execute(
                "ALTER TABLE settings ADD COLUMN project_dirs TEXT NOT NULL DEFAULT '[]'"
            )
        if "api_key_gpt_image_2" not in setting_columns:
            connection.execute(
                "ALTER TABLE settings ADD COLUMN api_key_gpt_image_2 TEXT NOT NULL DEFAULT ''"
            )
        if "api_key_gpt_image_2_vip" not in setting_columns:
            connection.execute(
                "ALTER TABLE settings ADD COLUMN api_key_gpt_image_2_vip TEXT NOT NULL DEFAULT ''"
            )
        if "api_key_nano_banana_pro" not in setting_columns:
            connection.execute(
                "ALTER TABLE settings ADD COLUMN api_key_nano_banana_pro TEXT NOT NULL DEFAULT ''"
            )
        connection.execute(
            """
            UPDATE settings
            SET
                default_model = CASE
                    WHEN default_model = 'gpt-image-2-official' THEN ?
                    WHEN default_model = 'gemini-3-pro-image-preview-official' THEN ?
                    ELSE default_model
                END,
                api_key_gpt_image_2 = CASE WHEN api_key_gpt_image_2 = '' THEN api_key ELSE api_key_gpt_image_2 END,
                api_key_gpt_image_2_vip = CASE WHEN api_key_gpt_image_2_vip = '' THEN api_key ELSE api_key_gpt_image_2_vip END,
                api_key_nano_banana_pro = CASE WHEN api_key_nano_banana_pro = '' THEN api_key ELSE api_key_nano_banana_pro END
            WHERE id = 1
            """
            ,
            (GPT_MODEL, GEMINI_MODEL),
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                prompt TEXT NOT NULL,
                size TEXT NOT NULL,
                resolution TEXT NOT NULL,
                quality TEXT NOT NULL,
                background TEXT NOT NULL,
                moderation TEXT NOT NULL,
                output_format TEXT NOT NULL,
                output_compression INTEGER,
                image_count INTEGER NOT NULL,
                image_urls TEXT NOT NULL,
                reference_image_urls TEXT NOT NULL DEFAULT '[]',
                mask_url TEXT,
                status TEXT NOT NULL,
                remote_task_id TEXT,
                result_paths TEXT NOT NULL,
                temp_asset_paths TEXT NOT NULL DEFAULT '[]',
                error_message TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        job_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
        }
        if "temp_asset_paths" not in job_columns:
            connection.execute(
                "ALTER TABLE jobs ADD COLUMN temp_asset_paths TEXT NOT NULL DEFAULT '[]'"
            )
        if "reference_image_urls" not in job_columns:
            connection.execute(
                "ALTER TABLE jobs ADD COLUMN reference_image_urls TEXT NOT NULL DEFAULT '[]'"
            )
        connection.execute(
            """
            INSERT INTO settings (
                id,
                api_key,
                api_key_gpt_image_2,
                api_key_gpt_image_2_vip,
                api_key_nano_banana_pro,
                default_model,
                default_ratio,
                default_resolution,
                output_dir,
                project_dirs
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (
                1,
                DEFAULT_SETTINGS["api_key"],
                DEFAULT_SETTINGS["api_key_gpt_image_2"],
                DEFAULT_SETTINGS["api_key_gpt_image_2_vip"],
                DEFAULT_SETTINGS["api_key_nano_banana_pro"],
                DEFAULT_SETTINGS["default_model"],
                DEFAULT_SETTINGS["default_ratio"],
                DEFAULT_SETTINGS["default_resolution"],
                DEFAULT_SETTINGS["output_dir"],
                json.dumps(DEFAULT_SETTINGS["project_dirs"]),
            ),
        )
        connection.commit()


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


def normalize_resolution(value: str) -> str:
    normalized = value.upper()

    if normalized not in {"1K", "2K", "4K"}:
        raise HTTPException(status_code=422, detail="Unsupported resolution")

    return normalized


def normalize_model_name(value: str) -> str:
    normalized = value.strip()
    return LEGACY_MODEL_ALIASES.get(normalized, normalized)


def normalize_size(value: str) -> str:
    normalized = value.strip()

    if normalized in GPT_RATIO_OPTIONS or is_pixel_size(normalized):
        return normalized

    raise HTTPException(status_code=422, detail="Unsupported size")


def normalize_quality(value: str) -> str:
    normalized = value.lower()

    if normalized not in QUALITY_OPTIONS:
        raise HTTPException(status_code=422, detail="Unsupported quality")

    return normalized


def normalize_moderation(value: str) -> str:
    normalized = value.lower()

    if normalized not in {"auto", "low"}:
        raise HTTPException(status_code=422, detail="Unsupported moderation")

    return normalized


def normalize_background(value: str) -> str:
    normalized = value.lower()

    if normalized not in BACKGROUND_OPTIONS:
        raise HTTPException(status_code=422, detail="Unsupported background")

    if normalized == "transparent":
        return "auto"

    return normalized


def normalize_output_format(value: str) -> str:
    normalized = value.lower()

    if normalized not in OUTPUT_FORMAT_OPTIONS:
        raise HTTPException(status_code=422, detail="Unsupported output format")

    return normalized


def normalize_output_dir(value: str) -> str:
    output_dir = value.strip()
    if not output_dir:
        return DEFAULT_SETTINGS["output_dir"]

    normalized = Path(output_dir).expanduser()
    if not normalized.is_absolute():
        raise HTTPException(status_code=422, detail="Output directory must be an absolute path")

    return str(normalized)


def normalize_project_dirs(project_dirs: list[ProjectDirPayload]) -> list[dict[str, str]]:
    if len(project_dirs) > 4:
        raise HTTPException(status_code=422, detail="Project folders support at most 4 items")

    normalized: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for project in project_dirs:
        name = project.name.strip()
        path = project.path.strip()
        if not name or not path:
            raise HTTPException(status_code=422, detail="Project folder name and path are required")
        if name in seen_names:
            raise HTTPException(status_code=422, detail="Project folder names must be unique")
        normalized_path = Path(path).expanduser()
        if not normalized_path.is_absolute():
            raise HTTPException(status_code=422, detail="Project folder path must be an absolute path")
        seen_names.add(name)
        normalized.append({"name": name, "path": str(normalized_path)})

    return normalized


def is_pixel_size(value: str) -> bool:
    if "x" not in value:
        return False

    width, height = value.split("x", 1)
    return width.isdigit() and height.isdigit()


def validate_job_payload(payload: JobCreatePayload) -> dict[str, Any]:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt is required")

    model = normalize_model_identifier(payload.model)

    if model == GPT_MODEL:
        size = normalize_size(payload.size)
    elif model == GPT_VIP_MODEL:
        size = normalize_gpt_vip_size(payload.size)
    elif model == GEMINI_MODEL:
        size = normalize_gemini_size(payload.size)
    else:
        raise HTTPException(status_code=422, detail="Unsupported model")

    resolution = normalize_resolution(payload.resolution)
    quality = normalize_quality(payload.quality)
    moderation = "low" if model in GPT_MODELS else normalize_moderation(payload.moderation)
    background = normalize_background(payload.background)
    output_format = normalize_output_format(payload.output_format)

    if payload.n < 1 or payload.n > 4:
        raise HTTPException(status_code=422, detail="n must be between 1 and 4")

    max_image_count = 16 if model in GPT_MODELS else 14
    if len(payload.image_urls) > max_image_count:
        raise HTTPException(
            status_code=422,
            detail=f"image_urls supports at most {max_image_count} items",
        )

    if payload.mask_url and not payload.image_urls:
        raise HTTPException(status_code=422, detail="mask_url requires at least one reference image")

    if (
        model == GPT_MODEL
        and resolution == "4K"
        and size in GPT_RATIO_OPTIONS
        and size not in GPT_4K_RATIO_OPTIONS
    ):
        raise HTTPException(
            status_code=422,
            detail=f"resolution 4K not supported for size {size}",
        )

    if model == GPT_VIP_MODEL and resolution == "4K" and size not in GPT_VIP_RATIO_OPTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"resolution 4K not supported for size {size}",
        )

    if model == GEMINI_MODEL and payload.mask_url:
        raise HTTPException(status_code=422, detail="mask_url is not supported for Gemini Pro")

    if payload.output_compression is not None:
        if output_format not in {"jpeg", "webp"}:
            raise HTTPException(
                status_code=422,
                detail="output_compression only works with jpeg or webp",
            )
        if payload.output_compression < 0 or payload.output_compression > 100:
            raise HTTPException(
                status_code=422,
                detail="output_compression must be between 0 and 100",
            )

    return {
        "model": model,
        "prompt": prompt,
        "size": size,
        "resolution": resolution,
        "quality": quality,
        "background": background,
        "moderation": moderation if model in GPT_MODELS else "",
        "output_format": output_format,
        "output_compression": payload.output_compression,
        "n": payload.n,
        "image_urls": payload.image_urls,
        "mask_url": payload.mask_url,
    }


def get_api_key(model: str) -> str:
    model = normalize_model_identifier(model)
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                api_key,
                api_key_gpt_image_2,
                api_key_gpt_image_2_vip,
                api_key_nano_banana_pro
            FROM settings
            WHERE id = 1
            """
        ).fetchone()

    if row is None:
        api_key = ""
    elif model == GPT_MODEL:
        api_key = (row["api_key_gpt_image_2"] or row["api_key"] or "").strip()
    elif model == GPT_VIP_MODEL:
        api_key = (row["api_key_gpt_image_2_vip"] or row["api_key"] or "").strip()
    elif model == GEMINI_MODEL:
        api_key = (row["api_key_nano_banana_pro"] or row["api_key"] or "").strip()
    else:
        api_key = (row["api_key"] or "").strip()

    if not api_key:
        raise HTTPException(status_code=400, detail=f"{model} 的 API key 未设置")

    return api_key


def get_output_dir() -> Path:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT output_dir FROM settings WHERE id = 1"
        ).fetchone()

    output_dir = DEFAULT_SETTINGS["output_dir"] if row is None else row["output_dir"]
    return Path(normalize_output_dir(output_dir))


def get_project_dirs() -> list[dict[str, str]]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT project_dirs FROM settings WHERE id = 1"
        ).fetchone()

    raw_project_dirs = "[]" if row is None else row["project_dirs"]
    try:
        parsed = json.loads(raw_project_dirs)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    project_dirs: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        path = str(item.get("path", "")).strip()
        if name and path:
            project_dirs.append({"name": name, "path": path})

    return project_dirs[:4]


def create_job_record(job_id: str, payload: dict[str, Any], temp_asset_paths: list[str]) -> None:
    now = int(time.time())

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO jobs (
                id,
                model,
                prompt,
                size,
                resolution,
                quality,
                background,
                moderation,
                output_format,
                output_compression,
                image_count,
                image_urls,
                reference_image_urls,
                mask_url,
                status,
                remote_task_id,
                result_paths,
                temp_asset_paths,
                error_message,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                payload["model"],
                payload["prompt"],
                payload["size"],
                payload["resolution"],
                payload["quality"],
                payload["background"],
                payload["moderation"],
                payload["output_format"],
                payload["output_compression"],
                payload["n"],
                json.dumps(payload.get("provider_image_urls", payload["image_urls"])),
                json.dumps(payload["image_urls"]),
                payload["mask_url"],
                "created",
                None,
                json.dumps([]),
                json.dumps(temp_asset_paths),
                None,
                now,
                now,
            ),
        )
        connection.commit()


def update_job_record(
    job_id: str,
    *,
    status: Optional[str] = None,
    remote_task_id: Optional[str] = None,
    result_paths: Optional[list[str]] = None,
    temp_asset_paths: Optional[list[str]] = None,
    error_message: Optional[str] = None,
) -> None:
    assignments: list[str] = ["updated_at = ?"]
    values: list[Any] = [int(time.time())]

    if status is not None:
        assignments.append("status = ?")
        values.append(status)
    if remote_task_id is not None:
        assignments.append("remote_task_id = ?")
        values.append(remote_task_id)
    if result_paths is not None:
        assignments.append("result_paths = ?")
        values.append(json.dumps(result_paths))
    if temp_asset_paths is not None:
        assignments.append("temp_asset_paths = ?")
        values.append(json.dumps(temp_asset_paths))
    if error_message is not None:
        assignments.append("error_message = ?")
        values.append(error_message)

    values.append(job_id)

    with get_connection() as connection:
        connection.execute(
            f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        connection.commit()


def get_job_record(job_id: str) -> Optional[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()


def list_job_records(limit: int = 20) -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM jobs
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def delete_job_record(job_id: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        connection.commit()


def serialize_job(row: sqlite3.Row) -> dict[str, Any]:
    model = normalize_model_identifier(row["model"])
    image_urls = normalize_local_reference_urls(json.loads(row["image_urls"]))
    reference_image_urls = normalize_local_reference_urls(json.loads(row["reference_image_urls"]))
    return {
        "id": row["id"],
        "model": model,
        "prompt": row["prompt"],
        "size": row["size"],
        "resolution": row["resolution"],
        "quality": row["quality"],
        "background": row["background"],
        "moderation": row["moderation"],
        "output_format": row["output_format"],
        "output_compression": row["output_compression"],
        "n": row["image_count"],
        "image_urls": image_urls,
        "reference_image_urls": reference_image_urls,
        "mask_url": row["mask_url"],
        "status": row["status"],
        "remote_task_id": row["remote_task_id"],
        "result_paths": json.loads(row["result_paths"]),
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_job_for_list(row: sqlite3.Row) -> dict[str, Any]:
    serialized = serialize_job(row)
    if serialized["reference_image_urls"]:
        serialized["image_urls"] = serialized["reference_image_urls"]
    return serialized


def normalize_local_reference_urls(values: list[str]) -> list[str]:
    return [normalize_local_reference_url(value) for value in values]


def normalize_local_reference_url(value: str) -> str:
    parsed = urllib_parse.urlparse(value)
    if parsed.path.startswith("/reference-assets/") and parsed.hostname in {
        "127.0.0.1",
        "localhost",
    }:
        return build_reference_asset_url(Path(urllib_parse.unquote(parsed.path)).name)
    return value


def normalize_gemini_size(value: str) -> str:
    normalized = value.strip()

    if normalized not in GEMINI_RATIO_OPTIONS:
        raise HTTPException(status_code=422, detail="Unsupported size for Gemini Pro")

    return normalized


def normalize_gpt_vip_size(value: str) -> str:
    normalized = value.strip()

    if normalized not in GPT_VIP_RATIO_OPTIONS:
        raise HTTPException(status_code=422, detail="Unsupported size for GPT Image 2 VIP")

    return normalized


def perform_json_request(request: urllib_request.Request) -> dict[str, Any]:
    try:
        with urllib_request.urlopen(request, timeout=PROVIDER_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        message = format_provider_error(parse_provider_error(body, exc.reason))
        raise ProviderError(exc.code, message) from exc
    except urllib_error.URLError as exc:
        raise ProviderError(502, str(exc.reason)) from exc
    except TimeoutError as exc:
        raise ProviderError(504, "Provider request timed out") from exc


def parse_provider_error(body: str, fallback: str) -> str:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body.strip() or fallback

    error_payload = parsed.get("error")
    if isinstance(error_payload, dict) and error_payload.get("message"):
        return str(error_payload["message"])

    if parsed.get("message"):
        return str(parsed["message"])

    if parsed.get("detail"):
        return str(parsed["detail"])

    return fallback


def format_provider_error(message: str) -> str:
    if is_provider_safety_error(message):
        violation_match = re.search(r"safety_violations=\[([^\]]+)\]", message)
        request_match = re.search(r"(?:request id|request-id|req(?:uest)?_id)[:= ]+([A-Za-z0-9_-]+)", message)
        details: list[str] = []
        if violation_match:
            details.append(f"违规类型：{violation_match.group(1)}")
        if request_match:
            details.append(f"请求ID：{request_match.group(1)}")
        suffix = f"（{'，'.join(details)}）" if details else ""
        return (
            "内容安全审核拦截：请弱化或移除涉性、未成年、裸露、亲密姿态等描述，"
            f"或更换参考图后重试。{suffix}"
        )
    return message


def is_provider_safety_error(message: str) -> bool:
    normalized = message.lower()
    return (
        "safety_violations=" in normalized
        or "rejected by the safety system" in normalized
        or "moderation_blocked" in normalized
    )


def submit_provider_job(
    job_id: str,
    api_key: str,
    payload: dict[str, Any],
) -> list[str]:
    image_count = int(payload.get("n", 1))
    if image_count > 1:
        result_paths: list[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(image_count, 4)) as executor:
            futures = [
                executor.submit(
                    submit_single_provider_job,
                    f"{job_id}_{index}",
                    api_key,
                    {**payload, "n": 1},
                )
                for index in range(image_count)
            ]
            for future in futures:
                result_paths.extend(future.result())
        return result_paths

    return submit_single_provider_job(job_id, api_key, payload)


def submit_single_provider_job(
    job_id: str,
    api_key: str,
    payload: dict[str, Any],
) -> list[str]:
    if payload["model"] in GPT_MODELS:
        return submit_gpt_image_job(job_id, api_key, payload)

    if payload["model"] == GEMINI_MODEL:
        return submit_gemini_image_job(job_id, api_key, payload)

    raise ProviderError(422, "Unsupported model")


def submit_gpt_image_job(job_id: str, api_key: str, payload: dict[str, Any]) -> list[str]:
    provider_images = payload.get("provider_images", [])
    if isinstance(provider_images, list) and provider_images:
        return submit_gpt_image_edit_job(job_id, api_key, payload)

    request_payload = {
        "model": payload["model"],
        "prompt": payload["prompt"],
        "size": resolve_gpt_size(payload["model"], payload["size"], payload["resolution"]),
        "output_format": payload["output_format"],
    }

    if payload["model"] == GPT_MODEL:
        request_payload["quality"] = payload["quality"]
        request_payload["background"] = payload["background"]
        request_payload["moderation"] = payload["moderation"]
        request_payload["n"] = payload["n"]
        if payload["output_compression"] is not None:
            request_payload["output_compression"] = payload["output_compression"]
    else:
        request_payload["response_format"] = "b64_json"

    if payload["image_urls"]:
        request_payload["image_urls"] = payload["image_urls"]

    body = json.dumps(request_payload).encode("utf-8")
    request = urllib_request.Request(
        f"{APIYI_BASE_URL}/v1/images/generations",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    response_data = perform_json_request(request)
    return save_gpt_images(job_id, response_data)


def submit_gpt_image_edit_job(job_id: str, api_key: str, payload: dict[str, Any]) -> list[str]:
    form_fields = [
        ("model", payload["model"]),
        ("prompt", payload["prompt"]),
    ]
    if payload["model"] == GPT_MODEL:
        form_fields.append(
            ("size", resolve_gpt_size(payload["model"], payload["size"], payload["resolution"]))
        )
        form_fields.append(("quality", payload["quality"]))
        form_fields.append(("moderation", payload["moderation"]))
    else:
        form_fields.append(
            ("size", resolve_gpt_size(payload["model"], payload["size"], payload["resolution"]))
        )
        form_fields.append(("response_format", "b64_json"))

    files: list[tuple[str, str, str, bytes]] = []
    image_field_name = "image[]" if payload["model"] == GPT_MODEL else "image"
    for image in payload.get("provider_images", []):
        files.append(
            (
                image_field_name,
                image["filename"],
                image["content_type"],
                image["raw_bytes"],
            )
        )

    mask_image = payload.get("provider_mask_image")
    if isinstance(mask_image, dict):
        files.append(
            (
                "mask",
                mask_image["filename"],
                mask_image["content_type"],
                mask_image["raw_bytes"],
            )
        )

    body, content_type = encode_multipart_form_data(form_fields, files)
    request = urllib_request.Request(
        f"{APIYI_BASE_URL}/v1/images/edits",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    response_data = perform_json_request(request)
    return save_gpt_images(job_id, response_data)


def submit_gemini_image_job(job_id: str, api_key: str, payload: dict[str, Any]) -> list[str]:
    request_payload = build_gemini_request_payload(payload)
    request = urllib_request.Request(
        f"{APIYI_NATIVE_BASE_URL}/{urllib_parse.quote(payload['model'])}:generateContent",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    response_data = perform_json_request(request)
    return save_gemini_images(job_id, response_data)


def resolve_gpt_size(model: str, size: str, resolution: str) -> str:
    if "x" in size:
        return size

    if size == "auto":
        return "auto"

    size_map = GPT_VIP_SIZE_MAP if model == GPT_VIP_MODEL else GPT_IMAGE_SIZE_MAP
    resolved = size_map.get(resolution, {}).get(size)
    if not resolved:
        raise HTTPException(status_code=422, detail=f"Unsupported size {size} for {resolution}")
    return resolved


def build_gemini_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text_part = {"text": payload["prompt"]}
    contents: list[dict[str, Any]] = [{"parts": [text_part]}]

    if payload["image_urls"]:
        parts = [text_part]
        for image_url in payload["image_urls"]:
            parts.append(build_gemini_image_part(image_url))
        contents = [{"parts": parts}]

    return {
        "contents": contents,
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": payload["size"],
                "imageSize": payload["resolution"],
            },
        },
    }


def build_gemini_image_part(image_url: str) -> dict[str, Any]:
    if is_data_url(image_url):
        content_type, raw_bytes = decode_data_url(image_url)
        return build_gemini_inline_image_part(content_type, raw_bytes)

    if is_reference_asset_url(image_url):
        content_type, raw_bytes, _ = load_reference_asset(image_url)
        return build_gemini_inline_image_part(content_type, raw_bytes)

    content_type, raw_bytes = download_reference_image(image_url)
    return build_gemini_inline_image_part(content_type, raw_bytes)


def build_gemini_inline_image_part(content_type: str, raw_bytes: bytes) -> dict[str, Any]:
    return {
        "inlineData": {
            "mimeType": content_type,
            "data": base64.b64encode(raw_bytes).decode("ascii"),
        }
    }


def save_gpt_images(job_id: str, response_data: dict[str, Any]) -> list[str]:
    output_dir = get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    data = response_data.get("data")
    if not isinstance(data, list):
        raise ProviderError(502, "Provider returned invalid image data")

    result_paths: list[str] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        b64_json = item.get("b64_json")
        image_url = item.get("url")

        if isinstance(b64_json, str) and b64_json:
            raw_bytes = decode_base64_image(b64_json)
            destination = output_dir / f"{job_id}_{index}.{payload_output_extension(item.get('output_format'))}"
            destination.write_bytes(raw_bytes)
            result_paths.append(str(destination))
            continue

        if isinstance(image_url, str) and image_url:
            destination = output_dir / f"{job_id}_{index}{infer_image_suffix(image_url)}"
            download_file(image_url, destination)
            result_paths.append(str(destination))

    if not result_paths:
        raise ProviderError(502, "Provider returned no images")

    return result_paths


def save_gemini_images(job_id: str, response_data: dict[str, Any]) -> list[str]:
    output_dir = get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = response_data.get("candidates")
    if not isinstance(candidates, list):
        raise ProviderError(502, "Provider returned invalid image data")

    result_paths: list[str] = []
    image_index = 0

    for candidate in candidates:
        content = candidate.get("content") if isinstance(candidate, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            continue

        for part in parts:
            inline_data = part.get("inlineData") if isinstance(part, dict) else None
            if not isinstance(inline_data, dict):
                inline_data = part.get("inline_data") if isinstance(part, dict) else None
            if not isinstance(inline_data, dict):
                continue

            data = inline_data.get("data")
            mime_type = inline_data.get("mimeType") or inline_data.get("mime_type")
            if not isinstance(data, str) or not isinstance(mime_type, str):
                continue

            raw_bytes = decode_base64_image(data)
            destination = output_dir / f"{job_id}_{image_index}{content_type_to_extension(mime_type)}"
            destination.write_bytes(raw_bytes)
            result_paths.append(str(destination))
            image_index += 1

    if not result_paths:
        raise ProviderError(502, "Provider returned no images")

    return result_paths


def decode_base64_image(value: str) -> bytes:
    if value.startswith("data:"):
        _, _, value = value.partition(",")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ProviderError(502, "Provider returned invalid base64 image") from exc


def payload_output_extension(output_format: Any) -> str:
    if isinstance(output_format, str) and output_format.lower() in OUTPUT_FORMAT_OPTIONS:
        return "jpg" if output_format.lower() == "jpeg" else output_format.lower()
    return "png"


def infer_image_suffix(url: str) -> str:
    suffix = Path(urllib_parse.urlparse(url).path).suffix
    return suffix or ".png"


def get_supabase_config() -> Optional[dict[str, str]]:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    bucket = os.environ.get("SUPABASE_BUCKET", "").strip()

    if not url and not service_role_key and not bucket:
        return None

    if not url or not service_role_key or not bucket:
        raise HTTPException(
            status_code=400,
            detail="检测到本地参考图，但 Supabase 未配置完整。请设置 SUPABASE_URL、SUPABASE_SERVICE_ROLE_KEY、SUPABASE_BUCKET。",
        )

    return {
        "url": url,
        "service_role_key": service_role_key,
        "bucket": bucket,
    }


def prepare_provider_assets(job_id: str, payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    image_urls = payload["image_urls"]
    mask_url = payload["mask_url"]
    if not image_urls and not mask_url:
        return payload, []

    provider_images: list[dict[str, Any]] = []
    stable_image_urls: list[str] = []
    for index, image_url in enumerate(image_urls):
        stable_url, provider_image = prepare_reference_image(payload["model"], image_url, index)
        stable_image_urls.append(stable_url)
        if provider_image is not None:
            provider_images.append(provider_image)

    stable_mask_url = mask_url
    provider_mask_image = None
    if isinstance(mask_url, str) and mask_url.strip():
        stable_mask_url, provider_mask_image = prepare_mask_image(mask_url)

    prepared_payload = {
        **payload,
        "image_urls": stable_image_urls,
        "provider_image_urls": image_urls,
        "mask_url": stable_mask_url,
        "provider_images": provider_images,
        "provider_mask_image": provider_mask_image,
    }
    return prepared_payload, []


def is_data_url(value: str) -> bool:
    return value.startswith("data:")


def is_reference_asset_url(value: str) -> bool:
    path = urllib_parse.urlparse(value).path
    return path.startswith("/reference-assets/")


def decode_data_url(value: str) -> tuple[str, bytes]:
    header, _, encoded = value.partition(",")
    if not header or not encoded or ";base64" not in header:
        raise HTTPException(status_code=422, detail="参考图格式无效")

    content_type = header[5:].split(";", 1)[0].strip().lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="参考图必须是图片")

    try:
        raw_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail="参考图内容损坏") from exc

    return content_type, raw_bytes


def prepare_reference_image(
    model: str,
    image_url: str,
    index: int,
) -> tuple[str, Optional[dict[str, Any]]]:
    if is_data_url(image_url):
        content_type, raw_bytes = decode_data_url(image_url)
        stable_url = persist_reference_asset(raw_bytes, content_type)
        return stable_url, build_provider_file(stable_url, content_type, raw_bytes)

    if is_reference_asset_url(image_url):
        content_type, raw_bytes, stable_url = load_reference_asset(image_url)
        return stable_url, build_provider_file(stable_url, content_type, raw_bytes)

    if model in GPT_MODELS:
        content_type, raw_bytes = download_reference_image(image_url)
        return image_url, build_provider_remote_file(image_url, index, content_type, raw_bytes)

    return image_url, None


def prepare_mask_image(mask_url: str) -> tuple[str, dict[str, Any]]:
    if is_data_url(mask_url):
        content_type, raw_bytes = decode_data_url(mask_url)
        stable_url = persist_reference_asset(raw_bytes, content_type)
        return stable_url, build_provider_file(stable_url, content_type, raw_bytes)

    if is_reference_asset_url(mask_url):
        content_type, raw_bytes, stable_url = load_reference_asset(mask_url)
        return stable_url, build_provider_file(stable_url, content_type, raw_bytes)

    content_type, raw_bytes = download_reference_image(mask_url)
    return mask_url, build_provider_remote_file(mask_url, 0, content_type, raw_bytes)


def build_temp_asset_path(job_id: str, asset_kind: str, index: int, content_type: str) -> str:
    suffix = content_type_to_extension(content_type)
    return f"temp/{job_id}/{asset_kind}_{index}{suffix}"


def content_type_to_extension(content_type: str) -> str:
    if content_type == "image/jpeg":
        return ".jpg"
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    return ".bin"


def extension_to_content_type(suffix: str) -> str:
    normalized = suffix.lower()
    if normalized == ".jpg" or normalized == ".jpeg":
        return "image/jpeg"
    if normalized == ".png":
        return "image/png"
    if normalized == ".webp":
        return "image/webp"
    return "application/octet-stream"


def build_reference_asset_url(filename: str) -> str:
    return f"{LOCAL_API_BASE_URL}/reference-assets/{urllib_parse.quote(filename)}"


def persist_reference_asset(raw_bytes: bytes, content_type: str) -> str:
    digest = hashlib.sha256(raw_bytes).hexdigest()
    filename = f"{digest}{content_type_to_extension(content_type)}"
    destination = REFERENCE_ASSET_DIR / filename
    if not destination.exists():
        destination.write_bytes(raw_bytes)
    return build_reference_asset_url(filename)


def load_reference_asset(image_url: str) -> tuple[str, bytes, str]:
    parsed = urllib_parse.urlparse(image_url)
    filename = Path(urllib_parse.unquote(parsed.path)).name
    if not filename:
        raise HTTPException(status_code=422, detail="参考图路径无效")

    asset_path = REFERENCE_ASSET_DIR / filename
    if not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(status_code=404, detail="参考图资源不存在")

    return (
        extension_to_content_type(asset_path.suffix),
        asset_path.read_bytes(),
        build_reference_asset_url(filename),
    )


def build_provider_file(image_url: str, content_type: str, raw_bytes: bytes) -> dict[str, Any]:
    filename = Path(urllib_parse.urlparse(image_url).path).name or f"reference{content_type_to_extension(content_type)}"
    return {
        "filename": filename,
        "content_type": content_type,
        "raw_bytes": raw_bytes,
    }


def build_provider_remote_file(
    image_url: str,
    index: int,
    content_type: str,
    raw_bytes: bytes,
) -> dict[str, Any]:
    path = urllib_parse.urlparse(image_url).path
    filename = Path(path).name or f"reference_{index}{content_type_to_extension(content_type)}"
    return {
        "filename": filename,
        "content_type": content_type,
        "raw_bytes": raw_bytes,
    }


def download_reference_image(image_url: str) -> tuple[str, bytes]:
    request = urllib_request.Request(image_url, method="GET")
    try:
        with urllib_request.urlopen(request, timeout=PROVIDER_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get_content_type() or extension_to_content_type(
                Path(urllib_parse.urlparse(image_url).path).suffix
            )
            raw_bytes = response.read()
    except urllib_error.URLError as exc:
        raise ProviderError(502, f"参考图下载失败：{exc.reason}") from exc
    except TimeoutError as exc:
        raise ProviderError(504, "参考图下载超时") from exc

    if not content_type.startswith("image/"):
        raise ProviderError(422, "参考图必须是图片")

    return content_type, raw_bytes


def encode_multipart_form_data(
    fields: list[tuple[str, str]],
    files: list[tuple[str, str, str, bytes]],
) -> tuple[bytes, str]:
    boundary = f"----AIGCFormBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    for name, filename, content_type, raw_bytes in files:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                raw_bytes,
                b"\r\n",
            ]
        )

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def upload_supabase_object(
    supabase_config: dict[str, str],
    object_path: str,
    content_type: str,
    raw_bytes: bytes,
) -> None:
    request = urllib_request.Request(
        f"{supabase_config['url']}/storage/v1/object/{supabase_config['bucket']}/{urllib_parse.quote(object_path, safe='/')}",
        data=raw_bytes,
        headers={
            "apikey": supabase_config["service_role_key"],
            "Authorization": f"Bearer {supabase_config['service_role_key']}",
            "Content-Type": content_type,
            "cache-control": "60",
            "x-upsert": "false",
        },
        method="POST",
    )
    perform_supabase_request(request)


def create_supabase_signed_url(supabase_config: dict[str, str], object_path: str) -> str:
    request = urllib_request.Request(
        f"{supabase_config['url']}/storage/v1/object/sign/{supabase_config['bucket']}/{urllib_parse.quote(object_path, safe='/')}",
        data=json.dumps({"expiresIn": SUPABASE_SIGNED_URL_TTL_SECONDS}).encode("utf-8"),
        headers={
            "apikey": supabase_config["service_role_key"],
            "Authorization": f"Bearer {supabase_config['service_role_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    response_data = perform_supabase_request(request)
    signed_url = response_data.get("signedURL")
    if not isinstance(signed_url, str) or not signed_url:
        raise HTTPException(status_code=502, detail="Supabase 未返回签名 URL")
    if signed_url.startswith("http://") or signed_url.startswith("https://"):
        return signed_url
    return f"{supabase_config['url']}/storage/v1{signed_url}"


def cleanup_job_temp_assets(job_id: str) -> None:
    row = get_job_record(job_id)
    if row is None:
        return

    try:
        temp_asset_paths = json.loads(row["temp_asset_paths"])
    except json.JSONDecodeError:
        temp_asset_paths = []

    if not isinstance(temp_asset_paths, list) or not temp_asset_paths:
        return

    supabase_config = get_supabase_config()
    if supabase_config is None:
        return

    cleanup_supabase_paths(supabase_config, [str(path) for path in temp_asset_paths])
    update_job_record(job_id, temp_asset_paths=[])


def cleanup_supabase_paths(supabase_config: dict[str, str], object_paths: list[str]) -> None:
    if not object_paths:
        return

    request = urllib_request.Request(
        f"{supabase_config['url']}/storage/v1/object/{supabase_config['bucket']}",
        data=json.dumps({"prefixes": object_paths}).encode("utf-8"),
        headers={
            "apikey": supabase_config["service_role_key"],
            "Authorization": f"Bearer {supabase_config['service_role_key']}",
            "Content-Type": "application/json",
        },
        method="DELETE",
    )
    try:
        perform_supabase_request(request)
    except ProviderError:
        return


def perform_supabase_request(request: urllib_request.Request) -> dict[str, Any]:
    try:
        with urllib_request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        message = parse_provider_error(body, exc.reason)
        raise HTTPException(status_code=502, detail=f"Supabase 请求失败：{message}") from exc
    except urllib_error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Supabase 请求失败：{exc.reason}") from exc
    except (TimeoutError, http.client.HTTPException, ConnectionError) as exc:
        raise HTTPException(status_code=502, detail=f"Supabase 请求失败：{exc}") from exc

    if not body:
        return {}

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def download_file(url: str, destination: Path) -> None:
    request = urllib_request.Request(url, method="GET")

    try:
        with urllib_request.urlopen(request, timeout=PROVIDER_TIMEOUT_SECONDS) as response:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.read())
    except urllib_error.URLError as exc:
        raise ProviderError(502, f"Download failed: {exc.reason}") from exc
    except OSError as exc:
        raise ProviderError(502, f"Download failed: {exc}") from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                api_key,
                api_key_gpt_image_2,
                api_key_gpt_image_2_vip,
                api_key_nano_banana_pro,
                default_model,
                default_ratio,
                default_resolution,
                output_dir,
                project_dirs
            FROM settings
            WHERE id = 1
            """
        ).fetchone()

    if row is None:
        return DEFAULT_SETTINGS

    return {
        "api_key": row["api_key"],
        "api_key_gpt_image_2": row["api_key_gpt_image_2"],
        "api_key_gpt_image_2_vip": row["api_key_gpt_image_2_vip"],
        "api_key_nano_banana_pro": row["api_key_nano_banana_pro"],
        "default_model": normalize_model_name(row["default_model"]),
        "default_ratio": row["default_ratio"],
        "default_resolution": row["default_resolution"],
        "output_dir": row["output_dir"] or DEFAULT_SETTINGS["output_dir"],
        "project_dirs": get_project_dirs(),
    }


@app.put("/api/settings")
def update_settings(payload: SettingsPayload) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE settings
            SET
                api_key = ?,
                api_key_gpt_image_2 = ?,
                api_key_gpt_image_2_vip = ?,
                api_key_nano_banana_pro = ?,
                default_model = ?,
                default_ratio = ?,
                default_resolution = ?,
                output_dir = ?,
                project_dirs = ?
            WHERE id = 1
            """,
            (
                payload.api_key,
                payload.api_key_gpt_image_2,
                payload.api_key_gpt_image_2_vip,
                payload.api_key_nano_banana_pro,
                normalize_model_name(payload.default_model),
                payload.default_ratio,
                payload.default_resolution,
                normalize_output_dir(payload.output_dir),
                json.dumps(normalize_project_dirs(payload.project_dirs)),
            ),
        )
        connection.commit()

    return get_settings()


@app.get("/generated/{filename}")
def get_generated_file(filename: str) -> FileResponse:
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    candidates = [
        get_output_dir() / filename,
        GENERATED_DIR / filename,
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return FileResponse(path)

    raise HTTPException(status_code=404, detail="Generated file not found")


@app.get("/reference-assets/{filename}")
def get_reference_asset_file(filename: str) -> FileResponse:
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = REFERENCE_ASSET_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Reference asset not found")

    return FileResponse(path)


@app.post("/api/system/pick-directory")
def pick_directory() -> dict[str, str]:
    if sys.platform == "darwin":
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'POSIX path of (choose folder with prompt "选择文件夹")',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            if "-128" in result.stderr:
                return {"path": ""}
            raise HTTPException(status_code=500, detail="Folder picker failed to open")

        return {"path": result.stdout.strip()}

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as error:
        raise HTTPException(status_code=501, detail="Folder picker is not available on this platform") from error

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected_path = filedialog.askdirectory(title="选择文件夹")
    finally:
        root.destroy()

    return {"path": selected_path.strip()}


@app.post("/api/projects/save")
def save_to_project(payload: ProjectSavePayload) -> dict[str, str]:
    source = Path(payload.source_path)
    if not source.exists() or not source.is_file():
        raise HTTPException(status_code=404, detail="Source image not found")

    project_name = payload.project_name.strip()
    project = next(
        (item for item in get_project_dirs() if item["name"] == project_name),
        None,
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project folder not found")

    destination_dir = Path(project["path"])
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = get_available_destination(destination_dir / source.name)
    shutil.copy2(source, destination)

    return {
        "project_name": project["name"],
        "saved_path": str(destination),
    }


def get_available_destination(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate

    raise HTTPException(status_code=500, detail="Could not create a unique destination file")


@app.post("/api/jobs")
def create_job(payload: JobCreatePayload) -> dict[str, Any]:
    api_key = get_api_key(payload.model)
    normalized_payload = validate_job_payload(payload)
    job_id = f"job_{uuid.uuid4().hex}"
    prepared_payload, temp_asset_paths = prepare_provider_assets(job_id, normalized_payload)

    create_job_record(job_id, prepared_payload, temp_asset_paths)
    update_job_record(job_id, status="submitted", error_message=None)

    try:
        result_paths = submit_provider_job(job_id, api_key, prepared_payload)
    except ProviderError as exc:
        cleanup_job_temp_assets(job_id)
        update_job_record(job_id, status="failed", error_message=exc.message)
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        cleanup_job_temp_assets(job_id)
        update_job_record(job_id, status="failed", error_message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cleanup_job_temp_assets(job_id)

    update_job_record(
        job_id,
        status="completed",
        result_paths=result_paths,
        error_message=None,
    )

    row = get_job_record(job_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Job was created but could not be loaded")

    return serialize_job(row)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    row = get_job_record(job_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return serialize_job(row)


@app.get("/api/jobs")
def list_jobs() -> list[dict[str, Any]]:
    return [serialize_job_for_list(row) for row in list_job_records()]


def delete_job_by_id(job_id: str) -> dict[str, Any]:
    row = get_job_record(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    serialized = serialize_job(row)
    for result_path in serialized["result_paths"]:
        try:
            Path(result_path).unlink(missing_ok=True)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    delete_job_record(job_id)
    return {"status": "deleted", "id": job_id}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict[str, Any]:
    return delete_job_by_id(job_id)


@app.post("/api/jobs/{job_id}/delete")
def delete_job_via_post(job_id: str) -> dict[str, Any]:
    return delete_job_by_id(job_id)
