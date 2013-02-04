#!/usr/local/bin/python

import os
import sys
import subprocess
from pkg_resources import require

require('VideoConverter')
require('lockfile')

from converter import Converter
from lockfile import FileLock



class MP4Maker:
    def __init__(self, file, dest_file):
        self.file = file
        self.dest_file = dest_file


    def make_mp4(self):
        self._scan_input()
        self._set_ffmpeg_video()
        self._set_ffmpeg_audio()
        self._set_ffmpeg_subtitles()
        self._run_ffmpeg()
        self._run_mp4box()


    def remove_old(self):
        os.remove(self.file)


    def _scan_input(self):
        print ' - Scanning file'
        c = Converter(config.get('paths', 'ffmpeg'), config.get('paths', 'ffprobe'))
        file = c.probe(self.file)

        video_count = 0
        audio_count = 0
        subtitle_count = 0
        self.audio_kind = ''
        self.video_kind = ''
        self.video_hd = False
        self.copy_subtitles = False
        for stream in file.streams:
            if stream.type == 'audio':
                audio_count += 1
                self.audio_kind = stream.codec
            elif stream.type == 'video':
                video_count += 1
                self.video_kind = stream.codec
                self.video_hd = True if (stream.video_height >= 700 or stream.video_width >= 1260) else False
            elif stream.type == 'subtitle':
                if stream.codec == 'subrip':
                    self.copy_subtitles = True

        if audio_count != 1 or video_count != 1:
            raise SystemExit('More than 1 video or audio stream, you\'d best check this file manually')

        self.ffmpeg_command = [config.get('paths', 'ffmpeg'), '-v', 'error', '-nostats', '-i', self.file]


    def _set_ffmpeg_video(self):
        print ' - Setting video options'
        if self.video_kind == 'h264':
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
                self.ffmpeg_command.append(config.get('makeMP4', 'x264_crf_hd'))
            else:
                self.ffmpeg_command.append(config.get('makeMP4', 'x264_crf_sd'))
            self.ffmpeg_command.append('-preset:v')
            self.ffmpeg_command.append(config.get('makeMP4', 'x264_preset'))
            self.ffmpeg_command.append('-x264opts')
            self.ffmpeg_command.append(config.get('makeMP4', 'x264_opts'))


    def _set_ffmpeg_audio(self):
        print ' - Setting audio options'
        self.multiple_audio = False
        if self.audio_kind == 'mp3':
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a:0')
            self.ffmpeg_command.append(config.get('makeMP4', 'aac_lib'))
            self.ffmpeg_command.append(config.get('makeMP4', 'aac_q_cmd') + ':a:0')
            self.ffmpeg_command.append(config.get('makeMP4', 'aac_q'))
            self.ffmpeg_command.append('-afterburner')
            self.ffmpeg_command.append('1')
            self.ffmpeg_command.append('-ac:a:0')
            self.ffmpeg_command.append('2')
        elif self.audio_kind == 'aac':
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a')
            self.ffmpeg_command.append('copy')
        else:
            self.multiple_audio = True
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a:0')
            self.ffmpeg_command.append(config.get('makeMP4', 'aac_lib'))
            self.ffmpeg_command.append(config.get('makeMP4', 'aac_q_cmd') + ':a:0')
            self.ffmpeg_command.append(config.get('makeMP4', 'aac_q'))
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
            # faststart not needed as AtomicParsley with do it
            #self.ffmpeg_command.append('-movflags')
            #self.ffmpeg_command.append('faststart')
            self.ffmpeg_command.append(self.dest_file)
            if config.get('general', 'debug') == 'True':
                print self.ffmpeg_command
            subprocess.check_call(self.ffmpeg_command)


    def _run_mp4box(self):
        if self.multiple_audio:
            print ' - Disabling 2nd audio track'
            self.mp4box_command = [config.get('paths', 'mp4box'), '-noprog', '-tmp', os.path.dirname(self.dest_file)]
            self.mp4box_command.append('-disable')
            self.mp4box_command.append('3')
            self.mp4box_command.append(self.dest_file)            
            if config.get('general', 'debug') == 'True':
                print self.mp4box_command
            subprocess.check_call(self.mp4box_command)



class MuxMP4:
    def __init__(self, cfg, file, dest_file):
        global config
        config = cfg
        self.file = file
        self.dest_file = dest_file


    def mux(self):
        print ''
        print 'Converting file to MP4 - ' + self.file

        maker = MP4Maker(self.file, self.dest_file)
        maker.make_mp4()
        if config.get('makeMP4', 'delete_old') == 'True':
            print ' - Removing old file'
            maker.remove_old()

        print ' * Done converting file to MP4'



if __name__ == '__main__':
    raise SystemExit('This file shouldn\'t be run directly')
