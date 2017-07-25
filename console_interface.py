#!/usr/bin/python3.5
# -*- coding: utf-8 -*-

import click
import regiojet
from datetime import datetime
import pprint


@click.group()
def main():
    '''
    Aplikace pro vyhledávání spojení a rezervování míst
    '''
    return


@main.command()
@click.option('--from', 'from_', type=str)
@click.option('--to', 'to_', type=str)
@click.option('--date_from', 'date_from', type=str)
@click.option('--date_to', 'date_to', type=str)
def search(from_, to_, date_from, date_to):
    '''
    Vyhledávání spojení
    '''

    date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

    search_result = regiojet.search(from_, to_, date_from, date_to)
    if search_result is None:
        print('Nenalezeno')
        return
    for ticket in search_result:
        # pp = pprint.PrettyPrinter(depth=6)
        # pp.pprint(ticket)
        print('{type:^10} {departure} - {arrival} {price:>15}Kč {free_seats:>5} volných míst'.format(**ticket))


@main.command()
def booking():
    '''
    Rezervace spojení
    '''
    print('booking')


if __name__ == '__main__':
    main()
