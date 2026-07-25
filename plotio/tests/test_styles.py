"""Tests for style coercion."""

from plotio.styles import EdgeStyle, NodeStyle


def test_node_style_coercion():
    style = NodeStyle({'strokewidth': '2.5', 'fillcolor': 'default', 'garbage': '1'})
    mpl_kwargs = style.as_mpl_kwargs()

    # Original data preserved
    assert style.raw_styles['strokewidth'] == '2.5'
    assert style.raw_styles['garbage'] == '1'

    # Coerced types and mapped keys
    assert style.raw_styles['linewidth'] == 2.5
    assert style.raw_styles['facecolor'] == 'white'

    # Matplotlib specific filtering
    assert mpl_kwargs == {'linewidth': 2.5, 'facecolor': 'white'}
    assert 'garbage' not in mpl_kwargs


def test_edge_style_coercion():
    style = EdgeStyle({'dashed': '1', 'strokecolor': '#FF0000'})
    mpl_kwargs = style.as_mpl_kwargs()

    assert style.raw_styles['linestyle'] == 'dashed'
    assert style.raw_styles['color'] == '#FF0000'
    assert mpl_kwargs == {'linestyle': 'dashed', 'color': '#FF0000'}


def test_node_style_value_error():
    style = NodeStyle({'strokewidth': 'invalid', 'strokecolor': 'default'})
    assert 'linewidth' not in style.raw_styles
    assert style.raw_styles['edgecolor'] == 'black'


def test_edge_style_value_error():
    style = EdgeStyle({'strokewidth': 'invalid'})
    assert 'linewidth' not in style.raw_styles


def test_label_style_coercion():
    from plotio.styles import LabelStyle

    style = LabelStyle({'fontsize': '14', 'fontcolor': 'default'})
    assert style.raw_styles['fontsize'] == 14.0
    assert style.raw_styles['color'] == 'black'

    style2 = LabelStyle({'fontsize': 'invalid'})
    assert style2.raw_styles['fontsize'] == 'invalid'
