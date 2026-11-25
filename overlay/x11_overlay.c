/*
 * Xvfb active-picture bridge for raspi5-teletext.
 * Written for the Pi Teletext Modulator project.
 *
 * Reads a screenshot from DISPLAY (normally :99) at <=25fps, converts it
 * to XRGB8888 and puts it in PAL active scanlines 32..607. The caller writes
 * the independent Teletext VBI afterwards, into lines 0..31.
 *
 * Requires an X11 server and libX11-dev. No DRM ownership is taken here.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include "x11_overlay.h"

#define VBI_LINES 32
#define FRAME_NS 40000000LL

static Display *display;
static Window root;
static XImage *snapshot;
static int source_width, source_height;
static int64_t last_capture;
static int warned;

static int64_t mono_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static void capture(void)
{
    int64_t now = mono_ns();
    if (snapshot && now - last_capture < FRAME_NS) return;

    if (!display) {
        display = XOpenDisplay(NULL);
        if (!display) {
            if (!warned) {
                fprintf(stderr, "X11 overlay: cannot open DISPLAY; PAL image remains black\n");
                warned = 1;
            }
            return;  /* retry if Xvfb starts later */
        }
        root = DefaultRootWindow(display);
        warned = 0;
    }
    XWindowAttributes attrs;
    if (!XGetWindowAttributes(display, root, &attrs)) return;
    if (attrs.width <= 0 || attrs.height <= 0) return;

    int w = attrs.width < 720 ? attrs.width : 720;
    int h = attrs.height < 576 ? attrs.height : 576;
    XImage *new_image = XGetImage(display, root, 0, 0, (unsigned)w,
                                 (unsigned)h, AllPlanes, ZPixmap);
    if (!new_image) return;
    if (snapshot) XDestroyImage(snapshot);
    snapshot = new_image;
    source_width = w;
    source_height = h;
    last_capture = now;
}

void x11_overlay_copy(uint8_t *target, uint32_t pitch, int width, int height)
{
    capture();
    if (!snapshot || width <= 0 || height <= VBI_LINES) return;

    int visible_height = height - VBI_LINES;
    int fast = snapshot->bits_per_pixel == 32 &&
               snapshot->red_mask == 0x00ff0000 &&
               snapshot->green_mask == 0x0000ff00 &&
               snapshot->blue_mask == 0x000000ff &&
               snapshot->byte_order == LSBFirst;

    for (int y = 0; y < visible_height; y++) {
        int sy = (int)((int64_t)y * source_height / visible_height);
        if (sy >= source_height) sy = source_height - 1;
        uint32_t *out = (uint32_t *)(target + (size_t)(y + VBI_LINES) * pitch);
        const uint32_t *in = fast ? (const uint32_t *)(snapshot->data + (size_t)sy * snapshot->bytes_per_line) : NULL;
        for (int x = 0; x < width; x++) {
            int sx = (int)((int64_t)x * source_width / width);
            if (sx >= source_width) sx = source_width - 1;
            unsigned long color = fast ? in[sx] : XGetPixel(snapshot, sx, sy);
            out[x] = 0xff000000u | ((uint32_t)color & 0x00ffffffu);
        }
    }
}

void x11_overlay_close(void)
{
    if (snapshot) { XDestroyImage(snapshot); snapshot = NULL; }
    if (display) { XCloseDisplay(display); display = NULL; }
}
