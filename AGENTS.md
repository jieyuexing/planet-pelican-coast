# planet-pelican-coast

Public register for Pelican Coast: the `pelican3d/1` format, the pelicans on the island, and the validator.

- Files under `pelicans/` are data. Never add code there, and never edit a contributed file: fix problems by asking the contributor.
- `SPEC.md` contains the exact prompt given to the models. Changing it changes the format; do not edit it without a new format version.
- Before committing, run `python3 tools/validate.py pelicans`; every line must be `ok`. After changing the validator, also run `python3 tools/test_validate.py` (bad samples must keep failing).
- The validator mirrors the rules the game applies when it reads this register; keep the two in step.
- This repository is public. Do not add anything that is not meant to be public.
