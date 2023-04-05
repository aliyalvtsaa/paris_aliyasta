import requests
import json
import telebot
import random
import pandas as pd
import telebot
from telebot import types 
from pandas import json_normalize
import sys
import locale
from datetime import datetime, date, timedelta
pd.set_option('mode.chained_assignment', None)

#это большая функция, с помощью которой мы соберем информацию о дешевых билетах из указанного города
def get_cheap_tickets(city, time):
    #подключимся к апи, чтобы через него получать специальные коды городов
    response=requests.get('https://api.travelpayouts.com/data/ru/cities.json?_gl=1*y98zhy*_ga*MTM3NzY1NTU4Ni4xNjgwMzY2Njcz*_ga_1WLL0NEBEH*MTY4MDM2NjY3Mi4xLjEuMTY4MDM2ODAzNi41NC4wLjA.').json()
    сity_code=''
    status=''
    for i in range(len(response)):
        try:
            if response[i]['cases']['su']==city.title():
                сity_code=response[i]['code']
            if сity_code!='':
                break
        except:
            pass
    #подключимся к основному апи, заберем результат в виде json и создадим датафрейм 
    url = 'https://api.travelpayouts.com/aviasales/v3/prices_for_dates'
    params = {'origin': сity_code, 'limit': 1000, 'token': 'a45807ecda7030099b5ac0393908a2a3','unique':'true'}
    try:
        cheap_tickets=requests.get(url, params=params).json()
        cheap_tickets = json_normalize(cheap_tickets['data'])
        cheap_tickets['departure_at']= pd.to_datetime(cheap_tickets['departure_at'])
        #time - это время в днях с сегодняшнего дня, указанное пользователем. оставим только билеты, полет по которым состоится раньше этой даты
        for i in range(len(cheap_tickets)):
            if cheap_tickets['departure_at'][i].timestamp()>(datetime.now().timestamp()+int(time)*24*3600):
                cheap_tickets=cheap_tickets.drop(i)
        cheap_tickets.reset_index(inplace=True, drop=True)
        #и из 1000 запрошенных оставим только 10 самых дешевых значений (если после фильтрации 10 не наберется, то просто выведем датафрейм)
        cheap_tickets=cheap_tickets[:10]
        cheap_tickets=cheap_tickets.sort_values(by=['price'])
        
        #поставим русский язык, чтобы выводить дату
        locale.setlocale(
                locale.LC_ALL,
                'rus_rus' if sys.platform == 'win32' else 'ru_RU.UTF-8')
        for i in range(len(cheap_tickets)):
            cheap_tickets['departure_at'][i]=cheap_tickets['departure_at'][i].strftime("%-d %B в %H:%M")
        
        #теперь снова подключимся к апи с кодами, чтобы перевести код пункта прибытия в город
        for city_to in range(len(cheap_tickets)):
            for i in range(len(response)):
                try:
                    if response[i]['code']==cheap_tickets['destination'][city_to]:
                        cheap_tickets['destination'][city_to]=response[i]['cases']['vi']

                except:
                    pass

        messages=[]
        #соберем сообщение для каждого билета
        for i in range(len(cheap_tickets)):
            message=f'{cheap_tickets["destination"][i]} за {cheap_tickets["price"][i]} рублей! - {cheap_tickets["departure_at"][i]} \n https://www.aviasales.ru{cheap_tickets["link"][i]}'
            messages.append(message)
        text='Вы можете поехать\n'
        text+='\n'.join(messages)
    #если пользователь выбрал, например, "сегодня" но по апи билеты с сегодняшней датой не попали в вывод, напишем:
        if cheap_tickets.empty:
            status='В этом временном промежутке дешевые билеты не нашлись( Попробуйте выбрать больший промежуток'
            text=''
    #если не получилось подключиться к апи по этому городу, напишем:
    except:
        status='Город не нашелся('
        text=''
    return text,status

#подключимся к боту
bot = telebot.TeleBot("6140076958:AAFu7gI7y50xltfDPFv19KC3JP5LDmxbLC0", parse_mode=None)
dic1 = {'city': ''}

 


#сделаем кнопки для быстрого выбора города и приветственное сообщение
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Москва")
    btn2 = types.KeyboardButton("Санкт-Петербург")
    btn3 = types.KeyboardButton("Казань")
    markup.add(btn1,btn2,btn3)
    bot.send_message(message.chat.id, text="Привет, я бот, который находит самые дешевые билеты на самолет! Выберите город или введите свой⬇️⬇️⬇️".format(message.from_user), reply_markup=markup)

#создадим кнопки, прикрепленные к сообщению, чтобы пользователь мог выбрать временной промежуток
@bot.message_handler(content_types=['text'])
def start(message):
    #а название города, введенное в прошлом сообщении, сохраним в глобальный словарь
    global dic1
    dic1['city'] = message.text
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton('Сегодня',callback_data='0')
    item2 = types.InlineKeyboardButton('Завтра',callback_data='1')
    item3 = types.InlineKeyboardButton('Неделя',callback_data='7')
    item4 = types.InlineKeyboardButton('Две недели',callback_data = '14')
    item5 = types.InlineKeyboardButton('Месяц',callback_data = '30')
    item6 = types.InlineKeyboardButton('Два месяца',callback_data = '60')
    markup.add(item1, item2,item3,item4,item5,item6)
    bot.send_message(message.chat.id, text="В течение какого времени вы хотели бы отправиться?".format(message.from_user), reply_markup=markup)
    
    
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.message:
        text,status=get_cheap_tickets(dic1['city'], call.data)
        #если статус так и остался строкой, значит билеты удалось найти, выведем текст сообщения
        if status=='':
            bot.send_message(call.message.chat.id, text)
        #или скажем, что не смогли найти город - выведем статус    
        else:
            bot.send_message(call.message.chat.id, status)

            
#строка чтобы наш бот всегда работал:   
bot.infinity_polling()


    