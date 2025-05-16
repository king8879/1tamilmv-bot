import os
from dotenv import load_dotenv
import random
import logging
import threading
import time
from flask import Flask, request
import telebot
from telebot import TeleBot, types
from bs4 import BeautifulSoup
import cloudscraper
from torrent_uploader import upload_torrent_files


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def callback_handler(call):
    logger.info(f"User {call.from_user.id} clicked {call.data}")


# Bot Token and Channel Details
load_dotenv()

TOKEN = os.getenv('TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
TAMILMV_URL = os.getenv('TAMILMV_URL', 'https://www.1tamilmv.fi')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)

scraper.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://www.google.com/',
    'Upgrade-Insecure-Requests': '1',
    'DNT': '1',  # Do Not Track
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
})

posted_titles = set()

def tamilmv():
    mainUrl = TAMILMV_URL
    movie_list = []
    real_dict = {}

    try:
        response = scraper.get(mainUrl)
        if response.status_code != 200:
            print(f"Failed to fetch TamilMV. Status Code: {response.status_code}")
            return [], {}

        soup = BeautifulSoup(response.text, 'lxml')
        posts = soup.find_all('div', {'class': 'ipsType_break ipsContained'})

        for post in posts[:20]:
            title_tag = post.find('a')
            if not title_tag:
                continue
            title = title_tag.text.strip()
            link = title_tag['href']
            if not link.startswith("http"):
                link = TAMILMV_URL + link
            movie_list.append(title)
            details = get_movie_details(link)
            if details:
                real_dict[title] = details

    except Exception as e:
        print(f"[tamilmv error]: {e}")
    
    return movie_list, real_dict

def get_movie_details(url):
    try:
        res = scraper.get(url)
        soup = BeautifulSoup(res.text, 'lxml')

        mag_links = [a['href'] for a in soup.find_all('a', href=True) if 'magnet:' in a['href']]
        torrent_links = [a['href'] for a in soup.find_all('a', {"data-fileext": "torrent"}, href=True)]

        movie_title = soup.find('h1').text.strip()
        result = []

        for i in range(len(mag_links)):
            magnet = mag_links[i]
            torrent = torrent_links[i] if i < len(torrent_links) else '#'
            detail = (
                f"<blockquote><b>📂 Movie Title:</b> {movie_title}</blockquote>\n"
                f"<b>🧲 Magnet Link</b><pre>{magnet}</pre>\n"
                f"🗒️ <a href='{torrent}'>Torrent File</a> ❖ 𝐖𝐃 𝐙𝐎𝐍𝐄 ❖ ™"
            )
            result.append(detail)

        return result

    except Exception as e:
        print(f"[get_movie_details error]: {e}")
        return []

def post_to_channel():
    global posted_titles
    print("Auto posting thread started.")
    
    while True:
        try:
            movie_list, real_dict = tamilmv()
            if not real_dict:
                print("No new data found. Sleeping for 1 hour.")
                time.sleep(3600)
                continue

            for title, details in real_dict.items():
                if title in posted_titles:
                    continue
                for detail in details:
                    try:
                        bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=detail,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )

                        # === .torrent ফাইল পাঠানোর অংশ ===
                        movie_title = title
                        torrent_links = [
                            line.split("href='")[1].split("'")[0]
                            for line in detail.splitlines()
                            if "Torrent File Download" in line
                        ]
                        if torrent_links:
                            upload_torrent_files(bot, CHANNEL_ID, movie_title, torrent_links)
                        # ==================================

                        print(f"Posted: {title}")
                        time.sleep(10)
                    except Exception as e:
                        print(f"Error posting message: {e}")
                posted_titles.add(title)

            time.sleep(3600)

        except Exception as e:
            print(f"[post_to_channel error]: {e}")
            time.sleep(600)

# Random flower selection function
def get_random_flower():
    flowers = ["💐", "🌸", "🌹", "🌺", "🌻"]
    return random.choice(flowers)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    first_name = message.from_user.first_name
    selected_flower = get_random_flower()

    caption = (
        f"╔════════════════════════╗\n"
        f"║ {selected_flower} Hello <b>{first_name}</b>\n"
        f"╚════════════════════════╝\n\n"
        f"<b>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</b>\n"
        f"<blockquote>🗳 This bot automatically posts latest Movies from 1Tamilmv to channel</blockquote>\n"
        f"<b>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</b>\n\n"
        f"🔗 <b>Channel:</b> @{CHANNEL_USERNAME}\n\n"
        f"⚡ <b>Credits:</b> @Farooq_is_king"
    )

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton('📖 Help', callback_data='help'),
        types.InlineKeyboardButton('🔗 Visit Channel', url=f'https://t.me/{CHANNEL_USERNAME}'),
        types.InlineKeyboardButton("⚡ Powered By", url='https://t.me/Opleech_WD')
    )

    sent_msg = bot.send_photo(
        message.chat.id,
        photo='https://graph.org/file/4e8a1172e8ba4b7a0bdfa.jpg',
        caption=caption,
        parse_mode='HTML',
        reply_markup=keyboard
    )
    bot.register_next_step_handler(sent_msg, process_help)

def process_help(message):
    pass

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == "help":
            help_text = (
                "╔══════════════════════╗\n"
                "║ 🛠️ <b>BOT USAGE GUIDE</b>\n"
                "╚══════════════════════╝\n\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "<blockquote>"
                "✦ <b>Auto Updates:</b> Tamil/Telugu/Hindi movies\n"
                "✦ <b>Subscription:</b> Stay connected for new posts\n"
                "✦ <b>Direct Access:</b> .torrent + magnet links"
                "</blockquote>\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
                "📢 <b>Official Channel:</b> @Opleech_WD\n"
                "🔔 <i>Regular updates guaranteed!</i>"
            )

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"))

            bot.answer_callback_query(call.id)
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=help_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )

        elif call.data == "back_to_main":
            first_name = call.from_user.first_name
            selected_flower = get_random_flower()  # Get new random flower for back button
            
            caption = (
                f"╔════════════════════════╗\n"
                f"║ {selected_flower} Hello <b>{first_name}</b>\n"
                f"╚════════════════════════╝\n\n"
                f"<b>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</b>\n"
                f"<blockquote>🗳 This bot automatically posts latest Movies from 1Tamilmv to channel</blockquote>\n"
                f"<b>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</b>\n\n"
                f"🔗 <b>Channel:</b> @{CHANNEL_USERNAME}\n\n"
                f"⚡ <b>Credits:</b> @Farooq_is_king"
            )

            keyboard = types.InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                types.InlineKeyboardButton('📖 Help', callback_data='help'),
                types.InlineKeyboardButton('🔗 Visit Channel', url=f'https://t.me/{CHANNEL_USERNAME}'),
                types.InlineKeyboardButton("⚡ Powered By", url='https://t.me/Opleech_WD')
            )

            bot.answer_callback_query(call.id)
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=caption,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
    except Exception as e:
        print(f"Error in callback handler: {e}")
        bot.answer_callback_query(call.id, "⚠️ An error occurred. Please try again.")


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(json_str)])
    return 'OK', 200

@app.route('/')
def home():
    return 'Webhook is live', 200

@app.route('/1Tamilmv', methods=['GET'])
def handle_all_feeds():
    try:
        movie_list, real_dict = tamilmv()
        posted = 0
        for title, details in real_dict.items():
            if title in posted_titles:
                continue
            for detail in details:
                bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=detail,
                    parse_mode='HTML',
                    disable_web_page_preview=True 
                )
                posted_titles.add(title)
                posted += 1
                time.sleep(5)
        return {"message": f"{posted} messages posted!"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    threading.Thread(target=post_to_channel, daemon=True).start()
    bot.remove_webhook()
    bot.set_webhook(url=f'{WEBHOOK_URL}/{TOKEN}')
    app.run(host='0.0.0.0', port=3000)
