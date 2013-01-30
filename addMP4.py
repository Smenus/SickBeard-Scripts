#!/usr/local/bin/python

import os
import sys
import subprocess
import textwrap
import ConfigParser
from pkg_resources import require

require('tvdb_api')

import tvdb_api



def main():
    if len(sys.argv) != 7:
        print 'Not enough arguments, this script should be called by Sick Beard'
        sys.exit(1)

    config = ConfigParser.ConfigParser()
    config_file = os.path.join(os.path.dirname(sys.argv[0]), 'config.cfg')
    config.read(config_file)

    path = os.path.splitext(sys.argv[1])[0] + config.get('general', 'extension')
    tvdb_id = int(sys.argv[3])
    season_num = sys.argv[4]
    episode_num = sys.argv[5]
    tvdb_instance = tvdb_api.Tvdb(cache=True)
    tvdb_show = tvdb_instance[tvdb_id]
 
    print 'Adding file to iTunes - ' + path
   
    if not os.path.exists(path):
        print ' @ Error: Path doesn\'t exist'
        sys.exit(1)

    osascript_command = [config.get('paths', 'osascript'), '-e']
    
    script = textwrap.dedent("""\
        set p to "%s"
        set f to POSIX file p
        set outText to ""

        set seasonnumber to "%s"
        set episodenumber to "%s"
        set seasonname to "%s"

        set outText to outText & " - Checking to see if episode already exists in iTunes\n"

        tell application "iTunes"
            set theTracks to tracks of library playlist 1 whose show contains (seasonname as string) and season number is (seasonnumber as integer) and episode number is (episodenumber as integer) and video kind is TV show

            repeat with theTrack in theTracks
                set outText to outText & " - Found in iTunes, deleting previous entry\n"
                delete theTrack
            end repeat

            set outText to outText & " - Sending file to iTunes\n"
            tell application "iTunes" to add f
        end tell

        return outText""")

    script = script % (path, season_num, episode_num, tvdb_show['seriesname'])
    osascript_command.append(script)

    subprocess.check_call(osascript_command)

    print ' * Done adding file to iTunes'


if __name__ == '__main__':
    main()
