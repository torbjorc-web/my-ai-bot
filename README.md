# My AI Bot

This project is an AI bot designed to interact with users and provide responses based on predefined prompts and configurations. The bot is built using Python and follows a modular structure for easy maintenance and scalability.

## Project Structure

```
my-ai-bot
├── src
│   ├── bot.py               # Main logic for the AI bot
│   ├── main.py              # Entry point for the application
│   ├── config
│   │   └── settings.py      # Configuration settings for the bot
│   ├── prompts
│   │   └── system_prompt.txt # System prompt for guiding bot responses
│   └── types
│       └── __init__.py      # Custom data types or interfaces
├── tests
│   └── test_bot.py          # Unit tests for the bot's functionality
├── requirements.txt          # List of dependencies
├── .env.example              # Example environment variables
└── README.md                 # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone https://github.com/torbjorc-web/my-ai-bot.git
   cd my-ai-bot
   ```

2. **Create a virtual environment (optional but recommended):**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Copy the `.env.example` file to `.env` and fill in the required values.

## Usage

To run the bot, execute the following command:

```
python src/main.py
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.