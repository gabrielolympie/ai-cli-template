from mirascope import llm
import os
import sys
import platform
import subprocess
import uuid
import shutil
from datetime import datetime
from PIL import Image

PROJECT_ROOT = os.getcwd()

# Try importing mss for cross‑platform screenshots
try:
    from mss import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


def linux_to_windows_path(linux_path: str) -> str:
    """Convert a Linux path from /mnt/c/... to Windows C:\\... format."""
    if linux_path.startswith('/mnt/'):
        parts = linux_path.split('/')
        if len(parts) >= 3:
            drive = parts[2].upper() + ':'
            rel_path = '/'.join(parts[3:])
            return drive + '\\' + rel_path.replace('/', '\\')
    return linux_path


def detect_os() -> str:
    """Detect if we are running on Windows, macOS, Linux, or WSL."""
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "mac"
    elif "microsoft" in platform.uname().release.lower():
        return "wsl"
    else:
        return "linux"


def resize_to_1_megapixel(img: Image.Image) -> Image.Image:
    """Resize an image to ~1 MP while preserving aspect ratio."""
    width, height = img.size
    current_pixels = width * height
    target_pixels = 1_000_000

    if current_pixels <= target_pixels:
        return img

    scale_factor = (target_pixels / current_pixels) ** 0.5
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def crop_to_bbox(img: Image.Image, bbox: dict) -> Image.Image:
    """Crop image to a bounding box (supports two bbox formats)."""
    width, height = img.size

    if all(k in bbox for k in ['x1', 'y1', 'x2', 'y2']):
        left = max(0, bbox['x1'])
        top = max(0, bbox['y1'])
        right = min(width, bbox['x2'])
        bottom = min(height, bbox['y2'])
    elif all(k in bbox for k in ['x', 'y', 'width', 'height']):
        left = max(0, bbox['x'])
        top = max(0, bbox['y'])
        right = min(width, bbox['x'] + bbox['width'])
        bottom = min(height, bbox['y'] + bbox['height'])
    else:
        raise ValueError(
            "bbox must contain either 'x','y','width','height' or 'x1','y1','x2','y2'"
        )

    if left >= right or top >= bottom:
        raise ValueError(
            f"Invalid bbox coordinates: left={left}, top={top}, right={right}, bottom={bottom}"
        )

    return img.crop((left, top, right, bottom))


def take_screenshot_mss(path: str) -> None:
    """Take a screenshot using the mss library (cross‑platform)."""
    with mss() as sct:
        sct.shot(mon=-1, output=path)


def take_screenshot_wsl(path: str) -> None:
    """
    WSL‑specific screenshot using PowerShell with DPI‑aware capture.
    The image is first saved to a temporary `.tmp/` folder, then moved to `path`.
    """
    temp_dir = os.path.join(PROJECT_ROOT, ".tmp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_capture_path = os.path.join(
        temp_dir, f"capture_{uuid.uuid4().hex[:8]}.png"
    )

    windows_output_path = linux_to_windows_path(temp_capture_path)
    windows_path_escaped = windows_output_path.replace('\\', '\\\\')

    ps_script = fr"""Add-Type @"
using System;
using System.Runtime.InteropServices;

public class ScreenCapture {{
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    public static extern IntPtr GetDC(IntPtr hwnd);

    [DllImport("gdi32.dll")]
    public static extern int GetDeviceCaps(IntPtr hdc, int index);

    [DllImport("user32.dll")]
    public static extern int ReleaseDC(IntPtr hwnd, IntPtr hdc);

    public const int DESKTOPHORZRES = 118;
    public const int DESKTOPVERTRES = 117;

    public static int[] GetPhysicalResolution() {{
        IntPtr hdc = GetDC(IntPtr.Zero);
        int w = GetDeviceCaps(hdc, DESKTOPHORZRES);
        int h = GetDeviceCaps(hdc, DESKTOPVERTRES);
        ReleaseDC(IntPtr.Zero, hdc);
        return new int[] {{ w, h }};
    }}
}}
"@

[ScreenCapture]::SetProcessDPIAware()
Add-Type -AssemblyName System.Drawing

$res = [ScreenCapture]::GetPhysicalResolution()
$width = $res[0]
$height = $res[1]

Write-Host "Capturing at: $width x $height"

$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen(0, 0, 0, 0, (New-Object System.Drawing.Size($width, $height)))

$bitmap.Save('{windows_path_escaped}', [System.Drawing.Imaging.ImageFormat]::Png)

$graphics.Dispose()
$bitmap.Dispose()

Write-Host "Screenshot saved successfully"
"""

    ps_script_path = os.path.join(
        temp_dir, f"screenshot_{uuid.uuid4().hex[:8]}.ps1"
    )
    with open(ps_script_path, "w", encoding="utf-8") as f:
        f.write(ps_script)

    try:
        ps_script_windows = linux_to_windows_path(ps_script_path)
        powershell_path = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
        result = subprocess.run(
            [powershell_path, "-ExecutionPolicy", "Bypass", "-File", ps_script_windows],
            capture_output=True,
            timeout=30,
        )

        stdout_text = (
            result.stdout.decode("utf-8", errors="ignore")
            if result.stdout
            else ""
        )
        stderr_text = (
            result.stderr.decode("utf-8", errors="ignore")
            if result.stderr
            else ""
        )

        if result.returncode != 0:
            raise Exception(f"PowerShell failed: {stderr_text}")

        # Move the temporary capture to the final destination (Linux side)
        if os.path.exists(temp_capture_path):
            shutil.move(temp_capture_path, path)
        else:
            raise Exception(
                f"Screenshot not created at temp path: {temp_capture_path}"
            )

        return stdout_text

    finally:
        if os.path.exists(ps_script_path):
            os.unlink(ps_script_path)
        if os.path.exists(temp_capture_path):
            os.unlink(temp_capture_path)


@llm.tool
def screenshot(
    path: str = None,
    bbox_x: int = None,
    bbox_y: int = None,
    bbox_width: int = None,
    bbox_height: int = None,
):
    """
    Take a screenshot and optionally crop to a bounding box.

    The function automatically selects the appropriate capture method:
    - Windows / macOS / Linux → mss library
    - WSL → PowerShell DPI‑aware capture (writes to .tmp/ first)

    The image is resized to ~1 MP after optional cropping.
    """
    os_type = detect_os()

    # ------------------------------------------------------------------
    # NEW DEFAULT DIRECTORY & RANDOM filename
    # ------------------------------------------------------------------
    screenshots_dir = os.path.join(PROJECT_ROOT, "screenshot")   # subfolder "./screenshot"

    try:
        # ---------- Determine output path ----------
        if path is None:
            # Random 8‑character hex name
            random_name = f"{uuid.uuid4().hex[:8]}.png"
            path = os.path.join(screenshots_dir, random_name)
        else:
            if not os.path.isabs(path):
                path = os.path.abspath(path)

        # ---------- Validate path ----------
        normalized_path = os.path.normpath(path)
        normalized_root = os.path.normpath(PROJECT_ROOT)

        if not (
            normalized_path == normalized_root
            or normalized_path.startswith(normalized_root + os.sep)
        ):
            return (
                f"Error: Path '{path}' is outside the project directory "
                f"'{PROJECT_ROOT}'"
            )

        # Ensure the directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)

        # ---------- Bounding‑box handling ----------
        use_bbox = all(
            v is not None for v in [bbox_x, bbox_y, bbox_width, bbox_height]
        )

        # ---------- Capture ----------
        print(f"Detected OS: {os_type.upper()}")

        if os_type == "wsl":
            take_screenshot_wsl(path)
        elif MSS_AVAILABLE:
            take_screenshot_mss(path)
        else:
            return (
                f"Error: mss library not available for {os_type}. "
                "Install with: pip install mss"
            )

        if not os.path.exists(path):
            return f"Error: Screenshot file not created at {path}"

        # ---------- Post‑process ----------
        with Image.open(path) as img:
            orig_w, orig_h = img.size
            print(f"Original image size: {orig_w}x{orig_h}")

            if use_bbox:
                bbox = {
                    "x": bbox_x,
                    "y": bbox_y,
                    "width": bbox_width,
                    "height": bbox_height,
                }
                img = crop_to_bbox(img, bbox)
                print(
                    f"Cropped to bbox: x={bbox_x}, y={bbox_y}, "
                    f"w={bbox_width}, h={bbox_height}"
                )

            img = resize_to_1_megapixel(img)
            new_w, new_h = img.size
            print(
                f"Resized to ~1 MP: {new_w}x{new_h} "
                f"({new_w * new_h} pixels)"
            )
            img.save(path, "PNG")

        # Return path relative to project root (now under ./screenshot)
        return f"screenshot/{os.path.basename(path)}"

    except Exception as e:
        return f"Error taking screenshot on {os_type.upper()}: {str(e)}"


# ----------------------------------------------------------------------
# Example usage (run directly for a quick test)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Basic screenshot (saved to ./screenshot/<random>.png)
    print(screenshot())

    # Screenshot with a bounding box (uncomment to test)
    # print(screenshot(bbox_x=100, bbox_y=100, bbox_width=800, bbox_height=600))