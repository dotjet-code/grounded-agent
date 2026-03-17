"""Persona CLI: local execution of observe/reflect/post cycles.

Usage:
    python -m src.persona run --input observed.txt
    python -m src.persona run --llm claude --input observed.txt
    python -m src.persona post --llm claude       # compose + safety + post to Bluesky
    python -m src.persona post --dry-run           # compose + safety, no actual post
    python -m src.persona status                   # show internal state summary

Default LLM is 'stub' (no network). Use '--llm claude' for real inference.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from src.persona.compose import PostComposer
from src.persona.core import LlmCall, PersonaCore
from src.persona.memory import Memory
from src.persona.outbox import Outbox, SafetyGuard
from src.persona.state import PersonaState

# Default paths
_DEFAULT_DB = Path("data/memory.db")
_DEFAULT_DIARY = Path("data/diary")
_DEFAULT_OUTBOX_DB = Path("data/outbox.db")
_DEFAULT_STOP_FILE = Path("data/STOP")


def _stub_llm(system: str, user: str) -> str:
    """Stub LLM that extracts observations without real inference.

    Looks for lines in the user message and echoes them as basic
    VOCAB/CURIOSITY entries. Good enough for testing the loop locally.
    """
    # For reflect (diary) prompts
    if "diary" in user.lower():
        return "Today I observed some things. I'm still thinking about them."

    # For observe prompts: echo back a simple observation
    return "Nothing in particular caught my attention today."


def _build_memory(db_path: Path, diary_dir: Path) -> Memory:
    """Create a Memory instance with the given paths."""
    return Memory(db_path=db_path, diary_dir=diary_dir)


def _resolve_llm(name: str) -> LlmCall:
    """Resolve LLM adapter by name."""
    if name == "stub":
        return _stub_llm
    if name == "claude":
        from src.persona.llm import make_claude_llm
        return make_claude_llm()
    raise ValueError(f"Unknown LLM adapter: {name!r}. Choose 'stub' or 'claude'.")


def cmd_run(args: argparse.Namespace) -> None:
    """Run one observe → reflect cycle."""
    memory = _build_memory(Path(args.db), Path(args.diary_dir))
    llm = _resolve_llm(args.llm)
    core = PersonaCore(memory, llm)

    # Read input texts
    if args.input:
        path = Path(args.input)
        if not path.exists():
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        raw = path.read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            print("Enter observed texts (Ctrl+D to finish):")
        raw = sys.stdin.read()

    texts = [t.strip() for t in raw.strip().split("\n---\n") if t.strip()]

    if not texts:
        print("No input texts provided.")
        return

    # Observe
    result = core.observe(texts)
    print(f"Observed {len(texts)} text(s).")
    print(f"  Vocabulary added: {result['vocabulary_added']}")
    print(f"  Curiosity added: {result['curiosity_added']}")

    if getattr(args, "verbose", False) and result["raw_response"]:
        print(f"\n[LLM raw response]\n{result['raw_response']}\n[/LLM raw response]")

    # Reflect
    diary = core.reflect()
    print(f"\nDiary entry written.")
    print(f"---\n{diary}\n---")

    memory.close()


def cmd_status(args: argparse.Namespace) -> None:
    """Show current persona internal state."""
    memory = _build_memory(Path(args.db), Path(args.diary_dir))
    state = PersonaState(memory)

    print(state.summary())

    memory.close()


def cmd_post(args: argparse.Namespace) -> None:
    """Compose a post, run safety checks, and post to the target platform."""
    from src.persona.platform import resolve_platform

    memory = _build_memory(Path(args.db), Path(args.diary_dir))
    state = PersonaState(memory)
    llm = _resolve_llm(args.llm)
    outbox = Outbox(db_path=Path(args.outbox_db))

    # Resolve platform for max_length
    platform_name = args.platform
    try:
        platform = resolve_platform(platform_name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    guard = SafetyGuard(
        outbox=outbox,
        stop_file=Path(args.stop_file),
        max_length=platform.max_length,
    )

    # 1. Compose
    composer = PostComposer(state, llm)
    candidate = composer.compose()
    print(f"Composed ({platform_name}): {candidate}")

    # 2. Safety check
    passed, reason = guard.check(candidate)
    if not passed:
        outbox_id = outbox.save(candidate, status="blocked", block_reason=reason)
        print(f"Blocked: {reason} (outbox #{outbox_id})")
        memory.close()
        outbox.close()
        return

    # 3. Save to outbox as ready
    outbox_id = outbox.save(candidate, status="ready")

    # 4. Dry run check
    if args.dry_run:
        print(f"Dry run — saved to outbox #{outbox_id}, not posted.")
        memory.close()
        outbox.close()
        return

    # 5. Post to platform
    try:
        platform.login()
        uri = platform.post(candidate)
        outbox.mark_posted(outbox_id, uri)
        print(f"Posted: {uri} (outbox #{outbox_id})")
    except Exception as exc:
        outbox.mark_failed(outbox_id, str(exc))
        print(f"Failed: {exc} (outbox #{outbox_id})", file=sys.stderr)

    memory.close()
    outbox.close()


def cmd_autopost_once(args: argparse.Namespace) -> None:
    """Guarded single-post cycle for autonomous operation.

    1. Pre-check (STOP, cooldown, daily cap) — before LLM call
    2. Compose post via LLM
    3. Full safety check on candidate
    4. Post to platform
    5. Update outbox

    Exit codes:
        0 = posted successfully
        1 = error
        2 = blocked by pre-check (normal, not an error)
        3 = blocked by post-check (normal, not an error)
    """
    from src.persona.platform import resolve_platform

    memory = _build_memory(Path(args.db), Path(args.diary_dir))
    outbox = Outbox(db_path=Path(args.outbox_db))

    platform_name = args.platform
    try:
        platform = resolve_platform(platform_name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    guard = SafetyGuard(
        outbox=outbox,
        stop_file=Path(args.stop_file),
        max_length=platform.max_length,
    )

    # 1. Pre-check (before LLM call)
    passed, reason = guard.pre_check()
    if not passed:
        print(f"Skipped: {reason}")
        memory.close()
        outbox.close()
        sys.exit(2)

    # 2. Compose
    state = PersonaState(memory)
    llm = _resolve_llm(args.llm)
    composer = PostComposer(state, llm)
    candidate = composer.compose()
    print(f"Composed ({platform_name}): {candidate}")

    # 3. Full safety check on candidate
    passed, reason = guard.check(candidate)
    if not passed:
        outbox_id = outbox.save(candidate, status="blocked", block_reason=reason)
        print(f"Blocked: {reason} (outbox #{outbox_id})")
        memory.close()
        outbox.close()
        sys.exit(3)

    # 4. Save + post
    outbox_id = outbox.save(candidate, status="ready")

    try:
        platform.login()
        uri = platform.post(candidate)
        outbox.mark_posted(outbox_id, uri)
        print(f"Posted: {uri} (outbox #{outbox_id})")
    except Exception as exc:
        outbox.mark_failed(outbox_id, str(exc))
        print(f"Failed: {exc} (outbox #{outbox_id})", file=sys.stderr)
        memory.close()
        outbox.close()
        sys.exit(1)

    memory.close()
    outbox.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the persona CLI."""
    parser = argparse.ArgumentParser(
        prog="persona",
        description="Autonomous persona system — local execution",
    )
    parser.add_argument(
        "--db", default=str(_DEFAULT_DB), help="Path to SQLite database",
    )
    parser.add_argument(
        "--diary-dir", default=str(_DEFAULT_DIARY), help="Path to diary directory",
    )
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run one observe → reflect cycle")
    run_parser.add_argument(
        "--input", "-i", default=None, help="Path to input text file (default: stdin)",
    )
    run_parser.add_argument(
        "--llm", default="stub", choices=["stub", "claude"],
        help="LLM adapter: 'stub' (offline) or 'claude' (requires ANTHROPIC_API_KEY)",
    )
    run_parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show raw LLM response for debugging",
    )

    post_parser = sub.add_parser("post", help="Compose and post to a platform")
    post_parser.add_argument(
        "--platform", default="x", choices=["x", "bluesky"],
        help="Target platform: 'x' or 'bluesky'",
    )
    post_parser.add_argument(
        "--llm", default="stub", choices=["stub", "claude"],
        help="LLM adapter: 'stub' (offline) or 'claude' (requires ANTHROPIC_API_KEY)",
    )
    post_parser.add_argument(
        "--dry-run", action="store_true",
        help="Compose and check safety, but do not actually post",
    )
    post_parser.add_argument(
        "--outbox-db", default=str(_DEFAULT_OUTBOX_DB),
        help="Path to outbox SQLite database",
    )
    post_parser.add_argument(
        "--stop-file", default=str(_DEFAULT_STOP_FILE),
        help="Path to emergency stop file",
    )

    auto_parser = sub.add_parser(
        "autopost-once", help="Guarded single-post cycle (for cron/launchd)",
    )
    auto_parser.add_argument(
        "--platform", default="x", choices=["x", "bluesky"],
        help="Target platform: 'x' or 'bluesky'",
    )
    auto_parser.add_argument(
        "--llm", default="claude", choices=["stub", "claude"],
        help="LLM adapter (default: claude for autonomous use)",
    )
    auto_parser.add_argument(
        "--outbox-db", default=str(_DEFAULT_OUTBOX_DB),
        help="Path to outbox SQLite database",
    )
    auto_parser.add_argument(
        "--stop-file", default=str(_DEFAULT_STOP_FILE),
        help="Path to emergency stop file",
    )

    sub.add_parser("status", help="Show persona internal state")

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the persona CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        cmd_run(args)
    elif args.command == "post":
        cmd_post(args)
    elif args.command == "autopost-once":
        cmd_autopost_once(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)
