#
# Copyright (C) 2026  Fabsgb (https://github.com/Fabsgb, https://codeberg.org/Fabsgb)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
import base64
import contextlib
import importlib.util
import io
import os
import runpy
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_IMAGE = b"local-health-check-image"


def load_script(filename: str, module_name: str):
    sys.path.insert(0, str(ROOT / "my-libs"))
    loader = SourceFileLoader(module_name, str(ROOT / filename))
    spec = importlib.util.spec_from_loader(module_name, loader)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BrowserContext:
    def __init__(self, browser=None):
        self.browser = browser or self

    def __enter__(self):
        return self.browser

    def __exit__(self, *_args):
        return False


class FakeOption:
    def __init__(self, options):
        self.options = options

    def wait_for(self):
        return None

    def locator(self, _selector):
        return self

    def count(self):
        return len(self.options)

    def evaluate_all(self, _script):
        return self.options


class ImageWorkflowChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_script("image_generator", "image_generator_workflow")
        cls.upscaler = load_script("upscale_image", "upscale_image_workflow")
        cls.info_script = load_script("get_image_infos", "get_image_infos_workflow")
        cls.api = load_script("image_api", "image_api_workflow")

    def _run_generator(
        self,
        root: Path,
        args: list[str],
        images: list[bytes],
        upscale_side_effect=None,
    ):
        module = self.generator
        temp_user = root.name.removeprefix("image_")
        image_output = []
        deadline = module.monotonic() + 120
        upscale_patch = (
            patch.object(module, "upscale_image", side_effect=upscale_side_effect)
            if upscale_side_effect is not None
            else patch.object(module, "upscale_image", return_value=b"upscaled-image")
        )

        def fake_browse(_browser, **kwargs):
            callback = kwargs["on_image_ready"]
            if callback is not None:
                for image in images:
                    callback(image, deadline)
            return True, images, deadline

        with (
            patch.object(module, "getuser", return_value=temp_user),
            patch.object(module, "chmod"),
            patch.object(module, "start_browser", return_value=BrowserContext()) as start,
            patch.object(module, "browse", side_effect=fake_browse) as browse,
            upscale_patch as upscale,
            patch.object(module, "subprocess_run") as preview,
            patch.object(module, "timed_input", return_value="yes"),
            patch.object(module, "output", side_effect=lambda value, **_kwargs: image_output.append(value)),
            patch.object(sys, "argv", ["image_generator", *args]),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as exit_info:
                module.run()

        self.assertEqual(exit_info.exception.code, 0)
        return SimpleNamespace(
            start=start,
            browse=browse,
            upscale=upscale,
            preview=preview,
            outputs=image_output,
        )

    def test_image_generator_writes_images_and_info_with_upscale_preview_toggles(self):
        with tempfile.TemporaryDirectory(prefix="image_health_") as temp_root:
            root = Path(temp_root)
            (root / "styles.txt").write_text("['Photo', 'Sketch']")
            (root / "shapes.txt").write_text("['Square', 'Portrait']")
            (root / "numbers.txt").write_text("['1', '2']")
            disk_dir = root / "disk"
            first = self._run_generator(
                root,
                [
                    "--prompt", "test",
                    "--negative-prompt", "test",
                    "--shape", "Square",
                    "--style", "Photo",
                    "--amount", "1",
                    "--timeout", "n+u+2",
                    "--info-file",
                    "--i-know-what-i-am-doing",
                    "--output-dir", str(disk_dir),
                ],
                [FIXTURE_IMAGE],
            )
            image_path = disk_dir / "image.jpg"
            self.assertEqual(image_path.read_bytes(), FIXTURE_IMAGE)
            self.assertIn("Prompt: test", (disk_dir / "info.txt").read_text())
            self.assertTrue(first.start.call_args.kwargs["headless"])
            self.assertTrue(first.browse.call_args.kwargs["proxy_warning"])
            self.assertTrue(first.browse.call_args.kwargs["select_dropdowns"])
            self.assertEqual(first.browse.call_args.kwargs["default_style"], "Photo")
            self.assertEqual(first.browse.call_args.kwargs["default_shape"], "Square")
            self.assertIsNone(first.browse.call_args.kwargs["on_image_ready"])
            self.assertFalse(first.preview.called)

            upscale_dir = root / "upscaled"
            second = self._run_generator(
                root,
                [
                    "--prompt", "test",
                    "--shape", "square",
                    "--style", "test",
                    "--amount", "2",
                    "--timeout", "n+u+1",
                    "--upscale-timeout", "1",
                    "--upscale",
                    "--upscale-retry", "1",
                    "--preview",
                    "--gui",
                    "--override",
                    "--i-know-what-i-am-doing",
                    "--proxy", "false",
                    "--disable-proxy-warning",
                    "--output-dir", str(upscale_dir),
                ],
                [FIXTURE_IMAGE, b"second-image"],
                [RuntimeError("retry test"), b"upscaled-image", b"upscaled-image"],
            )
            self.assertEqual((upscale_dir / "image_1.jpg").read_bytes(), b"upscaled-image")
            self.assertEqual((upscale_dir / "image_2.jpg").read_bytes(), b"upscaled-image")
            self.assertFalse(second.start.call_args.kwargs["headless"])
            self.assertFalse(second.start.call_args.kwargs["proxy"])
            self.assertFalse(second.browse.call_args.kwargs["proxy_warning"])
            self.assertTrue(second.preview.called)
            self.assertEqual(second.upscale.call_count, 3)

            base64_result = self._run_generator(
                root,
                [
                    "--prompt", "test",
                    "--timeout", "5",
                    "--override",
                    "--i-know-what-i-am-doing",
                    "--base-64",
                ],
                [FIXTURE_IMAGE],
            )
            self.assertEqual(
                base64_result.outputs, [base64.b64encode(FIXTURE_IMAGE).decode("ascii")]
            )

    def test_image_generator_list_uses_dynamic_option_files(self):
        with tempfile.TemporaryDirectory(prefix="image_") as temp_root:
            root = Path(temp_root)
            user = root.name.removeprefix("image_")
            (root / "styles.txt").write_text("['Photo', 'Sketch']")
            (root / "shapes.txt").write_text("['Square', 'Portrait']")
            (root / "numbers.txt").write_text("['1', '2']")
            with (
                patch.object(self.generator, "getuser", return_value=user),
                patch.object(self.generator, "chmod"),
                patch.object(self.generator, "log_event") as log_event,
                patch.object(self.generator, "timed_input", return_value="yes"),
                patch.object(
                    sys,
                    "argv",
                    [
                        "image_generator",
                        "--prompt", "test",
                        "--list",
                    ],
                ),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as exit_info:
                    self.generator.run()
            self.assertEqual(exit_info.exception.code, 0)
            logged_options = " ".join(str(call.args[0]) for call in log_event.call_args_list)
            self.assertIn("Photo", logged_options)
            self.assertIn("Square", logged_options)
            self.assertIn("'2'", logged_options)

    def test_upscale_script_saves_file_and_base64_with_preview_on_and_off(self):
        module = self.upscaler
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            input_path = root / "input.jpg"
            input_path.write_bytes(FIXTURE_IMAGE)
            output_dir = root / "output"
            with (
                patch.object(module, "start_browser", return_value=BrowserContext()) as start,
                patch.object(module, "browse", return_value=(True, b"upscaled-image")) as browse,
                patch.object(module, "subprocess_run") as preview,
                patch.object(sys, "argv", [
                    "upscale_image",
                    "--image", str(input_path),
                    "--gui",
                    "--proxy", "false",
                    "--disable-proxy-warning",
                    "--timeout", "5",
                    "--preview",
                    "--output-dir", str(output_dir),
                ]),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as exit_info:
                    module.run()
            self.assertEqual(exit_info.exception.code, 0)
            self.assertEqual((output_dir / "image.jpg").read_bytes(), b"upscaled-image")
            self.assertFalse(start.call_args.kwargs["headless"])
            self.assertFalse(start.call_args.kwargs["proxy"])
            self.assertEqual(browse.call_args.kwargs["image"], FIXTURE_IMAGE)
            self.assertFalse(browse.call_args.kwargs["proxy_warning"])
            self.assertTrue(preview.called)

            encoded = base64.b64encode(FIXTURE_IMAGE).decode("ascii")
            returned = []
            with (
                patch.object(module, "start_browser", return_value=BrowserContext()) as start,
                patch.object(module, "browse", return_value=(True, FIXTURE_IMAGE)) as browse,
                patch.object(module, "subprocess_run") as preview,
                patch.object(module, "timed_input", return_value="yes"),
                patch.object(module, "output", side_effect=returned.append),
                patch.object(module, "stdin", io.StringIO(encoded)),
                patch.object(sys, "argv", [
                    "upscale_image",
                    "--timeout", "5",
                    "--preview",
                    "--base64",
                ]),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as exit_info:
                    module.run()
            self.assertEqual(exit_info.exception.code, 0)
            self.assertEqual(returned, [encoded])
            self.assertTrue(start.call_args.kwargs["headless"])
            self.assertTrue(start.call_args.kwargs["proxy"])
            self.assertTrue(browse.call_args.kwargs["proxy_warning"])
            self.assertTrue(preview.called)

    def test_get_image_infos_full_run_writes_styles_shapes_and_amounts(self):
        module = self.info_script
        options = {
            "select[data-name='artStyle']": ["Photo", "Sketch"],
            "select[data-name='shape']": ["Square", "Portrait"],
            "select[data-name='numImages']": ["1", "2"],
        }

        class FakeFrame:
            def locator(self, selector):
                return FakeOption(options[selector])

        class FakePage:
            def goto(self, _url):
                return None

            def frame_locator(self, _selector):
                return FakeFrame()

        class FakeBrowser:
            def new_page(self):
                return FakePage()

        with tempfile.TemporaryDirectory() as temp_root:
            module.tmp_path = temp_root
            with patch.object(module, "prepare_image_site"):
                module.run(FakeBrowser())
            self.assertEqual(
                (Path(temp_root) / "styles.txt").read_text(), str(options["select[data-name='artStyle']"])
            )
            self.assertEqual(
                (Path(temp_root) / "shapes.txt").read_text(), str(options["select[data-name='shape']"])
            )
            self.assertEqual(
                (Path(temp_root) / "numbers.txt").read_text(), str(options["select[data-name='numImages']"])
            )

    def test_image_info_entrypoint_toggles_headless_and_gui(self):
        helper_browser = sys.modules["fabs_lib_playwright"]
        helper_generation = sys.modules["fabs_lib_image_gemeration"]

        class FakeFrame:
            def locator(self, _selector):
                return FakeOption(["First", "Second"])

        class FakePage:
            def goto(self, _url):
                return None

            def frame_locator(self, _selector):
                return FakeFrame()

        class FakeBrowser:
            def new_page(self):
                return FakePage()

        for gui, expected_headless in ((False, True), (True, False)):
            with tempfile.TemporaryDirectory(prefix="image_health_") as temp_root:
                root = Path(temp_root)
                user = root.name.removeprefix("image_")
                with (
                    patch("getpass.getuser", return_value=user),
                    patch.object(
                        helper_browser,
                        "start_browser",
                        return_value=BrowserContext(FakeBrowser()),
                    ) as start,
                    patch.object(helper_generation, "prepare_image_site"),
                    patch("os.system"),
                    patch.dict(os.environ, {"gen_url": "https://example.invalid"}),
                    patch.object(
                        sys,
                        "argv",
                        ["get_image_infos"] + (["--gui"] if gui else []),
                    ),
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    runpy.run_path(str(ROOT / "get_image_infos"), run_name="__main__")
                self.assertEqual(start.call_args.kwargs["headless"], expected_headless)
                self.assertTrue((root / "styles.txt").is_file())

    def test_image_api_endpoint_routes_single_and_multiple_image_runs(self):
        client = TestClient(self.api.app)
        one_image = SimpleNamespace(
            returncode=0,
            stderr="",
            stdout=base64.b64encode(FIXTURE_IMAGE).decode("ascii") + "\n",
        )
        with patch.object(self.api.subprocess, "run", return_value=one_image) as run:
            response = client.get(
                "/generate",
                params={
                    "prompt": "test",
                    "negative_prompt": "test",
                    "shape": "square",
                    "style": "test",
                    "amount": 1,
                    "timeout": 5,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.content, FIXTURE_IMAGE)
        command = run.call_args.args[0]
        self.assertIn("--negative-prompt", command)
        self.assertIn("--shape", command)
        self.assertIn("--style", command)
        self.assertIn("--upscale", command)

        two_images = SimpleNamespace(
            returncode=0,
            stderr="",
            stdout="\n".join(
                base64.b64encode(image).decode("ascii")
                for image in (FIXTURE_IMAGE, b"second-image")
            ),
        )
        with patch.object(self.api.subprocess, "run", return_value=two_images):
            response = client.get(
                "/generate",
                params={"prompt": "test", "amount": 2, "timeout": 5},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["images"],
            [
                base64.b64encode(FIXTURE_IMAGE).decode("ascii"),
                base64.b64encode(b"second-image").decode("ascii"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
