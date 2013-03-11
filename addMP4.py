#!/usr/bin/env python

import subprocess
import textwrap

from utils import Metadata_Source


class AddMP4:
    def __init__(self, config, filename, tvdb_id):
        self.config = config
        self.filename = filename
        self.tvdb_id = tvdb_id

    def add(self):
        print ''
        print 'Adding file to iTunes - ' + self.filename

        source = Metadata_Source(self.config)
        metadata = source.get_metadata(self.tvdb_id, self.filename)

        osascript_command = [self.config.get('paths', 'osascript'), '-e']

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

        script = script % (self.filename, metadata['seasonnumber'], metadata['episodenumber'], metadata['seriesname'])
        osascript_command.append(script)

        script_output = subprocess.check_output(osascript_command)

        print script_output

        print ' * Done adding file to iTunes'


if __name__ == '__main__':
    raise SystemExit('This file shouldn\'t be run directly')
