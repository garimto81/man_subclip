"""
Pytest 설정 및 공통 fixtures
"""
import pytest


def pytest_configure(config):
    """pytest 마커 등록"""
    config.addinivalue_line(
        "markers", "external: 외부 서비스 (Cloud Run) 테스트"
    )
    config.addinivalue_line(
        "markers", "slow: 느린 테스트 (성능 테스트)"
    )
