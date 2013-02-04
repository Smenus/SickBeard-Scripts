#!/usr/local/bin/python

import os
import sys
import subprocess
import textwrap
from pkg_resources import require

require('tvdb_api')

from tvdb_api import (Tvdb, tvdb_error)



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

        try:
            tvdb_instance = Tvdb(cache=True)
            tvdb_show = tvdb_instance[self.tvdb_id]
            seriesname = tvdb_show['seriesname']
        except tvdb_error, errormsg:
            print ' @ Error: Could not fetch episode information - %s' % errormsg
            seriesname = ''

        osascript_command = [config.get('paths', 'osascript'), '-e']

        script = textwrap.dedent("""\
            set p to "%s"
            set f to POSIX file p
            set outText to ""

            set seasonnumber to "%s"
            set episodenumber to "%s"
            set seriesname to "%s"

            tell application "iTunes"
                set playcount to 0
                set lastplayed to missing value
                if seriesname is not "" then
                    set outText to outText & " - Checking to see if episode already exists in iTunes\n"

                    set theTracks to tracks of library playlist 1 whose show contains (seriesname as string) and season number is (seasonnumber as integer) and episode number is (episodenumber as integer) and video kind is TV show

                    repeat with theTrack in theTracks
                        set outText to outText & " - Found in iTunes, deleting previous entry\n"
                        set playcount to played count of theTrack
                        set lastplayed to played date of theTrack
                        delete theTrack
                    end repeat
                end if

                set outText to outText & " - Sending file to iTunes\n"
                set newFile to (add f)
                set played count of newFile to playcount
                set played date of newFile to lastplayed
            end tell

            return outText""")

        script = script % (self.file, self.season_num, self.episode_num, seriesname)
        osascript_command.append(script)

        script_output = subprocess.check_output(osascript_command)

        print script_output

        print ' * Done adding file to iTunes'



if __name__ == '__main__':
    raise SystemExit('This file shouldn\'t be run directly')
