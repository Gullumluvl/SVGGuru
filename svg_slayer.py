#!/usr/bin/env python

from __future__ import print_function

###
# Modification of `https://raw.githubusercontent.com/splitbrain/material-icons/master/exportlayers.py` for more flexibility
###

# Usage: svg_slayer.py <input.svg> <output-dir> [<layers-config>]

"""
Exports all Inkscape layers from the given <input.svg> into separate SVG files
within the <output-dir> directory.
"""

EPILOG="""
<cfg> is an optional argument describing how layers are combined
in each svg file. It can take the value '+' (then each layer is successively added to the previous set), or it is a file containing the succession information:

Here is the syntax:

    - one line corresponds to one output svg file;
    - each line contains several layers names (whitespace separated);
    - when a layer is given prefixed with a '+', then the svg files;
      contains all layers included in the previous svg file + the 
      specified one (this must be the first layer of the line);
    - when prefixed with '-', the layer is removed from the previous set;
    - when prefixed with '*', the layer will be used here but automatically
      removed after;
    - when the layer is written as is, with no sign, then the set is cleared
      and initialized with this layer.

Spaces in layer names are not supported.
Layers with labels starting with _ will never be exported.
Existing files will not be overwritten, unless --force is used.
Layers are stacked in the same order as in the original file.
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
    with open(src) as stream:
        svg = minidom.parse(stream)

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
            else:
                if g.hasAttribute(STYLE_KEY):
                    # make sure the layer isn't hidden
                    style = g.getAttribute(STYLE_KEY)
                    style = style.replace('display:none', '')
                    g.setAttribute(STYLE_KEY, style)
                layerset.remove(layername)

    if layerset:
        print('WARNING: unfound layers: ' + ', '.join(map(repr, layerset)), file=sys.stderr)

    exported = svg.toxml()
    codecs.open(dst, "w", encoding="utf8").write(exported)


def iter_layersets(layer_configfile):
    """Follows the syntax of the file to give the set of layers
    (understand adding/removing commands)"""
    with open(layer_configfile) as IN:
        lines = IN.readlines()
    layerset = set()
    for line in lines:
        words = line.split()
        # Remove comments
        for i,w in enumerate(words):
            if w[0] == '#':
                words = words[:i]
                break
        if not words:
            # Skip blank lines
            continue
        if words[0][0] not in ('+', '-', '*'):
            layerset = set()
        use_once_layers = set()
        for word in words:
            if word.startswith('-'):
                layerset.remove(word[1:])
            else:
                if word[0] == '*':
                    use_once_layers.add(word[1:])
                if word[0] in '+*':
                    word = word[1:]
                layerset.add(word)
        yield layerset
        layerset.difference_update(use_once_layers)


def iter_add(layers):
    layer_set = set()
    for layer in layers:
        layer_set.add(layer)
        yield layer_set


def extract_layers_fromfile(infile, outdir, cfg=None, force=False,
                            suffix_fmt='-%d', start=0, list_layers=False):
    """
    """
    if not os.path.isfile(infile):
        print("ERROR: Can't find %s" % infile, file=sys.stderr)
        return 1

    if not os.path.isdir(outdir):
        print("ERROR: %s does not seem to be a directory" % outdir, file=sys.stderr)
        return 1

    base, _ = os.path.splitext(os.path.basename(infile))
    outfmt = os.path.join(outdir, base + suffix_fmt + ".svg")

    layers = get_layers(infile)
    print("INFO: Found %d suitable layers" % len(layers), file=sys.stderr)

    if list_layers:
        print('\n'.join(layer for layer in layers))
        return 0

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
            print("SKIP: %s exists, skipped" % outfile)
            continue
        else:
            export_layers(layerset, infile, outfile)
            print("OUT:  %s exported" % outfile)

    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog=EPILOG,
                formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('infile')
    parser.add_argument('outdir', nargs='?', default='.', help='[%(default)s]')
    parser.add_argument('cfg', nargs='?',
                        help='If not given, extract all found layers in separate files.')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Overwrite existing files')
    parser.add_argument('-S', '--suffix-fmt', default='-%d',
                        help=("Number suffix format of output filenames. The "
                              "default is compatible with beamer multiinclude,"
                              " generating 'basename-%%d.ext'. [%(default)r]"))
    parser.add_argument('-s', '--start', type=int, default=0,
                        help='Where to start the layer count [%(default)s]')
    parser.add_argument('-l', '--list-layers', '--list', action='store_true',
                        help='List layers. No output.')
    extract_layers_fromfile(**vars(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
