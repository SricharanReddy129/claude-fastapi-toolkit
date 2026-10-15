---
description: Set up a new project from the toolkit template. Run once, before anything else.
argument-hint: [project name]
---

# /init-project

Copies `.claude/project-template/` into the project root and prepares the
skeleton. **Run once, at the very start.**

**Calls:** `.claude/scripts/init_project.py`

---

## Preconditions

- `.claude/` exists (the toolkit has been cloned into it)
- The project root is otherwise empty, or has only `.git/`

If `CLAUDE.md` or `plan/` already exist, the script refuses and says so. Do not
force it — a half-initialised project is worse than an uninitialised one.

---

## Steps

**1. Ask for the project name** if `$ARGUMENTS` is empty. It replaces the
placeholder in `CLAUDE.md` and `README.md`.

**2. Dry run first.**

```
python .claude/scripts/init_project.py --dry-run
```

Show the user what will be created. If it refuses, report why and stop.

**3. Copy.**

```
python .claude/scripts/init_project.py --name "<project name>"
```

**4. Confirm `.gitignore` landed** at the project root — it comes from
`gitignore.template`. Check it contains `.env` and `.claude/.git/`.

Without the second line, the toolkit's git repo fights with the project's.

**5. Ask for the one-liner** describing what this service does, and write it
into `CLAUDE.md` under the project name.

**6. Report what exists now** and what the user must do by hand:

- `cp .env.example .env` and fill in real values — Claude cannot read or write
  `.env`
- `poetry init` and `poetry install`
- Create the database

---

## What this does not do

- **Does not run `poetry init`.** Python version and package metadata are
  yours to choose
- **Does not create `.env`.** Blocked by design
- **Does not create the database**
- **Does not scaffold `app/`.** The foundation stage builds it, after
  requirements are ingested — the sub-folder organisation is a project choice
  derived from the document
- **Does not touch `.claude/`**

---

## Do not

- Re-run this on an initialised project
- Edit files inside `.claude/project-template/` to suit this project — those
  are the blanks for the next one
- Copy files by hand instead of running the script; it handles the
  `gitignore.template` rename and the placeholder substitution
- Proceed to `/ingest-requirements` before `.env` exists and Poetry is set up

---

## Next

`/ingest-requirements <path-to-document>`

Then the foundation stage, then Phase 0 auth, then `/plan-phases`.
