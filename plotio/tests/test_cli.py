"""Tests for the CLI."""

from pytest_mock import MockerFixture

from plotio.cli import main


def test_cli_help(mocker: MockerFixture) -> None:
    test_args = ['plotio', '--help']

    mocker.patch('sys.argv', test_args)
    try:
        main()
    except SystemExit as e:
        assert e.code == 0


def test_render_command(mocker: MockerFixture) -> None:
    mock_render = mocker.patch('plotio.cli.render')
    test_args = ['plotio', 'render', 'input.drawio', 'output.svg']

    mocker.patch('sys.argv', test_args)
    main()

    mock_render.assert_called_once_with('input.drawio', 'output.svg')


def test_missing_command(mocker: MockerFixture) -> None:
    pass
