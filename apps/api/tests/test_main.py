from solo_api.main import _cors_origins


def test_cors_origins_include_configured_deployment_origins(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://solo.example.com, https://preview.example.com")
    monkeypatch.setenv("NEXTAUTH_URL", "https://solo-web.vercel.app")

    origins = _cors_origins()

    assert "http://localhost:3000" in origins
    assert "https://solo.example.com" in origins
    assert "https://preview.example.com" in origins
    assert "https://solo-web-beryl.vercel.app" in origins
