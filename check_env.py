# check_env.py
import os
import sys
import google.generativeai as genai
from getpass import getpass

print("--- STARTING DIAGNOSTIC ---")

# 1. Check which Python is being used
print(f"[*] Python Executable: {sys.executable}")

# 2. Check the installed library version
try:
    print(f"[*] Found google-generativeai version: {genai.__version__}")
except Exception as e:
    print(f"[!] Could not find google-generativeai library: {e}")
    sys.exit() # Exit if library not found

# 3. Get API Key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    api_key = getpass("[?] Please enter your Google AI API key: ")

if not api_key:
    print("[!] No API key provided. Exiting.")
    sys.exit()

# 4. Configure the API
print("[*] Configuring API key...")
genai.configure(api_key=api_key)

# 5. List available models
print("[*] Attempting to list all available models for your key...")
try:
    for m in genai.list_models():
        # We are looking for a model that supports the 'generateContent' method
        if 'generateContent' in m.supported_generation_methods:
            print(f"  - Model Name: {m.name}")
except Exception as e:
    print(f"\n[!!!] FAILED to list models. This is the critical error.")
    print(f"      Error details: {e}")

print("\n--- DIAGNOSTIC COMPLETE ---")