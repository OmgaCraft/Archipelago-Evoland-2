"""Lecteur/extracteur des fichiers .pak (format Heaps.io) d'Evoland Legendary Edition.

Usage :
    python pak.py list    <fichier.pak> [filtre]
    python pak.py extract <fichier.pak> <dossier_sortie> [filtre]
"""
import os
import struct
import sys


def read_pak(path):
    """Retourne (header_size, liste de (chemin, position, taille))."""
    with open(path, "rb") as f:
        if f.read(3) != b"PAK":
            raise ValueError("Pas un fichier PAK Heaps")
        version = f.read(1)[0]
        header_size, _data_size = struct.unpack("<ii", f.read(8))
        entries = []

        def read_entry(prefix):
            name_len = f.read(1)[0]
            name = f.read(name_len).decode("utf-8")
            flags = f.read(1)[0]
            full = f"{prefix}/{name}" if prefix else name
            if flags & 1:  # dossier
                (count,) = struct.unpack("<i", f.read(4))
                for _ in range(count):
                    read_entry(full)
            else:
                if flags & 2:  # position sur 64 bits (double)
                    (pos,) = struct.unpack("<d", f.read(8))
                    pos = int(pos)
                else:
                    (pos,) = struct.unpack("<i", f.read(4))
                size, _checksum = struct.unpack("<ii", f.read(8))
                entries.append((full, pos, size))

        read_entry("")
        return header_size, version, entries


def main():
    cmd, pak = sys.argv[1], sys.argv[2]
    header_size, _, entries = read_pak(pak)
    if cmd == "list":
        flt = sys.argv[3] if len(sys.argv) > 3 else ""
        for name, pos, size in entries:
            if flt in name:
                print(f"{size:>10}  {name}")
    elif cmd == "extract":
        out = sys.argv[3]
        flt = sys.argv[4] if len(sys.argv) > 4 else ""
        with open(pak, "rb") as f:
            for name, pos, size in entries:
                if flt not in name:
                    continue
                f.seek(header_size + pos)
                dest = os.path.join(out, name)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as o:
                    o.write(f.read(size))
                print("extrait :", name)


if __name__ == "__main__":
    main()
