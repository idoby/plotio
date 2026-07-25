"""Tests for IO parsing functions."""

from pathlib import Path

import pytest

from plotio.errors import ParseError
from plotio.io import parse_drawio_xml


def test_parse_drawio_xml_file_not_found(tmp_path: Path) -> None:
    invalid_path = tmp_path / 'does_not_exist.xml'

    with pytest.raises(FileNotFoundError, match='Draw.io file not found'):
        parse_drawio_xml(invalid_path)


def test_parse_drawio_xml_invalid_xml_no_graph_model(tmp_path: Path) -> None:
    test_file = tmp_path / 'test.xml'
    test_file.write_text('<root></root>')

    with pytest.raises(ParseError, match='Invalid Draw.io XML: No mxGraphModel found'):
        parse_drawio_xml(test_file)


def test_parse_drawio_xml_success(tmp_path: Path) -> None:
    xml_content = """<mxfile>
      <diagram id="test">
        <mxGraphModel pageWidth="827" pageHeight="1169" pageScale="2">
          <root>
            <mxCell id="0"/>
            <mxCell id="1" parent="0"/>
            <mxCell id="node1" value="A" style="shape=ellipse" vertex="1" parent="1">
              <mxGeometry x="0" y="0" width="10" height="10" as="geometry"/>
            </mxCell>
          </root>
        </mxGraphModel>
      </diagram>
    </mxfile>"""
    test_file = tmp_path / 'test_success.xml'
    test_file.write_text(xml_content)

    graph = parse_drawio_xml(test_file)

    assert graph.width == 827.0
    assert graph.height == 1169.0
    # scale = 1 / (827 * 2) = 1 / 1654
    assert graph.coord_scale == 1.0 / 1654.0
    assert len(graph.nodes) == 1
    assert 'node1' in graph.nodes
    assert len(graph.edges) == 0


def test_parse_drawio_xml_invalid_xml_no_root_cell(tmp_path: Path) -> None:
    xml_content = """<mxfile>
      <diagram id="test">
        <mxGraphModel>
        </mxGraphModel>
      </diagram>
    </mxfile>"""
    test_file = tmp_path / 'test_no_root.xml'
    test_file.write_text(xml_content)

    with pytest.raises(ParseError, match='Invalid Draw.io XML: No root cell found'):
        parse_drawio_xml(test_file)
