#!/usr/bin/python2

from __future__ import print_function

###
# Modification of `https://raw.githubusercontent.com/splitbrain/material-icons/master/exportlayers.py` for more flexibility
###

# Usage: svg_layersplitter.py <input.svg> <output-dir> [<layers-config>]

"""
Exports all Inkscape layers from the given <input.svg> into separate SVG files
within the <output-dir> directory.
"""

EPILOG="""
<cfg> is an optional argument describing how layers are combined
in each svg file. It can take the value '+' (then each layer is successively added to the previous set), or it is a file containing the succession information:

Here is the syntax:

    - one line corresponds to one output svg file
    - each line contains several layers names (space separated)
    - when a layer is given prepended with a '+', then the svg files
      contains all layers included in the previous svg file + the 
      specified one.
    - when prepended with '-', the layer is removed from the previous set
    - when the layer is written as is, with no sign, then the set is cleared
      and initialized with this layer.

Layers with labels starting with _ will never be exported.
Files are named after the layer names.
Existing files will not be overwritten, unless --force is used.
Layers are piled up in the same order as in the original file.
"""

import codecs
import sys
import os
import argparse
from copy import copy
from xml.dom import minidom

LAYER_KEY = 'inkscape:groupmode'
LAYER_VAL = 'layer'
LABEL_KEY = 'inkscape:label'
STYLE_KEY = 'style'

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
    Exports a set of layers and makes it visible

    :param layer: The name of the layer to export
    :param src: The source SVG to load
    :param dst: The destination SVG to write to
    :return:
    """
    svg = minidom.parse(open(src))
    
    layerset = copy(layerset)

    for g in svg.getElementsByTagName('g'):
        if (
            g.hasAttribute(LAYER_KEY) and
            g.getAttribute(LAYER_KEY) == LAYER_VAL and
            g.hasAttribute(LABEL_KEY)
        ):
            layername = g.getAttribute(LABEL_KEY)
            if layername not in layerset:
                # not the layer we want - remove
                g.parentNode.removeChild(g)
            elif g.hasAttribute(STYLE_KEY):
                # make sure the layer isn't hidden
                style = g.getAttribute(STYLE_KEY)
                style = style.replace('display:none', '')
                g.setAttribute(STYLE_KEY, style)
                layerset.remove(layername)

    if layerset:
        print('WARNING: unfound layers: ' + ' '.join(layerset), file=sys.stderr)

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


def iter_add(layers):
    layer_set = set()
    for layer in layers:
        layer_set.add(layer)
        yield layer_set


def main(infile, outdir, cfg=None, force=False, fmt='_02%d', start=0):
    """
    """
    if not os.path.isfile(infile):
        print("Can't find %s" % infile, file=sys.stderr)
        return 1

    if not os.path.isdir(outdir):
        print("%s seems not to be a directory" % outdir, file=sys.stderr)
        return 1

    base, _ = os.path.splitext(os.path.basename(infile))
    outfmt = os.path.join(outdir, base + fmt + ".svg")
    
    layers = get_layers(infile)
    print("found %d suitable layers" % len(layers))

    if not cfg:
        iter_layers = (set((layer,)) for layer in layers)
    elif cfg == '+':
        iter_layers = iter_add(layers)
    else:
        iter_layers = iter_layersets(cfg)

        #for layer in layers:
        #    outfile = "%s.svg" % os.path.join(outdir, layer)
        #    if os.path.isfile(outfile):
        #        print("%s - %s exists, skipped" % (layer, outfile))
        #        continue
        #    else:
        #        export_layers(set((layer,)), infile, outfile)
        #        print("%s - %s exported" % (layer, outfile))

    for i, layerset in enumerate(iter_layers, start=start):
        outfile = outfmt % i
        if os.path.isfile(outfile) and not force:
            print("%s exists, skipped" % outfile)
            continue
        else:
            export_layers(layerset, infile, outfile)
            print("%s exported" % outfile)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, epilog=EPILOG,
                formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('infile')
    parser.add_argument('outdir')
    parser.add_argument('cfg', nargs='?')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Overwrite existing files')
    parser.add_argument('-b', '--beamer', '--multiinclude',
                        action='store_const', dest='fmt', const='-%d',
                        default='_%02d',
                        help=("Format output filenames for beamer "
                              "multiinclude: 'file-%%d.ext' "
                              "['file%(default)s.ext']"))
    parser.add_argument('-s', '--start', type=int, default=0,
                        help='Where to start the layer count [%(default)s]')
    sys.exit(main(**vars(parser.parse_args())))

