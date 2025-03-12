import os
import datetime
import subprocess
import threading
import time

class StreamRecorder:
    """Handles continuous recording of a stream using FFmpeg safely with automatic segment merging."""

    def __init__(self, stream_url, output_dir, segment_time=600, retry_interval=1, max_retries=30, username=None, password=None):
        """
        Initialize the StreamRecorder.

        :param stream_url: The stream URL to record.
        :param output_dir: Directory to save the recordings.
        :param segment_time: Duration of each segment file (default: 10 minutes).
        :param retry_interval: Seconds to wait before retrying if RTSP is unavailable (default: 1s).
        :param max_retries: Maximum number of retries before failing.
        :param username: Optional username for RTSP authentication.
        :param password: Optional password for RTSP authentication.
        """
        self.stream_url = self._build_auth_url(stream_url, username, password)
        self.output_dir = output_dir
        self.segment_time = segment_time
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.recording = False
        self.thread = None
        self.file_list_path = os.path.join(self.output_dir, "file_list.txt")

        os.makedirs(self.output_dir, exist_ok=True)

    def _build_auth_url(self, url, username, password):
        """Adds authentication to the RTSP URL if needed."""
        if username and password:
            parsed_url = url.replace("rtsp://", f"rtsp://{username}:{password}@")
            print(f"🔐 Using authenticated RTSP URL: {parsed_url}")
            return parsed_url
        return url

    def _is_rtsp_available(self):
        """Check if RTSP stream is available before recording using GStreamer."""
        for attempt in range(1, self.max_retries + 1):
            print(f"⏳ Checking RTSP stream availability (Attempt {attempt}/{self.max_retries})...")

            try:
                result = subprocess.run(
                    ['gst-discoverer-1.0', self.stream_url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5  # Prevents hanging
                )

                output = result.stdout.decode().strip()
                error_output = result.stderr.decode().strip()

                if result.returncode == 0 and "video" in output.lower():
                    print(f"✅ RTSP stream is available! Details:\n{output}")
                    return True
                else:
                    print(f"⚠️ RTSP stream might be empty. Output:\n{output}\nErrors:\n{error_output}")

            except subprocess.TimeoutExpired:
                print("⏳ GStreamer discovery timed out. Retrying...")
            except Exception as e:
                print(f"❌ Error checking RTSP stream: {e}")

            time.sleep(self.retry_interval)

        print("🚨 RTSP stream did not become available. Aborting recording.")
        return False

    def _record(self):
        """Optimized GStreamer RTSP recording with x264enc and Matroska format."""
        if not self._is_rtsp_available():
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_file = os.path.join(self.output_dir, f"recording_{timestamp}.mkv")

        gst_command_str = (
            f'gst-launch-1.0 rtspsrc location={self.stream_url} ! decodebin '
            '! videoconvert ! video/x-raw'        
            '! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2048 '
            '! h264parse '
            '! matroskamux '
            f'! filesink location={output_file} sync=1 async=1'
        )

        try:
            print(f"🎥 Starting GStreamer recording with x264enc: {output_file}")
            process = subprocess.Popen(gst_command_str.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True)

            # Stream logs
            for line in iter(process.stderr.readline, ''):
                print(line, end='')

            process.wait()
        except subprocess.CalledProcessError as e:
            print(f"❌ GStreamer error: {e}")
            self.recording = False

    def start(self):
        """Start recording the stream in a separate thread."""
        if not self.recording:
            print(f"🎥 Waiting for RTSP stream to be available for {self.stream_url}")
            self.recording = True
            self.thread = threading.Thread(target=self._record, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop recording the stream and merge segments into one file."""
        if self.recording:
            print(f"🛑 Stopping recording for {self.stream_url}")
            self.recording = False
            if self.thread:
                self.thread.join()

            self.merge_segments()

    def merge_segments(self):
        """Automatically merge recorded segments into a single file when recording stops."""
        print("🔄 Merging recorded segments into one file...")

        # Create a list of recorded files
        with open(self.file_list_path, "w") as f:
            for file in sorted(os.listdir(self.output_dir)):
                if file.startswith("segment_") and file.endswith(".mp4"):
                    f.write(f"file '{os.path.join(self.output_dir, file)}'\n")

        merged_output = os.path.join(self.output_dir, "final_recording.mp4")
        merge_command = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', self.file_list_path,
            '-c', 'copy', merged_output
        ]

        try:
            subprocess.run(merge_command, check=True)
            print(f"✅ Merged recording saved: {merged_output}")

            # Delete old segment files
            for file in sorted(os.listdir(self.output_dir)):
                if file.startswith("segment_") and file.endswith(".mp4"):
                    os.remove(os.path.join(self.output_dir, file))
        except subprocess.CalledProcessError as e:
            print(f"❌ Merging error: {e}")


if __name__ == '__main__':
    recorder = StreamRecorder(
        stream_url="rtsp://localhost:8554/my_stream",
        output_dir="./recordings",
        segment_time=600,
        username="admin",  # Optional: Add authentication if needed
        password="password"
    )

    recorder.start()  # Start recording
    time.sleep(30)  # Let it record for 30 seconds
    recorder.stop()  # Stop and merge files
