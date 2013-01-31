#!/usr/local/bin/python

import os
import sys
import subprocess
import textwrap
from pkg_resources import require

require('tvdb_api')

from tvdb_api import Tvdb



class AddMP4:
    def __init__(self, cfg, file, tvdb_id, season_num, episode_num):
        global config
        config = cfg
        self.file = file
        self.tvdb_id = tvdb_id
        self.season_num = season_num
        self.episode_num = episode_num


    def add(self):
        print ''
        print 'Adding file to iTunes - ' + self.file

        tvdb_instance = Tvdb(cache=True)
        tvdb_show = tvdb_instance[self.tvdb_id]

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

        script = script % (self.file, self.season_num, self.episode_num, tvdb_show['seriesname'])
        osascript_command.append(script)

        script_output = subprocess.check_output(osascript_command)

        print script_output

        print ' * Done adding file to iTunes'



if __name__ == '__main__':
    raise SystemExit('This file shouldn\'t be run directly')
