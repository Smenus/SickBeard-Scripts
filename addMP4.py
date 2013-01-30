#!/usr/local/bin/python

import os
import sys
import subprocess
import textwrap
import tvdb_api



def main():
    if len(sys.argv) != 7:
        print 'Not enough arguments, this script should be called by Sick Beard'
        sys.exit(1)

    path = os.path.splitext(sys.argv[1])[0] + '.m4v'
    tvdb_id = int(sys.argv[3])
    season_num = sys.argv[4]
    episode_num = sys.argv[5]
    tvdb_instance = tvdb_api.Tvdb(cache=True)
    tvdb_show = tvdb_instance[tvdb_id]
    
    if not os.path.exists(path):
        print 'Path doesn\'t exist'
        sys.exit(1)

    osascript_command = ['/usr/bin/osascript', '-e']
    
    script = textwrap.dedent("""\
        set p to "%s"
        set f to POSIX file p
        set outText to ""

        set seasonnumber to "%s"
        set episodenumber to "%s"
        set seasonname to "%s"

        set outText to outText & "Checking to see if " & seasonname & " S" & seasonnumber & "E" & episodenumber & " exists in iTunes\n"

        tell application "iTunes"
            set theTracks to tracks of library playlist 1 whose show contains (seasonname as string) and season number is (seasonnumber as integer) and episode number is (episodenumber as integer) and video kind is TV show

            repeat with theTrack in theTracks
                set outText to outText & "Found in iTunes, deleting\n"
                delete theTrack
            end repeat

            tell application "iTunes" to add f
        end tell

        set outText to outText & "Done"

        return outText""")

    script = script % (path, season_num, episode_num, tvdb_show['seriesname'])
    osascript_command.append(script)

    subprocess.call(osascript_command)


if __name__ == '__main__':
    main()
