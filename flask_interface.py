#!/usr/bin/python3.5
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, render_template, send_file
import regiojet
import json
from datetime import datetime
from threading import Thread
from time import sleep

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
config_data = {}


def __config_loader(file_name):
    global config_data
    while True:
        with open(file_name) as data_file:
            config_data = json.load(data_file)
        sleep(5)


def __save_data(data):
    import psycopg2
    import psycopg2.extras as pg2

    conn = psycopg2.connect(**config_data['db_config'])
    cur = conn.cursor(cursor_factory=pg2.DictCursor)
    for data_row in data:
        cur.execute(
            'INSERT INTO connections_tomas_prochazka(departure,arrival,src,dst,free_seats,price) VALUES(\'{departure}\',\'{arrival}\',\'{src}\',\'{dst}\',{free_seats},{price})'
                .format(departure=data_row['departure'], arrival=data_row['arrival'], src=data_row['from'],
                        dst=data_row['to'], free_seats=data_row['free_seats'], price=data_row['price']))
    conn.commit()


@app.route('/<filename>.png', methods=['GET'])
def get_image(filename):
    return send_file(filename + '.png', mimetype='image/png')


@app.route('/search', methods=['GET'])
def search():
    '''
    Vyhledávání spojení, vrací stránku
    '''

    search_result = []
    try:
        from_ = request.args.get('from')
        to_ = request.args.get('to')

        if {from_, to_} & set(config_data['ban_list']):
            raise Exception('Město {} je na banlistu'.format(set([from_, to_]) & set(config_data['ban_list'])))

        date_from = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d').date()
        search_result = regiojet.search(from_, to_, date_from, date_to)
    except TypeError:
        raise
        print('Missing variables, return page with empty list')
    except Exception as ex:
        return render_template('error_template.jinja2', error_mesage=str(ex))
    __save_data(search_result)
    return render_template('template.jinja2', result_list=search_result)


@app.route('/search-json', methods=['GET'])
def search_json():
    '''
    Vyhledávání spojení, vrací JSON
    '''

    from_ = request.args.get('from')
    to_ = request.args.get('to')
    date_from = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d').date()
    date_to = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d').date()
    search_result = regiojet.search(from_, to_, date_from, date_to)
    if search_result is None:
        return 'Nenalezeno'
    return jsonify(search_result)


if __name__ == '__main__':
    t = Thread(target=__config_loader, args=('config.json',))
    t.start()
    app.run(debug=True)
