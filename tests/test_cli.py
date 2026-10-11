from click.testing import CliRunner
from vn_id.cli.main import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "extract" in result.output
    assert "--device" in runner.invoke(cli, ["extract", "--help"]).output


def test_cli_extract_requires_image():
    result = CliRunner().invoke(cli, ["extract"])
    assert result.exit_code == 1
    assert "Vui lòng cung cấp" in result.output

