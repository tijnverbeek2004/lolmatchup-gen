import os
import google.generativeai as genai
from getpass import getpass


# --- AI Configuration ---

def get_api_key():
    """
    Gets the Google AI API key from environment variables or prompts the user.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Google AI API key not found in environment variables.")
        print("You can set it permanently as 'GOOGLE_API_KEY'.")
        api_key = getpass("Please enter your Google AI API key: ")
    return api_key


def get_ai_matchup(role, enemy_champion, api_key):
    """
    Sends a request to the Google Gemini API to get matchup details.
    """
    print(f"\n🤖 BEEP BOOP... Consulting the Google AI Oracle for {enemy_champion}...")

    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Error configuring Google AI: {e}")
        return None

    # The prompt defines the AI's personality and instructions.
    # We can use the same prompt structure.
    prompt = f"""
    You are a snarky but brilliant League of Legends analyst bot. 
    Your goal is to provide a funny, slightly toxic, but genuinely helpful counter-pick guide.
    When the user gives you their role and an enemy champion, you MUST respond in the following format EXACTLY, using the '###' separators. Do not add any text before or after this structure.

    The user's request is: My role is {role} and I am playing against {enemy_champion}.

    ### Counter
    [The single best champion counter. Be confident.]

    ### Runes
    [The primary and secondary runes for the counter pick.]

    ### Build
    [A simple core build path. e.g., "Rush Item A, then build Item B and Item C."]

    ### Tips
    - [A short, funny, and actionable tip.]
    - [A second short, funny, and actionable tip.]
    - [A third short, funny, and actionable tip about how to make the enemy laner's life miserable.]
    """

    try:
        model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # The Google API can sometimes throw very long, complex errors.
        # This helps to make them more readable.
        error_message = str(e)
        if "API key not valid" in error_message:
            print("\n❌ AUTHENTICATION ERROR: Your Google AI API key is invalid.")
        else:
            print(f"\n❌ An error occurred while contacting the AI: {error_message}")
        return None


# The print_formatted_response and main functions can stay EXACTLY the same as before!
# (I'm including them here for completeness)

def print_formatted_response(response_text):
    """
    Parses the AI's response and prints it in a structured format.
    """
    if not response_text:
        print("Could not generate a response.")
        return

    parts = response_text.split('###')
    data = {}
    for part in parts:
        if not part.strip(): continue
        lines = part.strip().split('\n')
        key = lines[0].strip().lower()
        value = '\n'.join(lines[1:]).strip()
        data[key] = value

    print("\n" + "=" * 40)
    print("🔥 AI ANALYSIS COMPLETE! TIME TO DOMINATE. 🔥")
    print("=" * 40 + "\n")

    print(f"💥 COUNTER PICK: {data.get('counter', 'N/A')}\n")
    print(f"📜 RUNES: {data.get('runes', 'N/A')}\n")
    print(f"⚔️ BUILD: {data.get('build', 'N/A')}\n")
    print("💡 PRO TIPS TO SECURE THE LP:")
    tips = data.get('tips', 'N/A').replace('-', ' ').strip().split('\n')
    for tip in tips:
        print(f"   - {tip.strip()}")

    print("\n" + "=" * 40)
    print("GLHF! Now go make them question their life choices.")
    print("=" * 40 + "\n")


def main():
    """Main function to run the script."""
    print("--- Welcome to the AI-Powered LoL Matchup Dominator ---")

    api_key = get_api_key()
    if not api_key:
        return

    role = input("Enter your role (e.g., top, jungler, mid): ").lower().strip()
    enemy_champion = input(f"Enter your enemy in '{role}': ").lower().strip()

    ai_response = get_ai_matchup(role, enemy_champion, api_key)
    if ai_response:
        print_formatted_response(ai_response)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting the program. See you on the Rift!")