"""A self-test that does not need ComfyUI.

The behavioural tests live in the MieNodes pack and in the H3 engine, which
both consume these packages through their shims. This is the floor: the
package imports, its public surface is there, and the prompt families it
ships are readable.
"""

PACKAGE = "mie_craft"


def main() -> int:
    module = __import__(PACKAGE)
    assert hasattr(module, "__version__"), "no version"
    print(PACKAGE, module.__version__)

    from mie_craft.assets import library, script_asset
    from mie_craft.script.contract import validate_v2, to_runtime
    from mie_craft.script.builder import assemble_from_sockets
    from mie_craft.script.critic import critique_warnings
    from mie_craft.script.dialogue import DialogueTurn
    assert library.DESCRIPTION_MAX_CHARS == 2000
    assert callable(assemble_from_sockets)

    print(PACKAGE, "self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
