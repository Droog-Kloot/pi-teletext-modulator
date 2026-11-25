#ifndef X11_OVERLAY_H
#define X11_OVERLAY_H
#include <stdint.h>
void x11_overlay_copy(uint8_t *target, uint32_t pitch, int width, int height);
void x11_overlay_close(void);
#endif
