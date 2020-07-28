#!/usr/bin/env python3

'''
Developed with <3 by the Bishop Fox Continuous Attack Surface Testing (CAST) team.
https://www.bishopfox.com/continuous-attack-surface-testing/how-cast-works/

Author:     @noperator
Purpose:    Determine the software version of a remote PAN-OS target.
Notes:      - Requires version-table.txt in the same directory.
            - Usage of this tool for attacking targets without prior mutual
              consent is illegal. It is the end user's responsibility to obey
              all applicable local, state, and federal laws. Developers assume
              no liability and are not responsible for any misuse or damage
              caused by this program.
Usage:      python3 panos-scanner.py [-h] [-v] [-s] -t TARGET
'''

from argparse import ArgumentParser
from datetime import datetime, timedelta
from requests import get
from requests.exceptions import HTTPError, ConnectTimeout, SSLError, ConnectionError, ReadTimeout
from sys import argv, stderr, exit
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

disable_warnings(InsecureRequestWarning)

def etag_to_datetime(etag):
    epoch_hex = etag[-8:]
    return datetime.fromtimestamp(
               int(epoch_hex, 16)
           ).date()

def last_modified_to_datetime(last_modified):
    return datetime.strptime(
               last_modified[:-4],
               '%a, %d %b %Y %X'
           ).date()

def get_resource(target, resources, date_headers, errors, verbose):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
            'Connection': 'close',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1'
        }
        resp = get(
            '%s/%s' % (target, resource),
            headers=headers,
            timeout=5,
            verify=False
        )
        if verbose:
            sym = '+' if resp.ok else '-'
            print('[%s]' % sym, resp.status_code, resource, file=stderr)
        resp.raise_for_status()
        return {h: resp.headers[h].strip('"') for h in date_headers
                if h in resp.headers}
    except (HTTPError, ReadTimeout) as e:
        pass
    except errors as e:
        raise e

def load_version_table(version_table):
    with open(version_table, 'r') as f:
        entries = [line.strip().split() for line in f.readlines()]
    return {e[0]: datetime.strptime(' '.join(e[1:]), '%b %d %Y').date()
            for e in entries}

def check_date(version_table, date):
    matches = {}
    for n in [0, 1, -1, 2, -2]:
        nearby_date = date + timedelta(n)
        versions = [version for version, date in version_table.items()
                    if date == nearby_date]
        if n == 0:
            key = 'exact'
        else:
            key = 'approximate'
        if key not in matches:
            matches[key] = {'date': nearby_date, 'versions': versions}
    return matches

def get_matches(date_headers, resp_headers, verbose=False):
    matches = {}
    for header in date_headers.keys():
        if header in resp_headers:
            date = globals()[date_headers[header]](resp_headers[header])
            date_matches = check_date(version_table, date)
            for precision, match in date_matches.items():
                if match['versions']:
                    if precision not in matches.keys():
                        matches[precision] = []
                    matches[precision].append(match)
                    if verbose:
                        print(
                            '[*]',
                            '%s ~ %s' % (date, match['date']) if date != match['date'] else date,
                            '=>',
                            ','.join(match['versions']),
                            file=stderr
                        )
    return matches

if __name__ == '__main__':

    parser = ArgumentParser('Determine the software version of a remote PAN-OS target. Requires version-table.txt in the same directory.')
    parser.add_argument('-v', dest='verbose', action='store_true', help='verbose output')
    parser.add_argument('-s', dest='stop', action='store_true', help='stop after one exact match')
    parser.add_argument('-t', dest='target', required=True, help='https://example.com')
    args = parser.parse_args()

    static_resources = [
        'global-protect/login.esp',
        'php/login.php',
        'global-protect/portal/css/login.css',
        'js/Pan.js',
        'global-protect/portal/images/favicon.ico',
        'login/images/favicon.ico',
        'global-protect/portal/images/logo-pan-48525a.svg',
    ]

    version_table = load_version_table('version-table.txt')

    date_headers = {
        'ETag':          'etag_to_datetime',
        'Last-Modified': 'last_modified_to_datetime'
    }

    total_matches = {
        'exact': [],
        'approximate': []
    }

    errors = (ConnectTimeout, SSLError, ConnectionError)

    if args.verbose:
        print('[*]', args.target, file=stderr)

    # Check for the presence of each static resource.
    for resource in static_resources:
        try:
            resp_headers = get_resource(
                args.target,
                resource,
                date_headers.keys(),
                errors,
                args.verbose
            )
        except errors as e:
            print('[-]', args.target, type(e).__name__, file=stderr)
            exit(1)
        if resp_headers == None:
            continue

        # Convert date-related HTTP headers to a standardized format, and
        # store any matching version strings.
        total_matches.update(get_matches(date_headers, resp_headers, args.verbose))
        if args.stop and len(total_matches['exact']):
            break

    # Print results.
    printed = []
    for precision, matches in total_matches.items():
        for match in matches:
            if match['versions'] and match not in printed:
                printed.append(match)
                print(','.join(match['versions']), match['date'], '(%s)' % precision)
