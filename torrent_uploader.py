import requests
import os
import re

def upload_torrent_files(bot, chat_id, movie_title, torrent_links):
    thumbnail_url = "https://i.ibb.co/3yVXrs7k/op-torrent.png"
    thumb_path = "/tmp/thumb.jpg"
    # পুরনো ফাইল পরিষ্কার
    import glob, time
    for tfile in glob.glob("/tmp/*.torrent"):
        if time.time() - os.path.getmtime(tfile) > 3600:
            os.remove(tfile)

    # থাম্বনেইল ডাউনলোড করা (শুধু একবার)
    if not os.path.exists(thumb_path):
        try:
            r = requests.get(thumbnail_url, timeout=10)
            if r.status_code == 200:
                with open(thumb_path, 'wb') as f:
                    f.write(r.content)
            else:
                thumb_path = None
        except:
            thumb_path = None

    for link in torrent_links:
        try:
            r = requests.get(link, allow_redirects=True, timeout=15)
            content_type = r.headers.get('Content-Type', '')

            if r.status_code != 200:
                print(f"[upload_torrent_files warning]: Failed to download from {link}")
                continue

            filename = "file.torrent"
            cd = r.headers.get('Content-Disposition')
            if cd:
                fname_match = re.findall('filename="?([^"]+)"?', cd)
                if fname_match:
                    filename = fname_match[0]

            if not filename.endswith('.torrent'):
                filename += '.torrent'

            file_path = f"/tmp/{filename}"

            if 'application/x-bittorrent' in content_type or filename.endswith('.torrent'):
                with open(file_path, 'wb') as f:
                    f.write(r.content)

                with open(file_path, 'rb') as f, open(thumb_path, 'rb') if thumb_path else open(file_path, 'rb') as thumb:
                    bot.send_document(
                        chat_id=chat_id,
                        document=f,
                        caption=f"<blockquote>📂 <b>{movie_title}</b></blockquote>\n🧲 <b>.TORRENT File</b>\n\n ❖ 𝐖𝐃 𝐙𝐎𝐍𝐄 ❖ ™ @Opleech_WD",
                        parse_mode='HTML',
                        thumb=thumb
                    )

                os.remove(file_path)
            else:
                print(f"[upload_torrent_files warning]: Not a .torrent file. Content-Type: {content_type}, URL: {link}")

        except Exception as e:
            print(f"[upload_torrent_files error]: {e}")
