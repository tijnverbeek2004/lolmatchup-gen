# AI-Powered LoL Matchup Dominator

A command-line tool that provides a complete, AI-generated game plan for countering any League of Legends champion. It uses Selenium to scrape live, up-to-date matchup data and feeds it to Google's Gemini API for expert analysis.

  <!-- You should replace this with a real screenshot of your app running! -->

## Features

- **Live Data:** Scrapes [League of Graphs](https://www.leagueofgraphs.com) in real-time to find the statistically best counter-pick.
- **Full Build Paths:** Retrieves the counter's entire item build, including core, boots, and situational options.
- **AI-Powered Strategy:** Feeds the live data to the Gemini 1.5 Flash model to generate a comprehensive strategy, including rune recommendations, build explanations, and pro tips.
- **Robust & Resilient:** Gracefully handles scraper failures by falling back to the AI's general knowledge, ensuring you always get a useful response.
- **Fast & Efficient:** Uses a headless browser with image-loading disabled for maximum speed.

## How It Works

1.  **Input:** You provide your role and the enemy champion.
2.  **Scrape Counter:** The script uses Selenium to navigate to League of Graphs, handle cookie banners, and find the champion with the highest win rate against your opponent.
3.  **Scrape Build:** It then navigates to the specific matchup page for that counter and scrapes their most common Core Build, Boots, and Final Item Options.
4.  **Consult AI:** This live data is packaged and sent to the Google Gemini API with a specialized prompt.
5.  **Generate Output:** The AI returns a detailed, formatted game plan which is printed directly to your console.

## Setup & Installation

### 1. Prerequisites
- Python 3.8 or newer.
- Git.

### 2. Clone the Repository
Open your terminal and clone this repository:
```bash
git clone https://github.com/tijnverbeek2004/lolmatchup-gen.git
cd lolmatchup-gen
```

### 3. Install Dependencies
Install all the required Python packages using the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### 4. Set Up Your API Key
This tool requires a Google AI (Gemini) API key.

- **Get a key:** You can get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

- **Set the key:** The most secure way is to set it as an environment variable.
    - **Windows:** `setx GOOGLE_API_KEY "YOUR_API_KEY"` (in Command Prompt, then restart the terminal)
    - **macOS/Linux:** `export GOOGLE_API_KEY="YOUR_API_KEY"` (add this to your `.bashrc` or `.zshrc` file for it to be permanent)

If you don't set the environment variable, the script will prompt you to enter the key every time you run it.

## Usage

Simply run the script from your terminal:

```bash
python lolmatchup.py
```

The script will then ask for your role and the enemy champion.

#### Example:
```
--- Welcome to the AI-Powered LoL Matchup Dominator ---
Enter your role (e.g., top, jungle, mid, adc, support): jungle
Enter your enemy in 'jungle': viego
```
... and the magic happens.

## Disclaimer

This tool is for informational and entertainment purposes only. It scrapes data from a third-party website (League of Graphs) and uses an AI model for analysis. All data belongs to their respective owners. Don't blame me if you still lose lane.
