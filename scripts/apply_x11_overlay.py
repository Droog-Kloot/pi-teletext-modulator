#!/usr/bin/env python3
"""Apply the optional Xvfb-to-PAL visible-area modification to upstream source.

Intentionally changes only a disposable copy of nutki/raspi5-teletext.
A separately copied X11 bridge implements the active video region.
"""
import pathlib
import sys


def replace_one(text, old, new, filename):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{filename}: expected 1 occurrence, found {count}: {old!r}")
    return text.replace(old, new, 1)


def main(directory):
    render = directory / "render.c"
    makefile = directory / "Makefile"
    r = render.read_text()
    m = makefile.read_text()

    r = replace_one(r,
        '#include "render.h"',
        '#include "render.h"\n#include "x11_overlay.h"',
        "render.c")

    # The source VBI packet generator still paints only the first 32 rows.
    r = replace_one(r,
        '    memset(buffer->map, 0, buffer->size);\n'
        '    for (int y = 0; y < r->height && y < r->output_height; y++) {',
        '    memset(buffer->map, 0, buffer->size);\n'
        '    x11_overlay_copy(buffer->map, buffer->pitch,\n'
        '                     r->output_width, r->output_height);\n'
        '    for (int y = 0; y < r->height && y < r->output_height; y++) {',
        "render.c")

    r = replace_one(r,
        '    pthread_join(r->thread, NULL);',
        '    pthread_join(r->thread, NULL);\n'
        '    x11_overlay_close();',
        "render.c")

    m = replace_one(m, "LDFLAGS+=-ldrm -pthread",
                    "LDFLAGS+=-ldrm -pthread -lX11", "Makefile")
    m = replace_one(m, "TELETEXT_OFILES=teletext.o render.o buffer.o hamming.o demo.o",
                    "TELETEXT_OFILES=teletext.o render.o buffer.o hamming.o demo.o x11_overlay.o",
                    "Makefile")

    render.write_text(r)
    makefile.write_text(m)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 apply_x11_overlay.py <copy-of-upstream-source-dir>")
    main(pathlib.Path(sys.argv[1]))
