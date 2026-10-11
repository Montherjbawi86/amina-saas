"""
إعدادات التطبيق المركزية
متوافق مع Python 3.8
"""
import os
from pathlib import Path
from typing import Tuple, List
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_NAME: str = os.getenv("APP_NAME", "أمينة SaaS")
    APP_VERSION: str = "0.1.0"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()


def validate_config() -> Tuple[bool, List[str]]:
    errors = []
    if not settings.SUPABASE_URL:
        errors.append("ERROR: SUPABASE_URL missing in .env")
    elif not settings.SUPABASE_URL.startswith("https://"):
        errors.append("ERROR: SUPABASE_URL must start with https://")
    elif not settings.SUPABASE_URL.endswith(".supabase.co"):
        errors.append("ERROR: SUPABASE_URL must end with .supabase.co")
    elif "/rest/" in settings.SUPABASE_URL or settings.SUPABASE_URL.endswith("/"):
        errors.append("ERROR: SUPABASE_URL must not contain /rest/")

    if not settings.SUPABASE_SERVICE_KEY:
        errors.append("ERROR: SUPABASE_SERVICE_KEY missing in .env")
    elif not settings.SUPABASE_SERVICE_KEY.startswith("eyJ"):
        errors.append("ERROR: SUPABASE_SERVICE_KEY must start with eyJ")

    if settings.is_production and not settings.GROQ_API_KEY:
        errors.append("WARNING: GROQ_API_KEY missing (required in production)")

    return (len(errors) == 0, errors)


if __name__ == "__main__":
    print("=" * 50)
    print("APP: {} v{}".format(settings.APP_NAME, settings.APP_VERSION))
    print("ENV: {}".format(settings.APP_ENV))
    print("=" * 50)
    print("SUPABASE_URL        : {}".format(settings.SUPABASE_URL))
    if settings.SUPABASE_ANON_KEY:
        print("SUPABASE_ANON_KEY   : {}...".format(settings.SUPABASE_ANON_KEY[:20]))
    else:
        print("SUPABASE_ANON_KEY   : MISSING")
    if settings.SUPABASE_SERVICE_KEY:
        print("SUPABASE_SERVICE_KEY: {}...".format(settings.SUPABASE_SERVICE_KEY[:20]))
    else:
        print("SUPABASE_SERVICE_KEY: MISSING")
    print("GROQ_API_KEY        : {}".format("OK" if settings.GROQ_API_KEY else "EMPTY"))
    print("=" * 50)
    ok, errors = validate_config()
    if ok:
        print("OK: all required settings present")
    else:
        print("ERRORS:")
        for e in errors:
            print("   " + e)
