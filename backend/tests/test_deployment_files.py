from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"


def test_backend_requirements_pin_runtime_dependencies():
    requirements = (BACKEND_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "fastapi" in requirements
    assert "uvicorn" in requirements
    assert "httpx" in requirements


def test_render_blueprint_matches_backend_contract():
    render_yaml = yaml.safe_load((PROJECT_ROOT / "render.yaml").read_text(encoding="utf-8"))

    service = render_yaml["services"][0]
    assert service["type"] == "web"
    assert service["name"] == "parking-availability-backend"
    assert service["runtime"] == "python"
    assert service["rootDir"] == "backend"
    assert service["buildCommand"] == "pip install -r requirements.txt"
    assert service["startCommand"] == "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    assert service["healthCheckPath"] == "/api/health"
    env_keys = {env_var["key"] for env_var in service["envVars"]}
    assert {
        "PORT",
        "PARKING_DB_PATH",
        "PARKING_SEED_DEMO_DATA",
        "SEOUL_OPEN_API_KEY",
        "KAKAO_REST_API_KEY",
        "FRONTEND_ORIGIN",
    } <= env_keys


def test_vercel_config_serves_vite_spa():
    vercel_json = yaml.safe_load((PROJECT_ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8"))

    assert vercel_json["version"] == 2
    assert vercel_json["outputDirectory"] == "dist"
    assert {"source": "/(.*)", "destination": "/index.html"} in vercel_json["rewrites"]
