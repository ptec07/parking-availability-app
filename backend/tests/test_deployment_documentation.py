from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT_DOC = PROJECT_ROOT / "DEPLOYMENT.md"


def test_deployment_document_exists_and_covers_required_sections():
    content = DEPLOYMENT_DOC.read_text(encoding="utf-8")

    required_sections = [
        "# 주차될까 배포 가이드",
        "## 현재 배포 상태",
        "## 필요한 환경변수",
        "## API 키 발급처",
        "## 로컬 실행법",
        "## Render 백엔드 배포",
        "## Vercel 프론트엔드 배포",
        "## 배포 후 헬스체크",
        "## 보안 주의사항",
        "## 남은 배포 준비 작업",
    ]
    for section in required_sections:
        assert section in content


def test_deployment_document_keeps_secrets_as_placeholders():
    content = DEPLOYMENT_DOC.read_text(encoding="utf-8")

    assert "SEOUL_OPEN_API_KEY" in content
    assert "KAKAO_REST_API_KEY" in content
    assert "KAKAO_JAVASCRIPT_KEY" in content
    assert "[REDACTED]" in content
    assert "KakaoAK {api_key}" in content
    assert "sample" in content


def test_deployment_document_matches_current_app_contract():
    content = DEPLOYMENT_DOC.read_text(encoding="utf-8")

    assert "uvicorn app.main:app" in content
    assert "/api/health" in content
    assert "/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000" in content
    assert "PARKING_DB_PATH" in content
    assert "PARKING_SEED_DEMO_DATA" in content
    assert "VITE_API_BASE_URL" in content
