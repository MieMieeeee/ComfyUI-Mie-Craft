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
