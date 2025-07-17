import time
import struct
import threading
from jnius import autoclass, cast
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

# Android Java classes via Pyjnius
Context = autoclass('android.content.Context')
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothLeAdvertiser = autoclass('android.bluetooth.le.BluetoothLeAdvertiser')
BluetoothLeScanner = autoclass('android.bluetooth.le.BluetoothLeScanner')
AdvertiseSettings = autoclass('android.bluetooth.le.AdvertiseSettings')
AdvertiseData = autoclass('android.bluetooth.le.AdvertiseData')
ScanSettings = autoclass('android.bluetooth.le.ScanSettings')
ScanFilter = autoclass('android.bluetooth.le.ScanFilter')
ParcelUuid = autoclass('android.os.ParcelUuid')
PythonActivity = autoclass('org.kivy.android.PythonActivity')

# Mesh configuration
MESH_UUID = '0000181B-0000-1000-8000-00805F9B34FB'
MAX_PAYLOAD_SIZE = 23
TTL_DEFAULT = 7

class BluetoothMeshComm:
    def __init__(self, node_id, network_key):
        self.node_id = node_id  # 2-byte node ID
        self.network_key = network_key  # 16-byte AES key
        self.adapter = BluetoothAdapter.getDefaultAdapter()
        self.activity = PythonActivity.mActivity
        self.advertiser = self.adapter.getBluetoothLeAdvertiser()
        self.scanner = self.adapter.getBluetoothLeScanner()
        self.running = False
        self.message_callback = None
        self.sequence_number = 0

    def start(self):
        """Start the mesh network."""
        if not self.adapter.isEnabled():
            print("Bluetooth not enabled")
            return
        self.running = True
        self._start_scanning()
        threading.Thread(target=self._advertise_presence, daemon=True).start()

    def stop(self):
        """Stop the mesh network."""
        self.running = False
        self.scanner.stopScan(self.scan_callback)
        self.advertiser.stopAdvertising(self.advertise_callback)

    def send_message(self, destination_id, text):
        """Send a text message."""
        if len(text) > MAX_PAYLOAD_SIZE:
            print("Message too long")
            return
        payload = text.encode('utf-8')
        encrypted_payload = self._encrypt_payload(payload)
        packet = self._create_mesh_packet(destination_id, 0x01, encrypted_payload)
        self._advertise_packet(packet)

    def _start_scanning(self):
        """Start scanning for mesh messages."""
        class ScanCallback:
            def __init__(self, mesh):
                self.mesh = mesh

            def onScanResult(self, callback_type, result):
                scan_record = result.getScanRecord().getBytes()
                self.mesh._process_mesh_message(scan_record)

        self.scan_callback = ScanCallback(self)
        scan_filter = ScanFilter.Builder().setServiceUuid(ParcelUuid.fromString(MESH_UUID)).build()
        scan_settings = ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_POWER).build()
        self.scanner.startScan([scan_filter], scan_settings, self.scan_callback)

    def _advertise_presence(self):
        """Advertise node presence periodically."""
        class AdvertiseCallback:
            def onStartSuccess(self, settings):
                pass

            def onStartFailure(self, error_code):
                print(f"Advertising failed: {error_code}")

        self.advertise_callback = AdvertiseCallback()
        settings = AdvertiseSettings.Builder() \
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_POWER) \
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_LOW) \
            .setConnectable(False) \
            .build()
        data = AdvertiseData.Builder() \
            .addServiceUuid(ParcelUuid.fromString(MESH_UUID)) \
            .build()

        while self.running:
            self.advertiser.startAdvertising(settings, data, self.advertise_callback)
            time.sleep(5.0)
            self.advertiser.stopAdvertising(self.advertise_callback)

    def _advertise_packet(self, packet):
        """Advertise a specific packet."""
        settings = AdvertiseSettings.Builder() \
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY) \
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_MEDIUM) \
            .setConnectable(False) \
            .build()
        data = AdvertiseData.Builder() \
            .addServiceUuid(ParcelUuid.fromString(MESH_UUID)) \
            .addServiceData(ParcelUuid.fromString(MESH_UUID), packet) \
            .build()
        self.advertiser.startAdvertising(settings, data, self.advertise_callback)
        time.sleep(0.1)
        self.advertiser.stopAdvertising(self.advertise_callback)

    def _create_mesh_packet(self, destination_id, opcode, payload, ttl=TTL_DEFAULT):
        """Create a mesh packet."""
        packet = bytearray(8 + len(payload))
        packet[0] = opcode
        struct.pack_into('>HHBH', packet, 1, self.node_id, destination_id, ttl, self.sequence_number)
        packet[7:] = payload
        self.sequence_number = (self.sequence_number + 1) % 0xFFFF
        return bytes(packet)

    def _process_mesh_message(self, scan_record):
        """Process received mesh message."""
        if len(scan_record) < 8:
            return

        opcode = scan_record[0]
        source_id = struct.unpack('>H', scan_record[1:3])[0]
        destination_id = struct.unpack('>H', scan_record[3:5])[0]
        ttl = scan_record[5]
        seq_num = struct.unpack('>H', scan_record[6:8])[0]
        encrypted_payload = scan_record[8:]

        if ttl <= 0:
            return

        payload = self._decrypt_payload(encrypted_payload)
        if opcode == 0x01:
            message = payload.decode('utf-8', errors='ignore')
            if self.message_callback:
                self.message_callback(f"Node {source_id}: {message}")

        if ttl > 1 and self.running:
            packet = self._create_mesh_packet(destination_id, opcode, payload, ttl - 1)
            self._advertise_packet(packet)

    def _encrypt_payload(self, payload):
        """Encrypt payload with AES-128."""
        cipher = Cipher(algorithms.AES(self.network_key), modes.ECB(), default_backend())
        encryptor = cipher.encryptor()
        padded_payload = payload + b'\x00' * (16 - len(payload) % 16)
        return encryptor.update(padded_payload) + encryptor.finalize()

    def _decrypt_payload(self, encrypted_payload):
        """Decrypt payload with AES-128."""
        cipher = Cipher(algorithms.AES(self.network_key), modes.ECB(), default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted_payload) + decryptor.finalize()
        return decrypted.rstrip(b'\x00')

class MeshCommApp(App):
    def __init__(self, **kwargs):
        super().__init__()
        self.mesh = BluetoothMeshComm(node_id=0x0001, network_key=b'0123456789abcdef')
        self.mesh.message_callback = self.add_message

    def build(self):
        layout = BoxLayout(orientation='vertical')
        self.message_display = GridLayout(cols=1, size_hint_y=None)
        self.message_display.bind(minimum_height=self.message_display.setter('height'))
        scroll_view = ScrollView()
        scroll_view.add_widget(self.message_display)
        layout.add_widget(scroll_view)

        input_layout = BoxLayout(size_hint_y=None, height=100)
        self.text_input = TextInput(multiline=False, size_hint_x=0.8)
        send_button = Button(text='Send', size_hint_x=0.2)
        send_button.bind(on_press=self.send_message)
        input_layout.add_widget(self.text_input)
        input_layout.add_widget(send_button)
        layout.add_widget(input_layout)

        start_button = Button(text='Start Network', size_hint_y=None, height=50)
        start_button.bind(on_press=lambda x: self.mesh.start())
        stop_button = Button(text='Stop Network', size_hint_y=None, height=50)
        stop_button.bind(on_press=lambda x: self.mesh.stop())
        layout.add_widget(start_button)
        layout.add_widget(stop_button)

        return layout

    def add_message(self, message):
        self.message_display.add_widget(Label(text=message, size_hint_y=None, height=30))

    def send_message(self, instance):
        text = self.text_input.text.strip()
        if text:
            self.mesh.send_message(0xFFFF, text)
            self.text_input.text = ''

if __name__ == '__main__':
    MeshCommApp().run()