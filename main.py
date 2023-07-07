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

def get_url(name, page):
    if "/from_lyric" in name:
        index = 2
        url = BASE_LYRIC + name.replace("/from_lyric ", "").replace(" ", "%20")
        if page == 2:
            url = url.replace("page=1", "page=2")
    else:
        index = 1
        url = BASE_SONG + name.replace(" ", "%20")
        if page == 2:
            url = url.replace("page=1", "page=2")
    return url, index

def get_url_ar(name_ar):
    url_ar = BASE_AR + name_ar
    return url_ar

def first_page(name, page):
    url, index = get_url(name, page)
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        soup = bs(r.content, features='html.parser')
        data = soup.text
        parsed_json = json.loads(data)
        global searchq, links, photos, results_counter, album_photos
        searchq, links, photos, album_photos = ([] for i in range(4))
        results_counter = len(parsed_json['response']['sections'][0]['hits'])
        for x in range(results_counter):
            link = parsed_json['response']['sections'][0]['hits'][x]['result']['url']
            info = parsed_json['response']['sections'][0]['hits'][x]['result']['full_title'].replace('by', '-')
            photo = parsed_json['response']['sections'][0]['hits'][x]['result']['song_art_image_url']
            album_photo = parsed_json['response']['sections'][0]['hits'][x]['result']['header_image_url']
            links.append(link)
            searchq.append(info)
            photos.append(photo)
            album_photos.append(album_photo)
        
        #Serch kb:
        markup = types.InlineKeyboardMarkup()
        more = types.InlineKeyboardButton(text='➡️', callback_data='more')
        less = types.InlineKeyboardButton(text='⬅️', callback_data='less')
        ar_button = types.InlineKeyboardButton(text='ابحث عن أغانٍ عربية', callback_data='ar_result')
        close_button = types.InlineKeyboardButton(text='Close', callback_data='result_no')
        if index == 1:
            nmarkup = types.InlineKeyboardMarkup([[ar_button], [close_button]])
        elif index == 2:
            nmarkup = types.InlineKeyboardMarkup([[close_button]])
        count = 0
        for value in searchq:
            markup.add(types.InlineKeyboardButton(text=value,callback_data='result'+str(count)))
            count += 1
        if results_counter == 10:
            if page == 1 or page == 0:
                markup.add(more)
        if page == 2:
            markup.add(less)
        if index == 1 and page != 2:
            markup.add(ar_button)
        markup.add(close_button)

    else:
        return "Sorry, server error :)"
    
    return markup, nmarkup

def get_lyrics(link):
    r_lyrics = requests.get(link, headers=headers)
    soup_lyrics = bs(r_lyrics.content, features='html.parser')
    try:
        lyrics_raw = soup_lyrics.find("div", class_=re.compile("^lyrics$|Lyrics__Root"))
        lyrics_raw.find("div", class_=re.compile("^LyricsHeader")).decompose()
        lyrics_raw.find("div", class_=re.compile("^Lyrics__Footer")).decompose()
        try:
            lyrics_raw.find("div", class_=re.compile("^RightSidebar__Container")).decompose()
        except:
            pass
    except:
        if lyrics_raw == None:
            lyrics_raw = soup_lyrics.find('div', class_=re.compile("^LyricsPlaceholder__Message"))
    lyrics_fixed = str(lyrics_raw).replace('<br/>', '\n')
    convert = bs(lyrics_fixed, features='html.parser')
    lyrics = convert.text

    return lyrics

def get_about(link):
    r_about = requests.get(link, headers=headers)
    soup_about = bs(r_about.content, features='html.parser')
    try:
        about = soup_about.find('div', class_= re.compile("^SongDescription__Content")).get_text()
        if about == None:
            about = 'Sorry, couldn\'t find data.'
    except:
        about = 'Sorry, couldn\'t find data.'
    
    return about

def get_album(link):
    global n,y
    n=[]
    y=[]
    r_album = requests.get(link, headers=headers)
    soup_album = bs(r_album.content, features='html.parser')
    try:
        album_name = soup_album.find('a', class_=re.compile("^PrimaryAlbum__Title")).get_text()
        album = soup_album.find('ol', class_= re.compile("^AlbumTracklist__Container"))
        if album == None:
            album = 'Sorry, couldn\'t find data.'
        else:
            for li in soup_album.find_all('li', class_=re.compile("^AlbumTracklist__Track")):
                x = li.get_text()
                if re.search("\d", x) == None:
                    li.decompose()
                if li.div.a != None:
                    n.append(li.div.get_text())
                    y.append(li.div.a['href'])
                else:
                    n.append(li.div.get_text())
                    y.append(link)
            
            album_text = album_name
    except:
        album_text = 'Sorry, couldn\'t find data.'
    album_kb = types.InlineKeyboardMarkup()
    for track in n:
        c = re.split("\s", track)[0][:-1]
        album_kb.row(types.InlineKeyboardButton(text=str(track),callback_data='album'+str(c)))
    album_kb.row(types.InlineKeyboardButton(text='Done',callback_data='done_album'))

    return album_text, album_kb

def AR(url_ar):
    r_ar = requests.post(url_ar, headers=headers_ar)
    data_ar = r_ar.text
    parsed_json_ar = json.loads(data_ar)
    global ar_counter
    ar_counter = parsed_json_ar['sections'][0]['count']
    if ar_counter <= 5 and ar_counter != 0:
        ar_counter = ar_counter-1
    if ar_counter > 5:
        ar_counter = 0
        for x in range(5):
            try:
                if parsed_json_ar['sections'][0]['data'][x]['arabictext'] == 1:
                    ar_counter += 1
            except:
                pass
        if ar_counter != 0:
            ar_counter -= 1
        
    global songIds, infos_ar, picIds
    songIds, infos_ar, picIds= ([] for i in range(3))
    if ar_counter != 0:
        for x in range(ar_counter+1):
            try:
                if parsed_json_ar['sections'][0]['data'][x]['is_podcast'] == 1:
                    pass
            except:
                try:
                    if parsed_json_ar['sections'][0]['data'][x]['arabictext'] == 1:
                        songId = parsed_json_ar['sections'][0]['data'][x]['id']
                        artist = parsed_json_ar['sections'][0]['data'][x]['artist']
                        title = parsed_json_ar['sections'][0]['data'][x]['title']
                        picId = parsed_json_ar['sections'][0]['data'][x]['coverArt']
                        songIds.append(songId)
                        infos_ar.append(title + ' - ' + artist)
                        picIds.append(picId)
                except:
                    pass
    else:
        pass

def AR1(sId, pId, infos):
    pic_url = 'https://angartwork.anghcdn.co/?id=' + pId
    lyrics_url = 'https://kalimat.anghami.com/lyrics/' + sId
    ar_lyrics_req = requests.get(lyrics_url, headers=headers)
    soup_ar = bs(ar_lyrics_req.content, 'html.parser')
    try:
        ar_lryics = infos + ' | كلمات:\n\n' + soup_ar.find('pre', class_=re.compile("^lyrics-body")).text
    except:
        ar_lryics = infos + ' | كلمات:\n\n' + soup_ar.find('h4', class_=re.compile("^error-page")).text
    return ar_lryics, pic_url


def tbot():
    def chat(message):
        userId = message.chat.id
        nameUser = str(message.chat.first_name) + ' ' + str(message.chat.last_name)
        username = message.chat.username
        text = message.text
        date = datetime.now()
        data = f'User id: {userId}\nUsermae: @{username}\nName: {nameUser}\nText: {text}\nDate: {date}'
        bot.send_message(chat_id=CHATID, text=data)

    @bot.message_handler(commands=['start'])
    def start(message):
        bot.send_chat_action(message.chat.id, action='typing')
        smsg = "Lyricism is UP!\nSend me the name of a song and I will get its lyrics for you <3\n(You can send with artist name for more accuarcy)."
        bot.reply_to(message, smsg)
        
        
    @bot.message_handler(commands=['contact'])
    def contact(message):
        bot.send_chat_action(message.chat.id, action='typing')
        smsg = "Contact bot creator to report a bug or suggest a feature:\n@TheAtef\nhttps://t.me/TheAtef"
        bot.reply_to(message, smsg, disable_web_page_preview=True)

    @bot.message_handler(commands=['donate'])
    def donate(message):
        bot.send_chat_action(message.chat.id, action='typing')
        smsg = "Thanks for consedring donating!\nHere is my Buy Me a Coffee link:\nhttps://www.buymeacoffee.com/TheAtef"
        bot.reply_to(message, smsg, disable_web_page_preview=True)

    @bot.message_handler(commands=['from_lyric'])
    def from_lyric(message):
        bot.send_chat_action(message.chat.id, action='typing')
        if message.text == "/from_lyric":
            smsg = "Write the command with the lyrics you remember to find the song.\nExample:\n/from_lyric yesterday I woke up sucking a lemon"
            bot.reply_to(message, smsg)
        else:
            reply(message)

    @bot.message_handler(commands=['lrc'])
    def lrc(message):
        bot.send_chat_action(message.chat.id, action='typing')
        if message.text == "/lrc":
            smsg = "Write the command with the name of the song which you want the .lrc file.\nExample:\n/lrc exit music"
            bot.reply_to(message, smsg)
        else:
            global m_lrc
            global results
            m_lrc = message
            que = message.text.replace("/lrc ", "")
            ly = Lyricy()
            results = ly.search(que)
            lrc_markup = types.InlineKeyboardMarkup()
            count = 0
            for x in range(len(results)):
                tit = results[x].title
                titless = tit.split("LRC", 1)[0]
                if titless == " No result found":
                    break
                lrc_markup.add(types.InlineKeyboardButton(text=titless,callback_data='lrc'+str(count)))
                count += 1
            lrc_markup.add(types.InlineKeyboardButton(text='Close', callback_data='close_lrc'))
            if count == 0:
                bot.send_message(message.chat.id, "Sorry, no result found.", reply_to_message_id= message.message_id, reply_markup=lrc_markup)
            else:
                bot.send_message(message.chat.id, "Choose your song: ", reply_to_message_id= message.message_id, reply_markup=lrc_markup)
        chat(message)

    @bot.message_handler(commands=None)
    def reply(message, page=1):
        global m
        m = message
        if page == 1:
            bot.send_chat_action(message.chat.id, action='typing')
        global name
        name = message.text
        global name_ar
        name_ar = message.text
        markup, nmarkup = first_page(name, page)

        #Sending searchq:
        if results_counter != 0:
            if page == 1:
                global rep
                rep = bot.reply_to(message, 'Choose your song:', reply_markup=markup)
            elif page == 2 or page == 0:
                bot.edit_message_reply_markup(message.chat.id, rep.message_id, reply_markup=markup)
        else:
            bot.reply_to(message, 'Sorry, no matches.', reply_markup=nmarkup)
        
        #Sending data:
        if page == 1:
            chat(message)

    @bot.callback_query_handler(func=lambda call: True)
    def callback_data(call):
        global call_num
        if call.message:
            if call.data == 'result_no':
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                bot.delete_message(chat_id=call.message.chat.id, message_id=m.message_id)

            if call.data == 'close_lrc':
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                bot.delete_message(chat_id=call.message.chat.id, message_id=m_lrc.message_id)

            lrc_data = call.data[3:]
            if call.data == 'lrc' + lrc_data:
                slc = results[int(lrc_data)]
                slc.fetch()
                lrc_name = slc.title.split("LRC", 1)[0] + ".lrc"
                with open(lrc_name, "w", encoding="utf-8") as f:
                    f.write(slc.lyrics)
                bot.send_chat_action(call.message.chat.id, "upload_document")
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                bot.send_document(call.message.chat.id, open(lrc_name, 'rb'), m_lrc.message_id)


            call_data = call.data
            global lyricsfr
            if call.data == 'result' + call_data[-1]:
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                bot.delete_message(chat_id=call.message.chat.id, message_id=m.message_id)
                bot.send_chat_action(call.message.chat.id, action='typing')

                #More info kb:
                global keyboard
                button0 = types.InlineKeyboardButton(text='About the song', callback_data='click0')
                button1 = types.InlineKeyboardButton(text='Album tracklist', callback_data='click1')
                button2 = types.InlineKeyboardButton(text='Translation (beta)', callback_data='click2')
                button3 = types.InlineKeyboardButton(text='Done', callback_data='click_done')
                keyboard = types.InlineKeyboardMarkup([[button0, button1, button2], [button3]])
                long_keyboard = types.InlineKeyboardMarkup()
                long_keyboard.add(button0, button1, button3)

                call_num = int(call_data[-1])
                lyrics = get_lyrics(links[call_num])
                lyricsfr = searchq[call_num] + ' | Lyrics:\n\n' + lyrics
                bot.send_photo(chat_id=call.message.chat.id, photo=photos[call_num])
                if len(lyricsfr) > 4096:
                    for x in range(0, len(lyricsfr), 4096):
                        bot.send_message(chat_id=call.message.chat.id, text=lyricsfr[x:x+4096])
                    bot.send_message(chat_id=call.message.chat.id, text="More stuff to see:\n\n", reply_markup=long_keyboard)
                else:
                    bot.send_message(chat_id=call.message.chat.id, text=lyricsfr, reply_markup=keyboard)

            if call.data == 'click_done':
                if len(lyricsfr) > 4096:
                    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                else:
                    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)

            if call.data == 'more':
                reply(m, 2)
            if call.data == 'less':
                reply(m, 0)

            if call.data == 'ar_result':
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                bot.send_chat_action(call.message.chat.id, action='typing')
                #Ar_search kb:
                AR(get_url_ar(name_ar))
                ar_markup = types.InlineKeyboardMarkup()
                if ar_counter == 0:
                    ar_markup.add(types.InlineKeyboardButton(text='إغلاق', callback_data='result_no'))
                    bot.send_message(chat_id=call.message.chat.id, text='.عذراً، لم يتم العثور على نتائج', reply_to_message_id=m.message_id, reply_markup=ar_markup)
                else:
                    counter = 0
                    for value in infos_ar:
                        ar_markup.add(types.InlineKeyboardButton(text=value,callback_data='ar_result'+str(counter)))
                        counter += 1
                    ar_markup.add(types.InlineKeyboardButton(text='إغلاق', callback_data='result_no'))
                    bot.send_message(chat_id=call.message.chat.id, text='اختر الأغنية:', reply_markup=ar_markup, reply_to_message_id=m.message_id)

            if call.data == 'ar_result' + call_data[-1]:
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                bot.delete_message(chat_id=call.message.chat.id, message_id=m.message_id)
                bot.send_chat_action(call.message.chat.id, action='typing')
                call_num_ar = int(call_data[-1])
                ar_lyrics, pic = AR1(songIds[call_num_ar], picIds[call_num_ar], infos_ar[call_num_ar])
                bot.send_photo(chat_id=call.message.chat.id, photo=pic)
                if len(ar_lyrics) > 4096:
                    for x in range(0, len(ar_lyrics), 4096):
                        bot.send_message(chat_id=call.message.chat.id, text=ar_lyrics[x:x+4096])
                else:
                    bot.send_message(chat_id=call.message.chat.id, text=ar_lyrics)

            if call.data == 'click0':
                bot.send_chat_action(call.message.chat.id, action='typing')
                bot.send_message(chat_id=call.message.chat.id, text='About the song:\n' + get_about(links[call_num]), reply_to_message_id=call.message.message_id)
            
            if call.data == 'click1':
                bot.send_chat_action(call.message.chat.id, action='typing')
                album_text, album_kb = get_album(links[call_num])
                bot.send_photo(chat_id=call.message.chat.id, photo=album_photos[call_num], caption= album_text, reply_markup=album_kb, reply_to_message_id=call.message.message_id)
            if call.data == 'done_album':
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id)
            if call.data == 'album' + call_data[5:]:
                bot.send_chat_action(call.message.chat.id, action='typing')
                a = int(call_data[5:]) - 1
                lyrics = get_lyrics(y[a])
                lyrics_alb = n[a] + ' | Lyrics:\n\n' + lyrics
                if len(lyrics_alb) > 4096:
                    for x in range(0, len(lyrics_alb), 4096):
                        bot.send_message(chat_id=call.message.chat.id, text=lyrics_alb[x:x+4096], reply_to_message_id=call.message.message_id)
                else:
                    bot.send_message(chat_id=call.message.chat.id, text=lyrics_alb, reply_to_message_id=call.message.message_id)

            if call.data == 'click2':
                global kb_tanslate
                button2_1 = types.InlineKeyboardButton(text='Translate to English', callback_data='click2_1')
                button2_2 = types.InlineKeyboardButton(text='Translate to Arabic', callback_data='click2_2')
                button2_3 = types.InlineKeyboardButton(text='Translate to French', callback_data='click2_3')
                button2_4 = types.InlineKeyboardButton(text='Translate to Spanish', callback_data='click2_4')
                button2_0 = types.InlineKeyboardButton(text='Go back', callback_data='click2_0')
                kb_tanslate = types.InlineKeyboardMarkup([[button2_1, button2_2], [button2_3, button2_4], [button2_0]])
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb_tanslate)
            translator = Translator()
            if call.data == 'click2_1':
                bot.send_chat_action(call.message.chat.id, action='typing')
                en = translator.translate(lyricsfr, dest='en').text
                bot.send_message(chat_id=call.message.chat.id, text="English translation:\n\n" + en)
            if call.data == 'click2_2':
                bot.send_chat_action(call.message.chat.id, action='typing')
                ar = translator.translate(lyricsfr, dest='ar').text
                bot.send_message(chat_id=call.message.chat.id, text="Arabic translation:\n\n" + ar)
            if call.data == 'click2_3':
                bot.send_chat_action(call.message.chat.id, action='typing')
                fr = translator.translate(lyricsfr, dest='fr').text
                bot.send_message(chat_id=call.message.chat.id, text="French translation:\n\n" + fr)
            if call.data == 'click2_4':
                bot.send_chat_action(call.message.chat.id, action='typing')
                es = translator.translate(lyricsfr, dest='es').text
                bot.send_message(chat_id=call.message.chat.id, text="Spanish translation:\n\n" + es)
            if call.data == 'click2_0':
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
    print('Bot is running...')
    while True:
        try:
            bot.infinity_polling()
        except Exception as ex:
            print("Error: !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(ex)
            time.sleep(10)
            bot.infinity_polling()

if __name__ == "__main__":
    tbot()
