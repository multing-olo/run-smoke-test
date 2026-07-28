# Smoke-test strategies

Use only the section matching the discovered target. Confirm commands against
project instructions before execution.

## Local application

1. Verify the declared runtime and package manager.
2. Prefer the project's documented install, build, and start commands.
3. Record the exact started process and apply a startup timeout.
4. Wait for an explicit readiness signal; do not equate an open port with
   application readiness when a health endpoint exists.
5. Run one representative functional check.
6. Scan startup and request logs.
7. Stop only the process created by the smoke run.

## HTTP API

Prefer:

- a readiness or health endpoint;
- one critical read-only endpoint;
- explicit status, latency, content-type, and minimum body assertions;
- a test identity when authentication is required.

Avoid using `401`, `403`, or a generic homepage response as proof that the
application is healthy unless that behavior is the stated assertion.

## Web UI

Verify:

1. initial page load without fatal console or network errors;
2. one critical, low-side-effect user path;
3. an observable final state, not only a successful click;
4. screenshots at the assertion boundary when available.

Use stable roles, labels, or test identifiers. Do not rely on fragile visual
coordinates. Treat CAPTCHA, MFA, SSO approval, and subjective visual quality as
possible manual or blocked checkpoints.

## Container or Compose project

Confirm image build or pull, container state, health state, exposed ports, and
critical service logs. Distinguish a running container from a ready
application. Record the exact project or container identities before cleanup.

For multiple services, validate required dependencies before the entry service.

## Node project

Read `package.json` scripts and the matching lockfile. Use the lockfile's
package manager. Common candidates include `start`, `dev`, `serve`, and
`preview`, but project documentation takes precedence.

Do not run arbitrary lifecycle scripts merely because they exist.

## Python project

Identify the declared environment and entry point from `pyproject.toml`,
requirements files, framework configuration, or project documentation. Prefer
the project-managed interpreter and command.

For ASGI/WSGI applications, verify the documented application object and port
instead of guessing solely from filenames.

## Java project

Identify Maven or Gradle and use the project wrapper when present. Confirm the
actual framework and task before using common candidates such as
`spring-boot:run` or `bootRun`.

Account for slower startup and use a readiness signal rather than a fixed sleep.

## Deployed environment

Attach to the supplied endpoint; do not redeploy or restart services unless
explicitly requested. Confirm whether the environment is test, staging, or
production and apply the matching side-effect policy.

Check a public or authenticated health path plus one representative,
authorized, low-side-effect functional path.
