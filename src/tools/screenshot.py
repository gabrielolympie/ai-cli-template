from mirascope import llm
import os
import sys
import platform
import subprocess
import uuid
from datetime import datetime
from PIL import Image

PROJECT_ROOT = os.getcwd()

# Try importing mss for cross-platform screenshots
try:
    from mss import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


def linux_to_windows_path(linux_path):
    """Convert a Linux path from /mnt/c/... to Windows C:\\... format"""
    if linux_path.startswith('/mnt/'):
        parts = linux_path.split('/')
        if len(parts) >= 3:
            drive = parts[2].upper() + ':'
            rel_path = '/'.join(parts[3:])
            return drive + '\\' + rel_path.replace('/', '\\')
    return linux_path


def detect_os():
    """
    Detects if we are running on Windows, Mac, Linux, or WSL.
    """
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "mac"
    elif "microsoft" in platform.uname().release.lower():
        return "wsl"
    else:
        return "linux"


def resize_to_1_megapixel(img):
    """
    Resize an image to approximately 1 megapixel while maintaining aspect ratio.
    1 megapixel = 1,000,000 pixels, so target is ~1000x1000 or any combination
    that multiplies to ~1,000,000.

    Args:
        img: PIL Image object

    Returns:
        Resized PIL Image object
    """
    width, height = img.size
    current_pixels = width * height
    target_pixels = 1_000_000

    # If already under 1MP, just return
    if current_pixels <= target_pixels:
        return img

    # Calculate scaling factor
    scale_factor = (target_pixels / current_pixels) ** 0.5
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def crop_to_bbox(img, bbox):
    """
    Crop image to bounding box.

    Args:
        img: PIL Image object
        bbox: dict with 'x', 'y', 'width', 'height' keys (in pixels)
              or 'x1', 'y1', 'x2', 'y2' for corner coordinates

    Returns:
        Cropped PIL Image object
    """
    width, height = img.size

    # Support both bbox formats
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
        raise ValueError("bbox must contain either 'x', 'y', 'width', 'height' or 'x1', 'y1', 'x2', 'y2' keys")

    # Validate coordinates
    if left >= right or top >= bottom:
        raise ValueError(f"Invalid bbox coordinates: left={left}, top={top}, right={right}, bottom={bottom}")

    return img.crop((left, top, right, bottom))


def take_screenshot_mss(path):
    """
    Take screenshot using mss library (cross-platform).
    Works on Windows, macOS, and Linux.
    """
    with mss() as sct:
        # Capture all monitors (mon=-1) or primary monitor (mon=1)
        sct.shot(mon=-1, output=path)


def take_screenshot_wsl(path):
    """
    WSL-specific screenshot using PowerShell with DPI-aware capture.
    Ensures the full screen is captured at physical resolution.
    """
    # Convert paths to Windows format for PowerShell
    windows_output_path = linux_to_windows_path(path)
    windows_path_escaped = windows_output_path.replace('\\', '\\\\')

    # PowerShell script that captures physical screen resolution
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

# Get the REAL physical resolution
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

    # Save PowerShell script to temp file
    temp_dir = os.path.join(PROJECT_ROOT, ".tmp")
    os.makedirs(temp_dir, exist_ok=True)
    ps_script_path = os.path.join(temp_dir, f"screenshot_{uuid.uuid4().hex[:8]}.ps1")

    with open(ps_script_path, 'w', encoding='utf-8') as f:
        f.write(ps_script)

    try:
        # Convert script path to Windows format
        ps_script_windows = linux_to_windows_path(ps_script_path)

        # Execute PowerShell
        powershell_path = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
        result = subprocess.run(
            [powershell_path, '-ExecutionPolicy', 'Bypass', '-File', ps_script_windows],
            capture_output=True,
            timeout=30
        )

        stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
        stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""

        if result.returncode != 0:
            raise Exception(f"PowerShell failed: {stderr_text}")

        return stdout_text

    finally:
        # Clean up temp script
        if os.path.exists(ps_script_path):
            os.unlink(ps_script_path)


@llm.tool
def screenshot(
    path: str = None,
    bbox_x: int = None,
    bbox_y: int = None,
    bbox_width: int = None,
    bbox_height: int = None
):
    """Take a screenshot and optionally crop to a bounding box.

    This tool automatically detects the operating system and uses the appropriate method:
    - Windows: Uses mss library for fast, reliable screenshots
    - macOS: Uses mss library (requires screen recording permission)
    - Linux: Uses mss library
    - WSL: Uses PowerShell with DPI-aware capture to ensure full screen is captured

    The screenshot is automatically resized to approximately 1 megapixel (1000x1000 equivalent)
    while maintaining the aspect ratio.

    Args:
        path: Optional path where to save the screenshot.
              If not provided, saves to ./screenshots directory with timestamped filename.
              Should have .png extension.
        bbox_x: Optional X coordinate of the bounding box top-left corner (in pixels)
        bbox_y: Optional Y coordinate of the bounding box top-left corner (in pixels)
        bbox_width: Optional width of the bounding box (in pixels)
        bbox_height: Optional height of the bounding box (in pixels)

        Note: All four bbox parameters must be provided to enable cropping.
              The bounding box is applied BEFORE resizing to 1 megapixel.

    Returns:
        The relative path to the screenshot file (e.g., "screenshots/screenshot_20250214_143025.png").
    """
    os_type = detect_os()

    # Define screenshots directory
    screenshots_dir = os.path.join(PROJECT_ROOT, "screenshots")

    try:
        # Determine output path
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            path = os.path.join(screenshots_dir, filename)
        else:
            # If custom path provided, ensure it's absolute
            if not os.path.isabs(path):
                path = os.path.abspath(path)

        # Validate path is within project root
        normalized_path = os.path.normpath(path)
        normalized_root = os.path.normpath(PROJECT_ROOT)
        if not normalized_path.startswith(normalized_root + os.sep):
            return f"Error: Path '{path}' is outside the project directory '{PROJECT_ROOT}'"

        # Ensure parent directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        # Check if all bbox parameters are provided
        use_bbox = all(v is not None for v in [bbox_x, bbox_y, bbox_width, bbox_height])

        # Take screenshot based on OS
        print(f"Detected OS: {os_type.upper()}")

        if os_type == "wsl":
            # Use PowerShell for WSL with DPI-aware capture
            take_screenshot_wsl(path)
        elif MSS_AVAILABLE:
            # Use mss for Windows, macOS, and Linux
            take_screenshot_mss(path)
        else:
            return f"Error: mss library not available for {os_type}. Install with: pip install mss"

        # Check if screenshot was created
        if not os.path.exists(path):
            return f"Error: Screenshot file not created at {path}"

        # Open and process the image
        with Image.open(path) as img:
            original_width, original_height = img.size
            print(f"Original image size: {original_width}x{original_height}")

            # Crop to bounding box if specified
            if use_bbox:
                bbox = {
                    'x': bbox_x,
                    'y': bbox_y,
                    'width': bbox_width,
                    'height': bbox_height
                }
                img = crop_to_bbox(img, bbox)
                print(f"Cropped to bbox: x={bbox_x}, y={bbox_y}, width={bbox_width}, height={bbox_height}")

            # Resize to 1 megapixel
            img = resize_to_1_megapixel(img)
            final_width, final_height = img.size
            print(f"Resized to 1 megapixel: {final_width}x{final_height} ({final_width * final_height} pixels)")

            # Save the processed image
            img.save(path, 'PNG')

        # Return relative path from project root
        relative_path = os.path.relpath(path, PROJECT_ROOT)

        bbox_info = f" (cropped to bbox: {bbox_x},{bbox_y} {bbox_width}x{bbox_height})" if use_bbox else ""

        return f"screenshots/{os.path.basename(path)}"

    except Exception as e:
        return f"Error taking screenshot on {os_type.upper()}: {str(e)}"


# Example usage and testing
if __name__ == "__main__":
    # Test basic screenshot
    result = screenshot()
    print(result)

    # Test with bounding box
    # result = screenshot(bbox_x=100, bbox_y=100, bbox_width=800, bbox_height=600)
    # print(result)
