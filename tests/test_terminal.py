"""Unit tests for terminal command builder."""

import unittest
from devpilot.core.terminal import (
    get_available_terminals,
    build_terminal_command,
)


class TestTerminal(unittest.TestCase):
    def test_get_available_terminals(self):
        terminals = get_available_terminals()
        self.assertTrue(len(terminals) > 0)
        self.assertIn("powershell", terminals)

    def test_build_terminal_command_powershell(self):
        cmd = build_terminal_command(
            terminal_type="powershell",
            working_dir="C:/projects/myapp",
            startup_command="npm run dev"
        )
        self.assertEqual(cmd[0], "powershell.exe")
        self.assertIn("-NoExit", cmd)
        self.assertTrue(any("npm run dev" in arg for arg in cmd))

    def test_build_terminal_command_wt(self):
        cmd = build_terminal_command(
            terminal_type="wt",
            working_dir="C:/projects/myapp",
            startup_command="flutter run",
            title="Flutter App"
        )
        self.assertEqual(cmd[0], "wt.exe")
        self.assertIn("-d", cmd)
        self.assertIn("--title", cmd)
        self.assertIn("Flutter App", cmd)
        self.assertIn("powershell.exe", cmd)

    def test_build_terminal_command_cmd(self):
        cmd = build_terminal_command(
            terminal_type="cmd",
            working_dir="C:/projects/myapp",
            startup_command="echo Hello"
        )
        self.assertEqual(cmd[0], "cmd.exe")
        self.assertIn("/k", cmd)


if __name__ == "__main__":
    unittest.main()
