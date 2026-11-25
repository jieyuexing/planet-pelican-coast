#!/usr/bin/env python3
"""Bad samples for tools/validate.py: the register as it is must pass, and every broken copy must fail.

Usage: python3 tools/test_validate.py
Each case copies pelicans/ to a temporary folder, breaks one thing and runs the validator on the copy.
"""
import copy, hashlib, json, os, re, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER = os.path.join(os.path.dirname(HERE), "pelicans")
BASE = "claude-opus-5-5"


def run(folder):
    result = subprocess.run([sys.executable, "-I", os.path.join(HERE, "validate.py"), folder], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


class Register:
    """A writable copy of pelicans/ in a temporary folder."""

    def __init__(self):
        self.root = tempfile.mkdtemp()
        self.folder = os.path.join(self.root, "pelicans")
        shutil.copytree(REGISTER, self.folder)
        with open(os.path.join(self.folder, "index.json"), encoding="utf-8") as f:
            self.index = json.load(f)
        with open(os.path.join(self.folder, f"{BASE}.json"), encoding="utf-8") as f:
            self.model = json.load(f)

    def entry(self):
        return next(e for e in self.index["pelicans"] if e["id"] == BASE)

    def save(self):
        text = json.dumps(self.model)
        with open(os.path.join(self.folder, f"{BASE}.json"), "w", encoding="utf-8") as f:
            f.write(text)
        self.entry()["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.write_index()

    def write_index(self):
        with open(os.path.join(self.folder, "index.json"), "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2)

    def first(self, test):
        return next(p for p in self.model["parts"] if isinstance(p, dict) and test(p))


def model_case(change):
    """Break the model file; the index gets the new hash, so only the model is wrong."""
    def apply(reg):
        change(reg.model, reg)
        reg.save()
    return apply


def index_case(change):
    """Break index.json after the hashes are right, so only the index is wrong."""
    def apply(reg):
        reg.save()
        change(reg.index, reg.entry())
        reg.write_index()
    return apply


def leaf(model):
    parents = {p.get("parent") for p in model["parts"]}
    return next(p for p in model["parts"] if p["id"] not in parents)


BAD = {
    # pelican3d/1 files
    "id longer than 48": model_case(lambda m, r: leaf(m).update(id="x" * 49)),
    "position beyond 10": model_case(lambda m, r: m["parts"][0].update(position=[11, 0, 0])),
    "rotation beyond 3600": model_case(lambda m, r: m["parts"][0].update(rotation=[0, 4000, 0])),
    "scale beyond 10": model_case(lambda m, r: r.first(lambda p: p["shape"] != "group").update(scale=[11, 0.1, 0.1])),
    "group with a bad colour": model_case(lambda m, r: r.first(lambda p: p["shape"] == "group").update(color="red")),
    "tube on a box": model_case(lambda m, r: r.first(lambda p: p["shape"] == "box").update(tube=0.1)),
    "tube thinner than 0.005": model_case(lambda m, r: r.first(lambda p: p["shape"] == "torus").update(tube=0.001)),
    "motion amount beyond 20": model_case(lambda m, r: r.first(lambda p: p.get("motion")).update(motion={"type": "spin", "axis": "z", "per": "meter", "amount": 21})),
    "swing beyond 180 degrees": model_case(lambda m, r: r.first(lambda p: p.get("motion")).update(motion={"type": "swing", "axis": "z", "per": "second", "amount": 1, "degrees": 200})),
    "spin with non-numeric degrees": model_case(lambda m, r: r.first(lambda p: p.get("motion")).update(motion={"type": "spin", "axis": "z", "per": "meter", "amount": 1, "degrees": "x"})),
    "phase beyond 2": model_case(lambda m, r: r.first(lambda p: p.get("motion")).update(motion={"type": "swing", "axis": "z", "per": "second", "amount": 1, "degrees": 10, "phase": 3})),
    "swing without degrees": model_case(lambda m, r: r.first(lambda p: p.get("motion")).update(motion={"type": "swing", "axis": "z", "per": "second", "amount": 1})),
    "only groups": model_case(lambda m, r: m.update(parts=[{"id": "a", "parent": None, "shape": "group"}])),
    "too wide at rest": model_case(lambda m, r: m["parts"].append({"id": "plank", "parent": None, "shape": "box", "position": [0, 1, 0], "scale": [9, 0.1, 0.1], "color": "#ffffff"})),
    "below the ground at rest": model_case(lambda m, r: m["parts"].append({"id": "stake", "parent": None, "shape": "box", "position": [0, -2, 0], "scale": [0.1, 0.5, 0.1], "color": "#ffffff"})),
    "parent loop": model_case(lambda m, r: m["parts"].extend([{"id": "a", "parent": "b", "shape": "group"}, {"id": "b", "parent": "a", "shape": "group"}])),
    "part that is not an object": model_case(lambda m, r: m["parts"].append(7)),
    "unknown part field": model_case(lambda m, r: m["parts"][0].update(script="x")),
    # pelicans/index.json
    "entry that is not an object": index_case(lambda i, e: i["pelicans"].append("x")),
    "pelicans that is not a list": index_case(lambda i, e: i.update(pelicans={"a": 1})),
    "wrong index format": index_case(lambda i, e: i.update(format="pelican-registry/2")),
    "file with ..": index_case(lambda i, e: e.update(file=f"pelicans/../pelicans/{BASE}.json")),
    "file that does not match the id": index_case(lambda i, e: e.update(id="renamed")),
    "uppercase sha256": index_case(lambda i, e: e.update(sha256=e["sha256"].upper())),
    "id with an underscore": index_case(lambda i, e: e.update(id="bad_id")),
    "impossible date": index_case(lambda i, e: e.update(date="2026-02-30")),
    "name with a newline": index_case(lambda i, e: e.update(name="a\nb")),
    "name longer than 60": index_case(lambda i, e: e.update(name="n" * 61)),
    "author that is a number": index_case(lambda i, e: e.update(author=42)),
    "licence with a space": index_case(lambda i, e: e.update(license="CC BY")),
    "unknown entry field": index_case(lambda i, e: e.update(homepage="https://example.com")),
    "source outside GitHub": index_case(lambda i, e: e.update(source="https://example.com/a/b")),
    "the same id twice": index_case(lambda i, e: i["pelicans"].append(copy.deepcopy(e))),
}


class Validator(unittest.TestCase):
    def test_register_passes(self):
        code, out = run(REGISTER)
        self.assertEqual(code, 0, out)

    def test_untouched_copy_passes(self):
        reg = Register()
        reg.save()
        code, out = run(reg.folder)
        self.assertEqual(code, 0, out)

    def test_bad_samples_fail(self):
        for name, apply in BAD.items():
            with self.subTest(name):
                reg = Register()
                apply(reg)
                code, out = run(reg.folder)
                self.assertEqual(code, 1, out)
                self.assertNotIn("Traceback", out)

    def test_player_shape_id_fails(self):
        reg = Register()
        os.rename(os.path.join(reg.folder, f"{BASE}.json"), os.path.join(reg.folder, "u12.json"))
        reg.entry().update(id="u12", file="pelicans/u12.json")
        reg.write_index()
        code, out = run(reg.folder)
        self.assertEqual(code, 1, out)

    def test_stray_files_fail(self):
        for name in ("evil.js", "x.svg", "notes.txt"):
            with self.subTest(name):
                reg = Register()
                with open(os.path.join(reg.folder, name), "w") as f:
                    f.write("x")
                code, out = run(reg.folder)
                self.assertEqual(code, 1, out)

    def test_nan_fails(self):
        reg = Register()
        reg.save()
        path = os.path.join(reg.folder, f"{BASE}.json")
        with open(path, encoding="utf-8") as f:
            text = re.sub(r'"position": ?\[[^,\]]+', '"position":[NaN', f.read(), count=1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        code, out = run(reg.folder)
        self.assertEqual(code, 1, out)


if __name__ == "__main__":
    unittest.main()
