#!/usr/bin/env python3
"""Shared color conversion and I/O utilities.

Color conversion formulas based on Björn Ottosson's OKLAB/OKLCH:
https://bottosson.github.io/posts/oklab/
"""

import csv
import math

import numpy as np


# =============================================================================
# Color Conversion Functions
# =============================================================================

def srgb_to_linear(c: float) -> float:
    """Convert sRGB component (0-1) to linear RGB.

    Args:
        c: sRGB component value in range [0, 1]

    Returns:
        Linear RGB component value
    """
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_srgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert linear sRGB to OKLab.

    Based on Björn Ottosson's formulas:
    https://bottosson.github.io/posts/oklab/

    Args:
        r: Linear red component
        g: Linear green component
        b: Linear blue component

    Returns:
        tuple: (L, a, b) in OKLab color space
    """
    # Linear sRGB to LMS
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    # Cube root (handle negative values)
    l_ = np.cbrt(l)
    m_ = np.cbrt(m)
    s_ = np.cbrt(s)

    # LMS to OKLab
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_val = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    return L, a, b_val


def oklab_to_oklch(L: float, a: float, b: float) -> tuple[float, float, float]:
    """Convert OKLab to OKLCH (polar coordinates).

    Args:
        L: Lightness component
        a: Green-red component
        b: Blue-yellow component

    Returns:
        tuple: (L, C, H) where L is 0-1, C is chroma, H is 0-360 degrees
    """
    C = math.sqrt(a * a + b * b)
    H = math.atan2(b, a)  # in radians
    H_deg = math.degrees(H)
    if H_deg < 0:
        H_deg += 360
    return L, C, H_deg


def oklch_to_oklab(L: float, C: float, H: float) -> tuple[float, float, float]:
    """Convert OKLCH to OKLab (cartesian coordinates).

    Args:
        L: Lightness component (0-1)
        C: Chroma component
        H: Hue in degrees (0-360)

    Returns:
        tuple: (L, a, b) in OKLab color space
    """
    H_rad = math.radians(H)
    a = C * math.cos(H_rad)
    b = C * math.sin(H_rad)
    return L, a, b


def linear_to_srgb(c: float) -> float:
    """Convert linear RGB component to sRGB (0-1).

    Args:
        c: Linear RGB component value

    Returns:
        sRGB component value in range [0, 1]
    """
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (c ** (1 / 2.4)) - 0.055


def oklab_to_linear_srgb(L: float, a: float, b: float) -> tuple[float, float, float]:
    """Convert OKLab to linear sRGB.

    Based on Björn Ottosson's formulas:
    https://bottosson.github.io/posts/oklab/

    Args:
        L: Lightness component
        a: Green-red component
        b: Blue-yellow component

    Returns:
        tuple: (r, g, b) in linear sRGB (may be outside 0-1 if out of gamut)
    """
    # OKLab to LMS (cube root space)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    # Cube to get LMS
    l = l_ * l_ * l_
    m = m_ * m_ * m_
    s = s_ * s_ * s_

    # LMS to linear sRGB
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_val = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return r, g, b_val


def oklch_to_rgb(L: float, C: float, H: float) -> tuple[int, int, int]:
    """Convert OKLCH to RGB (0-255).

    Args:
        L: Lightness component (0-1)
        C: Chroma component (0-~0.4)
        H: Hue in degrees (0-360)

    Returns:
        tuple: (r, g, b) where each component is 0-255, clamped to sRGB gamut
    """
    # OKLCH to OKLab
    L_lab, a, b = oklch_to_oklab(L, C, H)

    # OKLab to linear sRGB
    r_lin, g_lin, b_lin = oklab_to_linear_srgb(L_lab, a, b)

    # Linear sRGB to sRGB with gamma, then to 0-255
    r = round(max(0, min(1, linear_to_srgb(r_lin))) * 255)
    g = round(max(0, min(1, linear_to_srgb(g_lin))) * 255)
    b = round(max(0, min(1, linear_to_srgb(b_lin))) * 255)

    return r, g, b


def is_in_srgb_gamut(L: float, C: float, H: float, epsilon: float = 1e-6) -> bool:
    """Check if an OKLCH color is within the sRGB gamut.

    Args:
        L: Lightness component (0-1)
        C: Chroma component (0-~0.4)
        H: Hue in degrees (0-360)
        epsilon: Tolerance for floating-point comparison (default 1e-6)

    Returns:
        True if the color is within sRGB gamut, False otherwise
    """
    # Convert OKLCH to OKLab
    L_lab, a, b = oklch_to_oklab(L, C, H)

    # Convert to linear sRGB
    r_lin, g_lin, b_lin = oklab_to_linear_srgb(L_lab, a, b)

    # Check if all components are within [0, 1] (with epsilon tolerance)
    return (
        -epsilon <= r_lin <= 1 + epsilon and
        -epsilon <= g_lin <= 1 + epsilon and
        -epsilon <= b_lin <= 1 + epsilon
    )


def rgb_to_oklch(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert RGB (0-255) to OKLCH.

    Args:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)

    Returns:
        tuple: (L, C, H) where L is 0-1, C is 0-~0.4, H is 0-360 degrees
    """
    # Normalize to 0-1
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # Convert to linear sRGB
    r_lin = srgb_to_linear(r_norm)
    g_lin = srgb_to_linear(g_norm)
    b_lin = srgb_to_linear(b_norm)

    # Convert to OKLab
    L, a, b_val = linear_srgb_to_oklab(r_lin, g_lin, b_lin)

    # Convert to OKLCH
    return oklab_to_oklch(L, a, b_val)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB (0-255) to hex color string.

    Args:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)

    Returns:
        Hex color string (e.g., "#FF0000")
    """
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#FF0000" or "FF0000")

    Returns:
        tuple: (r, g, b) where each component is 0-255
    """
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# =============================================================================
# File I/O Functions
# =============================================================================

def load_colors_csv(csv_path: str) -> list[dict]:
    """Load color data from CSV file.

    Args:
        csv_path: Path to CSV file with columns: Hex, R, G, B, Count

    Returns:
        List of dicts with keys: Hex, R, G, B, Count
    """
    colors = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            colors.append({
                "Hex": row["Hex"],
                "R": int(row["R"]),
                "G": int(row["G"]),
                "B": int(row["B"]),
                "Count": int(row["Count"]),
            })
    return colors


def save_colors_to_csv(colors: list[dict], output_path: str) -> None:
    """Save color data to CSV file.

    Args:
        colors: List of dicts with keys: Hex, R, G, B, Count
        output_path: Path to output CSV file
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Hex", "R", "G", "B", "Count"])
        for color in colors:
            writer.writerow([
                color["Hex"],
                color["R"],
                color["G"],
                color["B"],
                color["Count"],
            ])
