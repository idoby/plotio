"""Tests for the Draw.io XML parser logic."""

import xml.etree.ElementTree as ET
import pytest

from plotio.errors import ParseError
from plotio.parse import _parse_edge, _parse_edge_label, _parse_vertex, parse_root_cell


def test_parse_vertex_success() -> None:
    xml_str = """
    <mxCell id="1" vertex="1" style="shape=ellipse;fillColor=#FF0000;strokeWidth=2">
        <mxGeometry x="10" y="20" width="100" height="50" as="geometry" />
    </mxCell>
    """
    cell = ET.fromstring(xml_str)
    metadata = {'value': 'Node 1'}

    node = _parse_vertex('1', cell, metadata, 2.0)

    assert node.id == '1'
    assert node.label == 'Node 1'
    assert node.shape == 'ellipse'
    assert node.bounding_box.x == 20.0
    assert node.bounding_box.y == 40.0
    assert node.bounding_box.w == 200.0
    assert node.bounding_box.h == 100.0
    assert node.style.raw_styles.get('fillcolor') == '#FF0000'
    assert node.style.raw_styles.get('linewidth') == 2.0


def test_parse_vertex_missing_geometry_raises_error() -> None:
    xml_str = '<mxCell id="1" vertex="1" />'
    cell = ET.fromstring(xml_str)

    with pytest.raises(ParseError, match='Vertex cell 1 missing mxGeometry'):
        _parse_vertex('1', cell, {}, 1.0)


def test_parse_edge_label_success() -> None:
    xml_str = """
    <mxCell id="2" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];" vertex="1" connectable="0">
      <mxGeometry x="-0.5" y="10" relative="1" as="geometry">
        <mxPoint x="-20" y="30" as="offset" />
      </mxGeometry>
    </mxCell>
    """
    cell = ET.fromstring(xml_str)
    metadata = {'value': 'Edge Label'}

    label = _parse_edge_label('2', cell, metadata, 2.0)

    assert label.id == '2'
    assert label.label == 'Edge Label'
    assert label.position == -0.5
    assert label.y_offset == 20.0
    assert label.offset.x == -40.0
    assert label.offset.y == 60.0


def test_parse_edge_success() -> None:
    xml_str = """
    <mxCell id="3" edge="1" source="1" target="2" style="dashed=1;strokeWidth=2">
      <mxGeometry relative="1" as="geometry">
        <Array as="points">
          <mxPoint x="10" y="20" />
          <mxPoint x="30" y="40" />
        </Array>
        <mxPoint x="0" y="0" as="sourcePoint" />
        <mxPoint x="100" y="100" as="targetPoint" />
      </mxGeometry>
    </mxCell>
    """
    cell = ET.fromstring(xml_str)

    edge = _parse_edge('3', cell, {}, 2.0)

    assert edge.id == '3'
    assert edge.source_id == '1'
    assert edge.target_id == '2'
    assert len(edge.waypoints) == 2
    assert edge.waypoints[0].x == 20.0
    assert edge.waypoints[0].y == 40.0
    assert edge.waypoints[1].x == 60.0
    assert edge.waypoints[1].y == 80.0
    assert edge.fixed_source is not None
    assert edge.fixed_target is not None
    assert edge.style.raw_styles.get('linestyle') == 'dashed'


def test_parse_root_cell_extracts_nodes_and_edges() -> None:
    xml_str = """
    <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="node1" value="A" style="shape=ellipse" vertex="1" parent="1">
            <mxGeometry x="0" y="0" width="10" height="10" as="geometry" />
        </mxCell>
        <mxCell id="edge1" edge="1" source="node1" parent="1">
            <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="label1" value="L" style="edgeLabel=1" vertex="1" parent="edge1">
            <mxGeometry x="0" y="0" relative="1" as="geometry" />
        </mxCell>
    </root>
    """
    root_cell = ET.fromstring(xml_str)

    nodes, edges = parse_root_cell(root_cell, 1.0)

    assert len(nodes) == 1
    assert 'node1' in nodes
    assert len(edges) == 1
    assert edges[0].id == 'edge1'
    assert len(edges[0].labels) == 1
    assert edges[0].labels[0].id == 'label1'
    assert edges[0].labels[0].label == "L"


def test_parse_root_cell_mxcell_no_id() -> None:
    # Arrange
    xml_str = '<root><mxCell /></root>'
    root_cell = ET.fromstring(xml_str)
    # Act / Assert
    with pytest.raises(ParseError, match="mxCell without id"):
        parse_root_cell(root_cell, 1.0)


def test_parse_root_cell_object_success() -> None:
    # Arrange
    xml_str = '''
    <root>
        <object id="obj1" custom="123">
            <mxCell vertex="1" style="shape=ellipse">
                <mxGeometry as="geometry" />
            </mxCell>
        </object>
    </root>
    '''
    root_cell = ET.fromstring(xml_str)
    # Act
    nodes, edges = parse_root_cell(root_cell, 1.0)
    # Assert
    assert "obj1" in nodes
    assert nodes["obj1"].metadata["custom"] == "123"


def test_parse_root_cell_object_no_mxcell() -> None:
    # Arrange
    xml_str = '<root><object id="obj1"></object></root>'
    root_cell = ET.fromstring(xml_str)
    # Act / Assert
    with pytest.raises(ParseError, match="object without mxCell"):
        parse_root_cell(root_cell, 1.0)


def test_parse_root_cell_object_no_id() -> None:
    # Arrange
    xml_str = '<root><object><mxCell /></object></root>'
    root_cell = ET.fromstring(xml_str)
    # Act / Assert
    with pytest.raises(ParseError, match="object without id"):
        parse_root_cell(root_cell, 1.0)


def test_parse_root_cell_unexpected_element() -> None:
    # Arrange
    xml_str = '<root><random /></root>'
    root_cell = ET.fromstring(xml_str)
    # Act / Assert
    with pytest.raises(ParseError, match="Unexpected element in root cell: random"):
        parse_root_cell(root_cell, 1.0)


def test_parse_edge_label_no_equals_in_style() -> None:
    # Arrange
    xml_str = '''
    <root>
        <mxCell id="1" />
        <mxCell id="edge1" edge="1" source="1" parent="1" style="dashed">
            <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="label1" value="L" style="edgeLabel" vertex="1" parent="edge1">
            <mxGeometry x="0" y="0" relative="1" as="geometry" />
        </mxCell>
    </root>
    '''
    root_cell = ET.fromstring(xml_str)
    # Act
    nodes, edges = parse_root_cell(root_cell, 1.0)
    # Assert
    assert len(edges) == 1
    assert len(edges[0].labels) == 1


def test_parse_vertex_various_shapes_and_styles() -> None:
    # Arrange
    xml_str = '''
    <root>
        <mxCell id="n1" vertex="1" style="rounded=1">
            <mxGeometry as="geometry" />
        </mxCell>
        <mxCell id="n2" vertex="1" style="shape=step;dashed">
            <mxGeometry as="geometry" />
        </mxCell>
        <mxCell id="n3" vertex="1" style="text;html=1">
            <mxGeometry as="geometry" />
        </mxCell>
        <mxCell id="n4" vertex="1" style="ellipse;html=1">
            <mxGeometry as="geometry" />
        </mxCell>
    </root>
    '''
    root_cell = ET.fromstring(xml_str)
    # Act
    nodes, edges = parse_root_cell(root_cell, 1.0)
    # Assert
    assert nodes["n1"].shape == "rounded_rectangle"
    assert nodes["n2"].shape == "step"
    assert "dashed" in nodes["n2"].style.raw_styles
    assert nodes["n3"].shape is None
    assert nodes["n4"].shape == "ellipse"


def test_parse_vertex_unsupported_shape() -> None:
    # Arrange
    xml_str = '''
    <root>
        <mxCell id="n1" vertex="1" style="unknown=1">
            <mxGeometry as="geometry" />
        </mxCell>
    </root>
    '''
    root_cell = ET.fromstring(xml_str)
    # Act / Assert
    with pytest.raises(ParseError, match="Unsupported or missing shape"):
        parse_root_cell(root_cell, 1.0)


def test_parse_edge_label_missing_geometry() -> None:
    # Arrange
    xml_str = '<mxCell id="1" style="edgeLabel" />'
    cell = ET.fromstring(xml_str)
    # Act / Assert
    with pytest.raises(ParseError, match="Edge label cell 1 missing mxGeometry"):
        _parse_edge_label("1", cell, {}, 1.0)


def test_parse_edge_missing_geometry() -> None:
    # Arrange
    xml_str = '<mxCell id="1" edge="1" />'
    cell = ET.fromstring(xml_str)
    # Act / Assert
    with pytest.raises(ParseError, match="Edge cell 1 missing mxGeometry"):
        _parse_edge("1", cell, {}, 1.0)
