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

    file = sys.argv[1]
    m4v_file = os.path.splitext(sys.argv[1])[0] + config.get('general', 'extension')
    tvdb_id = int(sys.argv[3])
    season_num = int(sys.argv[4])
    episode_num = int(sys.argv[5])

    if os.path.splitext(file)[1] == config.get('general', 'extension'):
        raise SystemExit('File is already an ' + config.get('general', 'extension'))

    if not os.path.exists(file):
        raise SystemExit('File doesn\'t exist')

    print ''
    print 'Processing file - ' + file

    mux = MuxMP4(config, file)
    tag = TagMP4(config, m4v_file, tvdb_id, season_num, episode_num)
    add = AddMP4(config, m4v_file, tvdb_id, season_num, episode_num)

    mux.mux()
    tag.tag()
    add.add()

    print ' * Done processing file'



if __name__ == '__main__':
    main()
