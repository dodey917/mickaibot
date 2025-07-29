import os
import openai
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration - Get secrets from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize conversation history
conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when user sends /start"""
    user = update.message.from_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 🤖\n"
        "I'm your ChatGPT-3.5 Telegram bot.\n\n"
        "Just send me a message and I'll respond like ChatGPT!\n"
        "Use /reset to clear our conversation history."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process user messages with ChatGPT-3.5"""
    user_id = update.message.from_user.id
    user_message = update.message.text
    
    # Initialize conversation history if new user
    if user_id not in conversations:
        conversations[user_id] = [
            {"role": "system", "content": "You are a helpful assistant. Respond concisely and helpfully."}
        ]
    
    # Add user message to history
    conversations[user_id].append({"role": "user", "content": user_message})
    
    try:
        # Generate response using ChatGPT-3.5
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversations[user_id],
            max_tokens=1000,
            temperature=0.7
        )
        
        # Get AI reply
        ai_reply = response.choices[0].message.content
        
        # Add to history
        conversations[user_id].append({"role": "assistant", "content": ai_reply})
        
        # Split long messages (>4000 characters)
        if len(ai_reply) > 4000:
            for i in range(0, len(ai_reply), 4000):
                await update.message.reply_text(ai_reply[i:i+4000])
        else:
            await update.message.reply_text(ai_reply)
    
    except Exception as e:
        error_msg = f"⚠️ Error: {str(e)}"
        await update.message.reply_text(error_msg[:4000])  # Truncate long errors

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history with /reset"""
    user_id = update.message.from_user.id
    conversations[user_id] = [
        {"role": "system", "content": "You are a helpful assistant. Respond concisely and helpfully."}
    ]
    await update.message.reply_text("🔄 Conversation history cleared!")

def main() -> None:
    # Create Telegram application
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Check if running on Render
    is_render = os.getenv("RENDER", False)
    
    if is_render:
        # Webhook configuration for Render
        public_url = os.getenv("RENDER_EXTERNAL_URL")
        
        # Construct URL if not provided
        if not public_url:
            service_name = os.getenv("RENDER_SERVICE_NAME")
            if service_name:
                public_url = f"https://{service_name}.onrender.com"
            else:
                raise ValueError("Missing RENDER_EXTERNAL_URL environment variable")
        
        print(f"🤖 Starting webhook mode on {public_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=f"{public_url}/webhook",
            drop_pending_updates=True
        )
    else:
        # Polling mode for local development
        print("🤖 Starting polling mode...")
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )

if __name__ == "__main__":
    # Verify required environment variables
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        raise ValueError("Missing required environment variables: TELEGRAM_TOKEN or OPENAI_API_KEY")
    
    main()
