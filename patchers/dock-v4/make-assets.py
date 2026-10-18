"""Generate original 512px rounded mask/focus artwork using only Python stdlib."""

import math
from pathlib import Path
import struct
import sys
import zlib


def png(path, ring):
    size = 512
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            coverage = 0
            for sy in (0.125, 0.375, 0.625, 0.875):
                for sx in (0.125, 0.375, 0.625, 0.875):
                    half = 253 if ring else 256
                    qx = abs(x + sx - 256) - (half - 104)
                    qy = abs(y + sy - 256) - (half - 104)
                    distance = (
                        math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - 104
                    )
                    coverage += distance <= 0 and (not ring or distance >= -6)
            pixels.extend(
                (255, 255, 255, round(coverage * (245 if ring else 255) / 16))
            )

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    png(destination / "focus-ring-v4.png", True)
    png(destination / "compact-dock-icon-mask-v4.png", False)
