# Contributing to CyberGems

Thanks for taking the time to help. CyberGems builds free, privacy-first Windows apps under GPLv3: no ads, no telemetry, no accounts, no cloud lock-in.

This guide applies to every repository in this account. A repository that ships its own `CONTRIBUTING.md` takes precedence over this one.

## Before you write code

- **Found a bug?** Open an issue with the bug report template. Include the app version, your Windows version and the steps that reproduce it.
- **Planning a large change?** Open an issue first and describe the problem and your proposed approach. It is much cheaper to agree on the direction before you write the patch.
- **Small fixes** (typos, broken links, an obvious one-line bug) can go straight to a pull request.

## Where the code lives

Each app has its own repository. Its `README.md` explains how to build and run it locally, and its wiki holds the longer notes. There is no monorepo: pick the repository of the app you want to change.

## README structure

Each app ships two READMEs, `README.md` and `README.es.md`, with the same sections in the same order (the Spanish file uses the translated names below). A README is the shop window, not the manual: long explanations belong in the wiki.

| # | English | Español |
|---|---|---|
| 1 | `👋 Introduction` | `👋 Introducción` |
| 2 | `🖼️ Screenshots` | `🖼️ Capturas` |
| 3 | `<identity emoji> Why <App>?` | `<identity emoji> ¿Por qué <App>?` |
| 4 | `✨ Key Features` | `✨ Funciones principales` |
| 5 | `🚀 Installation` | `🚀 Instalación` |
| 6 | `🧭 Using the App` | `🧭 Cómo usar la app` |
| 7 | `🛠️ Tech Stack & Architecture` | `🛠️ Stack tecnológico y arquitectura` |
| 8 | `⌨️ Keyboard Shortcuts` | `⌨️ Atajos de teclado` |
| 9 | `❤️ Donate` | `❤️ Donar` |
| 10 | `📄 License` | `📄 Licencia` |
| 11 | `❓ FAQ` | `❓ Preguntas frecuentes` |
| 12 | `🔗 See also` | `🔗 Ver también` |

A banner, the badges, a tagline and `📑 Table of Contents` come before section 1, and `---` separates every section. The `Why <App>?` emoji is the app's own identity emoji; choose section emoji that do not collide with it or with another heading.

Three sections are easy to blur, so keep them distinct:

- **Installation** — only what puts the app on the machine: downloads, installers, SmartScreen, portable builds and runtime requirements. No usage steps.
- **Using the App** — a short onboarding bridge: what appears on launch, three everyday steps using the app's own UI vocabulary, one short paragraph of caveats, and a link to the wiki's `How-Do-You-Use` page (or its `-es` translation when one exists). Do not copy the full guide here.
- **Tech Stack & Architecture** — internals for contributors: platform, frameworks, build commands and design. Not instructions for end users.

### Extra sections

A section outside the core is allowed only when it documents something genuinely exclusive to that app — for example CyberWall's `How It Works` (kernel-level filtering), CyberViewer's `Security` and `Updates`, CyberClock's `Themes & Customization`, or CyberGo's alpha-only notes. If the same text would make sense in another app's README, it belongs in the core or in the wiki instead.

Extras must be added to both READMEs, listed in both tables of contents, and placed near the related core section without breaking the core order. Do not rename a core section to match an extra. A few older READMEs still carry sections inherited from a different skeleton; treat the core above as the target and resolve that drift when the README is next revised, rather than copying the deviation into another app.

### Keeping both READMEs in sync

- Change `README.md` and `README.es.md` together, including their tables of contents and links. A Spanish wiki link points at the `-es` page only when that translation exists; otherwise say so in the link text.
- Copy heading anchors from the rendered README: emoji with a variation selector keep it in the slug (`#️-screenshots`), so a guessed anchor will silently break.
- Preserve each file's existing line endings; the suite mixes CRLF and LF files.
- Verify the rendered README (GitHub's HTML API or the preview), not just the Markdown source.

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
