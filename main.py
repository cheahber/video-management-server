import time

import requests
from urllib.parse import urlencode

from recorder import StreamRecorder


class Go2RTCClient:
    """Manages go2rtc API interactions and recording sessions."""

    def __init__(self, base_url='http://localhost:1984', output_dir='/path/to/save/recordings'):
        self.base_url = base_url
        self.recorders = {}  # Stores active recordings {stream_name: StreamRecorder}
        self.output_dir = output_dir

    def _send_request(self, method, endpoint, params=None):
        """Helper method to send requests with URL encoding and error handling."""
        url = f"{self.base_url}{endpoint}"
        if params:
            url += f"?{urlencode(params)}"

        try:
            response = requests.request(method, url)

            if not response.text.strip():
                print(f"✅ {method} request to {endpoint} completed successfully.")
                return {}

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f'❌ API error on {method} request to {endpoint}: {e}')
            return {}

    def list_streams(self):
        """Retrieve a list of all streams, returning an empty dict if none exist."""
        return self._send_request('GET', '/api/streams')

    def add_stream(self, name, src):
        """Add a new stream and start recording it continuously."""
        result = self._send_request('PUT', '/api/streams', {'name': name, 'src': src})
        self.start_recording(name)
        return result

    def update_stream(self, name, src):
        """Update an existing stream."""
        return self._send_request('PUT', '/api/streams', {'name': name, 'src': src})

    def delete_stream(self, src):
        """Delete a stream and stop recording."""
        result = self._send_request('DELETE', '/api/streams', {'src': src})
        if result:
            self.stop_recording(src)
        return result

    def discover_ffmpeg_devices(self):
        """Discover FFmpeg-compatible USB devices."""
        return self._send_request('GET', '/api/ffmpeg/devices')

    def discover_onvif_cameras(self):
        """Discover ONVIF cameras on the network."""
        return self._send_request('GET', '/api/onvif')

    def start_recording(self, stream_name):
        """Start recording a stream continuously using RTSP format."""
        if stream_name not in self.recorders:
            stream_url = f"rtsp://localhost:8554/{stream_name}"  # Generate RTSP URL dynamically
            print(f"🎬 Starting recording for {stream_name} at {stream_url}")
            recorder = StreamRecorder(stream_url, self.output_dir)
            self.recorders[stream_name] = recorder
            recorder.start()
        else:
            print(f"⚠️ Recording already running for {stream_name}")

    def stop_recording(self, stream_name):
        """Stop recording a stream."""
        if stream_name in self.recorders:
            print(f"🛑 Stopping recording for {stream_name}")
            self.recorders[stream_name].stop()
            del self.recorders[stream_name]
        else:
            print(f"⚠️ No recording found for {stream_name}")

if __name__ == '__main__':
    client = Go2RTCClient(output_dir='./recordings')

    # # 🔍 Discover FFmpeg USB devices
    # ffmpeg_devices = client.discover_ffmpeg_devices()
    # if ffmpeg_devices:
    #     print('🎥 FFmpeg USB Devices:', ffmpeg_devices)
    # else:
    #     print('📭 No FFmpeg USB devices found.')
    #
    # # 🔍 Discover ONVIF cameras
    # onvif_cameras = client.discover_onvif_cameras()
    # if onvif_cameras:
    #     print('📷 ONVIF Cameras:', onvif_cameras)
    # else:
    #     print('📭 No ONVIF cameras found.')


    # 📺 Add a new stream
    if client.add_stream('my_stream', 'ffmpeg:/home/intel/Desktop/sample.mp4'):
        print('✅ Stream added successfully')

    # 📡 List all streams
    streams = client.list_streams()
    if streams:
        print('📺 Current streams:', streams)
    else:
        print('📭 No streams available.')

    # 🔄 Update the stream
    if client.update_stream('my_stream', 'ffmpeg:/home/intel/Desktop/sample.mp4'):
        print('✅ Stream updated successfully')

    time.sleep(100)

    # 🗑️ Delete the stream
    if client.delete_stream('my_stream'):
        print('🗑️ Stream deleted successfully')

