import os
from flask import Flask, request
import logging
import json
import requests
import math
import random

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

cities = {
    'москва': ['213044/7a2492eb4d097ff2ccd5', '1030494/f16da10181a264efa0de'],
    'нью-йорк': ['1030494/27efce5abed41f6b82d4', '997614/09af94b94bb22d80b6b2'],
    'париж': ["997614/0a9e75a38c7cd21940b8", '965417/16aeee22583e485e468c']
}

sessionStorage = {}


def get_coordinates(city_name):
    try:
        # url, по которому доступно API Яндекс.Карт
        url = "https://geocode-maps.yandex.ru/1.x/"
        # параметры запроса
        params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            # город, координаты которого мы ищем
            'geocode': city_name,
            # формат ответа от сервера, в данном случае JSON
            'format': 'json'
        }
        # отправляем запрос
        response = requests.get(url, params)
        # получаем JSON ответа
        json = response.json()
        # получаем координаты города (там написаны долгота(longitude),
        # широта(latitude) через пробел).
        # Посмотреть подробное описание JSON-ответа можно
        # в документации по адресу
        # https://tech.yandex.ru/maps/geocoder/
        coordinates_str = json['response']['GeoObjectCollection'][
            'featureMember'][0]['GeoObject']['Point']['pos']
        # Превращаем string в список, так как точка -
        # это пара двух чисел - координат
        long, lat = map(float, coordinates_str.split())
        # Вернем ответ
        return long, lat
    except Exception as e:
        return e


def get_country(city_name):
    try:
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            'geocode': city_name,
            'format': 'json'
        }
        data = requests.get(url, params).json()
        print(data['response']['GeoObjectCollection']['featureMember'][0][
                  'GeoObject']['metaDataProperty']['GeocoderMetaData'][
                  'AddressDetails']['Country']['CountryName'])
        # все отличие тут, мы получаем имя страны
        return data['response']['GeoObjectCollection']['featureMember'][0][
            'GeoObject']['metaDataProperty']['GeocoderMetaData'][
            'AddressDetails']['Country']['CountryName']
    except Exception as e:
        return e


def get_distance(p1, p2):
    # p1 и p2 - это кортежи из двух элементов - координаты точек
    radius = 6373.0

    lon1 = math.radians(p1[0])
    lat1 = math.radians(p1[1])
    lon2 = math.radians(p2[0])
    lat2 = math.radians(p2[1])

    d_lon = lon2 - lon1
    d_lat = lat2 - lat1

    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(a ** 0.5, (1 - a) ** 0.5)

    distance = radius * c
    return distance


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)

    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    handle_dialog(response, request.json)

    logging.info('Request: %r', response)

    return json.dumps(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']

    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови свое имя!'
        sessionStorage[user_id] = {
            'first_name': None,
            'game_started': False
        }

        return

    first_name = get_first_name(req)

    if sessionStorage[user_id]['first_name'] is None:

        if first_name is None:
            res['response']['text'] = 'Не раслышала имя. Повтори!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['guessed_cities'] = []
            res['response']['text'] = 'Приятно познакомиться, ' + first_name.title() + '. Я Алиса. ' \
                                                                                       'Отгадаешь город по фото?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True

                },
                {
                    'title': 'Нет',
                    'hide': True

                },
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]

    else:

        if not sessionStorage[user_id]['game_started']:

            if 'да' in req['request']['nlu']['tokens']:

                if len(sessionStorage[user_id]['guessed_cities']) == 3:

                    res['response']['text'] = 'Ты отгадал все города!'
                    res['end_session'] = True

                else:

                    sessionStorage[user_id]['game_started'] = True
                    sessionStorage[user_id]['attempt'] = 1
                    play_game(res, req)

            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно!'
                res['end_session'] = True
            elif req['request']['original_utterance'].lower() == 'помощь':
                res['response']['text'] = 'удачи в игре, этот навык никому не нужен как в прочем-то и сама игра уже естьв оригинальной алисе...'
            else:
                res['response']['text'] = 'Не понял ответа! Так да или нет?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True

                    },
                    {
                        'title': 'Нет',
                        'hide': True

                    },
                    {
                        'title': 'Помощь',
                        'hide': True
                    }
                ]
        elif req['request']['original_utterance'].lower() == 'помощь':
            res['response']['text'] = 'Это текст помомщи. Будь смелее и продолжи общение.'
        else:

            play_game(res, req)


def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']

    if attempt == 1:

        city = list(cities.keys())[random.randint(0, 2)]

        while (city in sessionStorage[user_id]['guessed_cities']):
            city = list(cities.keys())[random.randint(0, 2)]

        sessionStorage[user_id]['city'] = city

        res['response']['card'] = {}
        res['response']['text'] = 'Тогда сыграем!'
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за город?'
        res['response']['card']['image_id'] = cities[city][attempt - 1]
        res['response']['buttons'] = [
            {
                'title': 'Помощь',
                'hide': True
            }
        ]
        return

    else:

        city = sessionStorage[user_id]['city']

        if get_city(req) == city:

            res['response']['text'] = 'Правильно! Сыграем еще?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True

                },
                {
                    'title': 'Нет',
                    'hide': True

                },
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
            sessionStorage[user_id]['guessed_cities'].append(city)
            sessionStorage[user_id]['game_started'] = False
            return

        else:

            res['response']['text'] = 'Неправильно'
            if attempt == 3:
                res['response']['text'] = 'Вы пытались. Это ' + city.title() + '. Сыграем еще?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True

                    },
                    {
                        'title': 'Нет',
                        'hide': True

                    },
                    {
                        'title': 'Помощь',
                        'hide': True
                    }
                ]
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['guessed_cities'].append(city)
                return
            else:
                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['title'] = 'Неправильно. Вот тебе дополнительное фото'
                res['response']['card']['image_id'] = cities[city][attempt - 1]
                res['response']['buttons'] = [
                    {
                        'title': 'Помощь',
                        'hide': True
                    }
                ]

    sessionStorage[user_id]['attempt'] += 1


def get_city(req):
    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.GEO':

            if 'city' in entity['value'].keys():
                return entity['value']['city']
            else:
                return None

    return None


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.FIO':

            if 'first_name' in entity['value'].keys():
                return entity['value']['first_name']
            else:
                return None
    return None


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
