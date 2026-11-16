# pelican3d/1

A pelican is one JSON file: a list of simple parts, each with a place, a colour and (optionally) a motion.
Anything that follows this format can live on the coast — it does not have to look like a pelican.

The text below is, word for word, the prompt that was given to each model in `pelicans/`. It is also the definition of the format.

```
Generate an animated 3D model of a pelican riding a bicycle.

Output only a JSON object in this format, nothing else:
{"format":"pelican3d/1","parts":[{"id":"front_wheel","parent":null,"shape":"torus","position":[x,y,z],"rotation":[rx,ry,rz],"scale":[sx,sy,sz],"color":"#rrggbb","motion":{"type":"spin","axis":"z","per":"meter","amount":0.45}}]}

Coordinates
- Right-handed, units are meters, Y is up, the ground is y = 0, and the bicycle travels toward +X.
- Keep the whole model within x in [-1.5, 1.5], y in [0, 2.5], z in [-0.8, 0.8].

Parts
- "id" is a unique string. "parent" is the id of another part or null. A part's "position" and "rotation" are relative to its parent (or to the model when parent is null). Children follow their parent's position, rotation and motion. "scale" only sizes the part's own primitive and is NOT inherited by children.
- "shape" is one of: box, sphere, cylinder, cone, torus, group.
  box = 1 x 1 x 1 cube centered at the part origin; sphere = radius 0.5; cylinder = radius 0.5, height 1, axis along Y; cone = base radius 0.5, height 1, axis along Y, tip toward +Y; torus = ring radius 0.5 lying in the XY plane (its axis is Z), with an optional "tube" field (tube radius before scaling, default 0.06); group = no geometry, only a pivot for its children (omit "scale" and "color").
- "rotation" is Euler angles in degrees with the same meaning as the three.js default order 'XYZ' (R = Rx * Ry * Rz).
- "color" is an opaque hex string. No textures.

Motion (optional, this is what makes it move)
- "motion" rotates the part (and its children) around one of its own local axes, through the part's origin. Use a group as a pivot when the rotation center is not the center of a primitive (for example a hip, a shoulder or the crank axle).
- {"type":"spin","axis":"x|y|z","per":"meter|second","amount":turns} turns continuously: "amount" full turns per meter travelled or per second. A wheel of radius r should spin about 1 / (2 * pi * r) turns per meter. Use the sign that makes it roll forward toward +X.
- {"type":"swing","axis":"x|y|z","per":"meter|second","amount":cycles,"degrees":angle,"phase":0..1} swings back and forth by +/- "degrees", "amount" cycles per meter travelled or per second, starting at "phase" of a cycle.
- Things driven by riding (wheels, crank, pedals, legs) should use "per":"meter" so they stop when the bicycle stops. Things that are alive (wings, head, tail, beak pouch) can use "per":"second".

Limits: at most 200 parts including groups, nesting at most 6 levels deep, no other fields.
```

## Limits the validator enforces

- top level: exactly `format` and `parts`
- at most 200 parts including groups, nesting at most 6 levels deep, file at most 200 KB
- `shape`: `box`, `sphere`, `cylinder`, `cone`, `torus`, `group`
- `position`, `rotation`, `scale`: three finite numbers each
- `color`: `#rrggbb` (not needed on a `group`)
- `tube`: a number in (0, 0.5]
- `motion`: `type` spin or swing, `axis` x, y or z, `per` meter or second, numeric `amount`; a swing also needs `degrees`
- no other fields anywhere

Run `python3 tools/validate.py` to check a file.

## How the game uses it

The game never runs code from a pelican file. It reads the numbers, builds the shapes and plays the motions.
How a pelican behaves on the coast (where it rides, when it stops, how it bumps into others) comes only from the geometry of its parts.
Part ids and names are never read for behaviour, so an abstract shape is treated exactly like a pelican.
