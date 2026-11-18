"""Host-neutral loop orchestration and per-call runtime isolation."""
import unittest
import contextlib
import io

class LoopGeneratorTests(unittest.TestCase):
    def test_runtime_is_per_instance(self):
        from mie_craft.loop_generator import H3LoopPromptEnhancer, LoopRuntime
        events = []
        first = H3LoopPromptEnhancer(object(), runtime=LoopRuntime(check_interrupt=events.append))
        second = H3LoopPromptEnhancer(object())
        first._check_interrupt("first")
        second._check_interrupt("second")
        self.assertEqual(["first"], events)

    def test_runtime_controls_cache_and_media(self):
        from mie_craft.loop_generator import H3LoopPromptEnhancer, LoopRuntime
        runtime = LoopRuntime(cache_root=lambda: "isolated-cache", image_urls=lambda image: ["data:image/png;base64,AAA"])
        enhancer = H3LoopPromptEnhancer(object(), runtime=runtime)
        self.assertEqual("isolated-cache", enhancer.runtime.cache_root())
        self.assertEqual(["data:image/png;base64,AAA"], enhancer.runtime.image_urls(object()))

    def test_data_url_references_need_no_tensor_stack(self):
        from mie_craft.loop_generator import H3LoopPromptEnhancer
        class Connector:
            def invoke(self, messages, **kwargs):
                return "A red ceramic cup with a white rim sits on a wooden table in soft natural light."
        enhancer = H3LoopPromptEnhancer(Connector())
        with contextlib.redirect_stdout(io.StringIO()):
            manifest, warnings = enhancer._caption_images(images=["data:image/png;base64,AAA"], ref_code="i2va", seed=3, force_recaption=True)
        self.assertEqual(1, len(manifest))
        self.assertIn("red ceramic cup", manifest[0]["about"])

if __name__ == "__main__":
    unittest.main()
