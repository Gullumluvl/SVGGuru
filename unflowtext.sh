#!/bin/bash

input_file=${1:-}

if [ -z "$input_file" ]; then
	echo "Error: no input_file given." >&2
	exit 1
fi

# 4 levels of ungrouping should be enough
# TODO: choose how many ungrouping are needed. In combination with a script
# counting the number and nesting of groups.

inkscape --verb LayerShowAll \
	--verb EditSelectAllInAllLayers \
	--verb SelectionUnGroup \
	--verb SelectionUnGroup \
	--verb SelectionUnGroup \
	--verb SelectionUnGroup \
	--verb ObjectFlowtextToText \
	"$input_file"
