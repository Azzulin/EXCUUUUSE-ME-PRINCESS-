# AoC Recomp — player's guide

*(Versão em português: [GUIA.md](GUIA.md).)*

AoC Recomp turns **your own copy** of *Hyrule Warriors: Age of Calamity* (Nintendo Switch, update 1.3.0) into a
native version for the **Steam Deck**, **Linux** and **Windows**. The launcher does the whole job on your PC: it reads
your files, sets up the tools it needs and compiles the game. Nothing from the game comes with this download, and
nothing you make should be shared.

---

## 1. What you need

| | |
|---|---|
| **Your game files**, in one folder | the base game NSP (`01002B00111A2000`), the **update 1.3.0** NSP (`01002B00111A2800`), the DLC NSPs (optional) and your console's **`prod.keys`**, all dumped from **your own** Switch |
| **A PC** | Windows 10 (version 2004 or newer) or Windows 11, or a 64-bit Linux with `python3` (almost every distribution has it); **8 GB of RAM** (16 GB is better) |
| **Free disk space** | about **45 GB** the first time (it drops to ~25 GB when the build is done) |
| **Internet** | only the first time: the launcher downloads ~2 GB of free tools (compiler, Linux for Windows) |
| **To play on the PC** | a graphics card with Vulkan (any recent NVIDIA, AMD or Intel) |

---

## 2. Windows, step by step

1. **Download** `AoC-Recomp-<version>-Windows.zip` from the project's *Releases* page.
2. **Extract** it: right-click the zip → *Extract All…* → choose a folder with room, for example `C:\Games`.
   You get a folder called `AoC-Recomp`.
3. Open **`AoC-Launcher.exe`** inside it. Windows may say it "protected your PC" (the program is not signed):
   click *More info* → *Run anyway*.
4. **YOUR COPY** — click **Browse…** and pick the folder with your NSPs and `prod.keys`.
   Four green dots mean everything was found.
5. **WHERE YOU WILL PLAY** — tick **Steam Deck / Linux**, **Windows (this PC)**, or both.
6. Click **FORGE** (bottom right) and let the PC work. The first time takes **1 to 2 hours**; the list on the right
   shows each step and the time it took. You can keep using the PC, it will only be slower.
7. When it is done:
   - **Windows:** the window turns into the game's launcher (below). Press **PLAY**.
   - **Steam Deck:** copy the folder to the Deck (section 4); **Deck folder** at the bottom opens it.

**The game's launcher.** Once the game for this PC is forged, `AoC-Launcher.exe` opens straight on it:

| | |
|---|---|
| **GRAPHICS** | window mode and size, presentation (VSync), game resolution (1920 × 1080 or the lighter 1280 × 720), internal resolution (TV or handheld), 3D render scale, picture shape, texture filtering, shadows, performance overlay |
| **CONTROLS AND SOUND** | button layout (Nintendo or Xbox), vibration, stick dead zone, invert camera, volume, mute in the background, in-game menu language |
| Bottom bar | **Report…** (a zip with the logs and your PC's details, for asking for help), **Game folder**, **Forge again** (after an update, or to add the Steam Deck version), **Save**, **Close**, and **PLAY** |

Hover over a setting for a short explanation. **PLAY** saves first. Everything else (remapping buttons, colours, HDR)
is in the game's own menu: **F1**, or Minus + Plus on a controller.

> **"WSL is not installed"?** The Steam Deck version is compiled inside WSL (Linux that comes with Windows). Click
> **Install WSL**, accept the administrator question, **restart the PC**, open the launcher again and click
> **FORGE** once more. It continues from where it stopped. If WSL still fails, turn on *virtualization*
> (Intel VT-x / AMD SVM) in your PC's BIOS.

The language switch (**PT / EN**) is at the top right; **Guide** opens this page.

---

## 3. Linux, step by step

1. **Download** `AoC-Recomp-<version>-Linux.tar.gz` and extract it:
   ```sh
   tar xf AoC-Recomp-*-Linux.tar.gz
   cd AoC-Recomp
   ./aoc-launcher
   ```
2. Same steps as on Windows (pick the folder, keep **Steam Deck / Linux** ticked, **FORGE**).
3. The first time, your system asks for your **password**: the launcher installs the compiler with your package
   manager (`pacman`, `apt` or `dnf`). Tested on Arch Linux; Ubuntu/Debian and Fedora are supported by the setup
   script but not tested yet — if they fail, the log says which package is missing.
4. When it is done the window turns into the game's launcher, as on Windows: settings and **PLAY** (or run
   `dist/aoc-deck/aoc.sh`). The same folder also works on the Steam Deck.

---

## 4. Copying to the Steam Deck

The Deck does not compile anything: it gets the ready folder `AoC-Recomp/dist/aoc-deck`.

1. **The first time**, tick **include romfs.bin** before forging (the game data, 10.9 GiB, goes into the folder). For
   later updates you can leave it unticked: the data does not change.
2. Copy the whole `aoc-deck` folder to the Deck — USB stick, SD card, network share, or `scp` — for example to the
   SD card: `/run/media/mmcblk0p1/aoc-deck`.
3. On the Deck, in **Desktop Mode**, open the folder, open a terminal there (*Konsole*) and run once:
   ```sh
   sh instalar-atalho.sh
   ```
4. In Steam: *Games* → *Add a Non-Steam Game* → tick **Hyrule Warriors: Age of Calamity (AoC Recomp)** → *Add*.
   Back in **Game Mode** it is in your library.

The `LEIA-ME.txt` file in the folder has the controls (hold **L3+R3** for the quick menu) and the log tools.

---

## 5. Updating to a new version

Extract the new zip **over the old `AoC-Recomp` folder** (replace the files) and forge again. Your `build` and `dist`
folders stay, so it only redoes what changed — usually minutes. Saves and settings in `dist/*/profile` and
`dist/*/aoc.ini` are never overwritten. On the Deck, copy only the `aoc` file and the `lib` folder again.

---

## 6. Where things go, and how to remove them

| What | Where | Size |
|---|---|---|
| The launcher, the game data it extracted, the finished folders | the `AoC-Recomp` folder (`build/`, `dist/`) | ~25 GB |
| Linux for Windows (only for the Steam Deck version) | WSL distro **AoC-Recomp**, in `%LOCALAPPDATA%\AoC-Recomp\wsl` | ~6 GB |
| The Windows compiler (only for the Windows version) | `C:\msys64` (MSYS2), if you did not have it already | ~3 GB |
| Linux: compiler build folder and Python packages | `~/aoc-build`, `~/.venvs/aoc` | ~6 GB |

To remove everything: delete the `AoC-Recomp` folder; on Windows run `wsl --unregister AoC-Recomp` in a terminal, and
delete `C:\msys64` if the launcher installed it; on Linux delete `~/aoc-build` and `~/.venvs/aoc`.

---

## 7. If something goes wrong

- **A red dot in "Your files"**: the file is not in the chosen folder. The NSP names must contain the title IDs shown,
  and `prod.keys` must sit in the same folder.
- **"Not enough free space"**: the message says how much is needed; free some space and forge again.
- **A step failed**: the reason is under the step, in red, and the full log is below. Click **FORGE** again:
  finished steps are skipped. **Only check** tests your dump without building. To ask for help, press **Report…**
  and attach `aoc-report.zip` (it holds the logs and your PC's details, nothing of the game).
- **The build is very slow**: an antivirus scanning every file slows the compiler a lot; adding the `AoC-Recomp`
  folder (and on Windows `%LOCALAPPDATA%\AoC-Recomp`) to its exclusions helps.
- **The game shows stutters the first time**: shaders are translated while you play the first time; they are cached
  for the next sessions.
- **The game froze, the screen went black or dark, or an effect is missing**: the game writes a report to its log by
  itself when it shows no picture for 10 s or stays black/dark for 15 s; press **F8** when you see any other glitch to
  mark it. To look into hits and effects, start the game with `monitor.bat` in the game folder (Windows) instead of
  **PLAY**: it saves pictures of every hit and a full frame capture at a mark or a dark scene (a bit slower, and it
  takes space in `logs\diag`). Then press **Report…** and send the zip.

---

## Legal

Use only a copy you own, dumped from your own console. This project contains no game code, data or keys, and it is
not affiliated with Nintendo or Koei Tecmo. The project's own code is under the [MIT licence](LICENSE); the components
it uses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
