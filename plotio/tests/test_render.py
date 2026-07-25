import shutil
from pathlib import Path

import pytest
from matplotlib.testing.compare import compare_images

from plotio.render import render


def get_golden_tests() -> list[Path]:
    """Discover all golden test .drawio files."""
    golden_dir = Path(__file__).parent / 'data' / 'golden'
    return list(golden_dir.glob('*.drawio'))


@pytest.mark.parametrize('drawio_file', get_golden_tests(), ids=lambda p: p.stem)
def test_golden_render(drawio_file: Path, tmp_path: Path) -> None:
    """Test that rendering a .drawio file produces the expected golden PNG."""
    golden_png_file = drawio_file.with_suffix('.png')
    output_png_file = tmp_path / drawio_file.with_suffix('.png').name

    # Render directly to the temporary path
    render(str(drawio_file), str(output_png_file))

    # Compare images with a tolerance
    result = compare_images(str(golden_png_file), str(output_png_file), tol=1.0)

    if result is not None:
        diff_dir = drawio_file.parent / 'diffs'
        diff_dir.mkdir(exist_ok=True)
        shutil.copy(output_png_file, diff_dir / f'{drawio_file.stem}_generated.png')
        shutil.copy(golden_png_file, diff_dir / f'{drawio_file.stem}_expected.png')

        # compare_images generates a diff image in the same directory as the output file
        # result['diff'] is the path to the diff image
        if isinstance(result, dict) and 'diff' in result and Path(str(result['diff'])).exists():
            shutil.copy(str(result['diff']), diff_dir / f"{drawio_file.stem}_diff.png")

        pytest.fail(
                f'Rendered PNG does not match golden for {drawio_file.name}. Compare files in {diff_dir}\nError: {result}'
        )
