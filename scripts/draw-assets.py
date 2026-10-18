import shutil
import pathlib
import struct
import zlib
import math
import sys

p = pathlib.Path(sys.argv[1])
p.mkdir(parents=True, exist_ok=True)


def png(path, w, h, rows):
    def chunk(t, d):
        return (
            struct.pack(">I", len(d))
            + t
            + d
            + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(b"\0" + r for r in rows)))
        + chunk(b"IEND", b"")
    )


rows = []
for y in range(320):
    row = bytearray()
    for x in range(1920):
        dx = max(80 - x, 0, x - 1840)
        dy = max(52 - y, 0, y - 268)
        dist = math.hypot(dx, dy)
        a = max(0, min(1, 40.5 - dist))
        border = dist > 38.5
        row.extend(
            (66, 69, 79, round(246 * a)) if border else (27, 29, 36, round(246 * a))
        )
    rows.append(row)
png(p / "compact-dock-background-v2.png", 1920, 320, rows)
png(p / "compact-dock-transparent-v2.png", 2, 2, [b"\0" * 8] * 2)
rows = []
for y in range(256):
    row = bytearray()
    for x in range(256):
        dist = math.hypot(max(48 - x, 0, x - 207), max(48 - y, 0, y - 207))
        alpha = round(255 * max(0, min(1, 48.5 - dist)))
        row.extend((255, 255, 255, alpha))
    rows.append(row)
png(p / "compact-dock-icon-mask-v2.png", 256, 256, rows)

# The current dock fits its backdrop to a centered container.
rows = []
for y in range(250):
    row = bytearray()
    for x in range(1600):
        distance = math.hypot(max(40 - x, 0, x - 1559), max(44 - y, 0, y - 205))
        alpha = round(246 * max(0, min(1, 36.5 - distance)))
        rgb = (68, 71, 80) if distance > 35 else (27, 29, 36)
        row.extend((*rgb, alpha))
    rows.append(row)
png(p / "compact-dock-background-v3.png", 1600, 250, rows)
# v1 is retained only as an intermediate resource name during the build.

shutil.copyfile(
    p / "compact-dock-background-v2.png", p / "compact-dock-background-v1.png"
)
shutil.copyfile(
    p / "compact-dock-transparent-v2.png", p / "compact-dock-transparent-v1.png"
)
