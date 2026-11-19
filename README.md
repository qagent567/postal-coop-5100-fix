# POSTAL 2 Nicks Coop 5100 Fix

Windows utility for the Steam Workshop launch loop: selecting **Nicks Coop** restarts POSTAL 2 and returns to its regular menu. The fix is for Steam build **5100** and [Nicks Coop Workshop item 737631813](https://steamcommunity.com/sharedfiles/filedetails/?id=737631813).

## How to use

1. Subscribe to Nicks Coop. Launch Steam build **5100** on the default branch and open **New Game → Workshop** once so the game can unpack the mod. Close POSTAL 2.
2. Download `Postal2Coop5100Fix.exe` from [Releases](https://github.com/qagent567/postal-coop-5100-fix/releases/latest). Open it and select **1. Repair Workshop launch**. If prompted, select or enter your `POSTAL2Complete` folder.
3. Start POSTAL 2 again and select **New Game → Workshop → Nicks Coop → Start**. After the restart, the **Co-Op Game** menu should appear.

The utility restores the mod's launch settings and updates `ConfigVer` and `FirstRun` to 5100. It copies the previous INI to `POSTAL2Complete\Coop5100\Postal2CoOp.ini.original`. Choose option **2** to restore it. If the mod still points to the default game save and cache folders, the utility redirects them to `POSTAL2Complete\Coop5100`. Existing custom paths are preserved.

This project fixes the Workshop launch. The game and mod still come from Steam. Opening the Co-Op Game menu on 5100 was verified in-game. Multiplayer connections and campaign progression have yet to be verified.

## По-русски

Утилита исправляет возврат в обычное меню после запуска **Nicks Coop** из Мастерской на версии **5100**. Подпишитесь на мод, откройте **Новая игра → Мастерская**, затем закройте POSTAL 2. Скачайте `Postal2Coop5100Fix.exe` из [релиза](https://github.com/qagent567/postal-coop-5100-fix/releases/latest) и выберите **1**. После этого откройте **Новая игра → Мастерская → Nicks Coop → Старт**. Пункт **2** возвращает прежний конфиг. Установка Python для запуска `.exe` не нужна.

## Run or build from source

```powershell
python coop5100_fix.py
python -m pip install PyInstaller==6.22.3
python -m PyInstaller --onefile --name Postal2Coop5100Fix --specpath build coop5100_fix.py
```

The Windows executable is created in `dist`. Run `python coop5100_fix.py --help` for command-line options.

Nicks Coop is by NickTheDark. This is an unofficial configuration fix for his Workshop release.
