"""Prepare the checked Windows runtime from the upstream distribution files."""

import argparse
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from easytier import BUNDLED_FILES, BUNDLED_RUNTIME, RoomError, _digest, _verified, install_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('easytier_archive', type=Path)
    parser.add_argument('winpcap_packet_dll', type=Path)
    args = parser.parse_args()

    try:
        packet = args.winpcap_packet_dll.read_bytes()
        with TemporaryDirectory() as temporary:
            staging = Path(temporary)
            packet_path = staging / 'winpcap-packet.dll'
            packet_path.write_bytes(packet)
            if _digest(packet_path) != BUNDLED_FILES['Packet.dll']:
                parser.error('Packet.dll does not match the expected WinPcap x64 SHA-256.')
            install_archive(args.easytier_archive, staging / 'runtime')
            runtime = staging / 'runtime'
            packet_path.replace(runtime / 'Packet.dll')
            if not _verified(runtime, BUNDLED_FILES):
                parser.error('The staged EasyTier runtime failed verification.')
            BUNDLED_RUNTIME.mkdir(parents=True, exist_ok=True)
            for name in BUNDLED_FILES:
                (BUNDLED_RUNTIME / name).write_bytes((runtime / name).read_bytes())
    except (OSError, RoomError) as exc:
        parser.error(str(exc))
    print(f'Verified EasyTier files prepared in {BUNDLED_RUNTIME}')


if __name__ == '__main__':
    main()
