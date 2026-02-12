# Test virtual screen capture
Add-Type -AssemblyName System.Windows.Forms

# Get primary screen (current method)
$primary = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
Write-Host "Primary screen: $($primary.Width)x$($primary.Height)"

# Get virtual screen (all monitors combined) via GetSystemMetrics
$csharp = @'
using System;
using System.Runtime.InteropServices;

public class ScreenMetrics
{
    [DllImport("user32.dll")]
    public static extern int GetSystemMetrics(int nIndex);
    
    public const int SM_CXVIRTUALSCREEN = 78;
    public const int SM_CYVIRTUALSCREEN = 79;
}
'@

Add-Type -TypeDefinition $csharp

$virtWidth = [ScreenMetrics]::GetSystemMetrics([ScreenMetrics]::SM_CXVIRTUALSCREEN)
$virtHeight = [ScreenMetrics]::GetSystemMetrics([ScreenMetrics]::SM_CYVIRTUALSCREEN)
Write-Host "Virtual screen: $virtWidth x $virtHeight"

# Calculate target dimensions with 150% scaling
$physWidth = [int]($virtWidth * 1.5)
$physHeight = [int]($virtHeight * 1.5)
Write-Host "Physical target: $physWidth x $physHeight"

# Capture virtual screen
$virtualBounds = New-Object System.Drawing.Rectangle 0, 0, $virtWidth, $virtHeight

# Create temporary bitmap
$tempBitmap = New-Object System.Drawing.Bitmap $virtWidth, $virtHeight
$tempGraphics = [System.Drawing.Graphics]::FromImage($tempBitmap)
$tempGraphics.CopyFromScreen(0, 0, 0, 0, $virtWidth, $virtHeight, [System.Drawing.CopyPixelOperation]::Scroll)
#$tempGraphics.CopyFromScreen($virtualBounds.Location, [System.Drawing.Point]::Empty, $virtualBounds.Size)
$tempGraphics.Dispose()

# Create final scaled bitmap
$bitmap = New-Object System.Drawing.Bitmap $physWidth, $physHeight
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.DrawImage($tempBitmap, 0, 0, $physWidth, $physHeight)
$graphics.Dispose()

# Save
$bitmap.Save('C:\Users\gabol\Desktop\VibeCoding\base-cli\test_virtual.png', [System.Drawing.Imaging.ImageFormat]::Png)
Write-Host "Saved!"
$tempBitmap.Dispose()
$bitmap.Dispose()
