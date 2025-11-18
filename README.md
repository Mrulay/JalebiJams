# JalebiJams 🎵

A Discord music bot that plays YouTube music in voice channels using Python.

## Features

- 🎵 Play music from YouTube (URLs or search queries)
- ⏯️ Control playback (play, pause, resume, stop, skip)
- 📝 Queue system for multiple songs
- 🔊 Volume control
- 🎯 Simple and intuitive commands

## Prerequisites

Before running the bot, you need:

1. **Python 3.8 or higher**
2. **FFmpeg** - Required for audio processing
3. **Discord Bot Token** - From Discord Developer Portal

### Installing FFmpeg

#### Windows
Download from [FFmpeg official website](https://ffmpeg.org/download.html) and add to PATH, or use:
```bash
# Using Chocolatey
choco install ffmpeg

# Using Scoop
scoop install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Mrulay/JalebiJams.git
   cd JalebiJams
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a Discord Bot**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to the "Bot" section and click "Add Bot"
   - Under "Privileged Gateway Intents", enable:
     - Message Content Intent
     - Server Members Intent (optional)
   - Copy the bot token

4. **Configure the bot**
   - Copy `.env.example` to `.env`
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your Discord bot token:
     ```
     DISCORD_TOKEN=your_bot_token_here
     COMMAND_PREFIX=!
     ```

5. **Invite the bot to your server**
   - In Discord Developer Portal, go to "OAuth2" → "URL Generator"
   - Select scopes: `bot`
   - Select bot permissions:
     - Send Messages
     - Connect
     - Speak
     - Use Voice Activity
   - Copy the generated URL and open it in your browser
   - Select your server and authorize

## Usage

### Running the bot

```bash
python bot.py
```

### Commands

All commands use the prefix `!` (configurable in `.env`)

| Command | Description | Example |
|---------|-------------|---------|
| `!join` | Bot joins your voice channel | `!join` |
| `!leave` | Bot leaves the voice channel | `!leave` |
| `!play <url/query>` | Play music from YouTube | `!play https://www.youtube.com/watch?v=...` or `!play never gonna give you up` |
| `!pause` | Pause the current song | `!pause` |
| `!resume` | Resume the paused song | `!resume` |
| `!stop` | Stop playing and clear queue | `!stop` |
| `!skip` | Skip the current song | `!skip` |
| `!queue` | Show the current queue | `!queue` |
| `!volume <0-100>` | Set the volume | `!volume 50` |
| `!help` | Show all available commands | `!help` |

### Example Usage

1. Join a voice channel in your Discord server
2. Type `!join` to make the bot join your channel
3. Type `!play never gonna give you up` to play a song
4. Use `!pause`, `!resume`, `!skip` to control playback
5. Type `!leave` when you're done

## Project Structure

```
JalebiJams/
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── .env               # Your configuration (create this)
├── .gitignore         # Git ignore file
├── LICENSE            # License file
└── README.md          # This file
```

## Troubleshooting

### Bot doesn't respond to commands
- Make sure Message Content Intent is enabled in Discord Developer Portal
- Check that the bot has permission to read messages in the channel
- Verify the command prefix in your `.env` file

### Audio doesn't play
- Ensure FFmpeg is installed and in your system PATH
- Check that the bot has "Connect" and "Speak" permissions
- Verify you're in a voice channel when using play commands

### "Not connected to voice channel" error
- Make sure you're in a voice channel before using `!play`
- Try using `!join` first to connect the bot

## Dependencies

- `discord.py[voice]` - Discord API wrapper with voice support
- `yt-dlp` - YouTube video/audio downloader
- `PyNaCl` - Voice support library
- `python-dotenv` - Environment variable management
- `FFmpeg` - Audio processing (system dependency)

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube support

## Disclaimer

This bot is for educational purposes. Please respect YouTube's Terms of Service and copyright laws when using this bot. 
