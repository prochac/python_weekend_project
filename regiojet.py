# -*- coding: utf-8 -*-

from datetime import datetime
import requests
from requests import Session
import bs4
import time
import ujson
import re
from redis import StrictRedis

redis_config = {
    'host': '37.139.6.125',
    'password': 'wuaei44INlFurP2qMlng89HmH38',
    'port': 6379
}
CACHE_SYNTAX = 'connection_{studentagency_id_from}_{studentagency_id_to}_{date}'
URL = 'https://jizdenky.regiojet.cz/Booking/from/{from_}/to/{to_}/tarif/REGULAR/departure/{departure}/retdep/{retdep}/return/false?0'
DATE_FORMAT = '%Y%m%d'


def __get_destinations():
    cities_dict = dict()
    response = requests.get('https://www.studentagency.cz/data/wc/ybus-form/destinations-cs.json')
    response_json = response.json()
    for country in response_json['destinations']:
        for city in country['cities']:
            cities_dict[city['name']] = city['id']
    return cities_dict


def __str_to_id(city_str: str) -> int:
    city_convention_str = 'city_id_{}'.format(re.sub('(?!^)([A-Z]+)', r'_\1', city_str).lower())
    redis = StrictRedis(**redis_config)
    # try:
    cached_city_id = redis.get(city_convention_str)
    if cached_city_id:
        return int(cached_city_id)
    city_id = int(__get_destinations()[city_str])
    redis.setex(city_str, 60 * 60, city_id)
    return city_id


def search(from_, to_, departure, retdep):
    session = Session()
    session.head('https://www.regiojet.cz/')

    try:
        query = URL.format(
            from_=__str_to_id(from_),
            to_=__str_to_id(to_),
            departure=departure.strftime(DATE_FORMAT),
            retdep=retdep.strftime(DATE_FORMAT)
        )
    except KeyError:
        raise Exception('Město nenalezeno')

    redis = StrictRedis(**redis_config)
    # try:
    cache = redis.get(
        CACHE_SYNTAX.format(
            studentagency_id_from=__str_to_id(from_), studentagency_id_to=__str_to_id(to_),
            date=departure.strftime('%Y-%m-%d')))
    if cache is not None:
        try:
            return ujson.loads(cache.decode('utf-8'))
        except ValueError:
            return eval(cache.decode('utf-8'))

    session.get(query)
    query += '-1.IBehaviorListener.0-mainPanel-routesPanel&_={unix_timestamp}'.format(unix_timestamp=int(time.time()))
    response = session.get(query)

    soup = bs4.BeautifulSoup(response.text, 'html.parser')
    file = open('response.html', 'w')
    file.write(soup.prettify())
    tickets_table = soup.select_one('#ticket_lists > div > div > div.left_column')

    meta_data = tickets_table.select_one('h2').select('span')
    from_str = meta_data[0].text.lstrip().rstrip()
    to_str = meta_data[1].text.lstrip().rstrip()
    date_str = meta_data[2].text.lstrip().rstrip()

    ticket_list = tickets_table.select('div > div > div.item_blue')

    ret_list = []

    for ticket_list_row in ticket_list:
        col_type = ticket_list_row.select_one('.col_icon > a > img')['title'].lstrip().rstrip()
        col_depart = ticket_list_row.select_one('.col_depart').text.lstrip().rstrip()
        col_arival = ticket_list_row.select_one('.col_arival').text.lstrip().rstrip()
        col_space = ticket_list_row.select_one('.col_space').text.lstrip().rstrip()
        try:
            col_price = ticket_list_row.select_one('.col_price').text.lstrip().rstrip()
        except AttributeError:
            col_price = ticket_list_row.select_one('.col_price_no_basket_image').text.lstrip().rstrip()
        ret_list.append({
            'departure': datetime.combine(datetime.strptime(date_str, '%d.%m.%Y'),
                                          datetime.strptime(col_depart, '%H:%M').time()).strftime('%Y-%m-%d %H:%M:%S'),
            'arrival': datetime.combine(datetime.strptime(date_str, '%d.%m.%Y'),
                                        datetime.strptime(col_arival, '%H:%M').time()).strftime('%Y-%m-%d %H:%M:%S'),
            'from': from_str,
            'to': to_str,
            'free_seats': int(col_space),
            'price': float(re.findall(r'\d+', col_price)[0]),
            'type': {'Vlak': 'train', 'Autobus': 'bus', 'Autobus / Vlak': 'train/bus'}[col_type],
            'from_id': __str_to_id(from_str),
            'to_id': __str_to_id(to_str)

        })
    redis.setex(CACHE_SYNTAX.format(
        studentagency_id_from=__str_to_id(from_), studentagency_id_to=__str_to_id(to_),
        date=departure.strftime('%Y-%m-%d')),
        60 * 60,
        ujson.dumps(ret_list))

    return ret_list
