#!/usr/local/bin/python

import os
import sys
import ConfigParser

from muxMP4 import MuxMP4
from tagMP4 import TagMP4
from addMP4 import AddMP4


def main():
    if len(sys.argv) != 7:
        raise SystemExit('Not enough arguments, this script should be called by Sick Beard')

    config = ConfigParser.ConfigParser()
    config_file = os.path.join(os.path.dirname(sys.argv[0]), 'config.cfg')
    if not os.path.exists(config_file):
        raise SystemExit('Could not find config file')

    config.read(config_file)

    filename = sys.argv[1]
    dest_file = os.path.splitext(filename)[0] + config.get('general', 'extension')
    tvdb_id = int(sys.argv[3])

    if not os.path.exists(filename):
        raise SystemExit('File doesn\'t exist')

    print ''
    print 'Processing file - ' + filename

    if filename == dest_file:
        base, ext = os.path.splitext(filename)
        renamed = base + '-old' + ext
        os.rename(filename, renamed)
        mux = MuxMP4(config, renamed, dest_file)
        mux.mux()
    else:
        mux = MuxMP4(config, filename, dest_file)
        mux.mux()

    tag = TagMP4(config, dest_file, tvdb_id)
    tag.tag()

    add = AddMP4(config, dest_file, tvdb_id)
    add.add()

    print 'Done processing file'


if __name__ == '__main__':
    main()
