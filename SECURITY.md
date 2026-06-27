# Security Policy

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions, or pull
requests.** Public disclosure before a fix puts every user at risk.

Instead, report privately through GitHub's built-in **Private Vulnerability Reporting**:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability**.
3. Fill in the advisory form with as much detail as you can — affected version/commit, steps to
   reproduce, impact, and (if you have one) a suggested fix.

Evolve is a small, best-effort open-source project — there's **no guaranteed response time**, and a fix
may take a while depending on availability. We do read every report and will get to it as soon as we
reasonably can, and we'll coordinate disclosure timing with you when a fix is ready. Please allow
reasonable time before any public disclosure.

## Supported versions

Evolve is early-stage software (`v0.1.0`). Security fixes are made against the **latest `main`** — there
are no backported releases yet.

## What we're especially interested in

Evolve runs an autonomous agent swarm that reads your issues, executes code, and holds tokens, so its
security model matters. Reports we particularly want:

- **Secret / credential exposure** — anything that could leak a configured secret
  (`EVOLVE_DECIDE_TOKEN`, `EVOLVE_SERVICE_TOKEN`, `GITHUB_TOKEN`, the test host's read token, etc.).
- **Gate / authorization bypass** — any path by which the brain (which holds only a *service* token) or
  an agent could **decide its own gate**, or by which a non-operator could approve a gate. The
  two-token split (only the operator's machine holds the decide-token) is a core safety property.
- **Prompt injection** — a crafted GitHub issue or repository content that causes an agent to take an
  unintended action. The `manual` intake mode and the security-screen agent are the defenses; bypasses
  of them are in scope.
- **Command / code injection** in the engine, the adapter binding, or the dashboard.

**Out of scope:** vulnerabilities in *your own* product code that an Evolve instance manages (report
those to that project), and issues that require an already-compromised operator machine.

## Secrets & configuration

Evolve keeps all secrets and operator-specific configuration in **gitignored** files (`.env`,
`CHARTER.md`, `evolve.repos.yaml`, `adapters/<name>/`). These must never be committed. If you find a
committed secret anywhere in this repository or its history, please report it through the private flow
above rather than opening an issue.
