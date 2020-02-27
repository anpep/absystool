#!/usr/bin/env python3
# coding: utf8
"""
Usage: absystool COMMAND

Client for the AbsysNET library catalog

absystool login
    Authenticates the AbsysNET client

absystool logout
    Deletes stored session data for AbsysNET

absystool status
    Checks AbsysNET client status

Report bugs to <http://github.com/anpep/absystool>
"""

import os
import os.path
import sys
import json
import getpass
from datetime import date
import requests
import prettytable
from lxml import html


class AbsysClient:
    """
    Wrapper around AbsysNET virtual library software
    """

    CONFIG_DIR = os.path.join(os.environ['HOME'], '.config/absystool')
    ABNETSYS_BASE = 'https://catalogobiblioteca.uclm.es/cgi-bin/abnetopac'

    def __init__(self):
        self._creds = {}
        self.base = self.ABNETSYS_BASE

    def _load_credentials(self):
        creds_path = os.path.join(self.CONFIG_DIR, 'authid')
        if os.path.exists(creds_path):
            with open(creds_path, 'r') as creds:
                self._creds = json.load(creds)
                self.base = self.ABNETSYS_BASE + '/' + self._creds['auth_id']

    def _save_credentials(self, auth_id, user_id):
        creds_path = os.path.join(self.CONFIG_DIR, 'authid')
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        self._creds['auth_id'] = auth_id
        self._creds['user_id'] = user_id
        with open(creds_path, 'w+') as creds:
            json.dump(self._creds, creds)
            self.base = self.ABNETSYS_BASE + '/' + self._creds['auth_id']

    def _ensure_auth(self):
        self._load_credentials()
        if 'auth_id' not in self._creds:
            self.login()
        elif '/abnetopac/timeout.html' in requests.get(self.base).text:
            print('Previous session expired')
            self._creds = {}
            self.login()

    def logout(self):
        """
        Deletes saved AbsysNET session
        """
        if 'auth_id' not in self._creds:
            print('not authenticated')
        else:
            os.unlink(os.path.join(self.CONFIG_DIR, 'authid'))

    def login(self):
        """
        Authenticates the client
        """
        user = input('UCLM user: ')
        password = getpass.getpass('password for {}: '.format(user))

        # obtain index resource URL
        self.base = self.ABNETSYS_BASE
        tree = html.fromstring(requests.get(self.base).text)
        path = tree.xpath('//meta[@http-equiv="Refresh"]/@content')[0].split(
            'URL=')[1].split('?')[0]
        path = path.replace('/cgi-bin/abnetopac', '')

        # authenticate
        res = requests.post(self.base + path + '/NT1',
                            data={
                                'FBC': 316,
                                'NAC': 317,
                                'ACC': 201,
                                'leid': user,
                                'lepass': password
                            })
        if 'incorrecta' in res.text:
            self.login()
        else:
            tree = html.fromstring(res.text)
            name = tree.xpath('//a[@id="lecidentify"]/@title')[0].split(
                'Cerrar sesión ')[1]
            print('successfully authenticated as {} ({})'.format(user, name))
            self._save_credentials(
                res.url.split('abnetopac/')[1].split('/NT1')[0], user)

    def status(self):
        """
        Displays client status
        """
        self._ensure_auth()
        tree = html.fromstring(requests.get(self.base + '/NT1?ACC=101').text)
        name = tree.xpath('//a[@id="lecidentify"]/@title')[0].split(
            'Cerrar sesión ')[1]
        print('authenticated as {} ({})'.format(self._creds['user_id'], name))

    def list(self):
        """
        Displays current loans
        """
        self._ensure_auth()
        tree = html.fromstring(requests.get(self.base + '/NT29?ACC=210').text)
        loans = tree.xpath('//form[@id="abnformpre"]/table/tr')[1:]
        table = prettytable.PrettyTable(['Title', 'Due date', 'Remaining'])
        for loan in loans:
            title = loan.getchildren()[2].text.strip()
            due_date = loan.getchildren()[3].text.strip().split('/')
            due_date = date(int(due_date[2], 10), int(due_date[1], 10),
                            int(due_date[0], 10))
            remaining_days = (due_date - date.today()).days
            table.add_row(
                [title, due_date, '{} day(s)'.format(remaining_days)])
        print(table)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
    elif sys.argv[1] == 'login':
        AbsysClient().login()
    elif sys.argv[1] == 'logout':
        AbsysClient().logout()
    elif sys.argv[1] == 'status':
        AbsysClient().status()
    elif sys.argv[1] == 'list':
        AbsysClient().list()
    else:
        print(__doc__)
