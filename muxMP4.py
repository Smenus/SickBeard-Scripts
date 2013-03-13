import os
import sys
import subprocess

from pymediainfo import MediaInfo
from lockfile import FileLock


class MP4Maker:
    def __init__(self, config, filename, dest_file):
        self.config = config
        self.filename = filename
        self.dest_file = dest_file

        self.file_kind = ''
        self.audio_kind = ''
        self.video_kind = ''
        self.aac_present = False
        self.video_hd = False
        self.ref_frames = 0
        self.copy_subtitles = False

    def make_mp4(self):
        self._scan_input()
        if not self.aac_present or self.video_kind != 'AVC' or self.ref_frames > 9 or self.file_kind != 'MPEG-4':
            self._set_ffmpeg_video()
            self._set_ffmpeg_audio()
            self._set_ffmpeg_subtitles()
            self._run_ffmpeg()
            self._remove_old()
        else:
            print ' - File already fine, renaming'
            os.rename(self.filename, self.dest_file)

    def _remove_old(self):
        if self.config.get('makeMP4', 'delete_old') == 'True':
            print ' - Removing old file'
            os.remove(self.filename)

    def _clean_metadata(self):
        print ' - Removing tags'

        base, ext = os.path.splitext(self.filename)
        cleanedfile = base + '-cleaned' + ext

        command = [self.config.get('paths', 'atomicparsley'), self.filename, '-o', cleanedfile, '--metaEnema', '--artwork', 'REMOVE_ALL']

        if self.config.get('general', 'debug') == 'True':
            print command

        try:
            subprocess.check_output(command, env=os.environ, stderr=subprocess.STDOUT)
            os.remove(self.filename)
            os.rename(cleanedfile, self.filename)
        except subprocess.CalledProcessError, e:
            print ' - Error whilst removing tags: ', e.output

    def _scan_input(self):
        print ' - Scanning file'
        mi = MediaInfo.parse(self.filename)

        if len(mi.tracks) == 0 and os.path.splitext(self.filename)[1] in ['.m4v', '.mp4']:
            self._clean_metadata()
            mi = MediaInfo.parse(self.filename)

        video_count = 0
        audio_count = 0
        for track in mi.tracks:
            if track.track_type == 'General':
                self.file_kind = track.format
            if track.track_type == 'Audio':
                audio_count += 1
                self.audio_kind = track.format
                if track.format == 'AAC':
                    self.aac_present = True
            elif track.track_type == 'Video':
                video_count += 1
                self.video_kind = track.format
                self.video_hd = True if (track.height >= 700 or track.width >= 1260) else False
                if hasattr(track, 'codec_settings_refframes'):
                    self.ref_frames = int(track.codec_settings_refframes)
            elif track.track_type == 'Text':
                if track.format == 'UTF-8':
                    self.copy_subtitles = True

        if audio_count != 1 and not self.aac_present:
            raise SystemExit('More than 1 audio stream (%d), you\'d best check this file manually' % audio_count)

        if video_count != 1:
            raise SystemExit('More than 1 video stream (%d), you\'d best check this file manually' % video_count)

        self.ffmpeg_command = [self.config.get('paths', 'ffmpeg'), '-v', 'error', '-nostats', '-i', self.filename]

    def _set_ffmpeg_video(self):
        print ' - Setting video options'
        if self.video_kind == 'AVC' and self.ref_frames <= 9:
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:v')
            self.ffmpeg_command.append('-c:v')
            self.ffmpeg_command.append('copy')
        else:
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:v')
            self.ffmpeg_command.append('-c:v')
            self.ffmpeg_command.append('libx264')
            self.ffmpeg_command.append('-crf:v')
            if self.video_hd:
                self.ffmpeg_command.append(self.config.get('makeMP4', 'x264_crf_hd'))
            else:
                self.ffmpeg_command.append(self.config.get('makeMP4', 'x264_crf_sd'))
            self.ffmpeg_command.append('-preset:v')
            self.ffmpeg_command.append(self.config.get('makeMP4', 'x264_preset'))
            self.ffmpeg_command.append('-x264opts')
            self.ffmpeg_command.append(self.config.get('makeMP4', 'x264_opts'))

    def _set_ffmpeg_audio(self):
        print ' - Setting audio options'
        if self.audio_kind == 'AAC' or self.aac_present:
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a')
            self.ffmpeg_command.append('copy')
        elif self.audio_kind == 'MPEG Audio':
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a:0')
            self.ffmpeg_command.append(self.config.get('makeMP4', 'aac_lib'))
            self.ffmpeg_command.append(self.config.get('makeMP4', 'aac_q_cmd') + ':a:0')
            self.ffmpeg_command.append(self.config.get('makeMP4', 'aac_q'))
            self.ffmpeg_command.append('-afterburner')
            self.ffmpeg_command.append('1')
            self.ffmpeg_command.append('-ac:a:0')
            self.ffmpeg_command.append('2')
        else:
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a:0')
            self.ffmpeg_command.append(self.config.get('makeMP4', 'aac_lib'))
            self.ffmpeg_command.append(self.config.get('makeMP4', 'aac_q_cmd') + ':a:0')
            self.ffmpeg_command.append(self.config.get('makeMP4', 'aac_q'))
            self.ffmpeg_command.append('-afterburner')
            self.ffmpeg_command.append('1')
            self.ffmpeg_command.append('-ac:a:0')
            self.ffmpeg_command.append('2')
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a:1')
            self.ffmpeg_command.append('copy')

    def _set_ffmpeg_subtitles(self):
        if self.copy_subtitles:
            print ' - Setting subtitle options'
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:s')
            self.ffmpeg_command.append('-c:s')
            self.ffmpeg_command.append('mov_text')

    def _run_ffmpeg(self):
        print ' - Getting lock file'
        with FileLock(os.path.join(os.path.dirname(sys.argv[0]), 'ffmpeg-running')):
            print ' - Converting to MP4'
            self.ffmpeg_command.append('-f')
            self.ffmpeg_command.append('mp4')
            self.ffmpeg_command.append(self.dest_file)
            if self.config.get('general', 'debug') == 'True':
                print self.ffmpeg_command
            subprocess.check_call(self.ffmpeg_command)


class MuxMP4:
    def __init__(self, config, filename, dest_file):
        self.config = config
        self.filename = filename
        self.dest_file = dest_file

    def mux(self):
        print ''
        print 'Converting file to MP4 - ' + self.filename

        maker = MP4Maker(self.config, self.filename, self.dest_file)
        maker.make_mp4()

        print ' * Done converting file to MP4'


if __name__ == '__main__':
    raise SystemExit('This file shouldn\'t be run directly')
