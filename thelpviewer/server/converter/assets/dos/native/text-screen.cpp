// THelpViewer text-screen bridge for the pinned js-dos DOSBox backend.
// SPDX-License-Identifier: GPL-2.0-or-later
#include <emscripten.h>
#include <cstring>
#include <vector>
#include "vga.h"
#include "mem.h"
#include "int10.h"

EM_JS(void, thelp_send_screen, (const unsigned char* data, int length), {
    const bytes = Module.HEAPU8.slice(data, data + length);
    Module.sendMessage("ws-log", { tag: "thelp-screen", message: bytes });
});

// Called at the same boundary as the ordinary pixel frame. No guest program,
// interrupt hook, RAM dump or filesystem polling is involved.
void thelp_video_frame() {
    static std::vector<unsigned char> previous;
    static unsigned refresh = 0;
    std::vector<unsigned char> packet(16, 0);
    const unsigned cols = vga.draw.blocks, height = vga.draw.address_line_total;
    const unsigned rows = height ? vga.draw.lines_total / height : 0;
    const unsigned char* standard = height == 16 ? int10_font_16 :
        height == 14 ? int10_font_14 : height == 8 ? int10_font_08 : 0;
    bool supported = vga.mode == M_TEXT && IS_VGA_ARCH && standard &&
        cols > 0 && cols <= 160 && rows > 0 && rows <= 100 &&
        vga.draw.lines_total % height == 0 && !vga.draw.panning &&
        !vga.config.hlines_skip && !vga.draw.vblank_skip &&
        vga.draw.split_line >= vga.draw.lines_total && !vga.attr.disabled &&
        vga.tandy.draw_base && vga.draw.font_tables[0] && vga.draw.font_tables[1];
    // The HTML character view uses the standard CP437 font. Custom/dual fonts
    // and underline effects retain the accurate DOSBox pixel renderer.
    if (supported) {
        for (unsigned glyph = 0; glyph < 256 && supported; ++glyph) {
            for (unsigned row = 0; row < height; ++row) {
                if (vga.draw.font_tables[0][glyph * 32 + row] != standard[glyph * height + row] ||
                    vga.draw.font_tables[1][glyph * 32 + row] != standard[glyph * height + row]) {
                    supported = false; break;
                }
            }
        }
    }
    if (supported) {
        packet[0] = 1; // graphics/fallback=0, text=1
        packet[1] = cols; packet[2] = rows; packet[3] = height;
        packet[4] = vga.draw.char9dot ? 9 : 8;
        packet[5] = vga.draw.blinking ? 1 : 0;
        packet[6] = vga.draw.blink ? 1 : 0;
        packet[7] = vga.draw.cursor.enabled && (vga.draw.cursor.count & 0x10) ? 1 : 0;
        packet[8] = 255; packet[9] = 255;
        packet[10] = vga.draw.cursor.sline; packet[11] = vga.draw.cursor.eline;
        packet.resize(16 + 48 + cols * rows * 2);
        for (unsigned color = 0; color < 16; ++color) {
            const RGBEntry& rgb = vga.dac.rgb[vga.dac.combine[color] & vga.dac.pel_mask];
            packet[16 + color * 3] = (rgb.red << 2) | (rgb.red >> 4);
            packet[17 + color * 3] = (rgb.green << 2) | (rgb.green >> 4);
            packet[18 + color * 3] = (rgb.blue << 2) | (rgb.blue >> 4);
        }
        const unsigned start = (vga.config.real_start + vga.draw.bytes_skip) * 2;
        for (unsigned row = 0; row < rows; ++row) {
            const unsigned address = start + row * vga.draw.address_add;
            for (unsigned col = 0; col < cols; ++col) {
                const unsigned index = 64 + (row * cols + col) * 2;
                const unsigned at = (address + col * 2) & vga.draw.linear_mask;
                packet[index] = vga.tandy.draw_base[at];
                packet[index + 1] = vga.tandy.draw_base[(at + 1) & vga.draw.linear_mask];
                if ((packet[index + 1] & 0x77) == 1) { supported = false; }
                if (at == (vga.draw.cursor.address & vga.draw.linear_mask)) {
                    packet[8] = col; packet[9] = row;
                }
            }
        }
    }
    if (!supported) { packet.assign(16, 0); }
    // Refresh occasionally so listeners attaching after initial CI readiness
    // still receive a static screen. Otherwise publish only changed state.
    if (packet != previous || ++refresh >= 70) {
        thelp_send_screen(packet.data(), packet.size()); previous.swap(packet); refresh = 0;
    }
}
