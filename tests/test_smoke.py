def test_environment_baseline():
    """Smoke test verifying test runner and baseline configuration."""
    from src.core.config import ENVIRONMENT

    assert ENVIRONMENT in ["development", "testing", "production"]
