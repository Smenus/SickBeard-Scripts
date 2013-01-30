#!/usr/bin/env python

import os
import sys
import subprocess
import converter



class MP4Maker:
    def __init__(self, path):
        self.path = path

        if not os.path.exists(path):
            print 'Path doesn\'t exist'
            sys.exit(1)

        if os.path.splitext(path)[1] == '.m4v':
            print 'File is already an m4v'
            sys.exit(1)


    def make_mp4(self):
        self._scan_input()
        self._set_ffmpeg_video()
        self._set_ffmpeg_audio()
        self._set_ffmpeg_other()
        self._run_ffmpeg()


    def optimize_mp4(self):
        self._set_mp4box()
        self._run_mp4box()


    def remove_old(self):
        os.remove(self.path)


    def _scan_input(self):
        c = converter.Converter()
        file = c.probe(self.path)

        video_count = 0
        audio_count = 0
        self.audio_kind = ''
        self.video_kind = ''
        self.video_hd = False
        self.copy_subtitles = False
        self.copy_data = False
        self.copy_attachments = False
        for stream in file.streams:
            if stream.type == 'audio':
                audio_count += 1
                self.audio_kind = stream.codec
            elif stream.type == 'video':
                video_count += 1
                self.video_kind = stream.codec
                self.video_hd = True if (stream.video_height >= 700 or stream.video_width >= 1260) else False
            elif stream.type == 'subtitle':
                self.copy_subtitles = True
            elif stream.type == 'data':
                self.copy_data = True
            elif stream.type == 'attachment':
                self.copy_attachments = True

        if audio_count != 1 or video_count != 1:
            print 'More than 1 video or audio stream, you\'d best check this file manually'
            sys.exit(1)

        self.ffmpeg_command = ['ffmpeg', '-v', 'error', '-nostats', '-i', self.path]


    def _set_ffmpeg_video(self):
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
                self.ffmpeg_command.append('23')
            else:
                self.ffmpeg_command.append('21')
            self.ffmpeg_command.append('-preset:v')
            self.ffmpeg_command.append('medium')
            self.ffmpeg_command.append('-x264opts')
            self.ffmpeg_command.append('b-adapt=2')


    def _set_ffmpeg_audio(self):
        self.multiple_audio = False
        if self.audio_kind == 'mp3':
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a:0')
            self.ffmpeg_command.append('libfdk_aac')
            self.ffmpeg_command.append('-vbr:a:0')
            self.ffmpeg_command.append('5')
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
            self.ffmpeg_command.append('libfdk_aac')
            self.ffmpeg_command.append('-vbr:a:0')
            self.ffmpeg_command.append('5')
            self.ffmpeg_command.append('-ac:a:0')
            self.ffmpeg_command.append('2')
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:a')
            self.ffmpeg_command.append('-c:a:1')
            self.ffmpeg_command.append('copy')


    def _set_ffmpeg_other(self):
        if self.copy_subtitles:
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:s')
            self.ffmpeg_command.append('-c:s')
            self.ffmpeg_command.append('copy')
        if self.copy_data:
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:d')
            self.ffmpeg_command.append('-c:d')
            self.ffmpeg_command.append('copy')
        if self.copy_attachments:
            self.ffmpeg_command.append('-map')
            self.ffmpeg_command.append('0:t')
            self.ffmpeg_command.append('-c:t')
            self.ffmpeg_command.append('copy')


    def _run_ffmpeg(self):
        print 'Converting to MP4...'
        self.ffmpeg_command.append(os.path.splitext(self.path)[0] + '.m4v')
        subprocess.call(self.ffmpeg_command)


    def _set_mp4box(self):
        self.mp4box_command = ['MP4Box', '-noprog']
        if self.multiple_audio:
            self.mp4box_command.append('-disable')
            self.mp4box_command.append('3')
        self.mp4box_command.append(os.path.splitext(self.path)[0] + '.m4v')


    def _run_mp4box(self):
        print 'Optimizing MP4...'
        subprocess.call(self.mp4box_command)



def main():
    if len(sys.argv) != 7:
        print 'Not enough arguments, this script should be called by Sick Beard'
        sys.exit(1)

    path = sys.argv[1]

    maker = MP4Maker(path)
    maker.make_mp4()
    maker.optimize_mp4()
    maker.remove_old()


if __name__ == '__main__':
    main()
