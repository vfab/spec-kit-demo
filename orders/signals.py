"""Signal handlers for the orders app.

Cart migration on login is handled in accounts.views (CustomLoginView and
RegisterView) rather than a signal, because Django rotates the session key
via cycle_key() *before* user_logged_in fires, making the pre-login session
key inaccessible from within a signal handler.  The views capture the old
session key before calling login() / super().form_valid().
"""
