# ComfyUI-Mie-Craft

**Mie's creation line.** Everything that turns an asset into a plan.

```bash
pip install -e <this directory>
```

It sits on top of `ComfyUI-Mie-LLM` and `ComfyUI-Mie-Prompt`.

---

## What is in it

| Module | |
|---|---|
| `assets/library.py` | the character and scene library on disk |
| `assets/script_asset.py` | the script assets that sit above the library |
| `script/contract.py` | the script contract - the shape of a script asset, and the deterministic H3 compilation |
| `script/builder.py` | the **zero-LLM plan assembler**: a script asset plus the wired assets become a byte-stable `plan_json` |
| `script/generator.py` | the one checked LLM grouping pass that writes a script asset |
| `script/critic.py`, `script/critic_llm.py`, `script/review.py` | the continuity critic, in its deterministic and its model form, plus the asset independence review |
| `script/dialogue.py` | the dialogue model, the span validation and the pacing budget |
| `h3_loop_prompts.py` | the deterministic plan-building layer for the H3 loop track |

## The asset roster socket type

It is defined here rather than in a pack, so a plan built by the H3 engine
and a plan built by MieNodes are the same shape and the two can be wired
together.

## The bundled assets

The library resolves them against a plugin root. A ComfyUI pack that ships
its own seed library sets `MIE_PLUGIN_ROOT` to its own root before the
library is used; otherwise this package's own root is used.

## Licence

GPL-3.0.


## 发布 / Releasing

```
python -m build
python -m twine upload dist/*
python tools/notify_mirrors.py --wait 300     # 让国内 PyPI 镜像收录
```

**第三步是发布流程的一部分, 不是可选项。** 国内 PyPI 镜像 (阿里云 / 华为云 / 清华)
对 PyPI 是镜像同步, 新版本通常要等它们自己的同步周期才出现; 期间按
`requirements.txt` 里的版本号去装会拿到 `No matching distribution found`。
这些镜像**有按需回源机制** —— 请求一次该包的 simple index 就能触发它们去 PyPI
拉取, 约 1 分钟内收录 (2026-11-18 实测: 请求后 61 秒华为云就从 0.1.x 变成
0.2.0)。所以发布后跑一次 `tools/notify_mirrors.py`, 把等待从「同步周期」压到
「约一分钟」。

## 依赖声明的规矩

**包只声明依赖, 不指定用哪个镜像源。** `requirements.txt` / `pyproject.toml` 里
只写包名和版本约束, **不写 `-i` / `--index-url` / `extra-index-url`** —— 镜像
是**部署环境**的选择 (启动器那边按用户在「启动与更新页」配的来), 包管不了也不该管。
写出镜像源会导致: 换环境装不上、用户没法用官方源、镜像滞后时把包锁死在旧版本。

同理, 装包的那一侧 (启动器的伴生服务安装链) 负责按配置选镜像, 镜像上没有的
版本由它回退官方 PyPI —— 不需要包自己操心。
