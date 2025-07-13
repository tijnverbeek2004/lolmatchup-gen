# lol_analyzer.py

import os
import time
from getpass import getpass

import google.generativeai as genai
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# --- Configuration ---

def get_api_key():
    """Gets the Google AI API key from environment variables or prompts the user."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Google AI API key not found in environment variables.")
        api_key = getpass("Please enter your Google AI API key: ")
    return api_key


# --- Web Scraping Module ---

def handle_overlays(driver, wait):
    """
    Finds and handles cookie banners in multiple languages to clear the view.
    This is critical for scraping modern, GDPR-compliant websites.
    """
    try:
        # This XPath is a "master key" for common consent popups.
        overlay_locator = (By.XPATH,
                           "//button[contains(., 'Accept') or contains(., 'Continue') or contains(., 'Agree') or contains(., 'Accepteren')]")
        # Wait a short time for the banner to appear.
        overlay_wait = WebDriverWait(driver, 3)
        overlay_button = overlay_wait.until(EC.element_to_be_clickable(overlay_locator))

        # A JS click can be more reliable than a standard Selenium click.
        driver.execute_script("arguments[0].click();", overlay_button)

        # Wait for the banner to become invisible before proceeding.
        wait.until(EC.invisibility_of_element_located(overlay_locator))
    except TimeoutException:
        # This is expected if no overlay appears.
        pass


def scrape_item_section(driver, header_text):
    """
    A helper to scrape all items following a specific header (e.g., "Core Build").
    Returns a list of item names or an empty list if the section isn't found.
    """
    try:
        # This "God Mode" XPath finds the header, then any item images inside
        # the first "iconsRow" div that appears anywhere after it.
        xpath = f"//h3[contains(text(), '{header_text}')]/following::div[contains(@class, 'iconsRow')][1]//img"
        item_elements = driver.find_elements(By.XPATH, xpath)
        return [img.get_attribute('alt') for img in item_elements if img.get_attribute('alt')]
    except Exception:
        return []


def scrape_matchup_data(role, champion):
    """
    Main scraping function. Orchestrates the process of finding the best counter
    and scraping its full build path from League of Graphs.
    """
    print(f"🔎 Analyzing live data for the {champion} matchup...")

    champion_formatted = champion.strip().replace(" ", "").lower()
    role_map = {
        "JUNGLE": "JUNGLE", "JGL": "JUNGLE", "ADC": "ADC", "BOTTOM": "ADC",
        "TOP": "TOP", "MID": "MIDDLE", "MIDDLE": "MIDDLE", "SUPPORT": "SUPPORT", "SUP": "SUPPORT"
    }
    role_formatted = role_map.get(role.upper(), "all")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--window-size=1920,1080")
    # Performance boost: Disable image loading.
    options.add_experimental_option("prefs", {"profile.default_content_settings.images": 2})

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 15)

        # Step 1: Find the best counter champion.
        counters_url = f"https://www.leagueofgraphs.com/champions/counters/{champion_formatted}/{role_formatted}"
        driver.get(counters_url)
        handle_overlays(driver, wait)

        counter_name_locator = (By.XPATH,
                                "//h3[contains(text(), 'loses lane against')]/following-sibling::table/tbody/tr[2]//span[@class='name']")
        counter_name_element = wait.until(EC.visibility_of_element_located(counter_name_locator))
        counter_name = counter_name_element.text.strip()

        # Step 2: Navigate to the specific matchup build page.
        counter_url_name = counter_name.lower().replace(' ', '').replace('&willump', '').replace("'", "").replace(".",
                                                                                                                  "")
        tier_list_url = f"https://www.leagueofgraphs.com/champions/tier-list/{counter_url_name}/{role_formatted}/vs-{champion_formatted}"
        driver.get(tier_list_url)
        time.sleep(1)  # A brief, stable pause to allow the page to settle before checking for popups.
        handle_overlays(driver, wait)

        # Step 3: Scrape all build sections using the helper function.
        core_items = scrape_item_section(driver, "Core Build")
        if not core_items:
            raise Exception("Core build section not found; unable to continue.")

        boots = scrape_item_section(driver, "Boots")
        options = scrape_item_section(driver, "Final Item Options")

        print(f"✅ Live data acquired for {counter_name}!")
        return {
            "best_counter": counter_name,
            "core_build": core_items,
            "boots": boots,
            "options": options
        }

    except Exception as e:
        print(f"\n❌ Scraping failed. Could not retrieve live data. Error: {e}")
        print("   Falling back to the AI's general knowledge.")
        return None
    finally:
        if driver:
            driver.quit()


# --- AI & Formatting Modules ---

def get_ai_analysis(role, enemy_champion, api_key, scraped_data):
    """
    Contacts the Google Gemini API. It uses a different prompt depending on
    whether live scraped data is available.
    """
    print(f"🤖 Consulting the AI Oracle...")
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Error configuring Google AI: {e}")
        return None

    if scraped_data:
        # Prompt for when we have live data
        core_build_str = " -> ".join(scraped_data.get("core_build", []))
        boots_str = ", ".join(scraped_data.get("boots", []))
        options_str = ", ".join(scraped_data.get("options", []))

        prompt = f"""
        You are a snarky but brilliant League of Legends analyst.
        Use the live data provided to create a concise game plan.

        **Live Data Context:**
        - Enemy: {enemy_champion} ({role})
        - Strongest Counter: {scraped_data['best_counter']}
        - Scraped Core Items: {core_build_str}
        - Scraped Boots: {boots_str}
        - Scraped Situational Options: {options_str}

        **Your Task:**
        Present a complete game plan. Use the live data for all build sections.

        ### Counter
        [{scraped_data['best_counter']}]

        ### Why It Works
        [In one or two sentences, explain WHY this champion counters {enemy_champion}.]

        ### Recommended Runes
        [Suggest a standard and effective rune page for {scraped_data['best_counter']}.]

        ### Full Build Path (Live Data)
        **Core Items:** {core_build_str}
        **Boots:** {boots_str}
        **Situational Items:** {options_str}

        ### Build Explanation
        [Briefly explain the build. Why is this core build effective? When would you build the situational items?]

        ### Pro Tips
        - [A sharp, actionable tip for the early game.]
        - [A key tip for mid-game teamfights.]
        - [A final, funny tip on how to mentally dominate the enemy.]
        """
    else:
        # Fallback prompt for when scraping fails
        prompt = f"""
        You are a snarky but brilliant League of Legends analyst.
        Live data was unavailable, so rely on your general game knowledge.

        **User's Request:**
        I need a game plan to beat {enemy_champion} in the {role} role.

        **Your Task:**
        Provide a complete, standard game plan.

        ### Counter
        [Suggest one strong counter.]
        ### Why It Works
        [Explain why.]
        ### Recommended Runes
        [Suggest a standard rune page.]
        ### Full Build Path
        [Suggest a full, 6-item example build including boots.]
        ### Build Explanation
        [Explain the item choices.]
        ### Pro Tips
        - [Early game tip.]
        - [Mid game tip.]
        - [Funny tip.]
        """
    try:
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"\n❌ An error occurred while contacting the AI: {e}")
        return None


def print_formatted_response(response_text, has_live_data):
    """Cleans and prints the AI's response in a readable format."""
    if not response_text:
        print("Could not generate a response.")
        return

    data_source = "(Live from League of Graphs)" if has_live_data else "(General Knowledge)"
    print("\n" + "=" * 55)
    print(f"🔥 AI ANALYSIS COMPLETE! {data_source} 🔥")
    print("=" * 55 + "\n")

    sections = response_text.split('###')
    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().split('\n')
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip().replace('[', '').replace(']', '')
        print(f"--- {title.upper()} ---\n{content}\n")

    print("=" * 55)
    print("GLHF! Now go get those chips. You've earned them.")
    print("=" * 55 + "\n")


# --- Main Execution ---

def main():
    """Main function to run the application."""
    print("--- Welcome to the AI-Powered LoL Matchup Dominator ---")
    api_key = get_api_key()
    if not api_key:
        print("Exiting: API Key is required.")
        return

    try:
        role = input("Enter your role (e.g., top, jungle, mid, adc, support): ").lower().strip()
        enemy_champion = input(f"Enter your enemy in '{role}': ").strip()

        scraped_data = scrape_matchup_data(role, enemy_champion)
        ai_response = get_ai_analysis(role, enemy_champion, api_key, scraped_data)

        if ai_response:
            print_formatted_response(ai_response, has_live_data=(scraped_data is not None))

    except KeyboardInterrupt:
        print("\n\nExiting the program. Go get your chips.")


if __name__ == "__main__":
    main()