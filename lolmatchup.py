import os
import sys
import time
import requests

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Button, Static, Markdown
from textual.containers import Container, ScrollableContainer
from textual.screen import Screen
from textual.worker import Worker, WorkerState

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# ---------- SCRAPER (unchanged functional version) ----------

class ScrapedCounter:
    def __init__(self, name: str, win_rate: str):
        self.name = name
        self.win_rate = win_rate

    def __str__(self):
        return f"{self.name} ({self.win_rate})"


def handle_overlays(driver, wait):
    try:
        overlay_locator = (By.XPATH,
                           "//button[contains(., 'Accept') or contains(., 'Continue') or contains(., 'Agree') or contains(., 'Accepteren')]")
        overlay_wait = WebDriverWait(driver, 3)
        overlay_button = overlay_wait.until(EC.element_to_be_clickable(overlay_locator))
        driver.execute_script("arguments[0].click();", overlay_button)
        wait.until(EC.invisibility_of_element_located(overlay_locator))
    except TimeoutException:
        pass


def scrape_top_counters(role, enemy_champion) -> list[ScrapedCounter] | None:
    print(f"SCRAPER: Starting analysis for {enemy_champion}/{role}")
    champion_formatted = enemy_champion.strip().replace(" ", "").replace("'", "").lower()
    role_map = {
        "JUNGLE": "JUNGLE", "JGL": "JUNGLE", "ADC": "ADC", "BOTTOM": "ADC",
        "TOP": "TOP", "MID": "MIDDLE", "MIDDLE": "MIDDLE", "SUPPORT": "SUPPORT", "SUP": "SUPPORT"
    }
    role_formatted = role_map.get(role.upper(), "all")
    print(f"Formatted: {champion_formatted}/{role_formatted}")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("prefs", {"profile.default_content_settings.images": 2})
    driver = None

    try:
        print("Initializing Chrome driver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 15)

        counters_url = f"https://www.leagueofgraphs.com/champions/counters/{champion_formatted}/{role_formatted}"
        print(f"Navigating to: {counters_url}")
        driver.get(counters_url)
        handle_overlays(driver, wait)

        table_rows_xpath = "//h3[contains(text(), 'loses lane against')]/following-sibling::table/tbody/tr"
        print("Waiting for table...")
        wait.until(EC.visibility_of_element_located((By.XPATH, table_rows_xpath)))
        print("Table found!")

        time.sleep(2)
        counter_data = []

        for i in range(2, 5):
            try:
                row_xpath = f"({table_rows_xpath})[{i}]"
                counter_name_element = driver.find_element(By.XPATH, f"{row_xpath}//span[@class='name']")
                counter_name = counter_name_element.get_attribute('textContent').strip()
                winrate_element = driver.find_element(By.XPATH, f"{row_xpath}//div[@class='progressBarTxt']")
                winrate_raw = winrate_element.get_attribute('textContent').strip()

                try:
                    winrate_val = float(winrate_raw.replace('%', ''))
                    win_rate = f"{winrate_val:.1f}%"
                except (ValueError, TypeError):
                    win_rate = winrate_raw

                print(f"Found counter #{i - 1}: {counter_name} - {win_rate}")
                counter_data.append(ScrapedCounter(counter_name, win_rate))
            except Exception as e:
                print(f"Error getting counter #{i - 1}: {e}")
                break

        if not counter_data:
            raise Exception("No counter data found.")

        print(f"Successfully scraped {len(counter_data)} counters")
        return counter_data

    except Exception as e:
        print(f"SCRAPER ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            print("Closing driver...")
            driver.quit()


# ---------- TEXTUAL UI (modern visual update) ----------

class MatchupScreen(Screen):
    BINDINGS = [("q", "quit", "Quit App")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Footer()

        with Container(id="main_container"):
            with Container(id="input_area"):
                yield Static("🔮 Input Parameters", id="input_header")
                yield Input(placeholder="Role (mid, top, jungle, adc, support)", id="role_input")
                yield Input(placeholder="Enemy Champion", id="champion_input")
                yield Button("→ Analyze Matchup", variant="primary", id="analyze_button")

            with ScrollableContainer(id="output_scroll"):
                yield Static("⚔ Analysis Results", id="oracle_header")
                yield Markdown(
                    "Enter a **role** and **champion** above to retrieve counter data.\n\nPress the button to begin analysis.",
                    id="analysis_output"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "analyze_button":
            role = self.query_one("#role_input", Input).value.strip()
            champion = self.query_one("#champion_input", Input).value.strip()
            output_widget = self.query_one("#analysis_output", Markdown)

            if not role or not champion:
                output_widget.update("⚠ **Error:** Please enter both a role and a champion.")
                return

            self.query_one("#analyze_button", Button).disabled = True
            output_widget.update(
                f"⏳ **Analyzing** `{champion}` in `{role}` role...\n\nFetching live data from League of Graphs..."
            )
            self._current_champion = champion
            self.run_worker(lambda: scrape_top_counters(role, champion), thread=True, exclusive=True)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        output_widget = self.query_one("#analysis_output", Markdown)
        if event.state == WorkerState.SUCCESS:
            self.query_one("#analyze_button", Button).disabled = False
            results = event.worker.result
            if results is None:
                output_widget.update(
                    f"❌ **Analysis Failed**\n\nCould not retrieve data for `{self._current_champion}`."
                )
                return

            markdown_output = f"# ⚔ Counter Report: {self._current_champion.title()}\n\n"
            markdown_output += "| Rank | Champion | Win Rate |\n"
            markdown_output += "|:----:|:---------|:--------:|\n"
            for i, counter in enumerate(results):
                rank_symbol = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
                markdown_output += f"| {rank_symbol} | **{counter.name}** | `{counter.win_rate}` |\n"
            markdown_output += "\n---\n*Source: League of Graphs • Live Data*"
            output_widget.update(markdown_output)
        elif event.state == WorkerState.ERROR:
            self.query_one("#analyze_button", Button).disabled = False
            error_msg = str(event.worker.error) if event.worker.error else "Unknown error"
            output_widget.update(f"❌ **Scraping Error**\n\n```\n{error_msg}\n```")


# ---------- APP + VISUAL STYLE ----------

class MatchupApp(App):
    TITLE = "League Of Legends Pick Generator"
    CSS = """
    Screen {
        background: #0d0d12;
        color: #f5f5f5;
    }

    Header {
        background: #7c3aed;
        color: white;
        text-align: center;
        text-style: bold;
        height: 1;
    }

    Footer {
        background: #1a1a24;
        color: #a1a1aa;
        height: 1;
    }

    #main_container {
        layout: vertical;
        height: 100%;
        padding: 1 2;
        align: center middle;
    }

    #input_area {
        background: #161622;
        border: round #6d28d9;
        padding: 1 2;
        margin-bottom: 1;
        width: 80%;
        max-width: 80;
    }

    #input_header {
        color: #c084fc;
        text-style: bold;
        margin-bottom: 1;
    }

    Input {
        background: #0f0f1a;
        color: #ffffff;
        border: tall #8b5cf6;
        height: 3;
        padding: 0 1;
        margin-bottom: 1;
        text-style: bold;
    }

    Input:focus {
        background: #1e1e2d;
        border: tall #a78bfa;
    }

    Button {
        background: #8b5cf6;
        color: white;
        height: 3;
        text-style: bold;
        border: round #a78bfa;
    }

    Button:hover {
        background: #9f67ff;
    }

    Button:disabled {
        background: #3f3f46;
        color: #71717a;
    }

    #output_scroll {
        background: #12111b;
        border: round #4c1d95;
        padding: 1;
        height: 1fr;
        width: 80%;
        max-width: 80;
    }

    #oracle_header {
        color: #c084fc;
        text-style: bold;
        margin-bottom: 1;
    }

    Markdown {
        color: #e4e4e7;
        background: transparent;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(MatchupScreen())


if __name__ == "__main__":
    app = MatchupApp()
    app.run()
