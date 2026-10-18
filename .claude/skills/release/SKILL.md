---
name: release
description: Prepare a ConfigUpdater release. Runs the final checks, completes and finalizes the CHANGELOG.rst section, commits on main and creates the v* tag whose push publishes to PyPI. Only when the user runs /release.
argument-hint: "[version, e.g. 4.0 or 4.1b1]"
disable-model-invocation: true
---

# Release ConfigUpdater

Requested version: `$ARGUMENTS` (if empty, derive it in step 2).

Pushing a `v*` tag runs `.github/workflows/publish-package.yml`. It runs the whole CI
on the tag, uploads the sdist and wheel to PyPI (trusted publishing, `pypi`
environment) and creates a GitHub release whose notes are the version's
`CHANGELOG.rst` section (`tools/release_notes.py`). An upload to PyPI cannot be
undone, and a version number can never be uploaded twice. So do every check before
the tag exists, and never push without the user's explicit OK.

The release commit goes directly on `main`. This is the one exception to the rule
that changes reach `main` through PRs; the user chose it for releases.

Stop at the first failed check and report it. Don't work around it.

## 1. Repository state

- `git fetch origin --tags --prune`. Then check that the current branch is `main`
  (if not, ask before switching), that it equals `origin/main`, and that tracked
  files have no staged or unstaged changes. Untracked local artifacts are fine.
- `gh auth status` succeeds.
- CI is green on `origin/main`. The `All required checks pass` check run
  (`gh api repos/pyscaffold/configupdater/commits/<sha>/check-runs`) and the
  pre-commit.ci status (`gh api repos/pyscaffold/configupdater/commits/<sha>/status`)
  are both `success`. If they are still pending, wait or stop. Never release a
  commit that hasn't been checked.

## 2. Version

- The last release `L` is the nearest tag:
  `git describe --tags --abbrev=0 --match 'v*' origin/main`. For a final release,
  add `--exclude '*a[0-9]*' --exclude '*b[0-9]*' --exclude '*rc[0-9]*'`, so that
  the changelog check covers everything since the previous final release. Avoid
  `git tag --sort=-v:refname`, which sorts `v3.2b1` before `v3.2`.
- The top section of `CHANGELOG.rst` is `Version X (unreleased)`. Without an
  argument, propose `X`. With an argument, it must be `X` or a pre-release of it
  (`Xa1`, `Xb1`, `Xrc1`); otherwise ask.
- Compare `X` with the entries. A `**Breaking:**` entry or a dropped Python version
  suggests a major version, new features a minor one, and only fixes a patch
  release. Raise any mismatch with the user.
- `v<version>` must not exist yet, neither as a local or remote tag nor as a remote
  branch (`git ls-remote origin`). A branch and a tag with the same name make
  pushes and checkouts ambiguous.

## 3. Changelog completeness

- List the PRs merged since `L`:
  `gh pr list --state merged --search "merged:>$(git log -1 --format=%cI L)" --limit 300 --json number,title,baseRefName`.
  Don't take the PR numbers from commit subjects: many PRs are rebase-merged, and
  their commits don't mention the PR. PRs into an integration branch (such as
  `v4.0`) count once that branch is merged into `main`. Get the details with
  `gh pr view N --json title,body,closingIssuesReferences,files`.
- Changes pushed without a PR: go through `git log L..origin/main --no-merges --oneline`.
  `gh api repos/pyscaffold/configupdater/commits/<sha>/pulls --jq '.[].number'`
  shows which PR a commit belongs to; if it prints nothing, there is no PR.
- Classify each change:
  - User-visible: behavior, public API, exception types and messages, type hints
    (the package ships `py.typed`), supported Python versions, packaging metadata.
  - Internal: tests, CI, tooling, docs-only changes, refactorings that don't change
    behavior.
- Cross-check by diffing `L..origin/main`: `__all__` in
  `src/configupdater/__init__.py`, public signatures in `src/configupdater/`, and
  `requires-python` and the classifiers in `pyproject.toml`.
- Each user-visible change needs an entry that follows the conventions in
  `CLAUDE.md`. It references `issue #N` (the issue it closes), or `PR #N` if there is
  no issue. A breaking change starts with `**Breaking:**`.
- Show a table with one row per PR (or per commit without a PR): title,
  user-visible or internal, and whether it has an entry. For each missing entry,
  propose wording in the style of the existing ones. Add the entries only after the
  user agrees; they become part of the release commit.

## 4. Finalize the changelog

- Final release: change the heading `Version X (unreleased)` to `Version X`, and
  shorten the `=` underline to the heading's length. Don't add a date: the headings
  have none, and `tools/release_notes.py` looks for exactly `Version X`.
- Pre-release: keep `(unreleased)`. The workflow takes the notes from that section,
  and the final release still needs it.
- `python3 tools/release_notes.py <version>` must succeed. Show its output, because
  it becomes the GitHub release notes.
- `uv run tox -e docs -- -W` passes. The docs include the changelog, and Read the
  Docs fails on warnings.

## 5. Commit and tag

- Show the diff and get the user's OK.
- If `CHANGELOG.rst` changed, commit it on `main` as `Release <version>`. A
  pre-release without changelog changes needs no commit; it tags `origin/main`.
- `git tag -a v<version> -m "Version <version>"`, annotated like the earlier
  release tags. hatch-vcs takes the package version from this tag.
- Build into the scratchpad: `uv build --out-dir <scratchpad>/dist`. Check that it
  produces `configupdater-<version>.tar.gz` and
  `configupdater-<version>-py3-none-any.whl`. A suffix such as `.post1.dev0` or
  `+d2026…` means the tag is not on `HEAD`, or the tracked files are dirty.

## 6. Push, only after an explicit yes

Until now, everything can be undone locally. Ask the user to confirm the push. Name
the version, and say that after the CI passes it is uploaded to PyPI for good.
Then run:

```bash
git push --atomic origin main v<version>
```

`--atomic` pushes both refs or neither, so the tag never points to a commit that
`main` doesn't contain. For a pre-release without a commit, run
`git push origin v<version>` instead.

Afterwards, give the run's URL (`gh run list --workflow publish-package.yml -L 1`)
and the future release page
`https://github.com/pyscaffold/configupdater/releases/tag/v<version>`. Don't poll
the run. If the `pypi` environment has required reviewers, the upload waits until
the user approves it on GitHub.

## If the release run fails

- Failed before the upload (the CI or the release notes): nothing is published.
  Fix the problem with a PR as usual. Then, with the user's OK, delete the tag
  (`git push origin :refs/tags/v<version>` and `git tag -d v<version>`) and run
  `/release` again.
- Only the GitHub release job failed: the version is already on PyPI, so never move
  or reuse the tag. Fix the cause and re-run the failed job
  (`gh run rerun <run-id> --failed`). Or create the release by hand with the files
  that went to PyPI, not a local build:
  `gh run download <run-id> -n Packages -D <scratchpad>/pypi`, then
  `gh release create v<version> <scratchpad>/pypi/* --verify-tag --notes "$(python3 tools/release_notes.py <version>)"`.
