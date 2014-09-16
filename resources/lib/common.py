from sys import modules, argv
from time import strptime
from datetime import datetime
from urllib import urlencode
from urlparse import parse_qsl
from inspect import stack
from functools import wraps
from contextlib import contextmanager
from models import *


STRINGMAP = {
    'shows':            30010,
    'search':           30011,
    'episodes':         30012,
    'movies':           30013,
    'trailers':         30014,
    'clips':            30015,
    'next':             30016,
    'genres':           30017,
    'rating':           30018,

    # messages
    'error':            30600,
    'unknown_error':    30601,
    'no_episodes':      30603,
    'no_movies':        30604,
    'no_trailers':      30605,
    'no_clips':         30606,

    # genres
    'action':           30700,
    'adventure':        30701,
    'bishonen':         30702,
    'bishoujo':         30703,
    'comedy':           30704,
    'cyberpunk':        30705,
    'drama':            30706,
    'fan service':      30707,
    'fantasy':          30708,
    'harem':            30709,
    'historical':       30710,
    'horror':           30711,
    'live action':      30712,
    'magical girl':     30713,
    'martial arts':     30714,
    'mecha':            30715,
    'moe':              30716,
    'mystery':          30717,
    'reverse harem':    30718,
    'romance':          30719,
    'school':           30720,
    'sci fi':           30721,
    'shonen':           30722,
    'slice of life':    30723,
    'space':            30724,
    'sports':           30725,
    'super power':      30726,
    'supernatural':     30727,
    'yuri':             30728,
}

xbmc = modules['__main__'].xbmc
plugin = modules['__main__'].plugin
xbmcgui = modules['__main__'].xbmcgui
settings = modules['__main__'].settings
language = modules['__main__'].language

dbg = settings.getSetting('debug') == 'true'
if dbg:
    dbglevel = 3
else:
    dbglevel = 0


def to_minutes(t):
    t = t.split(':')
    if len(t) == 2:
        m, s = [int(i) for i in t]
        return (60 * m + s) / 60
    elif len(t) == 3:
        h, m, s = [int(i) for i in t]
        return (3600 * h + 60 * m + s) / 60


def fix_keys(d):
    def fix_key(key):
        return key.lower().replace(' ', '_').replace('-', '_')

    def fix(x):
        if isinstance(x, dict):
            return dict((fix_key(k), fix(v)) for k, v in x.iteritems())
        elif isinstance(x, list):
            return [fix(i) for i in x]
        else:
            return x

    return fix(d)


def convert_values(d):
    for k, v in d.items():
        if k == 'video_section' or k == 'aip':
            d[k] = d[k].values() if isinstance(d[k], dict) else []
        elif k == 'votes' or k == 'nid' or k == 'show_id':
            d[k] = int(d[k])
        elif k == 'episode_number':
            d[k] = int(float(d[k]))
        elif k == 'post_date':
            try:
                d[k] = datetime.strptime(d[k], '%m/%d/%Y')
            except TypeError:
                d[k] = datetime(*(strptime(d[k], '%m/%d/%Y')[0:6]))
        elif k == 'duration':
            d[k] = to_minutes(d[k])
        elif k == 'all_terms' or k == 'term':
            d[k] = d[k].split(', ')
        elif k == 'similar_shows':
            d[k] = [int(i) for i in d[k].split(',') if isinstance(i, list)]
        elif k == 'video_quality':
            d[k] = d[k].values() if isinstance(d[k], dict) else [d[k]]
        elif k == 'promo':
            d[k] = d[k] == 'Promo'
        elif k == 'type':
            d[k] = d[k][7:]
        elif k == 'maturity_rating':
            d[k] = str(d[k])
        elif k == 'mpaa':
            d[k] = ','.join(d[k].values()) if isinstance(d[k], dict) else d[k]

    return d


def process_response(data):
    # collapse data into list of dicts
    data = [i[i.keys()[0]] for i in data[data.keys()[0]]]
    # fix dict key names
    data = fix_keys(data)
    # fix up the values
    data = [convert_values(i) for i in data]

    if data[0].has_key('maturity_rating'):
        return [Show(**i) for i in data]
    elif data[0].has_key('episode_number'):
        return [Episode(**i) for i in data]
    elif data[0].has_key('tv_key_art'):
        return [Movie(**i) for i in data]
    elif data[0].has_key('funimationid'):
        return [Clip(**i) for i in data]
    elif data[0].has_key('is_mature'):
        return [Trailer(**i) for i in data]
    else:
        return data


def show_message(msg, title=None, icon=None):
    dur = int(settings.getSetting('notification_length'))
    if title is None:
        title = settings.getAddonInfo('name')
    if icon is None:
        icon = settings.getAddonInfo('icon')

    xbmc.executebuiltin(
        'Notification({title}, {msg}, {dur}, {icon})'.format(**locals()))


def show_error_message(result=None, title=None):
    if title is None:
        title = get_string('error')
    if result is None:
        result = get_string('unknown_error')
    show_message(result, title)


def get_string(string_key):
    if string_key in STRINGMAP:
        string_id = STRINGMAP[string_key]
        string = language(string_id).encode('utf-8')
        log('%d translates to %s' % (string_id, string), 4)
        return string
    else:
        log('String is missing: ' + string_key, 4)
        return string_key


def get_user_input(title, default=None, hidden=False):
    if default is None:
        default = u''

    result = None
    keyboard = xbmc.Keyboard(default, title)
    keyboard.setHiddenInput(hidden)
    keyboard.doModal()

    if keyboard.isConfirmed():
        result = keyboard.getText()

    return result


def build_url(map):
    return argv[0] + '?' + urlencode(map)


def get_params():
    return dict(parse_qsl(argv[2][1:]))


def log(msg, lvl=0):
    if dbg and dbglevel > lvl:
        log_msg = u'[{0}] {1} : {2}'.format(plugin, stack()[1][3], msg)
        xbmc.log(log_msg.decode('utf-8'), xbmc.LOGNOTICE)


def timethis(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        f = func(*args, **kwargs)
        elapsed = time.time() - start
        log('{0}.{1} : {2}'.format(func.__module__, func.__name__, elapsed))
        return f
    return wrapper


@contextmanager
def timeblock(label):
    start = time.time()
    try:
        yield
    finally:
        end = time.time()
        print('{0} : {1}'.format(label, end - start))
