import os
import requests
import time
from google import genai
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURATION
# ==========================================
# This command finds your .env file and loads the variables into memory
load_dotenv()

# Now we securely fetch the keys from the environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Initialize the new GenAI Client
client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. THE INPUT: Fetch Data from Hacker News
# ==========================================
print("📥 Fetching top 3 stories from Hacker News...")
top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
story_ids = requests.get(top_stories_url).json()

raw_news_data = ""

for story_id in story_ids[:3]:
    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
    story = requests.get(story_url).json()
    title = story['title']
    link = story.get('url', 'No external link')
    raw_news_data += f"- {title} ({link})\n"

print("✅ Data fetched successfully.\n")

# ==========================================
# 3. THE BRAIN: Ask Gemini to Summarize
# ==========================================
print("🧠 Passing data to Gemini 2.5 Flash for processing...")

# We combine our instructions and the raw data into one prompt
prompt = f"""
You are a tech analyst. I will give you a list of the top 3 trending news stories. 
Reply with a short, punchy 3-bullet-point summary of what is happening in the tech world right now based ONLY on those titles. 
Keep it casual but professional.

Here is the data:
{raw_news_data}
"""

# Setup our retry variables
max_retries = 3
retry_delay = 5 # seconds to wait between tries
ai_summary = ""

for attempt in range(max_retries):
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        ai_summary = response.text
        print("✅ Gemini finished thinking.\n")
        break # Success! Break out of the retry loop.
        
    except Exception as e:
        # If the error is a 503, we wait and try again
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            print(f"⚠️ Google servers are busy (Attempt {attempt + 1}/{max_retries}). Waiting {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            # If it is a different error (like a wrong API key), print it and stop
            print(f"❌ An unexpected error occurred: {e}")
            exit()

# If the loop finishes and we still don't have a summary, stop the script
if not ai_summary:
    print("❌ Failed to reach Gemini after maximum retries. Aborting.")

    # Send error notification to Discord
    error_message = {
        "content" : f"**🚨 Automated Tech Briefing**\nHere are the top stories right now:\n{raw_news_data}\n**🤖 AI Analysis:**\n**Google servers are busy!**\n**Unable to reach Gemini**"
    }
    discord_response = requests.post(DISCORD_WEBHOOK_URL, json=error_message)

    if discord_response.status_code == 204:
        print("Discord Notified.")
    else:
        print(f"❌ Discord failed. Error: {discord_response.status_code}")
    
    exit()

# ==========================================
# 4. THE OUTPUT: Send to Discord
# ==========================================
print("🚀 Firing payload to Discord...")

final_message = {
    "content": f"**🚨 Automated Tech Briefing**\nHere are the top stories right now:\n{raw_news_data}\n**🤖 AI Analysis:**\n{ai_summary}"
}

discord_response = requests.post(DISCORD_WEBHOOK_URL, json=final_message)

if discord_response.status_code == 204:
    print("🎉 MISSION ACCOMPLISHED! Check your Discord.")
else:
    print(f"❌ Discord failed. Error: {discord_response.status_code}")