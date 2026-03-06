"""
DIABLO SCRIPT PRO V3 - TELEGRAM BOT
ALL-IN-ONE FINAL CODE - FIXED VERSION
Real-time Wingo prediction with 1-minute periods
Made by @BLACKDEVIL9696
"""

import os
import json
import random
import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Telegram imports - FIXED: Added all required imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8737017483:AAGgMwfVu_tt7nkY6MCIoUcMxmoQKXEqCPM"  # ✅ Your token
API_URL = 'https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json'
SESSION_FILE = 'session.json'

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== TASHAN RULES ====================
TASHAN_RULES = [
    {"id": 1, "pattern": "ABABABABAB", "desc": "AB Alternating (1-1-1-1-1)"},
    {"id": 2, "pattern": "AABBAABB", "desc": "AABB Repeat (2-2-2-2)"},
    {"id": 3, "pattern": "AAABBBAAABBB", "desc": "AAABBB Repeat (3-3-3-3)"},
    {"id": 4, "pattern": "AAAABBBBAAAABBBB", "desc": "AAAABBBB Repeat (4-4-4-4)"},
    {"id": 5, "pattern": "AABAABAAB", "desc": "AAB Repeat (2-1-2-1)"},
    {"id": 6, "pattern": "ABABBABBB", "desc": "Progressive BIG (1-2-3)"},
    {"id": 7, "pattern": "ABBABBABB", "desc": "ABB Repeat (1-2-1-2)"},
    {"id": 8, "pattern": "AAABAAABAAAB", "desc": "AAAB Repeat (3-1-3-1)"},
    {"id": 9, "pattern": "AAABBAAABB", "desc": "AAABB Repeat (3-2-3-2)"},
    {"id": 10, "pattern": "ABBBABBBABBB", "desc": "ABBB Repeat (1-3-1-3)"},
    {"id": 11, "pattern": "AABBBABBB", "desc": "AABBB Pattern (2-3-1-3)"},
    {"id": 12, "pattern": "AAABBBAAAABBB", "desc": "3-3 then 4-3"},
    {"id": 13, "pattern": "AAAABBBAAAABBB", "desc": "4-3 Repeat"},
    {"id": 14, "pattern": "AABBAABBB", "desc": "AABB then AABBB"},
    {"id": 15, "pattern": "ABAABBAAABBB", "desc": "1-2-3 Blocks"},
    {"id": 16, "pattern": "ABBAAABBBBB", "desc": "1-2-3-4 Pattern"},
    {"id": 17, "pattern": "AAAABBBAAAB", "desc": "4-3-2-1 Pattern"},
    {"id": 18, "pattern": "AABBBABBBAA", "desc": "2-3-1-3-2 Pattern"},
    {"id": 19, "pattern": "ABBBABBB", "desc": "ABBB Repeat (1-3-1-3)"},
    {"id": 20, "pattern": "AAB BBAABBB", "desc": "AABBB Repeat (2-3-2-3)"}
]

# ==================== SESSION MANAGER ====================
class SessionManager:
    """Handle session save/load"""
    
    @staticmethod
    def load() -> Dict:
        """Load session from file"""
        try:
            if os.path.exists(SESSION_FILE):
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "history": [],
                "last_period": None,
                "last_results": [],
                "total_games": 0,
                "total_wins": 0,
                "last_update": None
            }
        except Exception as e:
            logger.error(f"Session load error: {e}")
            return {
                "history": [],
                "last_period": None,
                "last_results": [],
                "total_games": 0,
                "total_wins": 0
            }
    
    @staticmethod
    def save(data: Dict) -> bool:
        """Save session to file"""
        try:
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Session save error: {e}")
            return False

# ==================== CORE FUNCTIONS ====================
def get_size(num: int) -> str:
    """Convert number to BIG/SMALL"""
    return 'BIG' if num >= 5 else 'SMALL'

def get_pattern_string(results: List[Dict], length: int = 20) -> str:
    """Convert results to pattern string (A=SMALL, B=BIG)"""
    if not results:
        return ""
    pattern = []
    for r in results[:length]:
        pattern.append('A' if r.get('size') == 'SMALL' else 'B')
    return ''.join(pattern)

def detect_pattern(results: List[Dict]) -> Dict:
    """Real-time pattern detection from results"""
    if len(results) < 5:
        return {"rule": "--", "desc": "Collecting data...", "confidence": 0, "pattern": ""}
    
    pattern_str = get_pattern_string(results, 25)
    best_match = {"rule": "--", "desc": "No pattern detected", "confidence": 0, "pattern": ""}
    
    for rule in TASHAN_RULES:
        rule_pattern = rule["pattern"].replace(" ", "")
        
        # Full pattern match
        if rule_pattern in pattern_str:
            confidence = min(99, 75 + (len(rule_pattern) * 1.2))
            if confidence > best_match["confidence"]:
                best_match = {
                    "rule": rule["id"],
                    "desc": rule["desc"],
                    "confidence": round(confidence, 1),
                    "pattern": rule_pattern
                }
        
        # Partial matches for better detection
        for length in range(4, min(9, len(rule_pattern))):
            for i in range(0, len(rule_pattern) - length + 1):
                sub_pattern = rule_pattern[i:i+length]
                if sub_pattern in pattern_str:
                    confidence = 60 + (length * 5)
                    if confidence > best_match["confidence"]:
                        best_match = {
                            "rule": rule["id"],
                            "desc": f"{rule['desc'][:30]}... (partial)",
                            "confidence": round(confidence, 1),
                            "pattern": sub_pattern
                        }
    
    return best_match

def predict_next(results: List[Dict], pattern_info: Dict) -> Dict:
    """Predict next result based on pattern"""
    if len(results) < 4:
        return {"pred": random.choice(['BIG', 'SMALL']), "conf": 65.0}
    
    sizes = [r.get('size') for r in results if r.get('size')]
    
    # Pattern-based prediction
    if pattern_info["confidence"] > 65 and pattern_info.get("pattern"):
        pattern_str = get_pattern_string(results, 20)
        pattern = pattern_info["pattern"]
        last_idx = pattern_str.rfind(pattern)
        
        if last_idx >= 0:
            next_pos = (len(pattern_str) - last_idx) % len(pattern)
            next_char = pattern[next_pos]
            return {
                "pred": 'SMALL' if next_char == 'A' else 'BIG',
                "conf": pattern_info["confidence"]
            }
    
    # Streak detection
    if len(sizes) >= 3:
        last3 = sizes[:3]
        if last3[0] == last3[1] == last3[2]:
            return {
                "pred": 'SMALL' if last3[0] == 'BIG' else 'BIG',
                "conf": 80.0
            }
    
    # Alternating pattern
    if len(sizes) >= 3:
        last3 = sizes[:3]
        if last3[0] != last3[1] and last3[1] != last3[2]:
            return {
                "pred": 'SMALL' if last3[2] == 'BIG' else 'BIG',
                "conf": 75.0
            }
    
    # Frequency based
    last5 = sizes[:5]
    big_count = last5.count('BIG')
    if big_count >= 4:
        return {"pred": 'SMALL', "conf": 70.0}
    if big_count <= 1:
        return {"pred": 'BIG', "conf": 70.0}
    
    # Default to last result
    return {
        "pred": sizes[0] if sizes else random.choice(['BIG', 'SMALL']),
        "conf": 65.0
    }

def fetch_api_data() -> List:
    """Fetch real data from API"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(
            f"{API_URL}?t={int(time.time())}", 
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("list", [])
        else:
            logger.error(f"API returned status {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"API fetch failed: {e}")
        return []

def calculate_stats(history: List[Dict]) -> Dict:
    """Calculate win/loss statistics"""
    wins = sum(1 for h in history if h.get('result') == 'WIN')
    total = sum(1 for h in history if h.get('result') in ['WIN', 'LOSS'])
    rate = (wins / total * 100) if total > 0 else 0
    
    # Current streak
    streak = 0
    for h in history:
        if h.get('result') == 'WIN':
            streak += 1
        elif h.get('result') == 'LOSS':
            break
    
    return {
        'wins': wins,
        'total': total,
        'rate': round(rate, 1),
        'streak': streak
    }

# ==================== BOT COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_text = """
🔥 *DIABLO SCRIPT PRO V3* 🔥
🎯 *Real-time Wingo Prediction Bot*

*Available Commands:*
├─ /gen - Generate new 1-min period
├─ /history - Show last 10 results
├─ /pattern - Show current pattern
└─ /stats - View statistics

*Features:*
✅ Real 1-minute periods
✅ 20+ Tashan patterns
✅ 75%+ accuracy target
✅ Auto win/loss tracking

🤖 *Status:* ONLINE
⚡ *Mode:* Real-time API
👤 *Owner:* @BLACKDEVIL9696
    """
    
    keyboard = [
        [InlineKeyboardButton("🎯 Generate Now", callback_data="gen")],
        [InlineKeyboardButton("📜 History", callback_data="history"),
         InlineKeyboardButton("📊 Pattern", callback_data="pattern")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate new period with prediction"""
    # Handle both command and callback
    if update.callback_query:
        message = update.callback_query.message
        await update.callback_query.answer()
        chat_id = message.chat_id
        send_func = message.reply_text
    else:
        chat_id = update.message.chat_id
        send_func = update.message.reply_text
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Load session
    session = SessionManager.load()
    history = session.get("history", [])
    last_results = session.get("last_results", [])
    
    # Fetch latest API data
    api_list = fetch_api_data()
    
    if api_list:
        # Update last_results with new data
        new_results = []
        for item in api_list[:10]:
            try:
                num = int(item.get("number", 0))
                new_results.append({
                    "number": num, 
                    "size": get_size(num),
                    "period": item.get("issueNumber", "")
                })
            except:
                continue
        
        if new_results:
            last_results = new_results + last_results[:30]
        
        # Update history with actual results
        for item in api_list:
            issue = item.get("issueNumber", "")
            try:
                num = int(item.get("number", 0))
                size = get_size(num)
                
                for h in history:
                    if h["period"] == issue and h.get("actual") == "?":
                        h["actual"] = size
                        h["result"] = "WIN" if h["predict"] == size else "LOSS"
                        break
            except:
                continue
    
    # Get latest period
    latest_period = None
    if api_list:
        latest_period = api_list[0].get("issueNumber", "")
    
    # Generate next period (1-minute increment)
    if latest_period:
        try:
            # Convert to int and add 1 for 1-minute period
            next_period = str(int(latest_period) + 1)
        except:
            # Fallback to timestamp
            next_period = str(int(time.time()))
    else:
        next_period = str(int(time.time()))
    
    # Detect pattern and predict
    pattern_info = detect_pattern(last_results)
    prediction = predict_next(last_results, pattern_info)
    
    # Create new entry
    new_entry = {
        "period": next_period,
        "predict": prediction["pred"],
        "actual": "?",
        "result": "WAIT",
        "mode": "TASHAN" if pattern_info["confidence"] > 70 else "HYBRID",
        "rule": pattern_info["rule"],
        "time": datetime.now().strftime("%H:%M:%S"),
        "confidence": prediction["conf"]
    }
    
    history.insert(0, new_entry)
    history = history[:30]  # Keep last 30
    
    # Update stats
    session["history"] = history
    session["last_period"] = next_period
    session["last_results"] = last_results
    session["last_update"] = datetime.now().isoformat()
    SessionManager.save(session)
    
    # Create message
    msg = f"""
🎯 *NEW 1-MINUTE PERIOD* 🎯

📌 *Period:* `{next_period}`
🔮 *Prediction:* *{prediction['pred']}*
📊 *Confidence:* {prediction['conf']:.1f}%
🧠 *Pattern:* {pattern_info['desc'][:40]}...
🎲 *Rule:* #{pattern_info['rule']}

⏱️ *Time:* {datetime.now().strftime('%H:%M:%S')}
    """
    
    # Add buttons
    keyboard = [
        [InlineKeyboardButton("🔄 Generate Again", callback_data="gen")],
        [InlineKeyboardButton("📜 History", callback_data="history"), 
         InlineKeyboardButton("📊 Pattern", callback_data="pattern")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_func(msg, parse_mode='Markdown', reply_markup=reply_markup)

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last 10 results"""
    session = SessionManager.load()
    history = session.get("history", [])
    
    if not history:
        await update.message.reply_text("❌ No history found. Use /gen first!")
        return
    
    stats = calculate_stats(history)
    
    msg = "📜 *LAST 10 RESULTS*\n\n"
    for i, entry in enumerate(history[:10]):
        period_short = entry['period'][-6:]
        result_emoji = "✅" if entry.get('result') == "WIN" else "❌" if entry.get('result') == "LOSS" else "⏳"
        actual = entry.get('actual', '?')
        msg += f"{i+1}. `{period_short}` | {entry['predict']} ➜ {actual} {result_emoji}\n"
    
    msg += f"\n📊 *Stats:* {stats['wins']}/{stats['total']} ({stats['rate']}%)"
    msg += f"\n⚡ *Streak:* {stats['streak']}"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def pattern(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current detected pattern"""
    session = SessionManager.load()
    last_results = session.get("last_results", [])
    
    if len(last_results) < 5:
        await update.message.reply_text("⏳ Collecting data... Need at least 5 results!\nUse /gen karte rahein.")
        return
    
    pattern_info = detect_pattern(last_results)
    pattern_str = get_pattern_string(last_results, 15)
    
    # Create pattern visualization
    visual = []
    for i, r in enumerate(last_results[:15]):
        if i > 0 and i % 5 == 0:
            visual.append(" ")
        visual.append('🟢' if r.get('size') == 'SMALL' else '🔴')
    
    msg = f"""
🔍 *REAL-TIME PATTERN DETECTION*

📊 *Pattern String:* `{pattern_str}`

🎯 *Detected:* {pattern_info['desc']}
📈 *Confidence:* {pattern_info['confidence']}%
📌 *Rule #:* {pattern_info['rule']}

📊 *Visual Pattern:* 
{''.join(visual)}

📋 *Last 15:* {' '.join(str(r.get('size')) for r in last_results[:15])}
    """
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show overall statistics"""
    session = SessionManager.load()
    history = session.get("history", [])
    stats = calculate_stats(history)
    
    # Calculate mode distribution
    modes = {}
    for h in history:
        mode = h.get('mode', 'UNKNOWN')
        modes[mode] = modes.get(mode, 0) + 1
    
    mode_text = ""
    for mode, count in modes.items():
        mode_text += f"\n├─ {mode}: {count}"
    
    msg = f"""
📊 *OVERALL STATISTICS*

🎲 *Total Games:* {stats['total']}
🏆 *Total Wins:* {stats['wins']}
📈 *Win Rate:* {stats['rate']}%
⚡ *Current Streak:* {stats['streak']}

🔄 *Mode Distribution:*{mode_text}

⏱️ *Last Update:* {session.get('last_update', 'Never')[:19]}

👑 *Owner:* @BLACKDEVIL9696
    """
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "gen":
        # For gen callback, we need to call generate with the callback context
        await generate(update, context)
    elif query.data == "history":
        session = SessionManager.load()
        history = session.get("history", [])
        
        if not history:
            await query.message.reply_text("❌ No history found. Use /gen first!")
            return
        
        stats = calculate_stats(history)
        
        msg = "📜 *LAST 10 RESULTS*\n\n"
        for i, entry in enumerate(history[:10]):
            period_short = entry['period'][-6:]
            result_emoji = "✅" if entry.get('result') == "WIN" else "❌" if entry.get('result') == "LOSS" else "⏳"
            actual = entry.get('actual', '?')
            msg += f"{i+1}. `{period_short}` | {entry['predict']} ➜ {actual} {result_emoji}\n"
        
        msg += f"\n📊 *Stats:* {stats['wins']}/{stats['total']} ({stats['rate']}%)"
        
        await query.message.reply_text(msg, parse_mode='Markdown')
    
    elif query.data == "pattern":
        session = SessionManager.load()
        last_results = session.get("last_results", [])
        
        if len(last_results) < 5:
            await query.message.reply_text("⏳ Collecting data... Need at least 5 results!")
            return
        
        pattern_info = detect_pattern(last_results)
        pattern_str = get_pattern_string(last_results, 15)
        
        msg = f"""
🔍 *CURRENT PATTERN*

📊 `{pattern_str}`

🎯 {pattern_info['desc']}
📈 Confidence: {pattern_info['confidence']}%
📌 Rule #{pattern_info['rule']}
        """
        
        await query.message.reply_text(msg, parse_mode='Markdown')

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again."
            )
    except:
        pass

# ==================== MAIN ====================
def main():
    """Start the bot"""
    print("=" * 50)
    print("🤖 DIABLO SCRIPT PRO V3 - TELEGRAM BOT")
    print("=" * 50)
    print(f"✅ Bot Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
    print(f"📡 API URL: {API_URL}")
    print(f"📁 Session File: {SESSION_FILE}")
    print("=" * 50)
    print("🚀 Starting bot...")
    
    # Create Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("gen", generate))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("pattern", pattern))
    application.add_handler(CommandHandler("stats", stats))
    
    # Add callback handler for buttons - FIXED: Added missing import
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("=" 
