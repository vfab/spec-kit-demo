# Feature Specification: Testing Completion, CI/CD & Production Deployment

**Feature Branch**: `004-testing-deployment`
**Created**: 2026-03-24
**Status**: Draft
**Epic**: EPIC-06 (Tasks 6.6–6.15), EPIC-08 (Tasks 9–16), EPIC-09 (all tasks)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Merges Code and Gets Automated Feedback (Priority: P1)

A developer opens a pull request against the main branch. Within minutes, an automated CI pipeline runs the full test suite (unit, integration, security scan, and linting), reports pass/fail status on the PR, and blocks merging if any gate fails. The developer never has to manually trigger tests or chase down failures after a merge.

**Why this priority**: Automated PR gating is the foundation that makes all other quality guarantees enforceable. Without it, test coverage exists only on developer machines, not in the shared codebase.

**Independent Test**: Push a branch with a deliberate test failure, open a PR, and confirm the CI check turns red and prevents merge. Fix the failure, push again, and confirm the check turns green and the PR is unblocked.

**Acceptance Scenarios**:

1. **Given** a developer pushes a commit to any branch, **When** the push is received by the repository, **Then** a CI workflow starts automatically within 30 seconds.
2. **Given** the CI workflow is running, **When** any test in the suite fails, **Then** the workflow exits with a non-zero status, the PR check is marked as failed, and a summary of failing tests is available in the CI log.
3. **Given** all tests pass and coverage is at or above the configured threshold, **When** the CI workflow completes, **Then** the PR check is marked as passed and a coverage report summary is visible in the workflow run output.
4. **Given** the CI workflow runs, **When** security scanning (static analysis) detects a high-severity vulnerability, **Then** the workflow fails and the finding is reported in the CI output.
5. **Given** a scheduled nightly run of the full test suite, **When** the scheduled trigger fires, **Then** the workflow executes without manual intervention and results are recorded.

---

### User Story 2 - Developer Deploys to Staging with One Command (Priority: P1)

After CI passes on the main branch, a developer or automated process can deploy the application to a staging environment with a single action. The deployed staging app uses production-equivalent configuration (PostgreSQL, no debug mode, real static file serving) so that integration issues are caught before reaching production.

**Why this priority**: Staging acts as the final validation gate before production. An unreliable or manually operated staging environment causes defects to reach users.

**Independent Test**: Trigger a deployment to staging (manually or by merging to `main`), confirm the staging URL is reachable, log in with a test account, and verify the browsing → cart → checkout flow completes without errors.

**Acceptance Scenarios**:

1. **Given** a successful CI run on the `main` branch, **When** deployment to staging is triggered, **Then** the new version is deployed without downtime and the previous version continues serving traffic until health checks on the new version pass.
2. **Given** the staging deployment completes, **When** a smoke test is run against the staging URL, **Then** the home page, product listing, cart, and login pages all return HTTP 200.
3. **Given** the staging deployment completes, **When** `python manage.py check --deploy` is run against the staging configuration, **Then** no critical warnings are emitted.
4. **Given** a deployment fails (e.g., health check fails), **When** the failure is detected, **Then** the deployment is automatically rolled back to the previous stable version within 5 minutes.

---

### User Story 3 - Site Owner Deploys to Production and Monitors Health (Priority: P1)

A site owner or authorized operator can promote the staging release to production through a controlled process (requiring manual approval). After the production deployment, they can view real-time uptime status, receive alerts if the site goes down or errors spike, and access dashboards showing key health metrics.

**Why this priority**: Production deployments must be deliberate and observable. Surprise outages with no alerting directly damage the business.

**Independent Test**: Execute a production deployment (with required approval), confirm the production URL is healthy, then simulate a health-check failure by stopping the app and verifying an alert notification is sent within 5 minutes.

**Acceptance Scenarios**:

1. **Given** a release is ready for production, **When** the deployment approval step is triggered, **Then** it requires explicit human approval before proceeding, and the deployment cannot proceed if approval is denied.
2. **Given** the production deployment completes, **When** the health check endpoint is polled, **Then** it returns HTTP 200 with a valid response within 500ms.
3. **Given** the application is running in production, **When** the site becomes unreachable for more than 2 minutes, **Then** an alert is sent to the configured notification channel within 5 minutes of the outage starting.
4. **Given** the application is running, **When** an unhandled exception occurs, **Then** the error is captured with full stack trace and context in the error tracking system, and an alert is sent if the error rate exceeds the configured threshold.

---

### User Story 4 - Developer Validates Complete User Journeys via Browser Automation (Priority: P2)

A developer can run a suite of end-to-end browser automation tests that exercise the application through a real browser (headless), covering the primary user flows: browsing products, adding to cart, registering, logging in, and completing checkout. These tests run in CI on the staging environment and catch regressions that unit tests cannot.

**Why this priority**: The existing 153 unit/integration tests cover code paths but not rendered UI behavior. Browser automation closes this gap for critical checkout and account flows.

**Independent Test**: Run the E2E test suite against the local development server and confirm all primary journey tests pass (product browse → add to cart → checkout → order confirmation).

**Acceptance Scenarios**:

1. **Given** the E2E test suite, **When** tests run in headless mode against the application, **Then** at least the following journeys complete successfully: product browsing, cart add/remove, user registration, user login, and order placement.
2. **Given** the E2E suite runs, **When** a mobile viewport is configured, **Then** all primary flows are accessible without horizontal scroll or broken layouts.
3. **Given** the E2E tests are part of the CI pipeline, **When** a UI regression is introduced (e.g., a checkout button is removed), **Then** the relevant E2E test fails and reports a descriptive failure message.

---

### User Story 5 - Developer Measures Application Performance Under Load (Priority: P2)

A developer can run a load test that simulates concurrent users browsing products and placing orders, then review a report showing response time percentiles and throughput. The results are compared against defined performance targets to identify regressions before they reach production.

**Why this priority**: The application has no established performance baselines. Setting them now—before production traffic—ensures regressions are caught during development.

**Independent Test**: Run the load test scenario with 50 concurrent virtual users for 1 minute against the local server and confirm a performance report is generated showing p95 response times for the homepage, product list, and cart pages.

**Acceptance Scenarios**:

1. **Given** the load test scenario with 50 concurrent virtual users, **When** the test runs for 1 minute, **Then** p95 response time for the homepage is under 1 second and no requests return HTTP 5xx errors.
2. **Given** the load test results, **When** a performance report is generated, **Then** it includes request throughput, p50/p95/p99 response times, and error rate per endpoint.
3. **Given** a performance regression is introduced (e.g., an N+1 query added to the product list), **When** the load test is run, **Then** the p95 response time for the affected endpoint increases by more than 50%, making the regression detectable.

---

### User Story 6 - Security Engineer Runs Vulnerability Scan and Sees No High-Severity Findings (Priority: P2)

A security engineer or developer can run an automated security scan (static analysis + dependency vulnerability check) against the codebase and dependency list. The scan runs as part of CI and blocks merges that introduce new high-severity findings.

**Why this priority**: The application handles user accounts and financial transactions. Catching known vulnerability patterns automatically prevents the most common classes of security issues.

**Independent Test**: Run the security scan tools manually against the codebase and confirm the output shows zero high-severity findings. Introduce a known-bad pattern (e.g., `eval()` call), re-run, and confirm the scan detects and reports it.

**Acceptance Scenarios**:

1. **Given** the current codebase, **When** static security analysis is run, **Then** zero high-severity findings are reported.
2. **Given** the project's dependency list, **When** a dependency vulnerability check is run, **Then** any known CVEs with high or critical severity are reported and the CI step fails.
3. **Given** the CI pipeline, **When** a commit introduces a high-severity security finding, **Then** the security scan step fails and blocks the PR from merging.

---

### User Story 7 - Operator Performs Database Backup and Restore (Priority: P3)

An operator can trigger a manual database backup at any time and can restore from any retained backup within the defined retention window. The backup process is also automated to run daily without manual intervention.

**Why this priority**: Data is the most critical asset in an e-commerce application. Backup capability is a production-readiness requirement, even if it is less frequently exercised than CI/CD.

**Independent Test**: Trigger a manual backup, verify the backup file is created and accessible, then restore to a fresh database and confirm record counts match the original.

**Acceptance Scenarios**:

1. **Given** the production database, **When** a backup is triggered (manually or by schedule), **Then** a backup artifact is created and stored in the designated storage location within 15 minutes.
2. **Given** a stored backup, **When** a restore is performed, **Then** the restored database contains all records from the time of the backup and all foreign key relationships are intact.
3. **Given** the automated backup schedule, **When** the scheduled time arrives, **Then** a backup runs without manual intervention and the operator receives confirmation (or failure alert).

---

### Edge Cases

- What happens when a deployment is triggered while a migration is still running? (Deployment waits for migration to complete before switching traffic; partial migration state must not serve user requests.)
- What happens when a browser automation test fails because of a timing issue (flaky test), not a real regression? (Tests must use explicit waits, not fixed sleeps; flaky tests are tracked and must be quarantined or fixed.)
- What happens if the health check endpoint itself is slow due to a database issue? (Health check must have a strict timeout; a response exceeding the timeout is treated as failure.)
- What happens when a new migration cannot be reversed? (Irreversible migrations must be flagged and deployment runbooks updated to note they cannot be rolled back automatically.)
- What happens if a security scan produces false positives? (False-positive rules may be suppressed with inline comments and documented justification; suppression without justification is not permitted.)
- What happens when the backup storage location is full or unavailable? (Backup job must fail with an alert rather than silently skip the backup.)
- What happens when load testing is run against production accidentally? (Load tests must be blocked from targeting the production environment by configuration; the staging URL is the only permitted target.)

## Requirements *(mandatory)*

### Functional Requirements

#### Browser Automation Testing (Tasks 6.6, EPIC-08 Tasks 9–10, 14)

- **FR-001**: The project MUST include a browser automation test suite using Playwright (preferred) or Selenium, configured to run in headless mode.
- **FR-002**: The automation suite MUST cover the following user journeys with at least one test each: product browsing and search, add-to-cart and cart management, user registration, user login/logout, and order placement through checkout.
- **FR-003**: The E2E test suite MUST support execution against a configurable base URL so that the same tests can run against both local development and staging environments.
- **FR-004**: All browser automation tests MUST use explicit waits (wait for element visibility or network idle) rather than fixed sleep delays.
- **FR-005**: The E2E test suite MUST be executable in CI (headless mode, no display server required).
- **FR-006**: The test runner MUST produce a structured test result report (JUnit XML or equivalent) suitable for CI result parsing.

#### Performance & Load Testing (Tasks 6.7, EPIC-08 Task 11)

- **FR-007**: The project MUST include a load testing configuration using Locust defining at least the following scenarios: homepage browse, product list page, product detail page, add-to-cart (AJAX), and cart page.
- **FR-008**: The load test configuration MUST be parameterizable for user count, spawn rate, and target host via command-line arguments or environment variables.
- **FR-009**: Load tests MUST be blocked from running against the production environment by configuration guard (e.g., an environment variable check or allowlist of permitted hosts).
- **FR-010**: After a load test run, a performance report MUST be generated containing: request throughput, p50/p95/p99 response times per endpoint, and error rate.
- **FR-011**: Performance baselines MUST be documented in the project (initial measured values for key endpoints) so future runs can be compared against them.

#### Security Testing (Tasks 6.8, EPIC-08 Tasks 12–13)

- **FR-012**: The CI pipeline MUST run Bandit (Python static security analysis) on every CI run and fail if any HIGH or MEDIUM-severity finding is detected (per project constitution: `bandit -ll` threshold, zero medium/high).
- **FR-013**: The CI pipeline MUST run Safety (or pip-audit) to check installed dependencies against known CVE databases and fail if any critical or high CVE is found.
- **FR-014**: The test suite MUST include explicit security regression tests for: CSRF protection on all POST endpoints, authentication required on all authenticated views, and absence of sensitive data in HTTP error responses (no stack traces in production mode).
- **FR-015**: The test suite MUST verify that security headers (X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, Strict-Transport-Security) are present in HTTP responses.
- **FR-016**: Mock and patch tests MUST cover: email sending (no real emails sent during tests), payment processing (no real payment calls), and file upload handling (no real disk writes where avoidable).

#### Application Monitoring & Alerting (Tasks 6.9, 6.13, EPIC-09 Tasks 11, 15)

- **FR-017**: The application MUST expose a `/health/` endpoint that returns HTTP 200 and a JSON response `{"status": "ok"}` when the application and database connections are healthy, and HTTP 503 when unhealthy.
- **FR-018**: Uptime monitoring MUST be configured using a free monitoring service (UptimeRobot or equivalent) to poll the health endpoint at least every 5 minutes and notify on failure.
- **FR-019**: The application MUST use structured logging (JSON format) in production, with log records including: timestamp, log level, request ID (if applicable), and message.
- **FR-020**: Unhandled exceptions in production MUST be captured with full context (request path, user ID anonymized, full stack trace) and persisted in the structured log stream. A third-party error tracking SDK (e.g., Sentry) is not required; Django's built-in logging integration emitting JSON to stdout (FR-019) satisfies this requirement. Rate-threshold alerting is deferred to a future enhancement and is not required for initial go-live.
- **FR-021**: No external error tracking SDK is used; this requirement is satisfied trivially. Test settings MUST NOT configure any external reporting endpoint.

#### CI/CD Pipeline (Tasks 6.11, EPIC-09 Tasks 1, 8, 9, 14)

- **FR-022**: The repository MUST contain a GitHub Actions workflow file at `.github/workflows/ci.yml` that runs on `push` to any branch and on `pull_request` to `main`.
- **FR-023**: The CI workflow MUST execute the following stages in order, with each stage depending on the previous: (1) Code Quality (linting, formatting), (2) Security Scan, (3) Unit & Integration Tests with coverage, (4) Browser E2E Tests.
- **FR-024**: The CI workflow MUST fail fast: if any stage fails, subsequent stages MUST NOT run (to save CI minutes).
- **FR-025**: The CI workflow MUST enforce the configured code coverage threshold (**95% minimum**, per project constitution — stricter than the test-suite's current 97% baseline); the pipeline MUST fail if coverage drops below this value.
- **FR-026**: The CI workflow MUST use GitHub Secrets for all sensitive configuration values (database credentials, secret key, deployment credentials). No secrets MUST be hard-coded in workflow files.
- **FR-027**: The repository MUST contain a separate GitHub Actions workflow at `.github/workflows/deploy.yml` that handles deployment to staging (automatic on merge to `main`) and to production (requires manual approval).
- **FR-028**: The CI workflow MUST generate and upload a coverage report artifact (HTML) and a test results artifact (JUnit XML) on each run.
- **FR-029**: The CI workflow MUST support running tests against the project's officially supported Python versions (minimum: 3.11 and 3.12) via a matrix strategy.

#### Production Environment Configuration (Tasks 6.10, EPIC-09 Tasks 2, 5, 14)

- **FR-030**: The project MUST include `ecommerce_site/settings_production.py` (consistent with the existing `ecommerce_site/settings_test.py` structure) that: uses PostgreSQL (via `DATABASE_URL` environment variable), sets `DEBUG=False`, enables `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and configures `ALLOWED_HOSTS` from an environment variable.
- **FR-031**: Static files MUST be served via `whitenoise` (or equivalent) in production without requiring a separate web server for static content.
- **FR-032**: All environment-sensitive configuration values MUST be loaded from environment variables; the `.env.production.example` file MUST document every required production variable.
- **FR-033**: Secrets management MUST use GitHub Secrets for CI/CD variables and the deployment platform's native secrets store for runtime secrets. No plaintext secrets MUST appear in committed files.

#### Docker & Deployment Infrastructure (Tasks 6.12, EPIC-09 Tasks 3, 4, 6)

- **FR-034**: The project MUST include an optimized production `Dockerfile` using a multi-stage build: a build stage (installs dependencies) and a runtime stage (copies only necessary artifacts, runs as a non-root user).
- **FR-035**: The `Dockerfile` MUST include a `HEALTHCHECK` instruction pointing to the `/health/` endpoint.
- **FR-036**: The `docker-compose.yml` MUST be suitable for local development and include services for the Django app and PostgreSQL. It MUST NOT be used for production deployment directly.
- **FR-037**: Database migrations MUST run automatically as part of the deployment process before the new application container starts serving traffic.
- **FR-038**: The deployment process MUST implement a zero-downtime strategy (e.g., rolling update or blue-green switch) so that users experience no interruption during a deployment.

#### Maintenance, Operations & Backup (Tasks 6.14, EPIC-09 Tasks 10, 12, 13)

- **FR-039**: An automated database backup job MUST run on a daily schedule, storing backup artifacts in a durable location outside the application server, with a minimum 7-day retention period.
- **FR-040**: The project MUST include a documented runbook (`docs/runbooks/deployment.md` or equivalent) covering: how to trigger a deployment, how to roll back a deployment, how to restore from backup, and how to run database migrations manually.
- **FR-041**: The deployment pipeline MUST include an automated rollback trigger: if post-deployment health checks fail within 5 minutes, the system MUST automatically revert to the previous deployment without human intervention.
- **FR-042**: A deployment promotion flow MUST be implemented: code flows `development → staging → production`, and promotion from staging to production MUST require a manual approval gate in the CI/CD pipeline.

#### Production Validation (Task 6.15, EPIC-09 Tasks 8–9)

- **FR-043**: Before the go-live milestone, a final security audit MUST be conducted covering: OWASP Top 10 checklist, dependency vulnerability report (zero high/critical), and Django deployment checklist (`manage.py check --deploy` with no critical warnings).
- **FR-044**: A final load test MUST be run against the staging environment simulating the expected initial production traffic profile and MUST confirm that all performance targets defined in the Success Criteria are met.
- **FR-045**: A go-live checklist document MUST be completed and signed off, confirming: all monitoring alerts are configured, backup job is verified, rollback procedure is tested, SSL certificate is valid, and all smoke tests pass.

### Key Entities

- **CI Workflow**: A GitHub Actions workflow definition that orchestrates test, scan, and deploy jobs; produces coverage and test artifacts.
- **Deployment Environment**: A named runtime context (staging or production) with its own configuration, database, and infrastructure; promoted to sequentially.
- **Health Check Endpoint**: An application route (`/health/`) that reports the live health status of the application and its dependencies.
- **Browser Automation Test**: An executable test that controls a real browser instance (headless) to simulate a user interacting with the application.
- **Load Test Scenario**: A Locust configuration defining virtual user behavior (which pages to visit, what actions to take) used to measure performance under concurrency.
- **Backup Artifact**: A database dump file stored durably outside the application server, recoverable within the retention window.
- **Runbook**: A human-readable document describing step-by-step procedures for operational tasks (deploy, rollback, restore).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every pull request to the `main` branch triggers an automated CI run that completes within 10 minutes and produces a pass/fail result visible on the PR.
- **SC-002**: The CI pipeline blocks any merge that drops code coverage below **95%** (project constitution floor) or introduces a Bandit HIGH or MEDIUM-severity security finding.
- **SC-003**: A deployment to staging completes within 15 minutes of merging to `main`, with zero manual steps required by the developer.
- **SC-004**: A production deployment requires manual approval but otherwise completes within 15 minutes of approval and causes zero downtime (measured by continuous health-check polling during the deployment).
- **SC-005**: If a production deployment fails health checks, the system automatically rolls back to the previous stable version within 5 minutes.
- **SC-006**: The health check endpoint returns HTTP 200 under normal operating conditions and HTTP 503 within 10 seconds of a database connection failure.
- **SC-007**: Uptime monitoring sends an alert within 5 minutes of an outage starting.
- **SC-008**: The browser automation suite covers at least 5 primary user journeys and completes in under 5 minutes in CI.
- **SC-009**: Under a load of 50 concurrent virtual users on the staging environment, the homepage p95 response time is under 1 second and the error rate is under 1%.
- **SC-010**: The static security analysis tool reports zero HIGH or MEDIUM-severity Bandit findings on the codebase and zero high/critical CVEs in project dependencies at the time of go-live.
- **SC-011**: A full database restore from a recent backup can be completed and verified within 30 minutes.
- **SC-012**: `python manage.py check --deploy` produces no critical warnings on the production configuration.

## Assumptions

- The project's primary deployment platform is **Fly.io** (free tier, 3 shared VMs). Railway and Render are explicitly not used: Railway has no genuine free tier; Render's free tier has cold-start issues. Any platform supporting Docker containers and rolling deploys with health-check gating would satisfy the requirements.
- The GitHub repository is public or under a GitHub plan that provides GitHub Actions minutes sufficient for the CI pipeline. If the repository is private, Actions minutes budgets apply and should be monitored.
- Browser automation tests use Chrome (headless) in CI via a GitHub Actions runner (which has Chrome pre-installed). Firefox and Edge cross-browser testing is deferred to a future enhancement.
- Performance baselines are established by measuring the application under typical development conditions (SQLite or a local PostgreSQL instance). Staging benchmarks against PostgreSQL are the authoritative baselines.
- **Error tracking**: No third-party error tracking service (Sentry) is used. Django structured logging (JSON to stdout, FR-019/FR-020) captures all unhandled exceptions. **Uptime monitoring**: UptimeRobot free tier polls `/health/` every 5 minutes (FR-018) and is required for initial production operation.
- EPIC-05 (Frontend Templates) is sufficiently complete that browser automation tests can exercise real rendered pages, not placeholder stubs.
- Tasks 6.1–6.5 are complete: pytest configuration, unit tests, view/form tests, integration tests, and basic performance/security tests already exist and pass with 97% coverage (153 tests).
