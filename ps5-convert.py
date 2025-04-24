import os
import subprocess
import argparse
import json
from tkinter import Tk, filedialog, simpledialog, messagebox

def choose_subtitle_file(video_path):
    folder = os.path.dirname(video_path)
    srt_files = [f for f in os.listdir(folder) if f.lower().endswith(".srt")]

    if not srt_files:
        messagebox.showerror("No Subtitles Found", "No .srt subtitle files found in the video folder.")
        return None

    if len(srt_files) == 1:
        return os.path.join(folder, srt_files[0])

    root = Tk()
    root.withdraw()
    choice = simpledialog.askstring(
        title="Choose Subtitle File",
        prompt="Multiple .srt files found:\n" + "\n".join(f"{i+1}. {name}" for i, name in enumerate(srt_files)) +
               "\n\nEnter the number of the subtitle to hardcode:"
    )
    try:
        index = int(choice) - 1
        if 0 <= index < len(srt_files):
            return os.path.join(folder, srt_files[index])
    except (ValueError, TypeError):
        pass

    messagebox.showerror("Invalid Selection", "No valid subtitle selected.")
    return None

def get_embedded_subtitles(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", video_path],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        subs = []
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "subtitle" and stream.get("codec_name") in ("mov_text", "subrip", "ass"):
                index = stream["index"]
                lang = stream.get("tags", {}).get("language", "und")
                subs.append((index, lang))
        return subs
    except Exception as e:
        print(f"Failed to extract subtitle streams: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Convert videos for PS5 playback")
    parser.add_argument("--sub", action="store_true", help="Hardcode subtitles from .srt file")
    parser.add_argument("--embed-sub", action="store_true", help="Burn subtitles from embedded subtitle stream")
    args = parser.parse_args()

    root = Tk()
    root.withdraw()

    input_path = filedialog.askopenfilename(
        title="Select a video to convert for PS5",
        filetypes=[("Video files", "*.mp4 *.mkv *.mov *.avi *.webm")]
    )
    if not input_path:
        print("No file selected. Exiting.")
        return

    downscale = simpledialog.askstring(
        title="Resolution Option",
        prompt="Type '1' to keep original resolution, or '2' to downscale to 1080p:"
    )

    base, ext = os.path.splitext(input_path)
    suffix = "_ps5_1080p" if downscale == "2" else "_ps5"
    output_path = base + suffix + ".mp4"

    subtitle_filter = []
    font_path = "C:/Windows/Fonts/GoogleSans-Regular.ttf"  # Adjust path if needed

    if args.sub:
        sub_path = choose_subtitle_file(input_path)
        if not sub_path:
            return
        style = "Fontsize=24,Alignment=2" if downscale == "2" else "Fontsize=36,Alignment=2"
        sub_filter = f"subtitles='{sub_path}':fontfile='{font_path}':force_style='{style}'"
        if downscale == "2":
            subtitle_filter = ["-vf", f"scale=-2:1080,{sub_filter}"]
        else:
            subtitle_filter = ["-vf", sub_filter]

    elif args.embed_sub:
        subs = get_embedded_subtitles(input_path)
        if not subs:
            print("❌ No embedded text subtitles found.")
            return

        sub_choices = "\n".join(f"{i+1}. Stream {idx} ({lang})" for i, (idx, lang) in enumerate(subs))
        choice = simpledialog.askstring(
            title="Embedded Subtitles",
            prompt=f"Choose subtitle stream to burn in:\n{sub_choices}\nEnter number:"
        )
        try:
            stream_index = subs[int(choice) - 1][0]
            sub_filter = f"subtitles='{input_path.replace(':', '\\\\:')}':si={stream_index}"
            if downscale == "2":
                subtitle_filter = ["-vf", f"scale=-2:1080,{sub_filter}"]
            else:
                subtitle_filter = ["-vf", sub_filter]
        except:
            print("❌ Invalid subtitle stream selection.")
            return

    elif downscale == "2":
        subtitle_filter = ["-vf", "scale=-2:1080"]

    command = [
        "ffmpeg",
        "-hwaccel", "cuda",
        "-i", input_path,
        "-c:v", "h264_nvenc",
        "-profile:v", "high",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-color_range", "tv",
        "-colorspace", "bt709",
        "-color_trc", "bt709",
        "-color_primaries", "bt709",
        "-b:v", "8M",
        "-threads", "0",
        "-c:a", "aac",
        "-b:a", "384k",
        "-ac", "6",
        "-ar", "48000",
        "-profile:a", "aac_low",
        "-movflags", "+faststart",
        *subtitle_filter,
        output_path
    ]

    print("\n🚀 Running FFmpeg command:")
    print(" ".join(command))
    print("\nEncoding...")

    subprocess.run(command)

    print(f"\n✅ Done! Output saved to:\n{output_path}")

if __name__ == "__main__":
    main()
