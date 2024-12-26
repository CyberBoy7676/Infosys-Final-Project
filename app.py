from flask import Flask, request, render_template, redirect, url_for, send_file
from moviepy import VideoFileClip, AudioFileClip
from gtts import gTTS
from pydub import AudioSegment
import whisper
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Convert MP4 to MP3
def convert_video_to_audio(video_path, audio_output_path):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_output_path, codec='libmp3lame')

# Transcribe MP3 to text
def transcribe_mp3_to_text(mp3_path):
    model = whisper.load_model("base")
    result = model.transcribe(mp3_path)
    return result['text']

# Text-to-speech
def text_to_speech_gtts(text, language, output_path):
    tts = gTTS(text=text, lang=language, slow=False)
    tts.save(output_path)

# Adjust audio speed
def adjust_audio_speed(audio_file, target_duration, output_file):
    audio = AudioSegment.from_file(audio_file)
    current_duration = audio.duration_seconds
    speed_factor = current_duration / target_duration
    adjusted_audio = audio._spawn(audio.raw_data, overrides={
        "frame_rate": int(audio.frame_rate * speed_factor)
    }).set_frame_rate(audio.frame_rate)
    adjusted_audio.export(output_file, format="mp3")

# Replace audio in video
# def replace_audio_in_video(original_video_path, adjusted_audio_path, output_video_path):
#     video = VideoFileClip(original_video_path)
#     adjusted_audio = AudioFileClip(adjusted_audio_path)
#     video_with_new_audio = video.set_audio(adjusted_audio)
#     video_with_new_audio.write_videofile(output_video_path, codec="libx264", audio_codec="aac")

# from moviepy import VideoFileClip, AudioFileClip

# def replace_audio_in_video(video_path, audio_path, output_path):
#     # Load video and audio files
#     video = VideoFileClip(video_path)
#     audio = AudioFileClip(audio_path)

#     # Ensure the audio duration matches the video duration
#     adjusted_audio = audio.subclip(0, min(video.duration, audio.duration))

#     # Replace the audio in the video
#     video_with_new_audio = video.set_audio(adjusted_audio)

#     # Write the final video file
#     video_with_new_audio.write_videofile(output_path, codec="libx264", audio_codec="aac")

from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip



def replace_audio_in_video(video_path, audio_path, output_path):
    try:
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)

        # Ensure valid audio and video objects
        print(f"Video duration: {video.duration}, Audio duration: {audio.duration}")

        # Adjust the audio duration to match the video
        adjusted_audio = audio.subclip(0, min(video.duration, audio.duration))

        # Replace audio in the video
        video_with_new_audio = video.set_audio(adjusted_audio)

        # Write the final video file
        video_with_new_audio.write_videofile(output_path, codec="libx264", audio_codec="aac")
    except Exception as e:
        print(f"Error: {e}")



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    video_file = request.files['video']
    language = request.form['language']

    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file.filename)
    audio_path = os.path.join(app.config['OUTPUT_FOLDER'], 'audio.mp3')
    tts_path = os.path.join(app.config['OUTPUT_FOLDER'], 'tts.mp3')
    final_video_path = os.path.join(app.config['OUTPUT_FOLDER'], 'final_video.mp4')

    # Save uploaded video
    video_file.save(video_path)

    # Step 1: Convert video to audio
    convert_video_to_audio(video_path, audio_path)

    # Step 2: Transcribe audio to text
    transcription = transcribe_mp3_to_text(audio_path)

    # Step 3: Text-to-Speech
    text_to_speech_gtts(transcription, language, tts_path)

    # Step 4: Adjust audio and replace in video
    video_duration = VideoFileClip(video_path).duration
    adjust_audio_speed(tts_path, video_duration, tts_path)
    replace_audio_in_video(video_path, tts_path, final_video_path)

    return render_template('result.html', transcription=transcription, output_video=final_video_path)

@app.route('/download/<filename>')
def download(filename):
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
