#!/usr/bin/python2

###
# Modification of `https://raw.githubusercontent.com/splitbrain/material-icons/master/exportlayers.py` for more flexibility
###

"""
Usage: svg_layersplitter.py <input.svg> <output-dir> [<layers-config>]

Exports all Inkscape layers from the given <input.svg> into separate SVG files
within the <output-dir> directory.

<layers-config> is an optional file describing how layers are combined
in each svg file. Here is the syntax:

    - one line corresponds to one output svg file
    - each line contains several layers names (space separated)
    - when a layer is given prepended with a '+', then the svg files
      contains all layers included in the previous svg file + the 
      specified one.
    - when prepended with '-', the layer is removed from the previous set
    - when the layer is written as is, with no sign, then the set is cleared
      and initialized with this layer.

Layers with labels starting with _ will never be exported. Files are named
after the layer names. Existing files will NOT be overwritten.
"""

import codecs
import sys
import os
from xml.dom import minidom

LAYER_KEY = 'inkscape:groupmode'
LAYER_VAL = 'layer'
LABEL_KEY = 'inkscape:label'
STYLE_KEY = 'style'

def usage():
    print __doc__
def get_layers(src):
    """
    Returns all layers in the given SVG that don't start with an underscore

    :param src: The source SVG to load
    :return:
    """
    layers = []
    svg = minidom.parse(open(src))
    for g in svg.getElementsByTagName('g'):
        if (
            g.hasAttribute(LAYER_KEY) and
            g.getAttribute(LAYER_KEY) == LAYER_VAL and
            g.hasAttribute(LABEL_KEY) and
            g.getAttribute(LABEL_KEY)[:1] != '_'
        ):
            layers.append(g.attributes[LABEL_KEY].value)
    return layers

def export_layers(layerset, src, dst):
    """
    Exports a single layer and makes it visible

    :param layer: The name of the layer to export
    :param src: The source SVG to load
    :param dst: The destination SVG to write to
    :return:
    """
    svg = minidom.parse(open(src))

    for g in svg.getElementsByTagName('g'):
        if (
            g.hasAttribute(LAYER_KEY) and
            g.getAttribute(LAYER_KEY) == LAYER_VAL and
            g.hasAttribute(LABEL_KEY)
        ):
            if g.getAttribute(LABEL_KEY) not in layerset:
                # not the layer we want - remove
                g.parentNode.removeChild(g)
            elif g.hasAttribute(STYLE_KEY):
                # make sure the layer isn't hidden
                style = g.getAttribute(STYLE_KEY)
                style = style.replace('display:none', '')
                g.setAttribute(STYLE_KEY, style)

    export = svg.toxml()
    codecs.open(dst, "w", encoding="utf8").write(export)


def iter_layersets(layer_configfile):
    """Follows the syntax of the file to give the set of layers
    (understand adding/removing commands)"""
    with open(layer_configfile) as IN:
        lines = IN.readlines() 
    layerset = set(lines[0].split())
    yield layerset
    for line in lines[1:]:
        words = line.split()
        if words[0][0] not in ('+', '-'):
            layerset = set()
        for word in words:
            if word.startswith('-'):
                layerset.remove(word[1:])
            else:
                if word.startswith('+'):
                    word = word[1:]
                layerset.add(word)
        yield layerset


def main():
    """
    Handle commandline arguments and run the tool
    :return:
    """
    if len(sys.argv) not in (3, 4):
        usage()
        sys.exit(1)

    infile = sys.argv[1]
    if not os.path.isfile(infile):
        print "Can't find %s" % infile
        sys.exit(1)

    outdir = sys.argv[2]
    if not os.path.isdir(outdir):
        print "%s seems not to be a directory" % outdir
        sys.exit(1)

    layers = get_layers(infile)
    print "found %d suitable layers" % len(layers)

    if len(sys.argv) == 3:
        for layer in layers:
            outfile = "%s.svg" % os.path.join(outdir, layer)
            if os.path.isfile(outfile):
                print "%s - %s exists, skipped" % (layer, outfile)
                continue
            else:
                export_layers(set((layer,)), infile, outfile)
                print "%s - %s exported" % (layer, outfile)
    else:
        base, _ = os.path.splitext(os.path.basename(infile))
        for i, layerset in enumerate(iter_layersets(sys.argv[3]), start=1):
            outfile = os.path.join(outdir, "%s_%03d.svg" % (base, i))
            if os.path.isfile(outfile):
                print "%s exists, skipped" % outfile
                continue
            else:
                export_layers(layerset, infile, outfile)
                print "%s exported" % outfile


    sys.exit(0)


if __name__ == "__main__":
    main()


