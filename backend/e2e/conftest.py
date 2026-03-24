from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Callable, Iterator

import pytest
import requests
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


@dataclass
class E2EConfig:
    frontend_url: str
    backend_url: str
    headless: bool
    slow_mo_ms: int
    admin_secret: str | None
    timeout_ms: int


@dataclass
class TestUser:
    username: str
    password: str
    invite_code: str


def _generate_test_user(
    http_client: requests.Session,
    e2e_config: E2EConfig,
    prefix: str = "e2e",
) -> TestUser:
    response = http_client.post(f"{e2e_config.backend_url}/admin/invite", timeout=30)
    response.raise_for_status()
    invite_code = response.json()["invite_code"]

    suffix = uuid.uuid4().hex[:8]
    generated_secret = uuid.uuid4().hex
    return TestUser(
        username=f"{prefix}_{suffix}",
        password=generated_secret,
        invite_code=invite_code,
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="session")
def e2e_config() -> E2EConfig:
    return E2EConfig(
        frontend_url=os.getenv("E2E_FRONTEND_URL", "http://localhost:5173"),
        backend_url=os.getenv("E2E_BACKEND_URL", "http://localhost:8000"),
        headless=_env_bool("E2E_HEADLESS", True),
        slow_mo_ms=int(os.getenv("E2E_SLOW_MO_MS", "0")),
        admin_secret=os.getenv("E2E_ADMIN_SECRET"),
        timeout_ms=int(os.getenv("E2E_TIMEOUT_MS", "90000")),
    )


@pytest.fixture(scope="session")
def http_client(e2e_config: E2EConfig) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    if e2e_config.admin_secret:
        session.headers.update({"X-Admin-Secret": e2e_config.admin_secret})
    return session


@pytest.fixture(scope="session")
def playwright_instance() -> Iterator[Playwright]:
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture
def browser(playwright_instance: Playwright, e2e_config: E2EConfig) -> Iterator[Browser]:
    browser = playwright_instance.chromium.launch(
        headless=e2e_config.headless,
        slow_mo=e2e_config.slow_mo_ms,
    )
    try:
        yield browser
    finally:
        browser.close()


@pytest.fixture
def context(browser: Browser, e2e_config: E2EConfig) -> Iterator[BrowserContext]:
    context = browser.new_context()
    context.set_default_timeout(e2e_config.timeout_ms)
    context.set_default_navigation_timeout(e2e_config.timeout_ms)
    try:
        yield context
    finally:
        context.close()


@pytest.fixture
def page(context: BrowserContext) -> Iterator[Page]:
    page = context.new_page()
    yield page


@pytest.fixture(scope="session")
def test_user(http_client: requests.Session, e2e_config: E2EConfig) -> TestUser:
    return _generate_test_user(http_client, e2e_config, prefix="e2e")


@pytest.fixture
def make_test_user(
    http_client: requests.Session,
    e2e_config: E2EConfig,
) -> Callable[[str], TestUser]:
    def _make(prefix: str = "e2e") -> TestUser:
        return _generate_test_user(http_client, e2e_config, prefix=prefix)

    return _make
