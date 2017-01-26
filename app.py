#!env/bin/python
# -*- coding: utf-8 -*-
import argparse
import requests
import lxml.html as html
from datetime import datetime 
import re
import sys
import bokeh.plotting as plt
import tempfile
import os
import numpy as np
title_re = re.compile(r'#(?P<key>\d+) - (?P<date_string>.+)')
num_re = re.compile(r'(?P<num>\d+)')
trim_re = re.compile(r'[\n ]+')

def parse_detail(title, invitations_str, points_str):
    title = title.replace(u'–', '-').strip()
    invitations_str = invitations_str.replace(',', '')
    points_str = points_str.replace(',','')

    title_match = title_re.match(title)
    if not title_match:
        raise Exception(title)
    key = title_match.group('key')
    date_str = title_match.group('date_string').replace(u'\xa0', u' ')
    date = datetime.strptime(date_str, u'%B %d, %Y')
    date = datetime.strftime(date, u'%Y-%m-%d')

    invitations = int(invitations_str)

    points_match = num_re.match(points_str)
    points = int(points_match.group('num'))
    return key, date, invitations, points

graph_data = { 'dates':[], 'points':[], 'invitations':[] }

def print_detail(args, f):
    if f == 'human':
        print '%s\t%s\t%s\t\t%s' % args
    elif f == 'csv':
        print ','.join(map(lambda x: str(x) if ',' not in str(x) else '"{x}"'.format(x), args))
    elif f == 'plot':
        # number, date, invitations, point
        graph_data['dates'].append(datetime.strptime(args[1], '%Y-%m-%d'))
        graph_data['invitations'].append(args[2])
        graph_data['points'].append(args[3])

def get_current_draw():
    res = requests.get('http://www.cic.gc.ca/english/express-entry/rounds.asp')
    root = html.fromstring(res.content)
    sentence = root.cssselect('main > section:nth-child(3) > p:nth-child(11) > strong')[0].text_content().replace(u'–', '-')
    date_str = sentence.split('-')[1].strip()
    title = u'#0 - {date}'.format(date=date_str)

    invitations = root.cssselect('main > section:nth-child(3) > table > tbody > tr > td:nth-child(1)')[0].text
    points = root.cssselect('main > section:nth-child(3) > table > tbody > tr > td:nth-child(2)')[0].text
    return title, invitations, points

def get_past_draws():
    res = requests.get('http://www.cic.gc.ca/english/express-entry/past-rounds.asp')
    root = html.fromstring(re.sub('\r\n', '\n', res.content))
    details = root.cssselect('main details')
    
    for detail in details:
        title = trim_re.sub(' ', detail.cssselect('summary h3')[0].text_content()).strip()
        invitations = trim_re.sub(' ', detail.cssselect('table tbody tr td:nth-child(1)')[0].text)
        points = trim_re.sub(' ', detail.cssselect('table tbody tr td:nth-child(2)')[0].text)
        yield title, invitations, points

def print_header(f):
    if f == 'human':
        print 'Number\tDate\t\tInvitations\tPoint'
    elif f == 'csv':
        print 'Number,Date,Invitations,Point'
    elif f == 'plot':
        pass
    else:
        raise Exception('Unsupported format')

def main():
    parser = argparse.ArgumentParser(description='Get Express Entry rounds')
    parser.add_argument('-f', '--format', help='Format of the output', default='human', choices=('csv', 'human', 'plot'))
    args = parser.parse_args(sys.argv[1:])

    first_detail = parse_detail(*get_current_draw())
    first = True
    for title, invitations, points in get_past_draws():
        detail = parse_detail(title, invitations, points)
        if first:
            key, date, invs, pts = first_detail
            print_header(args.format)
            print_detail((str(int(detail[0]) + 1), date, invs, pts), args.format)
            first = False
        print_detail(detail, args.format)

    if args.format == 'plot':
        f, fpath = tempfile.mkstemp(suffix='.html' )
        plt.output_file(fpath)
        N = len(graph_data['dates'])
        moving_avg = list(np.convolve(graph_data['points'], np.ones((5,))/5, mode='valid'))
        d = N - len(moving_avg)
        moving_avg = ([float('nan')] * (d/2) ) + moving_avg + ([float('nan')] * (d/2))
        print graph_data['points']
        print moving_avg
        p = plt.figure(plot_width=600, plot_height=400, x_axis_type='datetime')
        p.line(graph_data['dates'], graph_data['points'], line_width=2, legend='Min score')
        p.line(graph_data['dates'], [510] * N, line_color='orange', legend='Our score')
        p.line(graph_data['dates'], moving_avg, legend='Rolling', color='gray', alpha=0.5)
        plt.show(p)
        raw_input('Hit enter')
        os.unlink(fpath)
if __name__ == '__main__':
    main()
