#!/usr/bin/env python3
"""Validate pelican3d/1 files against SPEC.md, and pelicans/index.json against the files.

Usage: python3 tools/validate.py [pelicans]
Exits 1 when any file has a problem. Read-only.
"""
import hashlib, json, math, os, re, sys

SHAPES = {"box", "sphere", "cylinder", "cone", "torus", "group"}
PART_FIELDS = {"id", "parent", "shape", "position", "rotation", "scale", "color", "tube", "motion"}
MOTION_FIELDS = {"type", "axis", "per", "amount", "degrees", "phase"}
MAX_PARTS, MAX_DEPTH, MAX_BYTES = 200, 6, 200_000


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def vec3(v):
    return isinstance(v, list) and len(v) == 3 and all(number(x) for x in v)


def check_model(path):
    problems = []
    if os.path.getsize(path) > MAX_BYTES:
        return [f"file is larger than {MAX_BYTES} bytes"]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as error:
        return [f"not valid JSON: {str(error)[:80]}"]
    if not isinstance(data, dict) or data.get("format") != "pelican3d/1" or not isinstance(data.get("parts"), list):
        return ['top level must be {"format":"pelican3d/1","parts":[...]}']
    if set(data) - {"format", "parts"}:
        problems.append(f"unknown top-level fields {sorted(set(data) - {'format', 'parts'})}")
    parts = data["parts"]
    if not parts:
        problems.append("no parts")
    if len(parts) > MAX_PARTS:
        problems.append(f"{len(parts)} parts, the limit is {MAX_PARTS}")
    by_id = {}
    for part in parts:
        if not isinstance(part, dict) or not isinstance(part.get("id"), str) or not part["id"]:
            problems.append("every part needs a non-empty string id")
            continue
        if part["id"] in by_id:
            problems.append(f"duplicate id {part['id']!r}")
        by_id[part["id"]] = part
    for part in by_id.values():
        pid = part["id"]
        if set(part) - PART_FIELDS:
            problems.append(f"{pid}: unknown fields {sorted(set(part) - PART_FIELDS)}")
        if part.get("shape") not in SHAPES:
            problems.append(f"{pid}: shape {part.get('shape')!r} is not one of {sorted(SHAPES)}")
        if part.get("parent") is not None and part.get("parent") not in by_id:
            problems.append(f"{pid}: parent {part.get('parent')!r} does not exist")
        for key in ("position", "rotation", "scale"):
            if key in part and not vec3(part[key]):
                problems.append(f"{pid}: {key} must be three finite numbers")
        if "tube" in part and not (number(part["tube"]) and 0 < part["tube"] <= 0.5):
            problems.append(f"{pid}: tube must be a number in (0, 0.5]")
        if part.get("shape") != "group" and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(part.get("color", ""))):
            problems.append(f"{pid}: color must look like #rrggbb")
        motion = part.get("motion")
        if motion is None:
            continue
        if not isinstance(motion, dict) or set(motion) - MOTION_FIELDS:
            problems.append(f"{pid}: motion has unknown fields")
        elif motion.get("type") not in ("spin", "swing") or motion.get("axis") not in ("x", "y", "z") \
                or motion.get("per") not in ("meter", "second") or not number(motion.get("amount")):
            problems.append(f"{pid}: motion needs type spin|swing, axis x|y|z, per meter|second and a numeric amount")
        elif motion["type"] == "swing" and not number(motion.get("degrees")):
            problems.append(f"{pid}: a swing needs numeric degrees")
        elif "phase" in motion and not number(motion["phase"]):
            problems.append(f"{pid}: phase must be a number")

    def depth(pid, seen=()):
        part = by_id.get(pid)
        if part is None or part.get("parent") is None:
            return 1
        if pid in seen:
            return 99
        return 1 + depth(part["parent"], seen + (pid,))

    deepest = max((depth(pid) for pid in by_id), default=0)
    if deepest >= 99:
        problems.append("parent links form a loop")
    elif deepest > MAX_DEPTH:
        problems.append(f"nesting is {deepest} levels deep, the limit is {MAX_DEPTH}")
    return problems


def check_index(folder, files):
    path = os.path.join(folder, "index.json")
    try:
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)["pelicans"]
    except Exception as error:
        return [f"index.json cannot be read: {str(error)[:80]}"]
    problems, listed = [], set()
    for entry in entries:
        name = os.path.basename(str(entry.get("file", "")))
        listed.add(name)
        for key in ("id", "name", "author", "date", "file", "sha256", "license"):
            if not entry.get(key):
                problems.append(f"{entry.get('id', '?')}: index entry is missing {key}")
        if name not in files:
            problems.append(f"{entry.get('id', '?')}: {entry.get('file')} does not exist")
        elif hashlib.sha256(open(os.path.join(folder, name), "rb").read()).hexdigest() != entry.get("sha256"):
            problems.append(f"{entry.get('id', '?')}: sha256 does not match the file")
    for name in sorted(files - listed):
        problems.append(f"{name} is not listed in index.json")
    return problems


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "pelicans"
    files = {n for n in os.listdir(folder) if n.endswith(".json") and n != "index.json"}
    failed = False
    for name in sorted(files):
        problems = check_model(os.path.join(folder, name))
        failed = failed or bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {name}" + "".join(f"\n       {p}" for p in problems[:8]))
    problems = check_index(folder, files)
    failed = failed or bool(problems)
    print(f"{'FAIL' if problems else 'ok  '} index.json" + "".join(f"\n       {p}" for p in problems[:8]))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
