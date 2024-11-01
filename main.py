import os
import time
from telebot.async_telebot import AsyncTeleBot
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

headers_az = {
    'Cookie': os.environ.get('COOKIE'),
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    }

API_KEY = os.environ.get('API_KEY')
BASE_LYRIC = os.environ.get('BASE_LYRIC')
BASE_SONG = os.environ.get('BASE_SONG')
BASE_AR = os.environ.get('BASE_AR')
BASE_AZ = os.environ.get('BASE_AZ')
BASE_SONGTELL = os.environ.get('BASE_SONGTELL')
BASE_SONGTELL_GET = os.environ.get('BASE_SONGTELL_GET')
CHATID = os.environ.get('CHATID')


bot = AsyncTeleBot(API_KEY)

server()

async def get_songs(name, from_lyric):
    global songs_matched
    songs_matched = dict()
    counter = 1
    with requests.Session() as s:
        for page in range(1,7):
            if from_lyric:
                url = f'{BASE_LYRIC}{page}&q={name.strip()}'
            else: 
                url = f'{BASE_SONG}{page}&q={name.strip()}'
            r = s.get(url, headers=headers)
            if r.status_code == 200:
                parsed_json = json.loads(r.text)
                for hit in parsed_json['response']['sections'][0]['hits']:
                    #number: [full_title, link, photo, album_photo]
                    songs_matched[str(counter)] = [hit['result']['full_title'].replace('by', '-'),
                                        hit['result']['url'],
                                        hit['result']['song_art_image_url'],
                                        hit['result']['header_image_url']]
                    counter += 1
    markup = await get_songs_markup(0)
    return markup

async def get_songs_markup(current_index):
    markup = types.InlineKeyboardMarkup()
    for key in list(songs_matched.keys())[current_index:current_index+5]:
        markup.row(types.InlineKeyboardButton(text=songs_matched[key][0],callback_data='selected' + key))
    if len(songs_matched.keys()) > 5 and current_index < 5:
        markup.row(types.InlineKeyboardButton(text='➡️', callback_data='right'))
    elif current_index >= 5 and current_index <= len(songs_matched.keys()) - current_index:
        markup.row(types.InlineKeyboardButton(text='⬅️', callback_data='left'), types.InlineKeyboardButton(text='➡️', callback_data='right'))
    elif len(songs_matched.keys()) != 0 and current_index >= 5:
        markup.row(types.InlineKeyboardButton(text='⬅️', callback_data='left'))
    if len(songs_matched.keys()) == 0:
        markup.row(types.InlineKeyboardButton(text='No results found', callback_data='ignore')) 
    markup.row(types.InlineKeyboardButton(text='Genius ✅', callback_data='genius_search'),
                types.InlineKeyboardButton(text='AZLyrics ☑️', callback_data='az_search'),
                types.InlineKeyboardButton(text='أنغامي ☑️', callback_data='ar_search'))
    markup.row(types.InlineKeyboardButton(text='Songtell ☑️ (For songs meanings!)', callback_data='st_search'))
    markup.row(types.InlineKeyboardButton(text='Close', callback_data='result_no'))
    return markup

async def get_lyrics(link):
    r_lyrics = requests.get(link, headers=headers)
    soup_lyrics = bs(r_lyrics.content, features='lxml')
    try:
        lyrics_raw = soup_lyrics.find("div", class_=re.compile("^lyrics$|Lyrics__Root"))
        lyrics_raw.find("div", class_=re.compile("^LyricsHeader")).decompose()
        lyrics_raw.find("div", class_=re.compile("^LyricsFooter__Container")).decompose()
        lyrics_raw.find("div", class_=re.compile("^RightSidebar__Container")).decompose()
    except AttributeError:
        pass
    if lyrics_raw == None:
        lyrics_raw = soup_lyrics.find('div', class_=re.compile("^LyricsPlaceholder__Message"))
    lyrics_fixed = str(lyrics_raw).replace('<br/>', '\n')
    convert = bs(lyrics_fixed, features='lxml')
    lyrics = convert.text
    return lyrics

async def get_info_markup():
    markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text='About the song', callback_data='info_about'),
                                                    types.InlineKeyboardButton(text='Album tracklist', callback_data='info_album'),
                                                    types.InlineKeyboardButton(text='Translation (beta)', callback_data='info_translation')],
                                                    [types.InlineKeyboardButton(text='Done', callback_data='click_done')]])
    return markup

async def get_about(link):
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

async def get_album(link):
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
                for i, li in enumerate(soup_album.find_all('li', class_=re.compile("^AlbumTracklist__Track"))):
                    x = li.get_text()
                    if re.search("\d", x) == None:
                        li.decompose()
                    if li.div.a != None:
                        #Number : [name, link]
                        tracks[str(i)] = [li.div.get_text(), li.div.a['href']]
                    else:
                        tracks[str(i)] = [li.div.get_text(), link]
        except AttributeError:
            pass
        return album_name, tracks 


async def get_songs_az(name):
    global songs_matched_az
    songs_matched_az = dict()
    counter = 1
    markup = types.InlineKeyboardMarkup()
    url = BASE_AZ + name.strip()
    r = requests.get(url, headers=headers_az)
    if r.status_code == 200:
        try:
            parsed_json = json.loads(r.text)
            for song in parsed_json['songs']:
                strip = song['autocomplete'].split('-')[0].strip().strip('\"')
                songs_matched_az[str(counter)] = [f"{strip} - {song['autocomplete'].split('-')[1].strip()}", song['url']]
                counter += 1
            for key in list(songs_matched_az.keys()):
                markup.row(types.InlineKeyboardButton(text=songs_matched_az[key][0], callback_data='az_selected' + key))
        except:
            pass
    if counter - 1 == 0:
        markup.row(types.InlineKeyboardButton(text='No results found', callback_data='ignore')) 
    markup.row(types.InlineKeyboardButton(text='Genius ☑️', callback_data='genius_search'),
                types.InlineKeyboardButton(text='AZLyrics ✅', callback_data='az_search'),
                types.InlineKeyboardButton(text='أنغامي ☑️', callback_data='ar_search'))
    markup.row(types.InlineKeyboardButton(text='Songtell ☑️ (For songs meanings!)', callback_data='st_search'))
    markup.row(types.InlineKeyboardButton(text='Close', callback_data='result_no'))
    return markup

async def get_data_az(song_selected_az):
    lyrics_url = (songs_matched_az[song_selected_az][1])
    r = requests.get(lyrics_url, headers=headers_az)
    global tracks_az
    tracks_az = dict()
    counter = 1
    if r.status_code == 200:
        soup_az = bs(r.content, 'lxml')
        lyrics = songs_matched_az[song_selected_az][0].split('-')[0].strip() + ' | Lyrics:\n\n' + soup_az.find('div', class_=None, id=None).text.strip()
        photo_url = f"https://www.azlyrics.com/{soup_az.find('img', class_='album-image')['src']}"
        album_panel = soup_az.find('div', class_='panel songlist-panel noprint')
        tracks_in_az = album_panel.findAll('div', class_='listalbum-item')
        for track in tracks_in_az:
            try: 
                tracks_az[counter] = [track.a.text, f"https://www.azlyrics.com/{track.a['href']}"]
                counter+=1
            except AttributeError:
                comment = track.find('div', class_='comment').text
                track.find('div', class_='comment').decompose()
                tracks_az[counter] = [track.text, comment]
                counter+=1
    return photo_url, lyrics

async def get_songs_arabic(name):
    global songs_matched_arabic
    songs_matched_arabic = dict()
    counter = 1
    markup = types.InlineKeyboardMarkup()
    url = BASE_AR + name.strip()
    r = requests.post(url, headers=headers_ar)
    if r.status_code == 200:
        parsed_json = json.loads(r.text)
        for song in parsed_json['sections'][0]['data']:
            if 'lyrics' in song and 'languageid' in song:
                if song['lyrics'] == 1 and song['languageid'] == 1:
                    songs_matched_arabic[str(counter)] = [song['id'],  song['coverArt'], song['title'] + ' - ' + song['artist']]
                    counter += 1
        for key in list(songs_matched_arabic.keys()):
            markup.row(types.InlineKeyboardButton(text=songs_matched_arabic[key][2], callback_data='ar_selected' + key))
    if counter - 1 == 0:
        markup.row(types.InlineKeyboardButton(text='لم يتم العثور على نتائج', callback_data='ignore')) 
    markup.row(types.InlineKeyboardButton(text='Genius ☑️', callback_data='genius_search'),
                types.InlineKeyboardButton(text='AZLyrics ☑️', callback_data='az_search'),
                types.InlineKeyboardButton(text='أنغامي ✅', callback_data='ar_search'))
    markup.row(types.InlineKeyboardButton(text='Songtell ☑️ (For songs meanings!)', callback_data='st_search'))
    markup.row(types.InlineKeyboardButton(text='إغلاق', callback_data='result_no'))
    return markup

async def get_data_arabic(song_selected_ar):
    photo_url = 'https://angartwork.anghcdn.co/?id=' + str(songs_matched_arabic[song_selected_ar][1])
    lyrics_url = 'https://kalimat.anghami.com/lyrics/' + str(songs_matched_arabic[song_selected_ar][0])
    r = requests.get(lyrics_url, headers=headers)
    if r.status_code == 200:
        soup_ar = bs(r.content, 'lxml')
        try:
            lyrics = songs_matched_arabic[song_selected_ar][2].split('-')[0].strip() + ' | كلمات:\n\n' + soup_ar.find('pre', class_=re.compile("^lyrics-body")).text
        except AttributeError:
            lyrics = songs_matched_arabic[song_selected_ar][2].split('-')[0].strip() + ' | كلمات:\n\n' + soup_ar.find('h4', class_=re.compile("^error-page")).text
        return photo_url, lyrics

async def get_songs_st(name):
    global songs_matched_st
    songs_matched_st = dict()
    counter = 1
    markup = types.InlineKeyboardMarkup()
    url = BASE_SONGTELL + name.strip()
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        try:
            parsed_json = json.loads(r.text)
            for song in parsed_json['pageProps']['searchResults']:
                title = song['full_title'].replace('by', '-').strip()
                songs_matched_st[str(counter)] = [title, song['artist_names'], song['title'], song['id'], song['url']]
                counter += 1
            for key in list(songs_matched_st.keys()):
                markup.row(types.InlineKeyboardButton(text=songs_matched_st[key][0], callback_data='st_selected' + key))
        except:
            pass
    if counter - 1 == 0:
        markup.row(types.InlineKeyboardButton(text='No results found', callback_data='ignore')) 
    markup.row(types.InlineKeyboardButton(text='Genius ☑️', callback_data='genius_search'),
                types.InlineKeyboardButton(text='AZLyrics ☑️', callback_data='az_search'),
                types.InlineKeyboardButton(text='أنغامي ☑️', callback_data='ar_search'))
    markup.row(types.InlineKeyboardButton(text='Songtell ✅ (For songs meanings!)', callback_data='st_search'))
    markup.row(types.InlineKeyboardButton(text='Close', callback_data='result_no'))
    return markup
    
async def get_data_st(song_selected_st):
    url = 'https://www.songtell.com/api/has-meaning'
    payload = {
        'artist_name': songs_matched_st[song_selected_st][1],
        'song_name': songs_matched_st[song_selected_st][2],
        'language': 'en'
    }
    r = requests.get(url, params=payload, headers=headers)
    if r.status_code == 200:
        parsed_json = json.loads(r.text)
        if parsed_json['success'] == True:
            artist_slug = parsed_json['artist_slug'].strip()
            song_slug = parsed_json['song_slug'].strip()
            rq = requests.get(f"{BASE_SONGTELL_GET}{artist_slug}/{song_slug}.json", headers=headers)
            if r.status_code == 200:
                parsed_json = json.loads(rq.text)
                meaning = songs_matched_st[song_selected_st][2] + ' | Meaning:\n\n' + parsed_json['pageProps']['meaning']
                return meaning
    else:
        url_req = 'https://hetzner.songtell.com/api/queue-meaning'
        payload_req = {
            'artist': songs_matched_st[song_selected_st][1],
            'title': songs_matched_st[song_selected_st][2],
            'genius_id': songs_matched_st[song_selected_st][3],
            'url': songs_matched_st[song_selected_st][4],
            'locale': 'en'
        }
        job = requests.get(url_req, params=payload_req, headers=headers)
        job_id = json.loads(job.text)['jobId']
        while True:
            job_check = requests.get(f"https://www.songtell.com/api/status?id={job_id}", headers=headers)
            job_checker = json.loads(job_check.text)[0]['status']
            if job_checker == 'pending':
                time.sleep(1)
            elif job_checker == 'failed':  
                return 'Sorry, couldn\'t find data.'
            elif job_checker == 'completed':
                return await get_data_st(song_selected_st)      
    
    
async def chat(message):
    userId = message.chat.id
    nameUser = str(message.chat.first_name) + ' ' + str(message.chat.last_name)
    username = message.chat.username
    text = message.text
    date = datetime.now()
    data = f'User id: {userId}\nUsername: @{username}\nName: {nameUser}\nText: {text}\nDate: {date}'
    await bot.send_message(chat_id=CHATID, text=data)

@bot.message_handler(commands=['start'])
async def start(message):
    await bot.send_chat_action(message.chat.id, action='typing')
    smsg = "Lyricism is UP!\nSend me a song name and I will get its lyrics for you <3\n(You can send with artist name for more accuracy)."
    await bot.reply_to(message, smsg)
    await chat(message)

@bot.message_handler(commands=['contact'])
async def contact(message):
    await bot.send_chat_action(message.chat.id, action='typing')
    smsg = "Contact bot creator to report a bug or suggest a feature:\n@TheAtef\nhttps://t.me/TheAtef"
    await bot.reply_to(message, smsg, disable_web_page_preview=True)
    await chat(message)

@bot.message_handler(commands=['donate'])
async def donate(message):
    await bot.send_chat_action(message.chat.id, action='typing')
    smsg = "Thanks for consedring donating!\nHere is my Buy Me a Coffee link:\nhttps://www.buymeacoffee.com/TheAtef"
    await bot.reply_to(message, smsg, disable_web_page_preview=True)
    await chat(message)

@bot.message_handler(commands=['from_lyric'])
async def from_lyric(message):
    await chat(message)
    await bot.send_chat_action(message.chat.id, action='typing')
    if message.text == "/from_lyric":
        smsg = "Write the command with the lyrics you remember to find the song.\nExample:\n/from_lyric yesterday I woke up sucking a lemon"
        await bot.reply_to(message, smsg)
    else:
        global message_received
        message_received = message
        await bot.send_message(message.chat.id, 'Choose your song:', reply_markup= await get_songs(message.text.removeprefix('/from_lyric '), True), reply_to_message_id=message.message_id)

@bot.message_handler(commands=['lrc'])
async def lrc(message):
    await chat(message)
    await bot.send_chat_action(message.chat.id, action='typing')
    if message.text == "/lrc":
        smsg = "Write the command with the name of the song which you want the .lrc file for.\nExample:\n/lrc exit music"
        await bot.reply_to(message, smsg)
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
        await bot.send_message(message.chat.id, "Choose your song: ", reply_to_message_id= message.message_id, reply_markup=markup)
    await chat(message)

@bot.message_handler(commands=None)
async def reply(message):
    global message_received
    message_received = message
    await bot.send_chat_action(message.chat.id, action='typing')
    await bot.send_message(message.chat.id, 'Choose your song:', reply_markup= await get_songs(message.text, False), reply_to_message_id=message.message_id)
    await chat(message)

swap_count = 0
@bot.callback_query_handler(func=lambda call: True)
async def callback_data(call):
    global swap_count
    global lyricsfr
    global song_selected
    
    if call.message:
        if call.data == 'ignore':
            await bot.answer_callback_query(callback_query_id=call.id, text="No results found")

        if call.data == 'result_no':
            await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            await bot.delete_message(chat_id=call.message.chat.id, message_id=message_received.message_id)

        if call.data.startswith('lrc'):
            result = lrc_files[int(call.data.removeprefix('lrc'))]
            result.fetch()
            lrc_name = result.title.split("LRC", 1)[0] + ".lrc"
            with open(lrc_name, "w", encoding="utf-8") as f:
                f.write(result.lyrics)
            await bot.send_chat_action(call.message.chat.id, "upload_document")
            await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            await bot.send_document(call.message.chat.id, open(lrc_name, 'rb'), message_received.message_id)

        if call.data.startswith('selected'):
            await bot.send_chat_action(call.message.chat.id, action='typing')
            await bot.delete_message(call.message.chat.id, call.message.message_id)
            song_selected = call.data.removeprefix('selected')
            lyrics = await get_lyrics(songs_matched[song_selected][1])
            lyricsfr = songs_matched[song_selected][0].split('-')[0].strip() + ' | Lyrics:\n\n' + lyrics
            if len(lyricsfr) <= 1024:
                await bot.send_photo(call.message.chat.id, songs_matched[song_selected][2], caption=lyricsfr, reply_markup= await get_info_markup(), reply_to_message_id=message_received.message_id)
            elif len(lyricsfr) > 1024 and len(lyricsfr) <= 4096:
                await bot.send_photo(call.message.chat.id, songs_matched[song_selected][2], reply_to_message_id=message_received.message_id)
                await bot.send_message(call.message.chat.id, lyricsfr, reply_markup= await  get_info_markup())
            elif len(lyricsfr) > 4096:
                await bot.send_photo(call.message.chat.id, songs_matched[song_selected][2], reply_to_message_id=message_received.message_id)
                for x in range(0, len(lyricsfr), 4096):
                    await bot.send_message(chat_id=call.message.chat.id, text=lyricsfr[x:x+4096])
                long_markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text='About the song', callback_data='info_about'),
                                                    types.InlineKeyboardButton(text='Album tracklist', callback_data='info_album')],
                                                    [types.InlineKeyboardButton(text='Done', callback_data='long_done')]])
                await bot.send_message(chat_id=call.message.chat.id, text="More stuff to see:\n\n", reply_markup=long_markup)
        
        if call.data == 'click_done':
            await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        
        if call.data == 'right':
            swap_count += 5
            markup = await get_songs_markup(swap_count)
            await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

        if call.data == 'left':
            swap_count -= 5
            markup = await get_songs_markup(swap_count)
            await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

        if call.data == 'genius_search':
            markup = await get_songs(message_received.text, False)
            await bot.edit_message_text('Choose your song:', call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        if call.data == 'az_search':
            markup = await get_songs_az(message_received.text)
            await bot.edit_message_text('Choose your song:', call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        if call.data == 'ar_search':
            markup = await get_songs_arabic(message_received.text)
            await bot.edit_message_text('اختر الأغنية:', call.message.chat.id, call.message.message_id, reply_markup=markup)

        if call.data == 'st_search':
            markup = await get_songs_st(message_received.text)
            await bot.edit_message_text('Choose your song:', call.message.chat.id, call.message.message_id, reply_markup=markup)
            
        if call.data.startswith('ar_selected'):
            await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            await bot.send_chat_action(call.message.chat.id, action='typing')
            song_selected_ar = call.data.removeprefix('ar_selected')
            photo, lyrics_ar = await get_data_arabic(song_selected_ar)
            if len(lyrics_ar) <= 1024:
                await bot.send_photo(call.message.chat.id, photo, caption=lyrics_ar, reply_to_message_id=message_received.message_id)
            elif len(lyrics_ar) > 1024 and len(lyrics_ar) <= 4096:
                await bot.send_photo(call.message.chat.id, photo, reply_to_message_id=message_received.message_id)
                await bot.send_message(call.message.chat.id, lyrics_ar)
            elif len(lyrics_ar) > 4096:
                await bot.send_photo(call.message.chat.id, photo, reply_to_message_id=message_received.message_id)
                for x in range(0, len(lyrics_ar), 4096):
                    await bot.send_message(chat_id=call.message.chat.id, text=lyrics_ar[x:x+4096])
                    
        if call.data.startswith('st_selected'):
            await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            await bot.send_chat_action(call.message.chat.id, action='typing')
            song_selected_st = call.data.removeprefix('st_selected')
            meaning = await get_data_st(song_selected_st)
            if len(meaning) <= 4096:
                await bot.send_message(call.message.chat.id, text=meaning, reply_to_message_id=message_received.message_id)
            elif len(meaning) > 4096:
                for x in range(0, len(meaning), 4096):
                    await bot.send_message(chat_id=call.message.chat.id, text=meaning[x:x+4096])
        
        if call.data.startswith('az_selected'):
            await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            await bot.send_chat_action(call.message.chat.id, action='typing')
            song_selected_az = call.data.removeprefix('az_selected')
            photo, lyrics_az = await get_data_az(song_selected_az)
            markup_az = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text='Album tracklist', callback_data='info_album_az')],
                                                    [types.InlineKeyboardButton(text='Done', callback_data='click_done')]])
            if len(lyrics_az) <= 1024:
                await bot.send_photo(call.message.chat.id, photo, caption=lyrics_az, reply_markup=markup_az, reply_to_message_id=message_received.message_id)
            elif len(lyrics_az) > 1024 and len(lyrics_az) <= 4096:
                await bot.send_photo(call.message.chat.id, photo, reply_to_message_id=message_received.message_id)
                await bot.send_message(call.message.chat.id, lyrics_az, reply_markup=markup_az)
            elif len(lyrics_az) > 4096:
                await bot.send_photo(call.message.chat.id, photo, reply_to_message_id=message_received.message_id)
                for x in range(0, len(lyrics_az), 4096):
                    await bot.send_message(chat_id=call.message.chat.id, text=lyrics_az[x:x+4096])
                long_markup_az = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text='Album tracklist', callback_data='info_album_az')],
                                                    [types.InlineKeyboardButton(text='Done', callback_data='long_done')]])
                await bot.send_message(chat_id=call.message.chat.id, text="More stuff to see:\n\n", reply_markup=long_markup_az)
            

        if call.data == 'info_about':
            await bot.send_chat_action(call.message.chat.id, action='typing')
            await bot.send_message(chat_id=call.message.chat.id, text='About the song:\n' + await get_about(songs_matched[song_selected][1]), reply_to_message_id=call.message.message_id)

        if call.data == 'info_album':
            global tracks
            await bot.send_chat_action(call.message.chat.id, action='typing')
            album_text, tracks = await get_album(songs_matched[song_selected][1])
            markup = types.InlineKeyboardMarkup()
            for track in tracks.keys():
                markup.row(types.InlineKeyboardButton(text= tracks[track][0], callback_data='album' + track))
            markup.row(types.InlineKeyboardButton(text='Done', callback_data='click_done'))
            await bot.send_photo(chat_id=call.message.chat.id, photo=songs_matched[song_selected][3], caption= album_text, reply_markup=markup, reply_to_message_id=call.message.message_id)
        
        if call.data == 'info_album_az':
            album_markup_az = types.InlineKeyboardMarkup()
            for key in list(tracks_az.keys()):
                album_markup_az.row(types.InlineKeyboardButton(text=tracks_az[key][0],callback_data='az_album' + str(key)))
            album_markup_az.row(types.InlineKeyboardButton(text='Done',callback_data='click_done'))
            await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=album_markup_az)
            
        if call.data.startswith('az_album'):
            await bot.send_chat_action(call.message.chat.id, action='typing')
            album_az_selected = int(call.data.removeprefix('az_album'))
            if tracks_az[album_az_selected][1].startswith('https'):
                r = requests.get(tracks_az[album_az_selected][1], headers=headers_az)
                if r.status_code == 200:
                    soup_az = bs(r.content, 'lxml')
                    lyrics_az = tracks_az[album_az_selected][0].split('-')[0].strip() + ' | Lyrics:\n\n' + soup_az.find('div', class_=None, id=None).text.strip()
                    if len(lyrics_az) > 4096:
                        for x in range(0, len(lyrics_az), 4096):
                            await bot.send_message(chat_id=call.message.chat.id, text=lyrics_az[x:x+4096], reply_to_message_id=call.message.message_id)
                    else:
                        await bot.send_message(chat_id=call.message.chat.id, text=lyrics_az, reply_to_message_id=call.message.message_id)
            else:
                lyrics_az = tracks_az[album_az_selected][0].split('-')[0].strip() + ' | Lyrics:\n\n' + tracks_az[album_az_selected][1].strip()
                await bot.send_message(chat_id=call.message.chat.id, text=lyrics_az, reply_to_message_id=call.message.message_id)
                
        if call.data == 'long_done':
            await bot.delete_message(call.message.chat.id, call.message.message_id)
        
        if call.data.startswith('album'):
            tracks = tracks
            await bot.send_chat_action(call.message.chat.id, action='typing')
            album_song_selected = call.data.removeprefix('album')
            lyrics = await get_lyrics(tracks[album_song_selected][1])
            lyrics_alb = tracks[album_song_selected][0] + ' | Lyrics:\n\n' + lyrics
            if len(lyrics_alb) > 4096:
                for x in range(0, len(lyrics_alb), 4096):
                    await bot.send_message(chat_id=call.message.chat.id, text=lyrics_alb[x:x+4096], reply_to_message_id=call.message.message_id)
            else:
                await bot.send_message(chat_id=call.message.chat.id, text=lyrics_alb, reply_to_message_id=call.message.message_id)

        if call.data == 'info_translation':
            en_btn = types.InlineKeyboardButton(text='Translate to English', callback_data='English')
            ar_btn = types.InlineKeyboardButton(text='Translate to Arabic', callback_data='Arabic')
            fr_btn = types.InlineKeyboardButton(text='Translate to French', callback_data='French')
            es_btn = types.InlineKeyboardButton(text='Translate to Spanish', callback_data='Spanish')
            back_btn = types.InlineKeyboardButton(text='Go back', callback_data='go_back')
            markup = types.InlineKeyboardMarkup([[en_btn, ar_btn], [fr_btn, es_btn], [back_btn]])
            await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

        if call.data == 'English':
            await bot.send_chat_action(call.message.chat.id, action='typing')
            en = Translator().translate(lyricsfr, dest='en').text
            await bot.send_message(chat_id=call.message.chat.id, text="English translation:\n\n" + en, reply_to_message_id=call.message.message_id)
        if call.data == 'Arabic':
            await bot.send_chat_action(call.message.chat.id, action='typing')
            ar = Translator().translate(lyricsfr, dest='ar').text
            await bot.send_message(chat_id=call.message.chat.id, text="Arabic translation:\n\n" + ar, reply_to_message_id=call.message.message_id)
        if call.data == 'French':
            await bot.send_chat_action(call.message.chat.id, action='typing')
            fr = Translator().translate(lyricsfr, dest='fr').text
            await bot.send_message(chat_id=call.message.chat.id, text="French translation:\n\n" + fr, reply_to_message_id=call.message.message_id)
        if call.data == 'Spanish':
            await bot.send_chat_action(call.message.chat.id, action='typing')
            es = Translator().translate(lyricsfr, dest='es').text
            await bot.send_message(chat_id=call.message.chat.id, text="Spanish translation:\n\n" + es, reply_to_message_id=call.message.message_id)
        if call.data == 'go_back':
            await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup= await get_info_markup())

print('Bot is running...')
import asyncio
while True:
    try:
        asyncio.run(bot.infinity_polling())
    except:
        asyncio.sleep(10)