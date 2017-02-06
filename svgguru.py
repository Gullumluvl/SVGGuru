#!/usr/bin/env python3


"""Perform simple transformations on a svg file.

USAGE:
    ./svgtweak2.py <command> <inputfile> <outputfile> [command arguments]

COMMANDS:"""


import sys
import re
import argparse

from lxml import etree as ET


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
    function."""
    styledict = parse_style(stylestr)
    # property must exist, otherwise error.
    prop = styledict[propertyname]
    styledict[propertyname] = func(prop, *funcargs)
    return format_style(styledict)


def change_all_attr(tree, tag, attrname, func, *funcargs):
    """transform all corresponding attributes in the tree with the function. 
    """
    root = tree.getroot()
    ns = root.nsmap
    if None in ns:
        ns.pop(None)
        
    xpath = './/%s[@%s]' % (tag, attrname)
    print('namespace: %r' % ns, file=sys.stderr)
    print('namespace: ', ' '.join(str(nitem) for nitem in ns.items()), file=sys.stderr)
    print('namespace:', '\n'.join(': '.join(nitem) for nitem in ns.items()),
            file=sys.stderr)
    print('search str: %r' % xpath, file=sys.stderr) 
    for node in tree.findall(xpath, ns):
        attr = node.attrib[attrname]
        node.set(attrname, func(attr, *funcargs))


### More specifically change all 'style' attributes of the given tag.
def change_all_styleprop(tree, tag, propertyname, func, *funcargs):
    """Change the given properties of all 'style' attributes of tag."""
    change_prop = lambda stylestr: change_style(stylestr, propertyname, func,
                                                *funcargs)
    change_all_attr(tree, tag, 'style', change_prop)


### Specific function affecting all elements. They are called directly with
### the script arguments.
def svg_resizefont(infile, outfile, factor):
    """Multiply font-size attributes by the given factor."""
    tree = ET.parse(infile)
    factor = float(factor)
    change_all_styleprop(tree, 'svg:tspan', 'font-size', atomic_resizefont, factor)
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


COMMANDS = {'resizefont': svg_resizefont}
ARGS = {'resizefont': [dict(args=('factor',), type=float,
                            help="by how much to multiply the font-size")]}

# Complete __doc__
longest_cmd_len = max(len(cmd) for cmd in COMMANDS)
cmd_fmt = "\n  %%-%ds: %%s" % longest_cmd_len
for command in sorted(COMMANDS):
    __doc__ += cmd_fmt % (command, COMMANDS[command].__doc__)


if __name__ == '__main__':
    if len(sys.argv) <= 1 or sys.argv[1] not in COMMANDS:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    command, *cl_args = sys.argv[1:]
    command_func = COMMANDS[command]

    # Create argument parser of the specific command.
    parser = argparse.ArgumentParser(description=command_func.__doc__)
    parser.add_argument('infile')
    parser.add_argument('outfile')

    for cmd_args in ARGS[command]:
        parser.add_argument(*cmd_args.pop('args'), **cmd_args)

    parsed_args = parser.parse_args(cl_args)

    # Finally process the svg file.
    command_func(**vars(parsed_args))

