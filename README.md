**English** · [Español](README.es.md)

# CyberGems community files

This repository holds the contribution guide, the security policy, the code of conduct and the issue and pull request templates that apply to every CyberGems repository.

GitHub treats a public repository named `.github` as the default source of community health files for the whole account. A repository that ships its own copy of a file takes precedence; everything else falls back to this one.

## What is here

| File | Used for |
|---|---|
| `CONTRIBUTING.md` | How to report a bug, open a pull request and write commits |
| `SECURITY.md` | How to report a vulnerability privately, and what is in scope |
| `CODE_OF_CONDUCT.md` | Expected behaviour and the enforcement ladder (Contributor Covenant 2.1) |
| `PULL_REQUEST_TEMPLATE.md` | The body preloaded when a pull request is opened |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | Required bug report form |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | Required feature request form |
| `.github/ISSUE_TEMPLATE/config.yml` | Template chooser settings and contact links |
| `scripts/validate_issue_forms.py` | Checks the forms against GitHub's rules |
| `.github/workflows/validate-issue-forms.yml` | Runs that check on every push and pull request |
| `AI-DISCLOSURE.md` | English source of the reusable AI-use disclosure |
| `AI-DISCLOSURE.es.md` | Spanish source of the same disclosure |

## Where each file goes

The location matters, and two of them differ from what intuition suggests:

- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` and `PULL_REQUEST_TEMPLATE.md` live at the **root** of this repository.
- Issue forms do **not**. They must be in **`.github/ISSUE_TEMPLATE/`** inside this repository. Templates placed at the root are ignored and simply never appear in the issue chooser, with no error anywhere.

If a repository defines any of its own issue templates, GitHub ignores the whole default `ISSUE_TEMPLATE` folder for that repository, so overrides are all-or-nothing.

## AI disclosure template

Unlike the community health files above, `AI-DISCLOSURE.md` and `AI-DISCLOSURE.es.md` are **not** applied automatically to other repositories. Copy both files into the root of each app repository and link them from the two READMEs. Replace `{{App}}` in both files with the app's own name, for example `CyberSnap`. Do not leave the placeholder in a published repository.

`{{App}}` appears twice: as the subject of the first paragraph and in the sentence stating that the app itself ships no AI features. That sentence is the default. If an app does ship AI features, replace it with a short statement of what runs, when, and where the data goes; `CyberPaste` is the reference wording.

Add one line under `## 📄 License` in `README.md` and under `## 📄 Licencia` in `README.es.md`. Do not add a new level-2 heading: app READMEs allow exactly 13 of them.

```markdown
This project uses AI coding assistants. See [AI disclosure](AI-DISCLOSURE.md).
```

```markdown
Este proyecto usa asistentes de programación con IA. Consulta la [declaración de uso de IA](AI-DISCLOSURE.es.md).
```

The master text is MIT-licensed like the rest of this repository. It refers to "the repository LICENSE" so that it stays accurate when copied into a GPL-licensed app repository.

## Changing these files

Edit the file, push to `main`, and the change applies to every repository that does not override it. Nothing is copied into the individual repositories, so a fix here fixes it everywhere at once.

Issue forms are validated by `.github/workflows/validate-issue-forms.yml`. GitHub silently drops a form whose YAML is invalid or breaks the form schema, so a template can be broken and still look fine in the repository. Run the same check locally with:

```bash
python3 -m pip install pyyaml
python3 scripts/validate_issue_forms.py
```

## Licence

The texts and templates in this repository are available under the MIT licence. See [LICENSE](LICENSE).
