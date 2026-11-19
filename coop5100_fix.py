"""Repair the Steam Workshop launch configuration for Nicks Coop on POSTAL 2 5100."""

import argparse
import csv
from contextlib import contextmanager
import os
from pathlib import Path
import re
import subprocess
import tempfile

if os.name == "nt":
    import msvcrt
    import winreg


APP_ID = "223470"
WORKSHOP_ID = "737631813"
GAME_MODE = b"NicksCoop.CoopGameInfoMenu"
CONFIG = "Postal2CoOp.ini"


class RepairError(Exception):
    pass


def steam_installations():
    steam_roots = []
    for hive, key, value in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ):
        try:
            with winreg.OpenKey(hive, key) as registry_key:
                steam_roots.append(Path(winreg.QueryValueEx(registry_key, value)[0]))
        except OSError:
            continue

    default_root = os.environ.get("ProgramFiles(x86)", os.environ.get("ProgramFiles"))
    if default_root:
        steam_roots.append(Path(default_root) / "Steam")

    libraries = set(steam_roots)
    for root in steam_roots:
        index = root / "steamapps" / "libraryfolders.vdf"
        if index.is_file():
            data = index.read_text(encoding="utf-8-sig", errors="replace")
            for path in re.findall(r'^\s*"(?:path|\d+)"\s*"([^"\r\n]+)"', data, re.M):
                libraries.add(Path(path.replace("\\\\", "\\")))

    installations = set()
    for library in libraries:
        apps = library / "steamapps"
        manifest = apps / f"appmanifest_{APP_ID}.acf"
        if not manifest.is_file():
            continue
        match = re.search(r'^\s*"installdir"\s*"([^"\r\n]+)"',
                          manifest.read_text(encoding="utf-8-sig", errors="replace"), re.M)
        if match:
            game = apps / "common" / match[1]
            if (game / "System" / "Postal2.exe").is_file():
                installations.add(game.resolve())
    return sorted(installations)


def require_closed_game():
    tasklist = Path(os.environ["SystemRoot"]) / "System32" / "tasklist.exe"
    result = subprocess.run([str(tasklist), "/FO", "CSV", "/NH"],
                            capture_output=True, text=True, errors="replace",
                            check=True, timeout=15)
    running = {row[0].lower() for row in csv.reader(result.stdout.splitlines()) if row}
    if running & {"postal2.exe", "postal2coop.exe"}:
        raise RepairError("Close POSTAL 2 before changing the configuration.")


def ini_setting(contents, key):
    match = re.search(rb"(?m)^" + key + rb"=([^\r\n]*)", contents)
    return match[1].strip() if match else None


def set_ini_setting(contents, key, value):
    updated, count = re.subn(rb"(?m)^" + key + rb"=[^\r\n]*",
                             lambda _: key + b"=" + value, contents)
    if count != 1:
        raise RepairError(f"Expected one {key.decode()} entry in the Nicks Coop configuration.")
    return updated


def atomic_write(destination, data):
    descriptor, path = tempfile.mkstemp(prefix="coop5100-", dir=destination.parent)
    temporary = Path(path)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def installation_lock(profile):
    with (profile / "repair.lock").open("a+b") as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise RepairError("Another repair is running. Close it and try again.") from error
        yield


def repair(game, restore=False):
    system = game / "System"
    workshop = game / "WorkshopContent" / WORKSHOP_ID
    config = workshop / CONFIG
    profile = game / "Coop5100"
    backup = profile / (CONFIG + ".original")
    if not (system / "Postal2.exe").is_file():
        raise RepairError("Select the POSTAL2Complete folder containing System\\Postal2.exe.")

    if not restore:
        defaults = system / "Default.ini"
        if not defaults.is_file() or ini_setting(defaults.read_bytes(), b"ConfigVer") != b"5100":
            raise RepairError("This fix requires POSTAL 2 build 5100. Select the default Steam branch.")
        if not all(path.is_file() for path in (config, workshop / "Scripts" / "NicksCoop.u")):
            raise RepairError("Subscribe to Nicks Coop, open the in-game Workshop once, then close the game.")
    elif not backup.is_file() or not workshop.is_dir():
        raise RepairError("The original configuration backup or Workshop directory is missing.")

    require_closed_game()
    profile.mkdir(exist_ok=True)
    with installation_lock(profile):
        if restore:
            atomic_write(config, backup.read_bytes())
            return "Original Workshop configuration restored. Co-op saves are still in Coop5100\\Save."

        original = config.read_bytes()
        settings = original
        if ini_setting(settings, b"DefaultGame") != GAME_MODE:
            template = workshop / "Default_Postal2CoOp.nodelete"
            if not template.is_file():
                raise RepairError("The original Nicks Coop template is missing. Re-download the Workshop item.")
            settings = template.read_bytes()
        if ini_setting(settings, b"DefaultGame") != GAME_MODE:
            raise RepairError("The Nicks Coop configuration does not contain the expected game mode.")

        settings = set_ini_setting(settings, b"ConfigVer", b"5100")
        settings = set_ini_setting(settings, b"FirstRun", b"5100")
        for key, folder in ((b"SavePath", "Save"), (b"CachePath", "Cache")):
            current_path = ini_setting(settings, key)
            if not current_path or current_path.lower() == b"..\\" + folder.lower().encode():
                (profile / folder).mkdir(exist_ok=True)
                settings = set_ini_setting(settings, key, b"..\\Coop5100\\" + folder.encode())

        if settings == original:
            return "Nicks Coop already has the required configuration."
        if not backup.exists():
            atomic_write(backup, original)
        atomic_write(config, settings)
    return "Repair applied. Start POSTAL 2 and select New Game > Workshop > Nicks Coop > Start."


def choose_installation():
    games = steam_installations()
    if len(games) == 1:
        return games[0]
    for number, game in enumerate(games, 1):
        print(f"  {number}. {game}")
    choice = input("Enter the number above or paste the POSTAL2Complete folder path: ").strip()
    if choice.isascii() and choice.isdecimal() and 1 <= int(choice) <= len(games):
        return games[int(choice) - 1]
    if not choice:
        raise RepairError("No game folder was selected.")
    return Path(choice.strip('"')).expanduser().resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="apply the fix without the menu")
    action.add_argument("--restore", action="store_true", help="restore the first backup")
    parser.add_argument("--game-dir", type=Path, help="path to POSTAL2Complete")
    args = parser.parse_args()
    interactive = not (args.apply or args.restore)
    try:
        if os.name != "nt":
            raise RepairError("This utility runs on Windows.")
        game = args.game_dir.expanduser().resolve() if args.game_dir else choose_installation()
        restore = args.restore
        if interactive:
            print(f"\nPOSTAL 2 Nicks Coop repair (Steam 5100)\n{game}\n")
            choice = input("1. Repair Workshop launch\n2. Restore original configuration\nEnter to exit\n> ").strip()
            if choice not in {"1", "2"}:
                return 0
            restore = choice == "2"
        print(repair(game, restore))
        return 0
    except (RepairError, OSError, subprocess.SubprocessError) as error:
        print(f"Error: {error}")
        return 1
    except (EOFError, KeyboardInterrupt):
        return 1
    finally:
        if interactive:
            try:
                input("\nPress Enter to close.")
            except (EOFError, KeyboardInterrupt):
                pass


if __name__ == "__main__":
    raise SystemExit(main())
