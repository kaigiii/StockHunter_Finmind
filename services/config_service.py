import os
from pydantic import BaseModel
from fastapi import HTTPException
from dotenv import load_dotenv

class SettingsUpdate(BaseModel):
    db_host: str
    db_port: str
    db_name: str
    db_user: str
    db_password: str
    finmind_token: str
    max_workers: int
    api_max_calls: int
    api_wait_402: int
    api_retry_delay: int
    db_pool_min: int
    db_pool_max: int
    log_level: str
    export_dir: str
    default_start_date: str
    api_rate_limit_action: str = "stop"

class ConfigService:
    def __init__(self):
        self.env_path = ".env"
        load_dotenv(self.env_path)

    def get_settings(self):
        return {
            "db_host": os.getenv("DB_HOST", "localhost"),
            "db_port": os.getenv("DB_PORT", "5432"),
            "db_name": os.getenv("DB_NAME", ""),
            "db_user": os.getenv("DB_USER", ""),
            "db_password": "*" * 8,
            "finmind_token": os.getenv("FINMIND_API_TOKEN_1", ""),
            "max_workers": int(os.getenv("MAX_WORKERS", 5)),
            "api_max_calls": int(os.getenv("API_MAX_CALLS_PER_HOUR", 300)),
            "api_wait_402": int(os.getenv("API_WAIT_TIME_402", 600)),
            "api_retry_delay": int(os.getenv("API_RETRY_DELAY", 5)),
            "db_pool_min": int(os.getenv("DB_POOL_MIN", 1)),
            "db_pool_max": int(os.getenv("DB_POOL_MAX", 20)),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "export_dir": os.getenv("EXPORT_DIR", "csv_exports"),
            "default_start_date": os.getenv("DEFAULT_START_DATE", "2020-01-01"),
            "api_rate_limit_action": os.getenv("API_RATE_LIMIT_ACTION", "stop")
        }

    def update_settings(self, settings: SettingsUpdate):
        try:
            lines = []
            if os.path.exists(self.env_path):
                with open(self.env_path, "r") as f:
                    lines = f.readlines()
            
            new_configs = {
                "DB_HOST": settings.db_host,
                "DB_PORT": settings.db_port,
                "DB_NAME": settings.db_name,
                "DB_USER": settings.db_user,
                "MAX_WORKERS": str(settings.max_workers),
                "FINMIND_API_TOKEN_1": settings.finmind_token,
                "API_MAX_CALLS_PER_HOUR": str(settings.api_max_calls),
                "API_WAIT_TIME_402": str(settings.api_wait_402),
                "API_RETRY_DELAY": str(settings.api_retry_delay),
                "DB_POOL_MIN": str(settings.db_pool_min),
                "DB_POOL_MAX": str(settings.db_pool_max),
                "LOG_LEVEL": settings.log_level,
                "EXPORT_DIR": settings.export_dir,
                "DEFAULT_START_DATE": settings.default_start_date,
                "API_RATE_LIMIT_ACTION": settings.api_rate_limit_action
            }
            
            if settings.db_password != "*" * 8:
                new_configs["DB_PASSWORD"] = settings.db_password

            updated_keys = set()
            new_lines = []
            for line in lines:
                stripped_line = line.strip()
                if "=" in stripped_line and not stripped_line.startswith("#"):
                    key = stripped_line.split("=")[0].strip()
                    if key in new_configs:
                        new_lines.append(f"{key}={new_configs[key]}\n")
                        updated_keys.add(key)
                        continue
                new_lines.append(line)
            
            # Add missing keys
            for key, val in new_configs.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={val}\n")
            
            with open(self.env_path, "w") as f:
                f.writelines(new_lines)
                
            # Update memory
            for key, val in new_configs.items():
                os.environ[key] = val
                
            return {"status": "success", "message": "設定已儲存，部分變更可能需要重啟伺服器才會生效"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"儲存失敗: {str(e)}")
