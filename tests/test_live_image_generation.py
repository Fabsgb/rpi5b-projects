import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LiveImageGeneration(unittest.TestCase):
    def test_remote_generation_starts_browser_and_saves_image(self):
        prompt = os.environ.get("LIVE_IMAGE_PROMPT", "test")
        with tempfile.TemporaryDirectory(prefix="live-image-generation-") as temp_dir:
            output_dir = Path(temp_dir) / "output"
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(
                part
                for part in (str(ROOT / "my-libs"), env.get("PYTHONPATH", ""))
                if part
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "image_generator"),
                    "--prompt",
                    prompt,
                    "--amount",
                    "1",
                    "--timeout",
                    "300",
                    "--override",
                    "--i-know-what-i-am-doing",
                    "--disable-proxy-warning",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=360,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            image_path = output_dir / "image.jpg"
            self.assertTrue(image_path.is_file(), result.stdout + result.stderr)
            image = image_path.read_bytes()
            self.assertGreater(len(image), 100, "Generated image file is empty or truncated.")
            image_signatures = (
                b"\xff\xd8\xff",
                b"\x89PNG\r\n\x1a\n",
                b"GIF87a",
                b"GIF89a",
                b"RIFF",
            )
            self.assertTrue(
                any(image.startswith(signature) for signature in image_signatures),
                f"Output does not look like a supported image: {image[:16]!r}",
            )


if __name__ == "__main__":
    unittest.main()
