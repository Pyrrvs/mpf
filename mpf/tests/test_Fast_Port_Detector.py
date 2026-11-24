"""Test the FAST serial port auto-detection."""
import asyncio
import unittest
from unittest.mock import MagicMock, patch

from mpf.platforms.fast.fast_port_detector import FastPortDetector


class FakeBoard:

    """A port that still holds old output and answers ID: after it."""

    def __init__(self, stale):
        self.incoming = bytearray(stale)
        self.data_ready = asyncio.Event()
        self.data_ready.set()
        self.transport = MagicMock()
        self.written = bytearray()

    async def read(self, size):
        while not self.incoming:
            self.data_ready.clear()
            await self.data_ready.wait()
        chunk = bytes(self.incoming[:size])
        del self.incoming[:size]
        return chunk

    def write(self, data):
        self.written += data
        if data == b'ID:\r':
            self.incoming += b'ID:NET FP-CPU-2000  02.13\r'
            self.data_ready.set()

    def close(self):
        pass


class TestFastPortDetector(unittest.IsolatedAsyncioTestCase):

    async def test_detects_port_behind_leftover_bytes(self):
        # 1000 old bytes: more than the five 100-byte reads of the ID: loop
        board = FakeBoard(b'\x00' * 1000)

        async def connect():
            return board, board

        platform = MagicMock()
        platform.config = {'net': {}}
        platform.machine.clock.open_serial_connection.return_value = connect()

        with patch('mpf.platforms.fast.fast_port_detector.list_ports.comports', return_value=[]):
            detector = FastPortDetector(platform, ['net'], [])
        await detector._connect_task('com3', 921600)

        self.assertEqual({'net': 'com3'}, detector.results)
        self.assertTrue(board.written.startswith(b'\r\r\r\r'))
