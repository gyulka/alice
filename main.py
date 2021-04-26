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

def get_geo_info(city, type_info):
    url = "https://geocode-maps.yandex.ru/1.x/"

    params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        'geocode': city,
        'format': 'json'
    }

    response = requests.get(url, params)
    json = response.json()

    if type_info == 'coordinates':
        point_str = \
            json['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
        point_array = [float(x) for x in point_str.split(' ')]
        return point_array
    elif type_info == 'country':
        return \
            json['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty'][
                'GeocoderMetaData']['AddressDetails']['Country']['CountryName']



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
        res['response'][
            'text'] = 'Привет! Я могу сказать в какой стране город или сказать расстояние между городами!'

        return

    cities = get_cities(req)

    if len(cities) == 0:

        res['response']['text'] = 'Ты не написал название не одного города!'

    elif len(cities) == 1:

        res['response']['text'] = 'Этот город в стране - ' + get_geo_info(cities[0], 'country')

    elif len(cities) == 2:

        distance = get_distance(get_geo_info(cities[0], 'coordinates'),
                                get_geo_info(cities[1], 'coordinates'))
        res['response']['text'] = 'Расстояние между этими городами: ' + str(round(distance)) + ' км.'

    else:

        res['response']['text'] = 'Слишком много городов!'


def get_cities(req):
    cities = []

    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.GEO':

            if 'city' in entity['value'].keys():
                cities.append(entity['value']['city'])

    return cities


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
