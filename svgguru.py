#!/usr/bin/env python3

from __future__ import print_function

"""Perform simple transformations on a svg file."""

# USAGE:
#     ./svgguru.py <command> <inputfile> <outputfile> [command arguments]
# 
# COMMANDS:"""


import sys
import re
import argparse

# TODO:
# - included image: add a invert filter

from lxml import etree as ET

# Later muted if command line argument --verbose not given
print_if_verbose = print

# hexadecimal RGB color manipulation
def hexcode2tuple(hexcolor):
    hexcolor = hexcolor.lstrip('#')
    if not len(hexcolor) in [3,6]:
        raise RuntimeError("Invalide hexadecimal color code: %r" % hexcolor)

    if len(hexcolor) == 3:
        hexchannels = (hexcolor[0], hexcolor[1], hexcolor[2])
    else:
        hexchannels = (hexcolor[:2], hexcolor[2:4], hexcolor[4:])
    # would be faster to use binary ?
    R, G, B = (int(ch, base=16) for ch in hexchannels)
    return R, G, B


# yeah, I made a function for that
def tuple2hexcode255(R, G, B):
    return '#%02x%02x%02x' % (R, G, B)

def tuple2hexcode15(R, G, B):
    return '#%01x%01x%01x' % (R, G, B)

tuple2hexcode = tuple2hexcode255

name_inverter = {'white': 'black', 'black': 'white'}


def hex_invert(hexcolor):
    if not hexcolor.startswith('#') or not len(hexcolor) in [4, 7] :
        return hexcolor
    base = 15 if len(hexcolor) == 4 else 255
    R, G, B = (base - C for C in hexcode2tuple(hexcolor))
    return tuple2hexcode255(R,G,B) if base==255 else tuple2hexcode15(R,G,B)


### TODO: make a decorator
def col_invert(color, default=None):
    name_inverter.update({None: default})
    try:
        return name_inverter[color]
    except KeyError:
        return hex_invert(color)


atomic_invert = col_invert

def rgb_invertlight(R, G, B):
    middle_lum = (min(R, G, B) + max(R, G, B)) / 2
    #new_middle_lum = 255 - middle_lum
    tr = int(255 - 2 * middle_lum)
    R, G, B = (C + tr for C in (R, G, B))
    return R, G, B

def rgb_invertlight2(R, G, B):
    lum = (R + G + B) / 3
    #new_lum = 255 - lum
    maxC = max(R, G, B)
    minC = min(R, G, B)
    tr = int(255 - 2 * lum)
    tr = min(255 - maxC, tr) # doesnt change tr if tr < 0
    tr =  max(- minC, tr) # doesnt change tr if tr > 0
    R, G, B = (C + tr for C in (R, G, B))
    return R, G, B


def hex_invertlight(hexcolor):
    """Invert luminosity, but keep hue."""
    if not hexcolor.startswith('#') or not len(hexcolor) == 7 :
        return hexcolor
    R, G, B = hexcode2tuple(hexcolor)
    R, G, B = rgb_invertlight(R, G, B)
    return tuple2hexcode(R, G, B)


def hex_invertlight2(hexcolor):
    """Invert luminosity, but keep hue."""
    if not hexcolor.startswith('#') or not len(hexcolor) == 7 :
        return hexcolor
    R, G, B = hexcode2tuple(hexcolor)
    R, G, B = rgb_invertlight2(R, G, B)
    return tuple2hexcode(R, G, B)


atomic_invertlight = hex_invertlight
atomic_invertlight2 = hex_invertlight2


def parse_style(stylestr):
    """Return a dictionary of the style attribute text."""
    stylelist = stylestr.rstrip(';').split(';')
    return dict(x.split(':') for x in stylelist)
    

def format_style(styledict):
    """convert a style dictionary to a string for the style xml attribute"""
    # TODO: ensure conversion to string.
    return ';'.join(':'.join(item) for item in styledict.items()) + ';'


REG_PX = re.compile(r'px$')


### Atomic functions to change ONE style property
def atomic_resizefont(fontstr, factor, to_int=True):
    """multiply font-size by factor"""
    try:
        fontsize = float(REG_PX.sub('', fontstr))
    except ValueError as err:
        err.args = list(err.args) + ['Wrong font-size specification: %r' % fontstr]
        raise

    fontsize *= factor
    if to_int:
        fontsize = int(fontsize)
    return str(fontsize) + 'px'


### Building blocks to make more specific changing functions
def change_style(stylestr, propertyname, func, *funcargs):
    """Change one property of the 'style' attribute, according to the given
    function.
    - func: use one of the atomic_func"""
    styledict = parse_style(stylestr)
    # property must exist, otherwise error.
    prop = styledict.get(propertyname)
    newprop = func(prop, *funcargs)
    if newprop is not None:
        styledict[propertyname] = newprop
    return format_style(styledict)


def iter_multiplefindall(tree, xpathlist, ns):
    # Totally inefficient but I don't see how to do this otherwise
    for xpath in xpathlist:
        for node in tree.findall(xpath, ns):
            yield node


def change_all_attr(tree, taglist, attrname, func, *funcargs):
    """transform all corresponding attributes in the tree with the function.

    It transforms the attribute *while* traversing the tree.
    """
    root = tree.getroot()
    ns = root.nsmap
    if None in ns:
        ns.pop(None)
        
    xpathlist = ['.//%s[@%s]' % (tag, attrname) for tag in taglist]
    #print('namespace: %r' % ns, file=sys.stderr)
    #print('namespace: ', ' '.join(str(nitem) for nitem in ns.items()), file=sys.stderr)
    #print('namespace:', '\n'.join(': '.join(nitem) for nitem in ns.items()),
    #        file=sys.stderr)
    #print('search str: %r' % xpath, file=sys.stderr) 
    for node in iter_multiplefindall(tree, xpathlist, ns):
        attr = node.attrib[attrname]
        node.set(attrname, func(attr, *funcargs))


def batch_change_all_nodes(tree, taglist, attrname, func, *funcargs):
    """The difference with `change_all_attr` is that the function 'func'
    is applied to all nodes at once. So you can define a function whose
    result depends on the multiple nodes.
    
    func must take the list of nodes, *funcargs, and modify in place the nodes.
    """
    root = tree.getroot()
    ns = root.nsmap
    if None in ns:
        ns.pop(None)
    
    if attrname:
        xpathlist = ['.//%s[@%s]' % (tag, attrname) for tag in taglist]
    else:
        xpathlist = ['.//%s' % tag for tag in taglist]
    nodelist = [node in iter_multiplefindall(tree, xpathlist, ns)]
    func(nodelist, *funcargs)


#def batch_resizefont():
#    """Increase font-size intelligently: if some text elements are aligned, 
#    keep them aligned. Otherwise keep it centered."""

### More specifically change all 'style' attributes of the given tag.
def change_all_styleprop(tree, taglist, propertyname, func, *funcargs):
    """Change the given properties of all 'style' attributes of tag."""
    change_prop = lambda stylestr: change_style(stylestr, propertyname, func,
                                                *funcargs)
    change_all_attr(tree, taglist, 'style', change_prop)


### Specific function affecting all elements. They are called directly with
### the script arguments.
def svg_resizefont(infile, outfile, factor):
    """Multiply font-size attributes by the given factor."""
    tree = ET.parse(infile)
    factor = float(factor)
    change_all_styleprop(tree, ['svg:tspan', 'svg:text'], 'font-size',
                         atomic_resizefont, factor)
    tree.write(outfile)


def svg_invert(infile, outfile, keep_gradients=True):
    tree = ET.parse(infile)
    # exclude gradients: 'stop-color', 
    #change_all_styleprop(tree, ['*'], 'stop-color', atomic_invertlight)
    for color_attr in ('fill', 'stroke', 'stop-color', 'pagecolor', 'bordercolor'):
        change_all_styleprop(tree, ['*'], color_attr, atomic_invert)

    change_all_styleprop(tree, ['svg:tspan', 'svg:text'], 'fill',
                         atomic_invert, 'white')
    #for color_attr in ('fill', 'stroke', 'stop-color', 'pagecolor', 'bordercolor'):
    #    change_all_styleprop(tree, ['*'], color_attr, atomic_invert)
    #for color_attr in ('fill', 'stroke', 'stop-color', 'pagecolor', 'bordercolor'):
    #    change_all_styleprop(tree, ['*'], color_attr, atomic_invert)
    tree.write(outfile)


def svg_invertlight(infile, outfile):
    tree = ET.parse(infile)
    # exclude gradients: 'stop-color', 
    for color_attr in ('fill', 'stroke', 'pagecolor', 'bordercolor'):
        change_all_styleprop(tree, ['*'], color_attr, atomic_invertlight)
    tree.write(outfile)


def svg_invertlight2(infile, outfile):
    tree = ET.parse(infile)
    # exclude gradients: 'stop-color', 
    for color_attr in ('fill', 'stroke', 'pagecolor', 'bordercolor'):
        change_all_styleprop(tree, ['*'], color_attr, atomic_invertlight2)
    tree.write(outfile)


### OLD less malleable versions
def resizefonts(tree, factor, outfile):
    """string: content of the svg file"""
    factor = float(factor)
    regex = re.compile(r'(?<=font-size:)(\d+)(?:px)')
    # get the xml namespaces
    # somewhere in root.attrib. Should be 'xmlns'
    # Too lazy: hardcoding it:
    ns = {"xmlns": "http://www.w3.org/2000/svg",
          "dc": "http://purl.org/dc/elements/1.1/",
          "cc": "http://creativecommons.org/ns#",
          "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
          "svg": "http://www.w3.org/2000/svg",
          "xlink": "http://www.w3.org/1999/xlink",
          "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
          "inkscape": "http://www.inkscape.org/namespaces/inkscape"}
    
    #sodipodi = root.find("sodipodi:namedview", ns)
    # /!\ the 'text' elements do not have the priority to set fontsize
    # you must check tspan
    for tspan in tree.findall('.//svg:tspan[@style]', ns):
        print(tspan.tag, file=sys.stderr, end=' ')
        style = tspan.attrib['style']
        match = regex.search(style)
        if match:
            fontsize = int(match.group(1)) # float allowed? TODO
            newfontsize = round(fontsize * factor)
            print("matched", fontsize, '->', newfontsize, file=sys.stderr)
            tspan.attrib['style'] = regex.sub(str(newfontsize) + 'px', style)
    # root is an _Element. It must be converted to _ElementTree
    #tree = ET.ElementTree(element=root)
    #print(ET.tostring(tree))
    tree.write(outfile, pretty_print=True)


def svg_resizefont_old(filename, factor, outfile):
    """Main command: rescale a font from a svg file by a given factor"""
    tree = ET.parse(filename)
    resizefonts(tree, factor, outfile)


COMMANDS = {'resizefont': svg_resizefont,
            'invert': svg_invert,
            'invertlight': svg_invertlight,
            'invertlight2': svg_invertlight2}

#CMD_FUNC = {cmd_name: globals()['svg_' + cmd_name] for cmd_name in COMMANDS}

CMD_ARGS = {'resizefont': [dict(args=('factor',), type=float,
                            help="by how much to multiply the font-size")]}

# Complete __doc__
#longest_cmd_len = max(len(cmd) for cmd in COMMANDS)
#cmd_fmt = "\n  %%-%ds: %%s" % longest_cmd_len
#for command in sorted(COMMANDS):
#    command_doc = COMMANDS[command].__doc__ or ''
#    __doc__ += cmd_fmt % (command, command_doc)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('infile')
    parent_parser.add_argument('outfile')
    parent_parser.add_argument('-v', '--verbose', action='store_true')

    subparsers = parser.add_subparsers(dest='command')

    #if len(sys.argv) <= 1 or sys.argv[1] not in COMMANDS:
    #    print(__doc__, file=sys.stderr)
    #    sys.exit(1)

    #command, *cl_args = sys.argv[1:]
    #command_func = COMMANDS[command]

    # Create argument parser of the specific command.
    for cmd_name, cmd_func in COMMANDS.items():
        cmd_parser = subparsers.add_parser(cmd_name, 
                                          description=cmd_func.__doc__, 
                                          parents=[parent_parser])
        for cmd_args in CMD_ARGS.get(cmd_name, []):
            #if cmd_args:
            cmd_parser.add_argument(*cmd_args.pop('args'), **cmd_args)

    parsed_args = parser.parse_args()

    # Finally process the svg file.
    argdict = vars(parsed_args)

    if not argdict.pop('verbose'):
        def print_if_verbose(*args, **kwargs):
            pass
        
    COMMANDS[argdict.pop('command')](**argdict)

