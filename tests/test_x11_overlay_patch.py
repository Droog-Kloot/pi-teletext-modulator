"""Check optional X11 PAL overlay transforms against expected source anchors."""
import importlib.util
import pathlib
import tempfile
import unittest

BASE = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = BASE / "scripts" / "apply_x11_overlay.py"
spec = importlib.util.spec_from_file_location("apply_x11_overlay", SCRIPT)
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


class TestPatch(unittest.TestCase):
    def test_patches_only_expected_spans(self):
        source = '''#include "render.h"
static void copy_to_scanout(void) {
    memset(buffer->map, 0, buffer->size);
    for (int y = 0; y < r->height && y < r->output_height; y++) {
    }
}
    pthread_join(r->thread, NULL);
'''
        make = '''LDFLAGS+=-ldrm -pthread
TELETEXT_OFILES=teletext.o render.o buffer.o hamming.o demo.o
'''
        with tempfile.TemporaryDirectory() as td:
            folder = pathlib.Path(td)
            (folder / "render.c").write_text(source)
            (folder / "Makefile").write_text(make)
            patcher.main(folder)
            out = (folder / "render.c").read_text()
            mk = (folder / "Makefile").read_text()
            self.assertIn("x11_overlay_copy", out)
            self.assertIn("x11_overlay_close", out)
            self.assertIn("for (int y = 0; y < r->height", out)
            self.assertIn("x11_overlay.o", mk)
            self.assertIn("-lX11", mk)
            with self.assertRaises(SystemExit):
                patcher.main(folder)


if __name__ == "__main__":
    unittest.main()
