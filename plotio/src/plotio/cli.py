"""CLI entrypoint for plotio."""

import argparse

from .render import render_drawio


def main():
    parser = argparse.ArgumentParser(description='Render Draw.io XML to Matplotlib graphics.')
    parser.add_argument('input', help='Input Draw.io file path')
    parser.add_argument('output', help='Output file path (e.g., .svg, .png)')
    args = parser.parse_args()

    render_drawio(args.input, args.output)


if __name__ == '__main__':
    main()
