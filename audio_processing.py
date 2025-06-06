from pprint import pprint
import numpy as np
from PySide6.QtGui import QImage, QColor
import wave
import logging


MAX_TEX_SIDE = 8192           # maximum texture width/height


def _read_wave(filepath: str):
    """Read wav into a numpy array of float16 in the range [-1, 1]."""
    with wave.open(filepath, 'rb') as wav:
        n_ch, samp_w, n_frames = wav.getnchannels(), wav.getsampwidth(), wav.getnframes()
        raw = wav.readframes(n_frames)

    # Convert to temporary int array
    if samp_w == 2:
        samples = np.frombuffer(raw, dtype=np.int16)
    elif samp_w == 3:                              # 24-bit little-endian
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        samples = (b[:, 0].astype(np.int32)          |
                   (b[:, 1].astype(np.int32) << 8)   |
                   (b[:, 2].astype(np.int32) << 16))
        samples = np.where(samples & 0x800000, samples - 0x1000000, samples)
    elif samp_w == 4:
        samples = np.frombuffer(raw, dtype=np.int16)
    else:
        raise ValueError(f'Unsupported sample width: {samp_w} bytes')

    # Normalize to [-1, 1]
    max_val = float(2 ** (8 * samp_w - 1))
    samples = samples.astype(np.float32) / max_val

    return samples.reshape(-1, n_ch)   # shape: (frames, channels)


def audio_to_qimage(filepath: str, samples_per_pixel: int = 1) -> tuple[QImage, int]:
    audio = _read_wave(filepath)

    if audio.shape[1] < 2:
        raise ValueError('Need at least two channels (stereo)')

    left, right = audio[:, 0], audio[:, 1]

    total = left.size
    pixels = int(np.ceil(total / samples_per_pixel))
    pad = pixels * samples_per_pixel - total
    if pad:
        left = np.pad(left, (0, pad), 'constant')
        right = np.pad(right, (0, pad), 'constant')

    # reshape creates a view without extra memory
    left = left.reshape(pixels, samples_per_pixel)
    right = right.reshape(pixels, samples_per_pixel)

    def norm(a: np.ndarray) -> np.ndarray:
        return ((a + 1.0) * 0.5).astype(np.float32)

    # Assemble RGBA line immediately
    line = np.stack(
        (
            norm(right.min(1)),  # R  – min right
            norm(right.max(1)),  # G  – max right
            norm(left.min(1)),  # B  – min left
            norm(left.max(1))  # A  – max left
        ),
        axis=1,
    )
    # Arrange into a texture with a MAX_TEX_SIDE limit
    width = min(pixels, MAX_TEX_SIDE)
    height = int(np.ceil(pixels / width))
    if height > MAX_TEX_SIDE:
        raise OverflowError("Texture is too big. Use a smaller 'samples_per_pixel' value or increase 'MAX_TEX_SIDE'.")

    tex_size = width * height
    if tex_size != pixels:  # pad up to rectangle
        line = np.vstack((line, np.zeros((tex_size - pixels, 4), np.float32)))

    img_array = line.reshape(height, width, 4).astype(np.float16)  # view, no copy
 
    # 1. float16 to bytes. Format_RGBA16FPx4 needs: R(float16), G(float16), B(float16), A(float16)
    bytes_data = img_array.tobytes()

    # 2. Create QImage from the byte array
    qimg = QImage(bytes_data, width, height, width * 8, QImage.Format.Format_RGBA16FPx4_Premultiplied)

    # Check if the QImage was created successfully
    if qimg.isNull():
        logging.error("ERROR: Failed to create QImage from array data! Returning fallback image.")
        # Return a fallback image
        fallback = QImage(MAX_TEX_SIDE, MAX_TEX_SIDE, QImage.Format.Format_RGBA16FPx4_Premultiplied)
        fallback.fill(QColor(154, 100, 154, 100))
        return fallback, 0

    # 4. Create a copy of the QImage
    qimg = QImage(qimg)

    logging.debug(f"Created QImage: {qimg.width()}x{qimg.height()}, format: {qimg.format()}, isNull: {qimg.isNull()}")
    # qimg.save("w.png", "PNG", 100)  # debug save to file
    return qimg, pixels

