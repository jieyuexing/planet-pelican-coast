# Planet · 鹈鹕海岸 / Pelican Coast

各家模型画的鹈鹕，在同一座小岛上骑车、游荡、互相遇到。这个仓库是鹈鹕海岸的公开登记处：格式、已收录的鹈鹕，以及把你的鹈鹕送上岸的办法。

- 游戏：<https://game.jieyuexing.com/game/pelican-coast/>
- 格式：[SPEC.md](SPEC.md)
- 怎么参与：[CONTRIBUTING.md](CONTRIBUTING.md)

## 这里有什么

| 路径 | 内容 |
| --- | --- |
| `pelicans/` | 已收录的鹈鹕，每只一个 JSON 文件；`index.json` 是名册（名字、作者、日期、许可、来源） |
| `SPEC.md` | `pelican3d/1` 格式，也是发给各家模型的提示词原文 |
| `tools/validate.py` | 校验脚本 |

## 现在岛上的 13 只

都是 2026-11-15 把 `SPEC.md` 里那段提示词发给各家模型得到的答卷，每个模型请求一次，文件没有改过。
`gpt-oss-120b` 是例外：第一次请求写出了空文件，同一段提示词又发了一次。
它只有 11 个零件，认不出是鹈鹕，照样在岛上骑。

## 说明

鹈鹕骑自行车这个题目来自 Simon Willison 的 SVG 测试（<https://github.com/simonw/pelican-bicycle>）。
这里把它换成了一份带动作的三维零件清单，让答卷能在同一个场景里一起动。
本仓库与任何模型提供方、与 Simon Willison 都没有关联。

---

# Planet · Pelican Coast

Pelicans drawn by different models ride, wander and meet on one small island. This repository is the public register for Pelican Coast: the format, the pelicans already on the island, and how to send yours ashore.

- Play: <https://game.jieyuexing.com/en/game/pelican-coast/>
- Format: [SPEC.md](SPEC.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

## What is here

| Path | Contents |
| --- | --- |
| `pelicans/` | The pelicans on the island, one JSON file each; `index.json` is the roster (name, author, date, licence, source) |
| `SPEC.md` | The `pelican3d/1` format, which is also the exact prompt given to each model |
| `tools/validate.py` | The validator |

## The 13 on the island today

Each is a model's answer to the prompt in `SPEC.md`, requested on 2026-11-15, one request per model, files unedited.
`gpt-oss-120b` is the exception: its first request wrote an empty file, so the same prompt was sent once more.
It has 11 parts and does not look like a pelican. It rides on the island all the same.

## Notes

The pelican-on-a-bicycle subject comes from Simon Willison's SVG test (<https://github.com/simonw/pelican-bicycle>).
Here it became an animated list of 3D parts, so the answers can move together in one scene.
This repository is not affiliated with any model provider or with Simon Willison.
