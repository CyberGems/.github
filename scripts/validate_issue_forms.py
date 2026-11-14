#!/usr/bin/env python3
"""Validate the issue forms in ISSUE_TEMPLATE against GitHub's rules.

GitHub silently ignores a form whose YAML is invalid or violates the form
schema, so a broken template looks fine in the repository and simply never
appears in the issue chooser. This script fails the build instead.

Rules covered: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/common-validation-errors-when-creating-issue-forms
"""

from __future__ import annotations

import pathlib
import sys

import yaml

TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent.parent / "ISSUE_TEMPLATE"

ALLOWED_TYPES = {"markdown", "input", "textarea", "dropdown", "checkboxes"}
INPUT_TYPES = {"input", "textarea", "dropdown", "checkboxes"}
REQUIRED_TOP_LEVEL = ("name", "description", "body")

# YAML parses these as booleans, so GitHub forbids them as labels.
FORBIDDEN_LABELS = {
    "y", "Y", "yes", "Yes", "YES",
    "n", "N", "no", "No", "NO",
    "true", "True", "TRUE", "false", "False", "FALSE",
    "on", "On", "ON", "off", "Off", "OFF",
}


def is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def validate_form(name: str, doc: object, errors: list[str]) -> None:
    if not isinstance(doc, dict):
        errors.append(f"{name}: the form must be a YAML mapping")
        return

    for key in REQUIRED_TOP_LEVEL:
        if key not in doc:
            errors.append(f"{name}: missing required key '{key}'")
    if not is_non_empty_string(doc.get("name")):
        errors.append(f"{name}: 'name' must be a non-empty string")
    if not is_non_empty_string(doc.get("description")):
        errors.append(f"{name}: 'description' must be a non-empty string")

    labels = doc.get("labels")
    if labels is not None and not (isinstance(labels, list) and all(isinstance(l, str) for l in labels)):
        errors.append(f"{name}: 'labels' must be a list of strings")

    body = doc.get("body")
    if not isinstance(body, list) or not body:
        errors.append(f"{name}: 'body' must be a non-empty list")
        return

    seen_ids: set[str] = set()
    inputs = 0

    for index, element in enumerate(body):
        where = f"{name}: body[{index}]"
        if not isinstance(element, dict):
            errors.append(f"{where}: element must be a mapping")
            continue

        element_type = element.get("type")
        if element_type not in ALLOWED_TYPES:
            errors.append(f"{where}: unknown type {element_type!r}, expected one of {sorted(ALLOWED_TYPES)}")
            continue

        attributes = element.get("attributes")
        if not isinstance(attributes, dict):
            errors.append(f"{where}: missing 'attributes'")
            continue

        if element_type == "markdown":
            if not is_non_empty_string(attributes.get("value")):
                errors.append(f"{where}: markdown needs a non-empty 'value'")
            continue

        inputs += 1
        element_id = element.get("id")
        if not is_non_empty_string(element_id):
            errors.append(f"{where}: missing 'id'")
        elif element_id in seen_ids:
            errors.append(f"{where}: duplicate id {element_id!r}")
        else:
            seen_ids.add(element_id)

        label = attributes.get("label")
        if not is_non_empty_string(label):
            errors.append(f"{where}: missing 'label'")
        elif label in FORBIDDEN_LABELS:
            errors.append(f"{where}: label {label!r} is forbidden because YAML parses it as a boolean")

        options = attributes.get("options")
        if element_type in {"dropdown", "checkboxes"}:
            if not isinstance(options, list) or not options:
                errors.append(f"{where}: {element_type} needs a non-empty 'options' list")
                continue
            if not all(isinstance(option, str) and option.strip() for option in options):
                errors.append(f"{where}: every option must be a non-empty string")
                continue
            if len(options) != len(set(options)):
                errors.append(f"{where}: options must be unique")
            if any(option.strip().lower() == "none" for option in options):
                errors.append(f"{where}: 'none' is a reserved word and cannot be used as an option")
            if element_type == "dropdown" and "default" in attributes and any(
                option.strip().lower() == "none" for option in options
            ):
                errors.append(f"{where}: a dropdown with 'default' cannot offer 'none'")

    if inputs == 0:
        errors.append(f"{name}: a form needs at least one input, textarea, dropdown or checkboxes element")


def validate_config(name: str, doc: object, errors: list[str]) -> None:
    if not isinstance(doc, dict):
        errors.append(f"{name}: the config must be a YAML mapping")
        return

    if "blank_issues_enabled" in doc and not isinstance(doc["blank_issues_enabled"], bool):
        errors.append(f"{name}: 'blank_issues_enabled' must be true or false")

    links = doc.get("contact_links", [])
    if not isinstance(links, list):
        errors.append(f"{name}: 'contact_links' must be a list")
        return

    for index, link in enumerate(links):
        where = f"{name}: contact_links[{index}]"
        if not isinstance(link, dict):
            errors.append(f"{where}: entry must be a mapping")
            continue
        for key in ("name", "url", "about"):
            if not is_non_empty_string(link.get(key)):
                errors.append(f"{where}: missing '{key}'")
        url = link.get("url")
        if is_non_empty_string(url) and not url.startswith(("https://", "http://")):
            errors.append(f"{where}: 'url' must start with https:// or http://")


def main() -> int:
    errors: list[str] = []
    forms = 0

    if not TEMPLATE_DIR.is_dir():
        print(f"No ISSUE_TEMPLATE directory at {TEMPLATE_DIR}", file=sys.stderr)
        return 1

    for path in sorted(TEMPLATE_DIR.glob("*.yml")):
        name = f"ISSUE_TEMPLATE/{path.name}"
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            errors.append(f"{name}: invalid YAML: {error}")
            continue

        if path.name == "config.yml":
            validate_config(name, doc, errors)
            print(f"checked {name} (config)")
        else:
            validate_form(name, doc, errors)
            forms += 1
            print(f"checked {name}")

    if forms == 0:
        errors.append("ISSUE_TEMPLATE has no issue forms")

    if errors:
        print("\nValidation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"\n{forms} issue form(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
