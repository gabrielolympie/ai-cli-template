# Only load WinForms, not System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# Check what's loaded
Write-Host "Loaded assemblies containing 'Drawing':"
[System.AppDomain]::CurrentDomain.GetAssemblies() | Where-Object { $_.FullName -like "*Drawing*" } | ForEach-Object { Write-Host "  $($_.FullName)" }

# Try to use System.Drawing types
try {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $tempBitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    Write-Host "System.Drawing Bitmap created successfully!"
} catch {
    Write-Host "Error creating Bitmap: $($_.Exception.Message)"
}

try {
    $graphics = [System.Drawing.Graphics]::FromImage($tempBitmap)
    Write-Host "System.Drawing Graphics created successfully!"
} catch {
    Write-Host "Error creating Graphics: $($_.Exception.Message)"
}
