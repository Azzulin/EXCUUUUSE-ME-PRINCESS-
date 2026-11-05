"""PNG statistics without Pillow: per-channel mean/max, share of non-black pixels, and an opaque copy (alpha forced to
255, colours scaled up by --gain) so a dark or transparent shot can be looked at.
Usage: python3 pngstat.py in.png [out.png] [--gain N]"""
import struct
import sys
import zlib

import numpy as np


def read_png(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, idat, w = 8, b'', None
    while pos < len(data):
        n, typ = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if typ == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', body[:10])
        elif typ == b'IDAT':
            idat += body
        pos += 12 + n
    ch = {2: 3, 6: 4, 0: 1, 4: 2}[ctype]
    raw = zlib.decompress(idat)
    stride = w * ch
    out = np.zeros((h, stride), np.uint8)
    prev = np.zeros(stride, np.int32)
    i = 0
    for y in range(h):
        f = raw[i]
        line = np.frombuffer(raw, np.uint8, stride, i + 1).astype(np.int32)
        i += 1 + stride
        if f == 0:
            cur = line
        elif f == 2:
            cur = (line + prev) & 255
        else:
            cur = np.zeros(stride, np.int32)
            for x in range(stride):
                a = cur[x - ch] if x >= ch else 0
                b = prev[x]
                c = prev[x - ch] if x >= ch else 0
                if f == 1:
                    p = a
                elif f == 3:
                    p = (a + b) >> 1
                else:
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    p = a if pa <= pb and pa <= pc else b if pb <= pc else c
                cur[x] = (line[x] + p) & 255
        out[y] = cur
        prev = cur
    return out.reshape(h, w, ch)


def write_png(path, img):
    h, w, ch = img.shape
    raw = b''.join(b'\x00' + img[y].tobytes() for y in range(h))
    def chunk(t, b):
        return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    ctype = 6 if ch == 4 else 2
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def main():
    img = read_png(sys.argv[1])
    h, w, ch = img.shape
    print(f'{w}x{h} channels {ch}')
    for c, name in zip(range(ch), 'RGBA'):
        print(f'  {name}: mean {img[..., c].mean():.2f} max {img[..., c].max()}')
    rgb = img[..., :3].astype(np.int32)
    print(f'  pixels with any colour > 8: {(rgb.max(axis=2) > 8).mean() * 100:.2f} %')
    if len(sys.argv) <= 2 or sys.argv[2].startswith('--'):
        return
    gain = float(sys.argv[sys.argv.index('--gain') + 1]) if '--gain' in sys.argv else 1.0
    o = np.clip(rgb * gain, 0, 255).astype(np.uint8)
    small = o[::2, ::2]   # half size for viewing
    write_png(sys.argv[2], small)
    print('  wrote', sys.argv[2])


if __name__ == "__main__":
    main()
