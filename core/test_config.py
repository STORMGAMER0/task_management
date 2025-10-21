# Test script (test_config.py)
from core.config import settings

print("✅ Configuration loaded successfully!")
print(f"Database: {settings.database_url}")
print(f"Environment: {settings.environment}")
print(f"Debug mode: {settings.debug}")
print(f"CORS origins: {settings.cors_origins_list}")
print(f"Is production? {settings.is_production}")