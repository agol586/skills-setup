"""Normalize invocation policy while preserving skill content and YAML metadata."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import re
import shlex


def yaml_parser():
    try:
        from ruamel.yaml import YAML
    except ImportError as exc:
        requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
        raise RuntimeError(f"Install the Python dependencies first: python3 -m pip install -r {shlex.quote(str(requirements))}") from exc
    parser = YAML()
    parser.preserve_quotes = True
    return parser


def check_visibility_paths(skill: Path, root: Path) -> None:
    for path in (skill / "SKILL.md", skill / "agents", skill / "agents" / "openai.yaml"):
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise RuntimeError(f"Skill visibility path needs local file review: {path}")


def visibility_updates(skill: Path, root: Path) -> dict[Path, str]:
    check_visibility_paths(skill, root)
    parser = yaml_parser()

    def mapping(text: str, path: Path):
        try:
            value = parser.load(text)
        except Exception as exc:
            raise RuntimeError(f"Invalid skill YAML in {path}: {exc}") from exc
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise RuntimeError(f"Expected a YAML mapping in {path}")
        return value

    def render(value) -> str:
        output = StringIO()
        parser.dump(value, output)
        return output.getvalue()

    manifest = skill / "SKILL.md"
    if not manifest.is_file():
        raise RuntimeError(f"Installed skill manifest is missing: {manifest}")
    original = manifest.read_bytes().decode("utf-8")
    match = re.match(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|$)([\s\S]*)", original, re.M | re.S)
    if not match:
        raise RuntimeError(f"Missing skill frontmatter: {manifest}")
    frontmatter = mapping(match[1], manifest)
    updates = {}
    if "disable-model-invocation" in frontmatter:
        del frontmatter["disable-model-invocation"]
        updates[manifest] = "---\n" + render(frontmatter) + "---\n" + match[2]

    metadata_path = skill / "agents" / "openai.yaml"
    metadata = mapping(metadata_path.read_text(encoding="utf-8"), metadata_path) if metadata_path.exists() else {}
    policy = metadata.get("policy")
    if policy is None:
        policy = {}
        metadata["policy"] = policy
    if not isinstance(policy, dict):
        raise RuntimeError(f"Expected a policy mapping in {metadata_path}")
    if policy.get("allow_implicit_invocation") is not True:
        policy["allow_implicit_invocation"] = True
        updates[metadata_path] = render(metadata)
    return updates


def enable_model_invocation(skills: list[Path], root: Path, dry_run: bool) -> None:
    if dry_run:
        print("After installation: remove disable-model-invocation and set policy.allow_implicit_invocation: true for selected skills.")
        return
    # Validate the whole selection before changing any invocation metadata.
    updates = {}
    for skill in skills:
        updates.update(visibility_updates(skill, root))
    for path, content in updates.items():
        print(f"Enable model invocation: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
