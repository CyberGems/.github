[English](README.md) · **Español**

# Archivos de comunidad de CyberGems

Este repositorio contiene la guía de contribución, la política de seguridad, el código de conducta y las plantillas de issues y pull requests que aplican a todos los repositorios de CyberGems.

GitHub trata un repositorio público llamado `.github` como la fuente por defecto de archivos de salud de comunidad para toda la cuenta. Un repositorio que incluye su propia copia de un archivo tiene prioridad; el resto recurre a este.

## Qué hay aquí

| Archivo | Para qué sirve |
|---|---|
| `CONTRIBUTING.md` | Cómo reportar un bug, abrir un pull request y escribir commits |
| `SECURITY.md` | Cómo reportar una vulnerabilidad en privado, y qué está en alcance |
| `CODE_OF_CONDUCT.md` | Comportamiento esperado y la escala de sanciones (Contributor Covenant 2.1) |
| `PULL_REQUEST_TEMPLATE.md` | El cuerpo que se precarga al abrir un pull request |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | Formulario obligatorio de reporte de bug |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | Formulario obligatorio de solicitud de función |
| `.github/ISSUE_TEMPLATE/config.yml` | Ajustes del selector de plantillas y enlaces de contacto |
| `scripts/validate_issue_forms.py` | Comprueba los formularios contra las reglas de GitHub |
| `.github/workflows/validate-issue-forms.yml` | Ejecuta esa comprobación en cada push y pull request |

## Dónde va cada archivo

La ubicación importa, y dos de ellas no son lo que la intuición sugiere:

- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` y `PULL_REQUEST_TEMPLATE.md` viven en la **raíz** de este repositorio.
- Los formularios de issue **no**. Deben estar en **`.github/ISSUE_TEMPLATE/`** dentro de este repositorio. Las plantillas colocadas en la raíz se ignoran y nunca aparecen en el selector de issues, sin ningún error en ningún sitio.

Si un repositorio define alguna de sus propias plantillas de issue, GitHub ignora la carpeta `ISSUE_TEMPLATE` por defecto para ese repositorio, así que las sobrescrituras son todo o nada.

## Cómo cambiar estos archivos

Edita el archivo, haz push a `main` y el cambio aplica a todos los repositorios que no lo sobrescriban. Nada se copia a los repositorios individuales, así que un arreglo aquí lo arregla en todos a la vez.

Los formularios de issue se validan con `.github/workflows/validate-issue-forms.yml`. GitHub descarta en silencio un formulario cuyo YAML es inválido o rompe el esquema del formulario, así que una plantilla puede estar rota y aun así verse bien en el repositorio. Ejecuta la misma comprobación en local con:

```bash
python3 -m pip install pyyaml
python3 scripts/validate_issue_forms.py
```

## Licencia

Los textos y plantillas de este repositorio están disponibles bajo la licencia MIT. Ver [LICENSE](LICENSE).
