"""CLI entrypoint for plotio."""

import argparse

from .render import render_drawio


def main() -> None:
    """Run the Plotio command line interface."""
    parser = argparse.ArgumentParser(description='Render Draw.io XML to Matplotlib graphics.')
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    render_parser = subparsers.add_parser('render', help='Render a Draw.io file')
    render_parser.add_argument('input', help='Input Draw.io file path')
    render_parser.add_argument('output', help='Output file path (e.g., .svg, .png)')
    
    args = parser.parse_args()

    if args.command == 'render':
        render_drawio(args.input, args.output)


if __name__ == '__main__':
    main()
