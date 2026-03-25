"""
Shared configuration and fixtures for Playwright E2E tests.

All tests in this directory are automatically marked with @pytest.mark.e2e.
The live_server fixture from pytest-django is used to start a Django server
for the E2E tests, avoiding port conflicts with a separate manage.py process.
"""

import pytest


def pytest_collection_modifyitems(items):
    """Auto-mark all items in the e2e directory with the e2e marker."""
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Override default browser context with desktop viewport."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Launch browser headless with no slow-mo."""
    return {
        **browser_type_launch_args,
        "headless": True,
        "slow_mo": 0,
    }


@pytest.fixture(scope="session")
def base_url(live_server):
    """
    Provide the base URL for E2E tests.

    Uses pytest-django's live_server fixture which starts a real Django
    server on a random port. When --base-url is passed via CLI, Playwright
    uses that instead; otherwise live_server.url is used as the base.
    """
    return live_server.url


@pytest.fixture
def mobile_page(page, browser):
    """
    Fixture providing a Playwright page with iPhone SE portrait viewport.

    Use this fixture in tests that verify mobile responsiveness.
    """
    context = browser.new_context(
        viewport={"width": 375, "height": 667},
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 "
            "Mobile/15E148 Safari/604.1"
        ),
    )
    mobile_page = context.new_page()
    yield mobile_page
    context.close()
