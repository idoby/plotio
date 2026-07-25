"""Tests for the CLI."""

from plotio.cli import main


def test_cli_help(mocker) -> None:
    # Arrange
    test_args = ["plotio", "--help"]

    # Act / Assert
    mocker.patch("sys.argv", test_args)
    try:
        main()
    except SystemExit as e:
        assert e.code == 0


def test_cli_render(mocker) -> None:
    # Arrange
    test_args = ["plotio", "render", "input.drawio", "output.svg"]

    # Act
    mocker.patch("sys.argv", test_args)
    mock_render = mocker.patch("plotio.cli.render_drawio")
    main()
    
    # Assert
    mock_render.assert_called_once_with("input.drawio", "output.svg")
