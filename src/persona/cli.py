"""Persona CLI: local execution of observe/reflect cycles.

Usage:
    python -m src.persona run --input observed.txt
    python -m src.persona run --llm claude --input observed.txt
    python -m src.persona run              # reads from stdin, stub LLM
    python -m src.persona status           # show internal state summary

Default LLM is 'stub' (no network). Use '--llm claude' for real inference.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.persona.core import LlmCall, PersonaCore
from src.persona.memory import Memory
from src.persona.state import PersonaState

# Default paths
_DEFAULT_DB = Path("data/memory.db")
_DEFAULT_DIARY = Path("data/diary")


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

    sub.add_parser("status", help="Show persona internal state")

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the persona CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)
