# Contributing to CyberGems

Thanks for taking the time to help. CyberGems builds free, privacy-first Windows apps under GPLv3: no ads, no telemetry, no accounts, no cloud lock-in.

This guide applies to every repository in this account. A repository that ships its own `CONTRIBUTING.md` takes precedence over this one.

## Before you write code

- **Found a bug?** Open an issue with the bug report template. Include the app version, your Windows version and the steps that reproduce it.
- **Planning a large change?** Open an issue first and describe the problem and your proposed approach. It is much cheaper to agree on the direction before you write the patch.
- **Small fixes** (typos, broken links, an obvious one-line bug) can go straight to a pull request.

## Where the code lives

Each app has its own repository. Its `README.md` explains how to build and run it locally, and its wiki holds the longer notes. There is no monorepo: pick the repository of the app you want to change.

## Pull requests

- One logical change per pull request. Keep the diff reviewable.
- Explain **why** in the description, not only what changed. Link the issue it closes.
- Make the app's own build, lint or test command pass before you open the PR. That command is documented in the app's README; if it is missing or wrong, say so in the PR.
- Update user-facing documentation (README, wiki) when behaviour changes.
- Every user-facing string needs both English and Spanish.
- Do not commit local agent files (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`), build output or anything from a personal scratch folder.

## Commits

- Write commit messages in English.
- Keep the subject line short and imperative, and put the reasoning in the body.
- One commit per completed task rather than one giant commit at the end.
- No AI attribution trailers, marketing lines or tool branding in commit messages.

## Licensing

All projects are GPLv3. By opening a pull request you agree that your contribution is licensed under the same terms as the repository you are contributing to.

## Conduct and security

Be respectful: discussions are about the code, not the person. Never report a vulnerability in a public issue; follow [SECURITY.md](SECURITY.md) instead.
