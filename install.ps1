# Terminal Continue Monitor - PowerShell Installation Script
# 
# This script automates the installation and setup process for the
# Terminal Continue Monitor application.

param(
    [switch]$SkipVenv,
    [switch]$DevMode,
    [switch]$Help
)

function Show-Help {
    Write-Host @"
Terminal Continue Monitor Installation Script

USAGE:
    .\install.ps1 [OPTIONS]

OPTIONS:
    -SkipVenv       Skip virtual environment creation
    -DevMode        Install development dependencies
    -Help           Show this help message

DESCRIPTION:
    This script will:
    1. Verify Python installation
    2. Create a virtual environment (unless -SkipVenv)
    3. Install required dependencies
    4. Copy configuration template
    5. Set up the application for use

REQUIREMENTS:
    - Windows 10/11
    - Python 3.8 or higher
    - Administrator privileges (recommended)

EXAMPLES:
    .\install.ps1                    # Standard installation
    .\install.ps1 -DevMode           # Install with development tools
    .\install.ps1 -SkipVenv          # Install globally (not recommended)
"@
}

function Test-Administrator {
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [System.Security.Principal.WindowsPrincipal]($currentUser)
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-Header {
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host "Terminal Continue Monitor v1.0.0" -ForegroundColor White
    Write-Host "Automated Terminal Session Activity Monitor" -ForegroundColor Gray
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-PythonInstallation {
    Write-Host "Checking Python installation..." -ForegroundColor Yellow
    
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python not found in PATH"
        }
        
        # Parse version
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            
            if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
                throw "Python version $pythonVersion is too old. Requires Python 3.8 or higher."
            }
            
            Write-Host "✓ Found $pythonVersion" -ForegroundColor Green
            return $true
        } else {
            throw "Could not parse Python version: $pythonVersion"
        }
    }
    catch {
        Write-Host "✗ $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Python 3.8 or higher from https://www.python.org/" -ForegroundColor Yellow
        Write-Host "Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
        return $false
    }
}

function New-VirtualEnvironment {
    if ($SkipVenv) {
        Write-Host "Skipping virtual environment creation (global installation)" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "Setting up virtual environment..." -ForegroundColor Yellow
    
    if (Test-Path "venv") {
        Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
        return $true
    }
    
    try {
        python -m venv venv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment"
        }
        
        Write-Host "✓ Virtual environment created successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Install-Dependencies {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    
    # Activate virtual environment if it exists
    if (-not $SkipVenv -and (Test-Path "venv\Scripts\Activate.ps1")) {
        Write-Host "Activating virtual environment..." -ForegroundColor Gray
        & .\venv\Scripts\Activate.ps1
    }
    
    try {
        # Install main dependencies
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install main dependencies"
        }
        
        # Install development dependencies if requested
        if ($DevMode) {
            Write-Host "Installing development dependencies..." -ForegroundColor Yellow
            pip install pytest pytest-cov black flake8 mypy
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Warning: Some development dependencies failed to install" -ForegroundColor Yellow
            } else {
                Write-Host "✓ Development dependencies installed" -ForegroundColor Green
            }
        }
        
        Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Initialize-Configuration {
    Write-Host "Setting up configuration..." -ForegroundColor Yellow
    
    if (-not (Test-Path "config.yaml")) {
        if (Test-Path "config.example.yaml") {
            Copy-Item "config.example.yaml" "config.yaml"
            Write-Host "✓ Configuration file created from template" -ForegroundColor Green
            Write-Host "  You can modify config.yaml to customize settings" -ForegroundColor Gray
        } else {
            Write-Host "Warning: No configuration template found" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✓ Configuration file already exists" -ForegroundColor Green
    }
    
    # Ensure logs directory exists
    if (-not (Test-Path "logs")) {
        New-Item -Type Directory -Path "logs" | Out-Null
        Write-Host "✓ Logs directory created" -ForegroundColor Green
    }
    
    return $true
}

function Test-Installation {
    Write-Host "Testing installation..." -ForegroundColor Yellow
    
    try {
        # Test import of main modules
        if (-not $SkipVenv -and (Test-Path "venv\Scripts\Activate.ps1")) {
            & .\venv\Scripts\Activate.ps1
        }
        
        $testResult = python -c "import sys; sys.path.insert(0, 'src'); from terminal_monitor import TerminalMonitor; print('Import successful')" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Installation test passed" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ Installation test failed: $testResult" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "✗ Installation test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Show-CompletionMessage {
    Write-Host ""
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host "Installation completed successfully!" -ForegroundColor Green
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "1. Review and modify config.yaml as needed" -ForegroundColor Gray
    Write-Host "2. Run the application using one of these methods:" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   Method 1 (Recommended): Use the batch file" -ForegroundColor Yellow
    Write-Host "   .\start_monitor.bat" -ForegroundColor White
    Write-Host ""
    Write-Host "   Method 2: Direct Python execution" -ForegroundColor Yellow
    if (-not $SkipVenv) {
        Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor White
    }
    Write-Host "   python src\terminal_monitor.py" -ForegroundColor White
    Write-Host ""
    Write-Host "For help and documentation, see:" -ForegroundColor Gray
    Write-Host "- README.md (usage instructions)" -ForegroundColor White
    Write-Host "- config.example.yaml (configuration options)" -ForegroundColor White
    Write-Host "- https://github.com/dbbuilder/terminalcontinue" -ForegroundColor White
    Write-Host ""
}

# Main installation process
function Main {
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Header
    
    # Check if running as administrator
    if (-not (Test-Administrator)) {
        Write-Host "Warning: Not running as administrator. Some features may not work properly." -ForegroundColor Yellow
        Write-Host ""
    }
    
    # Step 1: Verify Python installation
    if (-not (Test-PythonInstallation)) {
        exit 1
    }
    
    # Step 2: Create virtual environment
    if (-not (New-VirtualEnvironment)) {
        exit 1
    }
    
    # Step 3: Install dependencies
    if (-not (Install-Dependencies)) {
        exit 1
    }
    
    # Step 4: Set up configuration
    if (-not (Initialize-Configuration)) {
        exit 1
    }
    
    # Step 5: Test installation
    if (-not (Test-Installation)) {
        Write-Host ""
        Write-Host "Installation completed with warnings. The application may still work." -ForegroundColor Yellow
    }
    
    # Show completion message
    Show-CompletionMessage
}

# Execute main function
Main
