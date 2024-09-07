# Option-K: AI-Powered Instant CLI

Option-K is an AI-powered CLI assistant that helps you generate and execute shell and git commands based on natural language queries.

## Features

- Generate shell and git commands from natural language queries
- Execute generated commands directly from the CLI
- Quick suggestion mode for instant command generation
- Supports both macOS and Linux environments
- Configurable AI backend (Google AI Studio or Vertex AI)

## Installation

### Using Homebrew (macOS)

You can install Option-K using Homebrew:

```bash
brew tap zerocorebeta/core
brew install optionk
```

This will install both the Option-K CLI `opk` and server `opk-server`application.
After installation follow the instructions on the screen to complete setup.

## Usage

1. Type your query in terminal followed by `Option+K` hotkey combo. (configurable via alias)

2. The AI will generate a command based on your query. You can then edit or execute the command.

3. For more options, use the CLI directly:
   ```
   opk "your query here"
   ```

## Configuration

1. Request a free Google AI Studio API key [here](https://ai.google.dev/gemini-api/docs/getting-started)

2. Edit the `~/.optionk/config.ini` file to configure the AI backend:

```ini
[optionk]
port = 8089

[vertexai]
enabled = false
project = my-project
location = asia-south1
model = gemini-1.5-flash-001

[google_ai_studio]
enabled = true
api_key = YOUR_API_KEY_HERE
model = gemini-1.5-flash
```

Note on Region Support:
- Vertex AI: Supports custom regions, allowing you to specify a location of your choice.
- Google AI Studio: Only supports the `us-central1` region. This cannot be changed.

When configuring your `config.ini`, keep in mind this difference in regional flexibility between the two services.


## Installation via Source

1. Clone the repository:
   ```
   git clone https://github.com/zerocorebeta/Option-K.git
   cd Option-K
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure the AI backend:
   - Create `~/.optionk/config.ini` file (create directory if it doesn't exist)
   - Edit the `~/.optionk/config.ini` file to set up your preferred AI service (Google AI Studio or Vertex AI)

4. Run the server:
   ```
   python server/opk-server.py
   ```

5. Test command completion using the client:
   ```
   python client/opk.py "your query here"
   ```

6. (Optional) Set up the server as a service:
   - For macOS:
     ```
     cp scripts/opk.plist ~/Library/LaunchAgents/com.example.optionk.plist
     launchctl load ~/Library/LaunchAgents/com.example.optionk.plist
     ```
   - For Linux:
     Set up a systemd service (instructions not provided)

7. Add the alias to your shell configuration:
   
   Edit `scripts/opk_alias.sh` and replace `{INSTALL_PATH}` with the path to your Option-K directory.

   ```
   echo "source /path/to/Option-K/scripts/opk_alias.sh" >> ~/.zshrc  # or ~/.bashrc
   source ~/.zshrc  # reload zshrc
   ```

## Files

- `client/opk.py`: Main CLI interface
- `server/opk-server.py`: Backend server handling AI requests
- `scripts/opk.plist`: macOS launch agent configuration
- `scripts/opk_alias.sh`: Shell alias for quick access
- `setup.py`: Python package setup file

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT License](LICENSE)