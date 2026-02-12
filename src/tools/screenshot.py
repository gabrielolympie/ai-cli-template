from mirascope import llm
import os
import tempfile
import subprocess
import uuid

PROJECT_ROOT = os.getcwd()


def linux_to_windows_path(linux_path):
    """Convert a Linux path from /mnt/c/... to Windows C:\\... format"""
    if linux_path.startswith('/mnt/'):
        parts = linux_path.split('/')
        if len(parts) >= 3:
            drive = parts[2].upper() + ':'
            rel_path = '/'.join(parts[3:])
            return drive + '\\' + rel_path.replace('/', '\\')
    return linux_path


@llm.tool
def screenshot(path: str = None):
    """Take a screenshot of the primary monitor and save it to a file.
    
    This tool uses PowerShell to capture the screen and save it as PNG.
    In WSL, it captures the full Windows desktop (including XWayland windows).
    Uses physical pixel resolution detection for accurate capturing.
    
    Args:
        path: Optional path where to save the screenshot. 
              If not provided, saves to current working directory with timestamped filename.
              Should have .png extension.
    
    Returns:
        Message confirming the screenshot was taken and saved, or error message.
    """
    try:
        # Determine output path
        if path is None:
            timestamp = uuid.uuid4().hex[:8]
            path = os.path.join(PROJECT_ROOT, f"screenshot_{timestamp}.png")
        
        # Ensure we have an absolute path
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
        
        # Convert paths to Windows format for PowerShell
        windows_output_path = linux_to_windows_path(path)
        windows_output_escaped = windows_output_path.replace('\\', '\\\\')
        windows_path_escaped = windows_output_escaped
        
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
        
        # Save PowerShell script
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
            
            # Clean up temp script
            if os.path.exists(ps_script_path):
                os.unlink(ps_script_path)
            
            if result.returncode == 0:
                stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
                return f"Screenshot taken successfully and saved to: {path}\n{stdout_text.strip()}"
            else:
                stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
                return f"Error taking screenshot: {stderr_text}"
                
        except subprocess.TimeoutExpired:
            if os.path.exists(ps_script_path):
                os.unlink(ps_script_path)
            return "Error: Screenshot timed out after 30 seconds"
        except Exception as e:
            if os.path.exists(ps_script_path):
                os.unlink(ps_script_path)
            return f"Error executing PowerShell: {str(e)}"
    
    except Exception as e:
        return f"Error setting up screenshot: {str(e)}"
