#!/usr/bin/env python3
"""Validate pelican3d/1 files against SPEC.md, and pelicans/index.json against the files.

The rules are the ones the game applies when it reads this register, so a register that passes here
is taken in whole by the game: field whitelists, number ranges, the resting bounding box, index entry
formats, file paths, sizes and hashes. Anything else in pelicans/ is reported too: the folder holds data only.

Usage: python3 tools/validate.py [pelicans]
Exits 1 when any file has a problem. Read-only.
"""
import hashlib, json, math, os, re, stat, sys

MODEL_FORMAT, REGISTRY_FORMAT = "pelican3d/1", "pelican-registry/1"
SHAPES = {"box", "sphere", "cylinder", "cone", "torus", "group"}
PART_FIELDS = {"id", "parent", "shape", "position", "rotation", "scale", "color", "tube", "motion"}
MOTION_FIELDS = {"type", "axis", "per", "amount", "degrees", "phase"}
MAX_PARTS, MAX_DEPTH, MAX_ID = 200, 6, 48
LIMITS = {"position": 10, "rotation": 3600, "scale": 10}
MAX_AMOUNT, MAX_DEGREES, MAX_PHASE = 20, 180, 2
TUBE_MIN, TUBE_MAX = 0.005, 0.5
BOX_MIN, BOX_MAX = (-3, -1, -2), (3, 5, 2)
MAX_MODEL_BYTES, MAX_INDEX_BYTES, MAX_ENTRIES, MAX_TOTAL_BYTES = 200_000, 262_144, 64, 3_000_000

REQUIRED = ("id", "name", "author", "date", "file", "sha256", "license")
OPTIONAL = ("kind", "source", "generatedVia", "effort", "note")
CONTROL = re.compile("[\u0000-\u001f\u007f  ]")
SOURCE = re.compile(r"https://github\.com/[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}")


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def units(s):
    """Length as the game (JavaScript) counts it: UTF-16 code units."""
    return len(s.encode("utf-16-le")) // 2


def text(v, limit):
    return isinstance(v, str) and 0 < units(v) <= limit and not CONTROL.search(v)


def real_date(v):
    m = isinstance(v, str) and re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
    if not m:
        return False
    y, mo, d = (int(x) for x in m.groups())
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return 1 <= mo <= 12 and 1 <= d <= days[mo - 1]


def load_json(data):
    def reject(token):
        raise ValueError(f"{token} is not JSON")
    return json.loads(data.decode("utf-8"), parse_constant=reject)


def read_small(root, rel, limit):
    """Bytes of a plain file inside root (no symlink, no directory, real path inside root, at most limit bytes)."""
    path = os.path.join(root, rel)
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError("not a plain file (symlink or directory)")
    if info.st_size > limit:
        raise ValueError(f"larger than {limit} bytes")
    real, base = os.path.realpath(path), os.path.realpath(root)
    if real != base and not real.startswith(base + os.sep):
        raise ValueError("real path leaves the register")
    with open(path, "rb") as f:
        return f.read()


# ---------- resting pose (same maths as the game: T·R·S, R = Rx·Ry·Rz, scale not inherited) ----------

def axis_rotation(axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    m = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    i, j = (axis + 1) % 3, (axis + 2) % 3
    m[i][i] = m[j][j] = c
    m[i][j], m[j][i] = -s, s
    return m


def matmul(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]


def compose(parent, local):
    (pr, pt), (lr, lt) = parent, local
    return matmul(pr, lr), [pt[r] + sum(pr[r][k] * lt[k] for k in range(3)) for r in range(3)]


def resting_box(parts):
    """World bounding box of all primitives at distance 0 and time 0, or None when there is no geometry."""
    by_id, poses = {p["id"]: p for p in parts}, {}

    def pose(pid):
        if pid in poses:
            return poses[pid]
        p, d = by_id[pid], math.pi / 180
        rx, ry, rz = (axis_rotation(a, x * d) for a, x in enumerate(p.get("rotation", [0, 0, 0])))
        local = (matmul(rx, matmul(ry, rz)), list(p.get("position", [0, 0, 0])))
        world = compose(pose(p["parent"]), local) if p.get("parent") is not None else local
        motion = p.get("motion")
        if motion is not None:
            angle = 0.0
            if motion["type"] == "swing":
                angle = motion["degrees"] * d * math.sin(2 * math.pi * motion.get("phase", 0))
            world = compose(world, (axis_rotation("xyz".index(motion["axis"]), angle), [0, 0, 0]))
        poses[pid] = world
        return world

    low, high = [math.inf] * 3, [-math.inf] * 3
    for p in parts:
        if p["shape"] == "group":
            continue
        rot, move = pose(p["id"])
        tube = p.get("tube", 0.06)
        half = [0.5 + tube, 0.5 + tube, tube] if p["shape"] == "torus" else [0.5, 0.5, 0.5]
        scale = p.get("scale", [1, 1, 1])
        for k in range(8):
            corner = [(1 if k >> a & 1 else -1) * half[a] * scale[a] for a in range(3)]
            for r in range(3):
                v = move[r] + sum(rot[r][c] * corner[c] for c in range(3))
                low[r], high[r] = min(low[r], v), max(high[r], v)
    return None if low[0] == math.inf else (low, high)


# ---------- one pelican3d/1 file ----------

def check_parts(parts):
    problems, by_id = [], {}
    for part in parts:
        if not isinstance(part, dict):
            problems.append("every part must be an object")
            continue
        pid = part.get("id")
        if not isinstance(pid, str) or not 0 < units(pid) <= MAX_ID:
            problems.append(f"every part needs a string id of 1 to {MAX_ID} characters")
            continue
        if pid in by_id:
            problems.append(f"duplicate id {pid!r}")
        by_id[pid] = part
        if set(part) - PART_FIELDS:
            problems.append(f"{pid}: unknown fields {sorted(set(part) - PART_FIELDS)}")
        shape = part.get("shape")
        if shape not in SHAPES:
            problems.append(f"{pid}: shape {shape!r} is not one of {sorted(SHAPES)}")
        if part.get("parent") is not None and not isinstance(part["parent"], str):
            problems.append(f"{pid}: parent must be a string or null")
        for key, limit in LIMITS.items():
            v = part.get(key)
            if key in part and not (isinstance(v, list) and len(v) == 3 and all(number(x) and abs(x) <= limit for x in v)):
                problems.append(f"{pid}: {key} must be three finite numbers within ±{limit}")
        if (shape != "group" or "color" in part) and not (isinstance(part.get("color"), str) and re.fullmatch(r"#[0-9a-fA-F]{6}", part["color"])):
            problems.append(f"{pid}: color must look like #rrggbb")
        if "tube" in part and not (shape == "torus" and number(part["tube"]) and TUBE_MIN <= part["tube"] <= TUBE_MAX):
            problems.append(f"{pid}: tube is only for a torus and must be a number in [{TUBE_MIN}, {TUBE_MAX}]")
        problems += [f"{pid}: {p}" for p in check_motion(part.get("motion"))]
    for pid, part in by_id.items():
        parent = part.get("parent")
        if isinstance(parent, str) and parent not in by_id:
            problems.append(f"{pid}: parent {parent!r} does not exist")
    if problems:
        return problems, None
    for pid in by_id:
        depth, cur = 1, by_id[pid]
        while cur.get("parent") is not None:
            cur, depth = by_id[cur["parent"]], depth + 1
            if cur is by_id[pid] or depth > 64:
                return ["parent links form a loop"], None
        if depth > MAX_DEPTH:
            return [f"nesting is {depth} levels deep, the limit is {MAX_DEPTH}"], None
    return [], by_id


def check_motion(motion):
    if motion is None:
        return []
    if not isinstance(motion, dict) or set(motion) - MOTION_FIELDS:
        return ["motion must be an object with only " + ", ".join(sorted(MOTION_FIELDS))]
    problems = []
    if motion.get("type") not in ("spin", "swing") or motion.get("axis") not in ("x", "y", "z") or motion.get("per") not in ("meter", "second"):
        problems.append("motion needs type spin|swing, axis x|y|z and per meter|second")
    if not (number(motion.get("amount")) and abs(motion["amount"]) <= MAX_AMOUNT):
        problems.append(f"motion amount must be a number within ±{MAX_AMOUNT}")
    if "degrees" in motion and not (number(motion["degrees"]) and abs(motion["degrees"]) <= MAX_DEGREES):
        problems.append(f"motion degrees must be a number within ±{MAX_DEGREES}")
    if "phase" in motion and not (number(motion["phase"]) and -MAX_PHASE <= motion["phase"] <= MAX_PHASE):
        problems.append(f"motion phase must be a number in [-{MAX_PHASE}, {MAX_PHASE}]")
    if motion.get("type") == "swing" and "degrees" not in motion:
        problems.append("a swing needs degrees")
    return problems


def check_model(path):
    if os.path.getsize(path) > MAX_MODEL_BYTES:
        return [f"file is larger than {MAX_MODEL_BYTES} bytes"]
    try:
        with open(path, "rb") as f:
            data = load_json(f.read())
    except Exception as error:
        return [f"not valid JSON: {str(error)[:80]}"]
    if not isinstance(data, dict) or data.get("format") != MODEL_FORMAT or not isinstance(data.get("parts"), list):
        return [f'top level must be {{"format":"{MODEL_FORMAT}","parts":[...]}}']
    if set(data) - {"format", "parts"}:
        return [f"unknown top-level fields {sorted(set(data) - {'format', 'parts'})}"]
    parts = data["parts"]
    if not parts:
        return ["no parts"]
    if len(parts) > MAX_PARTS:
        return [f"{len(parts)} parts, the limit is {MAX_PARTS}"]
    problems, by_id = check_parts(parts)
    if problems:
        return problems
    box = resting_box(list(by_id.values()))
    if box is None:
        return ["no geometry: every part is a group"]
    low, high = box
    if any(low[a] < BOX_MIN[a] or high[a] > BOX_MAX[a] for a in range(3)):
        shown = ", ".join(f"{'xyz'[a]} {low[a]:.2f}..{high[a]:.2f}" for a in range(3))
        return [f"at rest the model spans {shown}; it must fit in x -3..3, y -1..5, z -2..2"]
    return []


# ---------- pelicans/index.json ----------

def check_entry(e):
    if not isinstance(e, dict):
        return "entry is not an object"
    unknown = [k for k in e if k not in REQUIRED and k not in OPTIONAL]
    if unknown:
        return f"unknown field {unknown[0]}"
    missing = [k for k in REQUIRED if k not in e]
    if missing:
        return f"missing {missing[0]}"
    if not (isinstance(e["id"], str) and re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,47}", e["id"])):
        return "id must be lowercase letters, digits, dots and hyphens, at most 48 characters"
    if re.fullmatch(r"u\d+", e["id"]):
        return "ids like u<number> are reserved for shapes players draw"
    if not text(e["name"], 60):
        return "name must be 1 to 60 characters without control characters"
    if not text(e["author"], 60):
        return "author must be 1 to 60 characters without control characters"
    if not real_date(e["date"]):
        return "date must be a real YYYY-MM-DD date"
    if e["file"] != f"pelicans/{e['id']}.json":
        return "file must be exactly pelicans/<id>.json"
    if not (isinstance(e["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", e["sha256"])):
        return "sha256 must be 64 lowercase hex digits"
    if not (isinstance(e["license"], str) and re.fullmatch(r"[A-Za-z0-9.+-]{1,40}", e["license"])):
        return "license must be an SPDX identifier, at most 40 characters"
    if "kind" in e and not (isinstance(e["kind"], str) and re.fullmatch(r"[a-z-]{1,20}", e["kind"])):
        return "kind must be lowercase letters and hyphens, at most 20 characters"
    if e.get("generatedVia") is not None and not text(e["generatedVia"], 60):
        return "generatedVia must be null or 1 to 60 characters"
    if e.get("note") is not None and not text(e["note"], 300):
        return "note must be null or 1 to 300 characters"
    if e.get("effort") is not None and not (isinstance(e["effort"], str) and re.fullmatch(r"[a-z]{1,12}", e["effort"])):
        return "effort must be null or lowercase letters, at most 12 characters"
    if e.get("source") is not None and not (isinstance(e["source"], str) and SOURCE.fullmatch(e["source"])):
        return "source must be null or https://github.com/<owner>/<repo>"
    return None


def check_index(folder):
    root = os.path.dirname(os.path.abspath(folder))
    rel = os.path.basename(os.path.abspath(folder))
    try:
        index = load_json(read_small(root, f"{rel}/index.json", MAX_INDEX_BYTES))
    except Exception as error:
        return [f"index.json cannot be read: {str(error)[:80]}"]
    if not isinstance(index, dict) or index.get("format") != REGISTRY_FORMAT or not isinstance(index.get("pelicans"), list):
        return [f'index.json must be {{"format":"{REGISTRY_FORMAT}","pelicans":[...]}}']
    entries = index["pelicans"]
    if len(entries) > MAX_ENTRIES:
        return [f"{len(entries)} entries, the limit is {MAX_ENTRIES}"]
    problems, seen, total = [], set(), 0
    named = {os.path.basename(e["file"]) for e in entries if isinstance(e, dict) and isinstance(e.get("file"), str)}
    for e in entries:
        name = e["id"][:48] if isinstance(e, dict) and isinstance(e.get("id"), str) else "?"
        bad = check_entry(e)
        if bad is None and e["id"] in seen:
            bad = "id appears twice"
        if bad is None:
            try:
                data = read_small(root, e["file"], MAX_MODEL_BYTES)
            except Exception as error:
                bad = f"{e['file']}: {str(error)[:80]}"
        if bad is None and total + len(data) > MAX_TOTAL_BYTES:
            bad = f"all files together pass {MAX_TOTAL_BYTES} bytes"
        if bad is None and hashlib.sha256(data).hexdigest() != e["sha256"]:
            bad = "sha256 does not match the file"
        if bad:
            problems.append(f"{name}: {bad}")
            continue
        seen.add(e["id"])
        total += len(data)
    for other in sorted(set(os.listdir(folder)) - named - {"index.json"}):
        problems.append(f"{other} is not a listed pelican; this folder holds only listed pelican3d/1 files")
    return problems


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "pelicans"
    files = sorted(n for n in os.listdir(folder) if n.endswith(".json") and n != "index.json" and os.path.isfile(os.path.join(folder, n)))
    failed = False
    for name in files:
        problems = check_model(os.path.join(folder, name))
        failed = failed or bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {name}" + "".join(f"\n       {p}" for p in problems[:8]))
    problems = check_index(folder)
    failed = failed or bool(problems)
    print(f"{'FAIL' if problems else 'ok  '} index.json" + "".join(f"\n       {p}" for p in problems[:8]))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
