"""
scripts/commit.py
------------------
Structured batch commit script for Hedera Agent Commerce Kit.

Rule: maximum 5 file changes per commit message.

Groups all pending changes (staged + unstaged + untracked) into
logical commits, each capped at 5 files, with a descriptive
conventional-commit message derived from the files in that group.

Usage:
    python scripts/commit.py            # dry run — shows plan, no commits
    python scripts/commit.py --apply    # executes the commits
    python scripts/commit.py --push     # executes commits then pushes to origin/main

The script never force-pushes and never amends existing commits.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─── Configuration ────────────────────────────────────────────────────────────

MAX_FILES_PER_COMMIT = 5

# Maps path prefixes / patterns to a (scope, description) tuple used to build
# the commit message when those files are in the same group.
COMMIT_GROUPS: list[tuple[list[str], str, str]] = [
    # (path_prefixes,  conventional-commit type(scope),  description)
    (["hack/nft/"],           "fix(nft)",       "NFT minting service"),
    (["hack/models/"],        "feat(sdk)",      "domain models"),
    (["hack/compliance/"],    "feat(sdk)",      "compliance certifier"),
    (["hack/audit/"],         "feat(sdk)",      "audit engine and probes"),
    (["hack/core/"],          "feat(sdk)",      "quote lifecycle and interfaces"),
    (["hack/receipts/"],      "feat(sdk)",      "HCS receipt service"),
    (["hack/verifiers/"],     "feat(sdk)",      "Mirror Node verifier"),
    (["hack/middleware/"],    "feat(sdk)",      "x402 middleware"),
    (["hack/stores/"],        "feat(sdk)",      "quote store implementations"),
    (["hack/metering/"],      "feat(sdk)",      "metering service"),
    (["hack/reporting/"],     "feat(sdk)",      "PDF and SKILL.md reporters"),
    (["hack/agent/"],         "feat(sdk)",      "Hedera Agent Kit integration"),
    (["hack/"],               "feat(sdk)",      "SDK package updates"),
    (["demo/routers/"],       "feat(demo)",     "FastAPI routers"),
    (["demo/"],               "feat(demo)",     "FastAPI application"),
    (["frontend/app/"],       "feat(frontend)", "Next.js app pages"),
    (["frontend/components/certification/"], "feat(frontend)", "certification components"),
    (["frontend/components/"], "feat(frontend)", "UI components"),
    (["frontend/hooks/"],     "feat(frontend)", "React hooks"),
    (["frontend/lib/"],       "feat(frontend)", "API client and types"),
    (["frontend/"],           "feat(frontend)", "Next.js portal"),
    (["docs/"],               "docs",           "screenshots and documentation"),
    (["examples/mcp/"],       "feat(examples)", "MCP server integration"),
    (["examples/"],           "feat(examples)", "usage examples"),
    (["scripts/"],            "chore(scripts)", "developer scripts"),
    (["backend/"],            "chore(cleanup)", "remove legacy backend folder"),
    (["Dockerfile",
      "docker-compose.yml",
      ".dockerignore"],       "feat(deploy)",   "Docker and Render deployment config"),
    (["DEPLOYMENT.md",
      "STRUCTURE.md",
      "README.md"],           "docs",           "deployment and project documentation"),
    ([".gitignore",
      "pyproject.toml"],      "chore",          "project configuration"),
    (["hedera_nft_certificate.jpg",
      ".env.production.example",
      "frontend/.env.production.example",
      "frontend/.env.local.example"], "chore", "environment templates and assets"),
]


# ─── Git helpers ──────────────────────────────────────────────────────────────

def run(cmd: list[str], check: bool = True) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if check and result.returncode != 0:
        print(f"git error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


ROOT = Path(__file__).parent.parent


def get_changed_files() -> list[str]:
    """Return all files that have changes (modified, deleted, untracked)."""
    # Staged
    staged = run(["git", "diff", "--cached", "--name-only"]).splitlines()
    # Unstaged tracked
    unstaged = run(["git", "diff", "--name-only"]).splitlines()
    # Untracked
    untracked_raw = run(["git", "ls-files", "--others", "--exclude-standard"]).splitlines()

    all_files: list[str] = []
    seen: set[str] = set()
    for f in staged + unstaged + untracked_raw:
        f = f.strip()
        if f and f not in seen:
            seen.add(f)
            all_files.append(f)

    # Include deleted files
    deleted = run(["git", "ls-files", "--deleted"]).splitlines()
    for f in deleted:
        f = f.strip()
        if f and f not in seen:
            seen.add(f)
            all_files.append(f)

    return sorted(all_files)


# ─── Grouping logic ───────────────────────────────────────────────────────────

@dataclass
class CommitGroup:
    label: str          # conventional commit message
    files: list[str] = field(default_factory=list)


def classify_file(path: str) -> tuple[str, str]:
    """Return (commit_type, description) for a file path."""
    for prefixes, ctype, desc in COMMIT_GROUPS:
        for prefix in prefixes:
            if path.startswith(prefix) or path == prefix:
                return ctype, desc
    # Fallback
    top = path.split("/")[0]
    return "chore", f"update {top}"


def build_commit_message(files: list[str]) -> str:
    """
    Derive a single conventional commit message for up to 5 files.
    Uses the most common (type, description) pair in the group.
    """
    classifications: list[tuple[str, str]] = [classify_file(f) for f in files]
    # Count by (type, desc)
    from collections import Counter
    counts = Counter(classifications)
    dominant_type, dominant_desc = counts.most_common(1)[0][0]

    # Collect unique descriptions for detail
    unique_descs = list(dict.fromkeys(d for _, d in classifications))
    if len(unique_descs) == 1:
        detail = unique_descs[0]
    elif len(unique_descs) <= 3:
        detail = ", ".join(unique_descs)
    else:
        detail = f"{unique_descs[0]} and {len(unique_descs) - 1} more areas"

    return f"{dominant_type}: {detail}"


def group_files(files: list[str]) -> list[CommitGroup]:
    """
    Group files into commits of at most MAX_FILES_PER_COMMIT.
    Files with the same (type, desc) classification are grouped together
    before being chunked to the size limit.
    """
    # First pass: group by (type, desc)
    from collections import defaultdict
    by_class: dict[tuple[str, str], list[str]] = defaultdict(list)
    for f in files:
        key = classify_file(f)
        by_class[key].append(f)

    # Second pass: chunk each class group into MAX_FILES_PER_COMMIT chunks
    commits: list[CommitGroup] = []
    for (ctype, desc), group_files_list in by_class.items():
        for i in range(0, len(group_files_list), MAX_FILES_PER_COMMIT):
            chunk = group_files_list[i:i + MAX_FILES_PER_COMMIT]
            label = f"{ctype}: {desc}"
            if len(group_files_list) > MAX_FILES_PER_COMMIT:
                chunk_num = i // MAX_FILES_PER_COMMIT + 1
                total_chunks = (len(group_files_list) + MAX_FILES_PER_COMMIT - 1) // MAX_FILES_PER_COMMIT
                label = f"{ctype}: {desc} [{chunk_num}/{total_chunks}]"
            commits.append(CommitGroup(label=label, files=chunk))

    return commits


# ─── Commit execution ─────────────────────────────────────────────────────────

def stage_and_commit(group: CommitGroup, dry_run: bool = True) -> None:
    """Stage the files in the group and create a commit."""
    print(f"\n  commit: {group.label}")
    for f in group.files:
        status_line = f"    + {f}"
        print(status_line)

    if dry_run:
        return

    # Stage each file (handles new, modified, deleted)
    for f in group.files:
        full_path = ROOT / f
        if full_path.exists():
            run(["git", "add", f])
        else:
            # Deleted file — stage the deletion
            run(["git", "rm", "--cached", "--ignore-unmatch", f], check=False)
            run(["git", "add", "-u", f], check=False)

    # Check if anything is actually staged
    staged = run(["git", "diff", "--cached", "--name-only"])
    if not staged.strip():
        print(f"    (nothing to commit — skipping)")
        return

    run(["git", "commit", "-m", group.label])
    print(f"    ✓ committed")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch commit with max 5 files per commit message"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute commits (default is dry run)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Execute commits then push to origin main",
    )
    args = parser.parse_args()

    dry_run = not (args.apply or args.push)

    files = get_changed_files()
    if not files:
        print("Nothing to commit. Working tree is clean.")
        return

    groups = group_files(files)

    total_commits = len(groups)
    total_files = sum(len(g.files) for g in groups)

    print(f"{'DRY RUN — ' if dry_run else ''}Found {total_files} changed files")
    print(f"Plan: {total_commits} commits (max {MAX_FILES_PER_COMMIT} files each)\n")
    print("─" * 60)

    for i, group in enumerate(groups, 1):
        print(f"\n[{i}/{total_commits}]", end="")
        stage_and_commit(group, dry_run=dry_run)

    print("\n" + "─" * 60)

    if dry_run:
        print(f"\nDry run complete. Run with --apply to execute, --push to execute and push.")
    else:
        print(f"\n✓ {total_commits} commits created.")
        if args.push:
            print("\nPushing to origin/main...")
            run(["git", "push", "-u", "origin", "main"])
            print("✓ Pushed.")


if __name__ == "__main__":
    main()
