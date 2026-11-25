#!/usr/bin/env python3
"""Stream Level-1 TTI pages as 42-byte packets to raspi5-teletext -.
Supports PN, SC, OL 0..25, ESC control codes, and odd parity.
Packet 26/28/29 enhancement data is not yet encoded.
"""
import argparse
import datetime
import pathlib
import sys
import time


def hamming84(d):
    d1, d2, d3, d4 = ((d >> i) & 1 for i in range(4))
    p1 = (1 + d1 + d3 + d4) & 1
    p2 = (1 + d1 + d2 + d4) & 1
    p3 = (1 + d1 + d2 + d3) & 1
    p4 = (1 + p1 + d1 + p2 + d2 + p3 + d3 + d4) & 1
    return p1 | d1 << 1 | p2 << 2 | d2 << 3 | p3 << 4 | d3 << 5 | p4 << 6 | d4 << 7


def odd_parity(d):
    d &= 0x7f
    return d | (0x80 if d.bit_count() % 2 == 0 else 0)


def decode_tti_line(raw):
    out = bytearray()
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == 0x1b and i + 1 < len(raw) and 0x40 <= raw[i + 1] <= 0x5f:
            out.append(raw[i + 1] - 0x40)
            i += 2
        else:
            out.append(c)
            i += 1
    return bytes(out[:40]).ljust(40, b' ')


def parse_file(path):
    pn = None
    subcode = 0
    rows = {}
    for raw in path.read_bytes().splitlines():
        if len(raw) < 3 or raw[2:3] != b',':
            continue
        tag, data = raw[:2], raw[3:]
        if tag == b'PN':
            val = data.decode('ascii', 'ignore').strip()
            if len(val) >= 3:
                page = val[:3]
                if all(ch in '0123456789ABCDEFabcdef' for ch in page):
                    pn = int(page, 16)
                    if len(val) >= 5:
                        try:
                            subcode = int(val[3:5], 16)
                        except ValueError:
                            pass
        elif tag == b'SC':
            try:
                subcode = int(data.strip(), 16) & 0x3f7f
            except ValueError:
                pass
        elif tag == b'OL':
            number, sep, content = data.partition(b',')
            if not sep:
                continue
            try:
                row = int(number)
            except ValueError:
                continue
            if 0 <= row <= 25:
                rows[row] = decode_tti_line(content)
            elif row in (26, 27, 28, 29):
                print(f'{path.name}: OL,{row} (enhancement packet) not supported yet', file=sys.stderr)
    if pn is None or not (0x100 <= pn <= 0x8ff) or (pn >> 8) > 8:
        raise ValueError(f'{path}: missing/invalid PN')
    return pn, subcode, rows


def packet_address(magazine, row):
    m = magazine & 7  # Magazine 8 is encoded as 0
    address = m | (row << 3)
    return bytes((hamming84(address & 15), hamming84(address >> 4)))


def make_packets(page):
    pn, subcode, rows = page
    mag = pn >> 8
    number = pn & 0xff
    # Header bytes 2..9: page number, subcode and control bits.
    # Default control bits: normal visible Level-1 page, no erase flag.
    header = bytes((
        hamming84(number & 15), hamming84(number >> 4),
        hamming84(subcode & 15), hamming84((subcode >> 4) & 7),
        hamming84((subcode >> 8) & 15), hamming84((subcode >> 12) & 3),
        hamming84(0), hamming84(0),
    ))
    raw_header = rows.get(0, b' ' * 40)
    clock = datetime.datetime.now().strftime('%H:%M:%S').encode()
    raw_header = raw_header.replace(b'%H:%M.%S', clock).replace(b'%H:%M:%S', clock)
    # The first eight characters of OL,0 are replaced by the encoded header.
    yield packet_address(mag, 0) + header + bytes(map(odd_parity, raw_header[8:40]))
    for row in range(1, 24):
        raw = rows.get(row, b' ' * 40)
        yield packet_address(mag, row) + bytes(map(odd_parity, raw))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('directory', type=pathlib.Path)
    ap.add_argument('--interval', type=float, default=0.1, help='seconds between pages')
    args = ap.parse_args()
    if not args.directory.is_dir():
        ap.error(f'not a directory: {args.directory}')
    warned = set()
    while True:
        pages = []
        for path in sorted(args.directory.glob('*.tti')):
            try:
                pages.append(parse_file(path))
            except (OSError, ValueError) as exc:
                if str(exc) not in warned:
                    print(exc, file=sys.stderr)
                    warned.add(str(exc))
        if not pages:
            print('No valid .tti files found; retrying...', file=sys.stderr)
            time.sleep(2)
            continue
        for page in pages:
            for packet in make_packets(page):
                sys.stdout.buffer.write(packet)
            sys.stdout.buffer.flush()
            time.sleep(args.interval)


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        pass