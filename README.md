# Grasshopper MCP workflow

Grasshopper MCP workflow is a bridging server that connects Grasshopper and Cursor using the Model Context Protocol (MCP) standard.

**Language Selection / 語言選擇**: [English](README.md) | [繁體中文](README.zh-TW.md)

## Features

- **MCP Protocol Integration**: Connects Grasshopper and Cursor through the Model Context Protocol (MCP) standard
- **Component Management**: Intuitive tool functions for creating, managing, and connecting Grasshopper components
- **Intent Recognition**: Supports high-level intent recognition, automatically creating complex component patterns from simple descriptions
- **Component Knowledge Base**: Includes a comprehensive knowledge base that understands parameters and connection rules for common components
- **Workflow Automation**: Provides tools for executing complex Grasshopper workflows from JSON and MMD files
- **CLI Tools**: Command-line interface for batch operations and automation
- **Parameter Management**: Advanced parameter setting and management capabilities
- **Group Management**: Organize components into groups with custom colors and names

## System Architecture

The system consists of the following parts:

1. **Grasshopper MCP Component (GH_MCP.gha)**: A C# plugin installed in Grasshopper that provides a TCP server to receive commands
2. **Python MCP Bridge Server** (`grasshopper_mcp`): A bridge server that connects Cursor and the Grasshopper MCP component
3. **Grasshopper Tools** (`grasshopper_tools`): A comprehensive Python library for managing Grasshopper components, connections, parameters, and workflows
4. **Component Knowledge Base**: JSON files containing component information, patterns, and intents
5. **Workflow Skill** (`grasshopper-workflow`): A specialized skill for Cursor that provides advanced workflow automation capabilities

## Installation Instructions

### Prerequisites

- Rhino 7 or higher
- Grasshopper
- Python 3.8 or higher
- Cursor

### Installation Steps

1. **Install the Grasshopper MCP Component**

   **Method 1: Download the pre-compiled GH_MCP.gha file (Recommended)**
   
   Download the [GH_MCP.gha](https://github.com/alfredatnycu/grasshopper-mcp/raw/master/releases/GH_MCP.gha) file directly from the GitHub repository and copy it to the Grasshopper components folder:
   ```
   %APPDATA%\Grasshopper\Libraries\
   ```

   **Method 2: Build from source**
   
   If you prefer to build from source, clone the repository and build the C# project using Visual Studio.

2. **Install the Python MCP Bridge Server**

   **Method 1: Install from PyPI (Recommended)**
   
   The simplest method is to install directly from PyPI using pip:
   ```
   pip install grasshopper-mcp
   ```
   
   **Method 2: Install from GitHub**
   
   You can also install the latest version from GitHub:
   ```
   pip install git+https://github.com/alfredatnycu/grasshopper-mcp.git
   ```
   
   **Method 3: Install from Source Code**
   
   If you need to modify the code or develop new features, you can clone the repository and install:
   ```
   git clone https://github.com/alfredatnycu/grasshopper-mcp.git
   cd grasshopper-mcp
   pip install -e .
   ```

## Usage

1. **Start Rhino and Grasshopper**

   Launch Rhino and open Grasshopper.

2. **Add the GH_MCP Component to Your Canvas**

   Find the GH_MCP component in the Grasshopper component panel and add it to your canvas.

3. **Start the Python MCP Bridge Server**

   Open a terminal and run:
   ```
   python -m grasshopper_mcp.bridge
   ```
   
   > **Note**: The command `grasshopper-mcp` might not work directly due to Python script path issues. Using `python -m grasshopper_mcp.bridge` is the recommended and more reliable method.

4. **Configure Cursor MCP Connection**

   Configure the MCP server connection in Cursor to enable communication between Cursor and the Grasshopper MCP bridge server.
   
   **Configuration Steps:**
   
   1. Locate Cursor's MCP configuration file `mcp.json`, typically located at:
      - Windows: `%APPDATA%\Cursor\User\mcp.json` or `~\.cursor\mcp.json`
      - macOS: `~/Library/Application Support/Cursor/User/mcp.json` or `~/.cursor/mcp.json`
   
   2. Add the following configuration to the `mcp.json` file:
   
      ```json
      {
        "mcpServers": {
          "grasshopper": {
            "command": "python",
            "args": ["-m", "grasshopper_mcp.bridge"]
          }
        }
      }
      ```
   
   3. **Using Virtual Environment or Specific Python Path**:
      
      If you're using a virtual environment or conda environment, specify the full path to the Python executable:
      
      ```json
      {
        "mcpServers": {
          "grasshopper": {
            "command": "C:\\Users\\YourUsername\\.conda\\envs\\grasshopper-mcp\\python.exe",
            "args": ["-m", "grasshopper_mcp.bridge"]
          }
        }
      }
      ```
      
      > **Tip**: On Windows, backslashes in paths need to be escaped with double backslashes `\\` or use forward slashes `/`.
   
   4. **Verify Python Path**:
      
      You can find the full path to your Python executable using:
      - Windows: `where python` or `where python3`
      - macOS/Linux: `which python` or `which python3`
      
      If using a conda environment, you can run:
      ```
      conda activate grasshopper-mcp
      where python  # Windows
      which python  # macOS/Linux
      ```
   
   5. After saving the configuration file, restart Cursor for the changes to take effect.
   
   > **Note**: Make sure you have completed steps 2 (adding the GH_MCP component to the Grasshopper canvas) and step 3 (starting the Python MCP bridge server) before configuring MCP. The MCP bridge server needs to be running before Cursor can connect.

5. **Start Using Grasshopper with Cursor**

   You can now use Cursor to control Grasshopper through natural language commands.

## Example Commands

Here are some example commands you can use with Cursor:

- "Create a circle with radius 5 at point (0,0,0)"
- "Connect the circle to an extrude component with a height of 10"
- "Create a grid of points with 5 rows and 5 columns"
- "Apply a random rotation to all selected objects"
- "Create a rectangle component and set its width to 10"
- "Group all selected components and name them 'Geometry Group'"

## Using Grasshopper Tools

The project includes a comprehensive `grasshopper_tools` library for programmatic control of Grasshopper:

### Python API Usage

```python
from grasshopper_tools import (
    GrasshopperClient,
    ComponentManager,
    ConnectionManager,
    ParameterSetter,
    GroupManager
)

# Create client connection
client = GrasshopperClient(host="localhost", port=8080)

# Create component manager
comp_mgr = ComponentManager(client)

# Add a component
component_id = comp_mgr.add_component(
    guid="e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da",  # Number Slider GUID
    x=100,
    y=200,
    component_id="SLIDER_WIDTH"
)

# Set component parameters
param_setter = ParameterSetter(client)
param_setter.set_slider_properties(
    component_id=component_id,
    value="10",
    min_value=0,
    max_value=100
)
```

### CLI Usage

```bash
# Execute a placement workflow from JSON
python -m grasshopper_tools.cli execute-placement GH_WIP/placement_info.json

# Parse MMD files
python -m grasshopper_tools.cli parse-mmd GH_WIP/component_info.mmd --action sliders

# View help
python -m grasshopper_tools.cli --help
```

For more detailed documentation, see the [grasshopper_tools documentation](grasshopper_tools/docs/).

## Troubleshooting

If you encounter issues, check the following:

1. **GH_MCP Component Not Loading**
   - Ensure the .gha file is in the correct location: `%APPDATA%\Grasshopper\Libraries\`
   - In Grasshopper, go to File > Preferences > Libraries and click "Unblock" to unblock new components
   - Restart Rhino and Grasshopper
   - Check that you have the correct .NET runtime installed (net48 or net7.0)

2. **Bridge Server Won't Start**
   - If `grasshopper-mcp` command doesn't work, use `python -m grasshopper_mcp.bridge` instead
   - Ensure all required Python dependencies are installed: `pip install -r requirements.txt`
   - Check if port 8080 is already in use by another application
   - Verify Python version is 3.8 or higher: `python --version`

3. **Cursor Can't Connect**
   - Ensure the bridge server is running
   - Verify you're using the correct connection settings (localhost:8080)
   - Check the console output of the bridge server for any error messages
   - Ensure the GH_MCP component is added to your Grasshopper canvas
   - Check that Cursor's MCP configuration is correct

4. **Commands Not Executing**
   - Verify the GH_MCP component is on your Grasshopper canvas
   - Check the bridge server console for error messages
   - Ensure Cursor is properly connected to the bridge server
   - Verify the component GUIDs are correct when using `grasshopper_tools`

5. **Grasshopper Tools Issues**
   - Ensure you're using the correct host and port (default: localhost:8080)
   - Check that the MCP bridge server is running before using the tools
   - Verify file paths when using CLI commands
   - See [grasshopper_tools documentation](grasshopper_tools/docs/) for detailed troubleshooting

## Development

### Project Structure

```
grasshopper-mcp/
├── grasshopper_mcp/           # Python MCP bridge server
│   ├── __init__.py
│   └── bridge.py              # Main bridge server implementation
├── grasshopper_tools/          # Python tools library
│   ├── client.py              # MCP client implementation
│   ├── component_manager.py  # Component management
│   ├── connection_manager.py  # Connection management
│   ├── parameter_setter.py    # Parameter setting utilities
│   ├── group_manager.py       # Group management
│   ├── placement_executor.py  # Workflow execution
│   ├── parser_utils.py        # MMD/JSON parsing
│   ├── cli.py                 # Command-line interface
│   └── docs/                  # Documentation
├── GH_MCP/                    # Grasshopper component (C#)
│   └── GH_MCP/
│       ├── Commands/          # Command handlers
│       ├── Models/            # Data models
│       ├── Utils/             # Utilities
│       └── Resources/         # Component knowledge base
├── grasshopper-workflow/      # Workflow skill for Cursor
│   ├── references/           # API references
│   ├── scripts/              # Workflow scripts
│   └── SKILL.md              # Skill documentation
├── GH_WIP/                    # Work in progress files
│   ├── component_info.mmd    # Component information
│   ├── part_info.mmd         # Part information
│   └── placement_info.json   # Placement workflow
├── scripts/                   # Utility scripts
├── prompt/                    # Prompt templates
├── docs/                      # Project documentation
├── releases/                  # Pre-compiled binaries
│   └── GH_MCP.gha            # Compiled Grasshopper component
├── setup.py                   # Python package setup
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

### Additional Resources

- **Grasshopper Tools Documentation**: See [grasshopper_tools/docs/](grasshopper_tools/docs/) for detailed API documentation and usage guides
- **Workflow Skill**: The `grasshopper-workflow` skill provides advanced workflow automation capabilities for Cursor
- **Example Scripts**: Check the `scripts/` directory for example usage scripts
- **Prompt Templates**: The `prompt/` directory contains prompt templates for various workflow steps

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

When contributing:
- Follow the existing code style and structure
- Add documentation for new features
- Include tests when possible
- Update this README if adding new features or changing installation steps

## Changelog

### Version 0.1.0

**Release Date**: 2024-12-19

- Initial release of Grasshopper MCP Bridge
- Support for MCP protocol integration with Cursor
- Component management and connection tools
- Intent recognition for automatic component pattern creation
- Comprehensive component knowledge base
- Workflow automation from JSON and MMD files
- CLI tools for batch operations
- Parameter and group management capabilities

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to the Rhino and Grasshopper community for their excellent tools
- Thanks to Cursor and the MCP protocol support

## Contact

For questions or support, please open an issue on the GitHub repository.
