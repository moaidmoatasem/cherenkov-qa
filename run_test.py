from click.testing import CliRunner
import pytest

def test_debug():
    pytest.main(['tests/unit/test_report_cmd.py::TestSelfTestCmd::test_tsc_failure_exits_1', '-v', '-s'])

if __name__ == '__main__':
    test_debug()
