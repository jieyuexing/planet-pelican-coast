# 怎么参与 / Contributing

## 送一只鹈鹕上岸

1. 照 [SPEC.md](SPEC.md) 写一个 JSON 文件。可以自己写，可以让任何模型写，也可以不是鹈鹕。
2. 运行 `python3 tools/validate.py`，没有 `FAIL` 再提交。
3. 把文件放到 `pelicans/<你的 id>.json`，并在 `pelicans/index.json` 里加一条：`id`、`name`、`author`、`date`、`file`、`sha256`、`license`；有来源仓库就写 `source`。
4. 提一个 Pull Request。检查通过并合并后，它会随游戏的下一次更新出现在岛上，详情卡上写着你的名字和来源链接。

不方便提 Pull Request 的话，开一个 issue（选「送一只鹈鹕」），把 JSON 贴进去也行。

## 几条约定

- 文件里只有数据。游戏不会运行其中的任何代码，带多余字段的文件过不了校验。
- 你提交的文件按你在 `index.json` 里写的许可公开；没有偏好就写 `CC-BY-4.0`。请只提交你有权公开的内容。
- 一个 Pull Request 里放一只或几只都行，每只一个文件。
- 想撤下自己的鹈鹕，开一个 issue 说一声就行。

## 你已经有一个三维鹈鹕的仓库

很多人让模型写过「鹈鹕骑自行车」的三维网页。那些页面是程序，不是这份格式的数据，游戏不能直接运行它们。
如果你愿意让它上岸，开一个 issue（选「我有一个鹈鹕仓库」）留下仓库地址，说明你是作者并同意展示。怎么把它搬上岛，我们还在试。

---

## Send a pelican ashore

1. Write a JSON file that follows [SPEC.md](SPEC.md). Write it yourself, ask any model, and it does not have to be a pelican.
2. Run `python3 tools/validate.py` and fix anything marked `FAIL`.
3. Put the file at `pelicans/<your-id>.json` and add an entry to `pelicans/index.json`: `id`, `name`, `author`, `date`, `file`, `sha256`, `license`; add `source` if there is a repository.
4. Open a pull request. Once it passes the check and is merged, it appears on the island with the game's next update, with your name and source link on its card.

If a pull request is inconvenient, open an issue ("Send a pelican") and paste the JSON.

## Ground rules

- Files contain data only. The game never runs code from them, and a file with extra fields fails validation.
- Your file is published under the licence you write in `index.json`; use `CC-BY-4.0` if you have no preference. Please submit only what you have the right to publish.
- One pull request can carry one pelican or several, one file each.
- To take your pelican down, open an issue.

## You already have a 3D pelican repository

Many people have asked a model for a 3D "pelican riding a bicycle" page. Those pages are programs, not data in this format, and the game cannot run them as they are.
If you would like yours on the island, open an issue ("I have a pelican repository") with the address, and say that you are the author and agree to it being shown. We are still working out how to bring these ashore.
