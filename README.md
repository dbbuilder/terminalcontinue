# Terminal Continue Monitor

A Python-based automation tool that monitors Windows terminal applications for periods of inactivity and automatically sends "continue" commands to maintain session activity.

## Overview

This application continuously monitors Command Prompt, PowerShell, and Windows Terminal instances, detecting when they become idle and automatically sending configurable keystrokes to maintain activity. This is particularly useful for long-running processes, remote sessions, or any scenario where you need to prevent terminal sessions from timing out.

## Features

- **Multi-Terminal Support**: Monitors Command Prompt, PowerShell, and Windows Terminal simultaneously
- **Intelligent Activity Detection**: Uses hash-based text comparison for efficient change detection
- **Configurable Thresholds**: Customizable inactivity periods and polling intervals
- **Robust Error Handling**: Gracefully handles window closures and system exceptions
- **Comprehensive Logging**: Detailed logging of all monitoring activities and actions
- **Low Resource Usage**: Efficient monitoring with minimal CPU and memory overhead
- **Dynamic Window Management**: Automatically detects new terminal windows and removes closed ones

## System Requirements

- **Operating System**: Windows 10 or Windows 11
- **Python**: Version 3.8 or higher
- **Architecture**: Compatible with both 32-bit and 64-bit systems

## Installation

### Prerequisites

Ensure you have Python 3.8+ installed on your system. You can download Python from the [official Python website](https://www.python.org/downloads/).

### Clone the Repository

```bash
git clone https://github.com/dbbuilder/terminalcontinue.git
cd terminalcontinue
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Alternative: Manual Dependency Installation

```bash
pip install pywinauto pypiwin32 pyyaml
```

## Configuration

The application uses a `config.yaml` file for configuration. Copy the example configuration and modify as needed:

```bash
copy config.example.yaml config.yaml
```

### Configuration Options

- **target_processes**: List of executable names to monitor (default: cmd.exe, powershell.exe, WindowsTerminal.exe)
- **inactivity_threshold_seconds**: Duration in seconds before considering a window idle (default: 30)
- **keys_to_send**: Keystroke sequence to send to idle windows (default: "continue{ENTER}")
- **polling_interval_seconds**: How often to check window states (default: 5)
- **log_level**: Logging verbosity level (default: INFO)

## Usage

### Basic Usage

Run the monitor with default settings:

```bash
python src/terminal_monitor.py
```

### Advanced Usage

Run with custom configuration file:

```bash
python src/terminal_monitor.py --config custom_config.yaml
```

Run with verbose logging:

```bash
python src/terminal_monitor.py --log-level DEBUG
```

### Command Line Options

- `--config PATH`: Specify custom configuration file path
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `--help`: Display help information

## How It Works

1. **Window Detection**: The application scans all visible top-level windows to identify terminal instances
2. **Text Extraction**: For each terminal window, it extracts the visible text content
3. **Change Detection**: It calculates a hash of the text content and compares it with the previous state
4. **Inactivity Tracking**: Windows with unchanged text content are tracked for inactivity duration
5. **Automated Response**: When the inactivity threshold is exceeded, configured keystrokes are sent
6. **State Management**: The application maintains state for all monitored windows and handles closures gracefully

## Logging

The application provides comprehensive logging including:

- Window detection and closure events
- Inactivity threshold breaches
- Keystroke transmission events
- Error conditions and recovery attempts
- Configuration loading and validation

Logs are written to both console output and log files in the `logs/` directory.

## Troubleshooting

### Common Issues

**Permission Errors**: Ensure the application has sufficient permissions for UI automation. Running as administrator may be required in some environments.

**Window Detection Issues**: Some terminal applications may require specific configuration adjustments for proper text extraction.

**High CPU Usage**: Consider increasing the polling interval if CPU usage is a concern.

### Debug Mode

Enable debug logging for detailed operational information:

```bash
python src/terminal_monitor.py --log-level DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/dbbuilder/terminalcontinue) and create an issue or discussion.

## Acknowledgments

- Built using the pywinauto library for Windows UI automation
- Utilizes pywin32 for Windows API access
- Inspired by the need for maintaining long-running terminal sessions