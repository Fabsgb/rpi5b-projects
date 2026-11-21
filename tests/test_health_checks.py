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
from ast import parse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from os import environ, pathsep
from runpy import run_path
from subprocess import CompletedProcess, run
from sys import executable, path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PYTHON_SCRIPTS = (
    "auto_report_f2b_email",
    "crawl",
    "get_image_infos",
    "image_api",
    "image_generator",
    "upscale_image",
)
SHELL_CHECKS = {
    "send_email": "sh",
    "monitor_swap": "bash",
    "update_time": "bash",
}


def run_script(script: str, *args: str) -> CompletedProcess[str]:
    env = environ.copy()
    helpers = str(ROOT / "my-libs")
    env["PYTHONPATH"] = pathsep.join(
        part for part in (helpers, env.get("PYTHONPATH", "")) if part
    )
    return run(
        [executable, str(ROOT / script), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class HealthChecks(TestCase):
    def test_python_scripts_parse(self):
        helper_scripts = tuple(
            str(path.relative_to(ROOT))
            for path in sorted((ROOT / "my-libs").glob("*.py"))
        )
        for script in PYTHON_SCRIPTS + helper_scripts:
            with self.subTest(script=script):
                parse((ROOT / script).read_text(encoding="utf-8"), filename=script)

    def test_shell_scripts_parse(self):
        for script, shell in SHELL_CHECKS.items():
            with self.subTest(script=script):
                result = run(
                    [shell, "-n", str(ROOT / script)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_swap_monitor_runs_bounded_threshold_on_and_off(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            meminfo = root / "meminfo"
            meminfo.write_text("SwapTotal: 100 kB\nSwapFree: 20 kB\n")
            for threshold, should_log in ((50, True), (80, False)):
                log_file = root / f"swap-{threshold}.log"
                env = environ.copy()
                env.update(
                    {
                        "MEMINFO_FILE": str(meminfo),
                        "LOG_FILE": str(log_file),
                        "THRESHOLD": str(threshold),
                        "SLEEP_TIME": "0",
                        "MAX_CHECKS": "1",
                    }
                )
                result = run(
                    ["bash", str(ROOT / "monitor_swap")],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(log_file.exists(), should_log)
                if should_log:
                    self.assertIn(
                        "WARNING: Swap usage is at 80%",
                        log_file.read_text(encoding="utf-8"),
                    )

    def test_safe_cli_help(self):
        result = run_script("upscale_image", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout.lower())

        result = run_script(
            "image_generator", "--override", "--i-know-what-i-am-doing", "--help"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--upscale-timeout", result.stdout)

    def test_image_info_help_without_filesystem_or_browser_side_effects(self):
        previous_path = list(path)
        path.insert(0, str(ROOT / "my-libs"))
        try:
            help_output = StringIO()
            with patch("sys.argv", ["get_image_infos", "--gui", "--help"]), patch(
                "os.makedirs"
            ), patch("os.system"), redirect_stdout(help_output), redirect_stderr(
                StringIO()
            ):
                with self.assertRaises(SystemExit) as exit_info:
                    run_path(str(ROOT / "get_image_infos"), run_name="__main__")
            self.assertEqual(exit_info.exception.code, 0)
            self.assertIn("--gui", help_output.getvalue())
        finally:
            path[:] = previous_path

    def test_image_generator_accepts_options_before_safe_timeout_rejection(self):
        with TemporaryDirectory() as output_dir:
            result = run_script(
                "image_generator",
                "--prompt", "test",
                "--negative-prompt", "test",
                "--shape", "square",
                "--style", "test",
                "--amount", "2",
                "--timeout", "0",
                "--upscale-timeout", "0.5",
                "--gui",
                "--upscale",
                "--info-file",
                "--preview",
                "--override",
                "--i-know-what-i-am-doing",
                "--proxy", "false",
                "--upscale-retry", "0",
                "--disable-proxy-warning",
                "--output-dir", output_dir,
            )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("must be a positive number", result.stderr)

    def test_image_generator_list_override_conflict_is_reported_without_browser(self):
        result = run_script(
            "image_generator",
            "--prompt", "test",
            "--override",
            "--i-know-what-i-am-doing",
            "--list",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("--list is unavailable with --override", result.stderr)

    def test_image_generator_base64_info_file_conflict_is_reported(self):
        result = run_script(
            "image_generator",
            "--prompt", "test",
            "--override",
            "--i-know-what-i-am-doing",
            "--base-64",
            "--info-file",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Cannot use --info-file and --base-64 together", result.stderr)

    def test_upscale_accepts_options_before_safe_timeout_rejection(self):
        with TemporaryDirectory() as output_dir:
            result = run_script(
                "upscale_image",
                "--image", "test",
                "--gui",
                "--proxy", "false",
                "--disable-proxy-warning",
                "--timeout", "0",
                "--preview",
                "--output-dir", output_dir,
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("--timeout must be a positive finite number", result.stderr)

    def test_upscale_output_modes_are_mutually_exclusive(self):
        with TemporaryDirectory() as output_dir:
            result = run_script(
                "upscale_image",
                "--image", "test",
                "--base64",
                "--output-dir", output_dir,
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("not allowed with argument", result.stderr)

if __name__ == "__main__":
    main()
