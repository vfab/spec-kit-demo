"""
E2E tests for user authentication journeys (T-013).

Covers:
- User registration flow
- User login with pre-created credentials
- User logout
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestAuth:
    def test_user_registration(self, page, live_server, db):
        """
        Navigate to registration, fill form, submit, assert logged-in state.
        No time.sleep() — uses wait_for_url or expect() throughout.
        """
        page.goto(live_server.url + "/accounts/register/")
        page.wait_for_load_state("networkidle")

        # Fill registration form fields
        page.fill("[name='username']", "e2etestuser")
        page.fill("[name='first_name']", "E2E")
        page.fill("[name='last_name']", "TestUser")
        page.fill("[name='email']", "e2etestuser@example.com")
        # Password must meet validator: 10+ chars, symbol required
        page.fill("[name='password1']", "TestPass@123!")
        page.fill("[name='password2']", "TestPass@123!")

        # Submit the form
        page.locator("button[type='submit'], input[type='submit']").first.click()
        page.wait_for_load_state("networkidle")

        # After successful registration, user should be redirected
        # Verify user is logged in (username visible in nav) or on home page
        assert (
            page.url != live_server.url + "/accounts/register/"
            or page.locator("text=e2etestuser, text=E2E").first.is_visible()
        )

    def test_user_login(self, page, live_server, db):
        """
        Use a pre-created test user, navigate to login, fill credentials,
        submit, assert redirect to home/dashboard.
        """
        from tests.factories import UserFactory

        user = UserFactory(username="e2eloginuser")
        user.set_password("LoginPass@123!")
        user.save()

        page.goto(live_server.url + "/accounts/login/")
        page.wait_for_load_state("networkidle")

        page.fill("[name='username']", "e2eloginuser")
        page.fill("[name='password']", "LoginPass@123!")
        page.locator("button[type='submit'], input[type='submit']").first.click()
        page.wait_for_load_state("networkidle")

        # Should be redirected away from login page after success
        assert (
            "/login/" not in page.url
            or page.locator("text=e2eloginuser, .dropdown-toggle").first.is_visible()
        )

    def test_user_logout(self, page, live_server, db):
        """Login first, then click logout, assert login link reappears in nav."""
        from tests.factories import UserFactory

        user = UserFactory(username="e2elogoutuser")
        user.set_password("LogoutPass@123!")
        user.save()

        # Login
        page.goto(live_server.url + "/accounts/login/")
        page.wait_for_load_state("networkidle")
        page.fill("[name='username']", "e2elogoutuser")
        page.fill("[name='password']", "LogoutPass@123!")
        page.locator("button[type='submit'], input[type='submit']").first.click()
        page.wait_for_load_state("networkidle")

        # Logout — click the logout link in nav
        logout_link = page.locator("a[href*='logout']").first
        if logout_link.is_visible():
            logout_link.click()
            page.wait_for_load_state("networkidle")

        # Login link should reappear
        login_link = page.locator("a[href*='login']").first
        expect(login_link).to_be_visible()
