import os
import time
import telebot
from telebot import types
from bs4 import BeautifulSoup as bs
from lyricy import Lyricy
import requests
import json
import re
from datetime import datetime
from googletrans import Translator
from server import server

headers = {
    'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    }

headers_ar = {
    'referer': 'https://kalimat.anghami.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
}

API_KEY = os.environ.get('API_KEY')
BASE_LYRIC = os.environ.get('BASE_LYRIC')
BASE_SONG = os.environ.get('BASE_SONG')
BASE_AR = os.environ.get('BASE_AR')
CHATID = os.environ.get('CHATID')

bot = telebot.TeleBot(API_KEY)

server()

def get_songs(name, from_lyric):
    global songs_matched
    songs_matched = dict()
    with requests.Session() as s:
        for page in range(1,7):
            if from_lyric:
                url = f'{BASE_LYRIC}{1}&q={name.strip()}'
            else: 
                url = f'{BASE_SONG}{page}&q={name.strip()}'
            r = s.get(url, headers=headers)
            if r.status_code == 200:
                parsed_json = json.loads(r.text)
                for hit in parsed_json['response']['sections'][0]['hits']:
                    #song_name: [link, photo, album_photo]
                    songs_matched[hit['result']['full_title'].replace('by', '-')] = [hit['result']['url'],
                                                                                    hit['result']['song_art_image_url'],
                                                                                    hit['result']['header_image_url']]
    markup = get_songs_markup(0)
    return markup

def get_songs_markup(current_index):
    markup = types.InlineKeyboardMarkup()
    for key in list(songs_matched.keys())[current_index:current_index+5]:
        markup.row(types.InlineKeyboardButton(text=key,callback_data='selected'+key.split('-')[0]))
    if len(songs_matched.keys()) > 0 and current_index < 5:
        markup.row(types.InlineKeyboardButton(text='➡️', callback_data='right'))
    elif current_index >= 5 and current_index <= len(songs_matched.keys()) - current_index:
        markup.row(types.InlineKeyboardButton(text='⬅️', callback_data='left'), types.InlineKeyboardButton(text='➡️', callback_data='right'))
    elif len(songs_matched.keys()) != 0 and current_index >= 5:
        markup.row(types.InlineKeyboardButton(text='⬅️', callback_data='left'))
    markup.row(types.InlineKeyboardButton(text='ابحث عن أغانٍ عربية', callback_data='ar_search'))
    markup.row(types.InlineKeyboardButton(text='Close', callback_data='result_no'))
    return markup

def get_lyrics(link):
    r_lyrics = requests.get(link, headers=headers)
    soup_lyrics = bs(r_lyrics.content, features='lxml')
    try:
        lyrics_raw = soup_lyrics.find("div", class_=re.compile("^lyrics$|Lyrics__Root"))
        lyrics_raw.find("div", class_=re.compile("^LyricsHeader")).decompose()
        lyrics_raw.find("div", class_=re.compile("^LyricsFooter__Container")).decompose()
        try:
            lyrics_raw.find("div", class_=re.compile("^RightSidebar__Container")).decompose()
        except:
            pass
    except:
        if lyrics_raw == None:
            lyrics_raw = soup_lyrics.find('div', class_=re.compile("^LyricsPlaceholder__Message"))
    lyrics_fixed = str(lyrics_raw).replace('<br/>', '\n')
    convert = bs(lyrics_fixed, features='lxml')
    lyrics = convert.text
    return lyrics


def get_info_markup():
    markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text='About the song', callback_data='info_about'),
                                                    types.InlineKeyboardButton(text='Album tracklist', callback_data='info_album'),
                                                    types.InlineKeyboardButton(text='Translation (beta)', callback_data='info_translation')],
                                                    [types.InlineKeyboardButton(text='Done', callback_data='click_done')]])
    return markup

def get_about(link):
    r_about = requests.get(link, headers=headers)
    if r_about.status_code == 200:
        soup_about = bs(r_about.content, features='lxml')
        try:
            about = soup_about.find('div', class_= re.compile("^SongDescription__Content")).get_text()
            if about == None:
                about = 'Sorry, couldn\'t find data.'
            return about
        except AttributeError:
            pass
    return '\nSorry, couldn\'t find data.'

def get_album(link):
    tracks = dict()
    r_album = requests.get(link, headers=headers)
    if r_album.status_code == 200:
        soup_album = bs(r_album.content, features='lxml')
        try:
            album_name = soup_album.find('a', class_=re.compile("^PrimaryAlbum__Title")).get_text()
        except AttributeError:
            album_name = 'Sorry, couldn\'t find data.'
        try:
            album_tracks = soup_album.find('ol', class_= re.compile("^AlbumTracklist__Container"))
            if album_tracks != None:
                for li in soup_album.find_all('li', class_=re.compile("^AlbumTracklist__Track")):
                    x = li.get_text()
                    if re.search("\d", x) == None:
                        li.decompose()
                    if li.div.a != None:
                        tracks[li.div.get_text()] = li.div.a['href']
                    else:
                        tracks[li.div.get_text()] = link
        except AttributeError:
            pass
        return album_name, tracks 

def get_songs_arabic(name):
    global songs_matched_arabic
    songs_matched_arabic = dict()
    markup = types.InlineKeyboardMarkup()
    url = BASE_AR + name.strip()
    r = requests.post(url, headers=headers_ar)
    if r.status_code == 200:
        parsed_json = json.loads(r.text)
        for song in parsed_json['sections'][0]['data']:
            if 'lyrics' in song and 'is_podcast' in song:
                if song['lyrics'] == 1 and song['is_podcast'] == 0:
                    songs_matched_arabic[song['title'] + ' - ' + song['artist']] = [song['id'],  song['coverArt']]
                    continue
            if 'lyrics' in song:
                if song['lyrics'] == 1:
                    songs_matched_arabic[song['title'] + ' - ' + song['artist']] = [song['id'],  song['coverArt']]
                    continue
            if 'is_podcast' in song:
                if song['is_podcast'] == 0:
                    songs_matched_arabic[song['title'] + ' - ' + song['artist']] = [song['id'],  song['coverArt']]
                    continue
        for key in songs_matched_arabic.keys():
            markup.row(types.InlineKeyboardButton(text=key, callback_data='ar_selected'+key.split('-')[0]))
    markup.row(types.InlineKeyboardButton(text='إغلاق', callback_data='result_no'))
    return markup

def get_data_arabic(song_selected_ar):
    photo_url = 'https://angartwork.anghcdn.co/?id=' + str(songs_matched_arabic[song_selected_ar][1])
    lyrics_url = 'https://kalimat.anghami.com/lyrics/' + str(songs_matched_arabic[song_selected_ar][0])
    r = requests.get(lyrics_url, headers=headers)
    if r.status_code == 200:
        soup_ar = bs(r.content, 'lxml')
        try:
            lyrics = song_selected_ar.split('-')[0].strip() + ' | كلمات:\n\n' + soup_ar.find('pre', class_=re.compile("^lyrics-body")).text
        except AttributeError:
            lyrics =  lyrics = song_selected_ar.split('-')[0].strip() + ' | كلمات:\n\n' + soup_ar.find('h4', class_=re.compile("^error-page")).text
        return photo_url, lyrics

def chat(message):
    userId = message.chat.id
    nameUser = str(message.chat.first_name) + ' ' + str(message.chat.last_name)
    username = message.chat.username
    text = message.text
    date = datetime.now()
    data = f'User id: {userId}\nUsername: @{username}\nName: {nameUser}\nText: {text}\nDate: {date}'
    bot.send_message(chat_id=CHATID, text=data)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_chat_action(message.chat.id, action='typing')
    smsg = "Lyricism is UP!\nSend me the name of a song and I will get its lyrics for you <3\n(You can send with artist name for more accuracy)."
    bot.reply_to(message, smsg)
    chat(message)

@bot.message_handler(commands=['contact'])
def contact(message):
    bot.send_chat_action(message.chat.id, action='typing')
    smsg = "Contact bot creator to report a bug or suggest a feature:\n@TheAtef\nhttps://t.me/TheAtef"
    bot.reply_to(message, smsg, disable_web_page_preview=True)
    chat(message)

@bot.message_handler(commands=['donate'])
def donate(message):
    bot.send_chat_action(message.chat.id, action='typing')
    smsg = "Thanks for consedring donating!\nHere is my Buy Me a Coffee link:\nhttps://www.buymeacoffee.com/TheAtef"
    bot.reply_to(message, smsg, disable_web_page_preview=True)
    chat(message)

@bot.message_handler(commands=['from_lyric'])
def from_lyric(message):
    chat(message)
    bot.send_chat_action(message.chat.id, action='typing')
    if message.text == "/from_lyric":
        smsg = "Write the command with the lyrics you remember to find the song.\nExample:\n/from_lyric yesterday I woke up sucking a lemon"
        bot.reply_to(message, smsg)
    else:
        global message_received
        message_received = message
        bot.send_message(message.chat.id, 'Choose your song:', reply_markup= get_songs(message.text.removeprefix('/from_lyric '), True), reply_to_message_id=message.message_id)

@bot.message_handler(commands=['lrc'])
def lrc(message):
    chat(message)
    bot.send_chat_action(message.chat.id, action='typing')
    if message.text == "/lrc":
        smsg = "Write the command with the name of the song which you want the .lrc file for.\nExample:\n/lrc exit music"
        bot.reply_to(message, smsg)
    else:
        global message_received
        global lrc_files
        message_received = message
        lrc_files = []
        ly = Lyricy()
        results = ly.search(message.text.removeprefix('/lrc '))
        markup = types.InlineKeyboardMarkup()
        for x in range(len(results)):
            title = results[x].title.split("LRC", 1)[0]
            if title == " No result found":
                break
            lrc_files.append(results[x])
            markup.add(types.InlineKeyboardButton(text=title, callback_data='lrc'+str(x)))
        markup.add(types.InlineKeyboardButton(text='Close', callback_data='result_no'))
        bot.send_message(message.chat.id, "Choose your song: ", reply_to_message_id= message.message_id, reply_markup=markup)
    chat(message)

@bot.message_handler(commands=None)
def reply(message):
    global message_received
    message_received = message
    bot.send_chat_action(message.chat.id, action='typing')
    bot.send_message(message.chat.id, 'Choose your song:', reply_markup= get_songs(message.text, False), reply_to_message_id=message.message_id)
    chat(message)

swap_count = 0
@bot.callback_query_handler(func=lambda call: True)
def callback_data(call):
    global swap_count
    global lyricsfr
    global song_selected
    
    if call.message:
        if call.data == 'result_no':
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.delete_message(chat_id=call.message.chat.id, message_id=message_received.message_id)

        if call.data.startswith('lrc'):
            result = lrc_files[int(call.data.removeprefix('lrc'))]
            result.fetch()
            lrc_name = result.title.split("LRC", 1)[0] + ".lrc"
            with open(lrc_name, "w", encoding="utf-8") as f:
                f.write(result.lyrics)
            bot.send_chat_action(call.message.chat.id, "upload_document")
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_document(call.message.chat.id, open(lrc_name, 'rb'), message_received.message_id)

        if call.data.startswith('selected'):
            bot.send_chat_action(call.message.chat.id, action='typing')
            bot.delete_message(call.message.chat.id, call.message.message_id)
            song_selected = ''
            for key in list(songs_matched.keys()):
                if key.startswith(call.data.removeprefix('selected')):
                    song_selected = key
                    break

            lyrics = get_lyrics(songs_matched[song_selected][0])
            lyricsfr = call.data.removeprefix('selected').strip() + ' | Lyrics:\n\n' + lyrics
            if len(lyricsfr) <= 1024:
                bot.send_photo(call.message.chat.id, songs_matched[song_selected][1], caption=lyricsfr, reply_markup=get_info_markup(), reply_to_message_id=message_received.message_id)
            elif len(lyricsfr) > 1024 and len(lyricsfr) <= 4096:
                bot.send_photo(call.message.chat.id, songs_matched[song_selected][1], reply_to_message_id=message_received.message_id)
                bot.send_message(call.message.chat.id, lyricsfr, reply_markup= get_info_markup())
            elif len(lyricsfr) > 4096:
                bot.send_photo(call.message.chat.id, songs_matched[song_selected][1], reply_to_message_id=message_received.message_id)
                for x in range(0, len(lyricsfr), 4096):
                    bot.send_message(chat_id=call.message.chat.id, text=lyricsfr[x:x+4096])
                long_markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text='About the song', callback_data='info_about'),
                                                    types.InlineKeyboardButton(text='Album tracklist', callback_data='info_album')],
                                                    [types.InlineKeyboardButton(text='Done', callback_data='long_done')]])
                bot.send_message(chat_id=call.message.chat.id, text="More stuff to see:\n\n", reply_markup=long_markup)
        
        if call.data == 'click_done':
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        
        if call.data == 'right':
            swap_count += 5
            markup = get_songs_markup(swap_count)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

        if call.data == 'left':
            swap_count -= 5
            markup = get_songs_markup(swap_count)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

        if call.data == 'ar_search':
            markup = get_songs_arabic(message_received.text)
            bot.edit_message_text('اختر الأغنية:', call.message.chat.id, call.message.message_id, reply_markup=markup)

        if call.data.startswith('ar_selected'):
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_chat_action(call.message.chat.id, action='typing')
            song_selected_ar = ''
            for key in list(songs_matched_arabic.keys()):
                if key.startswith(call.data.removeprefix('ar_selected')):
                    song_selected_ar = key
                    break

            photo, lyrics_ar = get_data_arabic(song_selected_ar)
            bot.send_photo(chat_id=call.message.chat.id, photo=photo)
            if len(lyrics_ar) > 4096:
                for x in range(0, len(lyrics_ar), 4096):
                    bot.send_message(chat_id=call.message.chat.id, text=lyrics_ar[x:x+4096])
            else:
                bot.send_message(chat_id=call.message.chat.id, text=lyrics_ar)

        if call.data == 'info_about':
            bot.send_chat_action(call.message.chat.id, action='typing')
            bot.send_message(chat_id=call.message.chat.id, text='About the song:\n' + get_about(songs_matched[song_selected][0]), reply_to_message_id=call.message.message_id)

        if call.data == 'info_album':
            global tracks
            bot.send_chat_action(call.message.chat.id, action='typing')
            album_text, tracks = get_album(songs_matched[song_selected][0])
            markup = types.InlineKeyboardMarkup()
            for track in tracks.keys():
                markup.row(types.InlineKeyboardButton(text= track,callback_data='album' +  track.split('-')[0]))
            markup.row(types.InlineKeyboardButton(text='Done',callback_data='click_done'))
            bot.send_photo(chat_id=call.message.chat.id, photo=songs_matched[song_selected][2], caption= album_text, reply_markup=markup, reply_to_message_id=call.message.message_id)
        
        if call.data == 'long_done':
            bot.delete_message(call.message.chat.id, call.message.message_id)
        
        if call.data.startswith('album'):
            tracks = tracks
            bot.send_chat_action(call.message.chat.id, action='typing')
            album_song_selected = ''
            for key in list(tracks.keys()):
                if key.startswith(call.data.removeprefix('album')):
                    album_song_selected = key
                    break
            lyrics = get_lyrics(tracks[album_song_selected])
            lyrics_alb = album_song_selected + ' | Lyrics:\n\n' + lyrics
            if len(lyrics_alb) > 4096:
                for x in range(0, len(lyrics_alb), 4096):
                    bot.send_message(chat_id=call.message.chat.id, text=lyrics_alb[x:x+4096], reply_to_message_id=call.message.message_id)
            else:
                bot.send_message(chat_id=call.message.chat.id, text=lyrics_alb, reply_to_message_id=call.message.message_id)

        if call.data == 'info_translation':
            en_btn = types.InlineKeyboardButton(text='Translate to English', callback_data='English')
            ar_btn = types.InlineKeyboardButton(text='Translate to Arabic', callback_data='Arabic')
            fr_btn = types.InlineKeyboardButton(text='Translate to French', callback_data='French')
            es_btn = types.InlineKeyboardButton(text='Translate to Spanish', callback_data='Spanish')
            back_btn = types.InlineKeyboardButton(text='Go back', callback_data='go_back')
            markup = types.InlineKeyboardMarkup([[en_btn, ar_btn], [fr_btn, es_btn], [back_btn]])
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

        if call.data == 'English':
            bot.send_chat_action(call.message.chat.id, action='typing')
            en = Translator().translate(lyricsfr, dest='en').text
            bot.send_message(chat_id=call.message.chat.id, text="English translation:\n\n" + en, reply_to_message_id=call.message.message_id)
        if call.data == 'Arabic':
            bot.send_chat_action(call.message.chat.id, action='typing')
            ar = Translator().translate(lyricsfr, dest='ar').text
            bot.send_message(chat_id=call.message.chat.id, text="Arabic translation:\n\n" + ar, reply_to_message_id=call.message.message_id)
        if call.data == 'French':
            bot.send_chat_action(call.message.chat.id, action='typing')
            fr = Translator().translate(lyricsfr, dest='fr').text
            bot.send_message(chat_id=call.message.chat.id, text="French translation:\n\n" + fr, reply_to_message_id=call.message.message_id)
        if call.data == 'Spanish':
            bot.send_chat_action(call.message.chat.id, action='typing')
            es = Translator().translate(lyricsfr, dest='es').text
            bot.send_message(chat_id=call.message.chat.id, text="Spanish translation:\n\n" + es, reply_to_message_id=call.message.message_id)
        if call.data == 'go_back':
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_info_markup())

print('Bot is running...')
while True:
    try:
        bot.infinity_polling()
    except:
        time.sleep(10)
