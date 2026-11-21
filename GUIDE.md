# AoC Recomp — player's guide

*(Versão em português: [GUIA.md](GUIA.md).)*

AoC Recomp turns **your own copy** of *Hyrule Warriors: Age of Calamity* (Nintendo Switch, update 1.3.0) into a
native version for the **Steam Deck**, **Linux** and **Windows**. The launcher does the whole job on your PC: it reads
your files, sets up the tools it needs and compiles the game. Nothing from the game comes with this download, and
nothing you make should be shared.

**The short version:** download the launcher → extract it to a folder with room → open it → pick the folder with your
NSPs and `prod.keys` → **BUILD** → wait 1 to 2 hours → **PLAY**. The rest of this page is the detail, and what to do
when something goes wrong.

---

## 1. What you need

| | |
|---|---|
| **Your game files**, in one folder | the base game NSP (`01002B00111A2000`), the **update 1.3.0** NSP (`01002B00111A2800`), the DLC NSPs (optional) and your console's **`prod.keys`**, all dumped from **your own** Switch. The update must be **1.3.0** (v327680): 1.4.1 is not accepted yet. The files can have any name: the builder identifies them by their contents |
| **A PC to build on** | Windows 10 (version 2004 or newer) or Windows 11, or a 64-bit Linux with `python3` (almost every distribution has it); **8 GB of RAM** (16 GB is better) |
| **Free disk space** | about **45 GB** the first time (it drops to ~25 GB when the build is done), on an **NTFS** drive on Windows (not FAT32 or exFAT: the game data is one 10.9 GiB file). An SSD makes the build much faster |
| **Internet** | only the first time: the launcher downloads ~2 GB of free tools (compiler, Linux for Windows) |
| **To play on the PC** | a processor with **AVX2**: Intel Core 4th generation (2013) or newer, AMD Ryzen or newer (older Pentium, Celeron and AMD FX do not have it). A graphics card with **Vulkan 1.3** and an up-to-date driver: NVIDIA GeForce GTX 900 or newer, AMD Radeon RX 400 or newer. Intel graphics have not been tested yet |
| **To play on the Steam Deck** | nothing beyond the Deck: any PC above can build the Deck's folder, even one whose processor or graphics card cannot run the game itself |

### Before you start: four checks that avoid most failures

1. **Is the update 1.3.0?** In the NSP's name, `v327680` is 1.3.0; `v458752` is 1.4.1, which does not work yet. If you
   are not sure, the builder reads each file before compiling anything and stops with a clear message when the update
   is another version (on Windows, **Only check** does just that, in seconds).
2. **Is `prod.keys` in the same folder as the NSPs?** It must come from the same console the game was dumped from.
3. **Where will the `AoC-Recomp` folder live?** On a disk with ~45 GB free, in a plain folder such as `C:\Games` or
   `D:\Games`. Avoid Desktop, Documents and Downloads when **OneDrive** syncs them (it would try to upload 25 GB),
   and avoid `C:\Program Files` (no write permission).
4. **Antivirus.** The launcher runs a compiler that writes thousands of files; some antiviruses slow it down a lot or
   quarantine tools (`hactool.exe`, `aoc_xlate.exe`). If that happens, add the `AoC-Recomp` folder (and on Windows
   `%LOCALAPPDATA%\AoC-Recomp`) to the antivirus exclusions.

---

## 2. Windows, step by step

1. **Download** `AoC-Recomp-<version>-Windows.zip` from the project's *Releases* page.
2. **Extract** it: right-click the zip → *Extract All…* → choose a folder with room, for example `C:\Games`.
   You get a folder called `AoC-Recomp`. Do not open the launcher from inside the zip: extract it first. If Windows
   Explorer hangs on the zip (it happens on some PCs while the antivirus scans it), extract it with
   [7-Zip](https://www.7-zip.org/) or WinRAR.
3. Open **`AoC-Launcher.exe`** inside it. Windows may say it "protected your PC" (the program is not signed):
   click *More info* → *Run anyway*.
4. **YOUR COPY** — click **Browse…** and pick the folder with your NSPs and `prod.keys`.
   Four green dots mean everything was found.
5. **WHERE YOU WILL PLAY** — tick **Steam Deck / Linux**, **Windows (this PC)**, or both.
6. Click **BUILD** (bottom right; up to version 0.1.5 it was called **FORGE**) and let the PC work. The first time takes
   **1 to 2 hours**; the list on the right shows each step and the time it took. You can keep using the PC, it will only
   be slower. Keep the PC from going to sleep while it works.
7. When it is done:
   - **Windows:** the window turns into the game's launcher (below). Press **PLAY**.
   - **Steam Deck:** copy the folder to the Deck (section 4); **Deck folder** at the bottom opens it.

**The game's launcher.** Once the game for this PC is built, `AoC-Launcher.exe` opens straight on it:

| | |
|---|---|
| **GRAPHICS** | window mode and size, presentation (VSync), game resolution (1920 × 1080 or the lighter 1280 × 720), internal resolution (TV or handheld), 3D render scale, picture shape, texture filtering, shadows, performance overlay |
| **CONTROLS AND SOUND** | button layout (Nintendo or Xbox), vibration, stick dead zone, invert camera, volume, mute in the background, in-game menu language |
| Bottom bar | **Report a problem…** (a zip with the logs and your PC's details, for asking for help), **Game folder**, **Build again** (after an update, or to add the Steam Deck version), **Save**, **Close**, and **PLAY** |

Hover over a setting for a short explanation. **PLAY** saves first. Everything else (remapping buttons, colours, HDR)
is in the game's own menu: **F1**, or Minus + Plus on a controller.

> **"WSL is not installed"?** The Steam Deck version is compiled inside WSL (Linux that comes with Windows). Click
> **Install WSL**, accept the administrator question, **restart the PC**, open the launcher again and click
> **BUILD** once more. It continues from where it stopped. If WSL still fails, turn on *virtualization*
> (Intel VT-x / AMD SVM) in your PC's BIOS. If you only want to play on this PC, untick **Steam Deck / Linux**: the
> Windows version does not need WSL.

The language switch (**PT / EN**) is at the top right; **Guide** opens this page.

---

## 3. Linux, step by step

You need a 64-bit Linux with `python3` (almost every distribution has it) and an internet connection the first time.
Everything is done by the launcher; the commands below are only to start it.

1. **Download** `AoC-Recomp-<version>-Linux.tar.gz` from the *Releases* page.
2. **Extract it and open the launcher.** In a terminal, in the folder where the download is (usually `~/Downloads`):
   ```sh
   tar xf AoC-Recomp-*-Linux.tar.gz
   cd AoC-Recomp
   ./aoc-launcher
   ```
   Next time, `./aoc-launcher` inside `AoC-Recomp` is enough (some file managers also open it with a double click).
   If your system lacks a library the launcher's window needs (`libdecor`, `libXss`, `libpulse`…), it uses a copy it
   carries, only of what is missing: nothing to install.
3. **YOUR COPY** — **Browse…** and pick the folder with your NSPs and `prod.keys`. Keep **Steam Deck / Linux**
   ticked: the same folder is the game for this PC and for the Deck.
4. Click **BUILD**. The first time the launcher installs the compiler, and how depends on your system:

   | System | What happens |
   |---|---|
   | Ubuntu, Kubuntu, Mint, Pop!_OS, Debian | your **password** is asked in a window, and the packages come from `apt`. **Tested: Ubuntu 24.04** |
   | Arch, Manjaro, EndeavourOS, CachyOS | the same with `pacman`. **Tested: Arch** |
   | Fedora Workstation | the same with `dnf`. Not tested yet: if it fails, the log says which package is missing |
   | **SteamOS** (Steam Deck, Steam Machine), **Bazzite**, Fedora Silverblue/Kinoite, NixOS | the system cannot take packages, so the builder makes a **distrobox container** (`aoc-recomp`, ~1.5 GB) and compiles inside it, without changing the system. SteamOS 3.5+ and Bazzite already have `distrobox`. **New and not yet confirmed by players**: if it fails, report it (section 8) and build on another PC meanwhile |

   No password window? Desktops without a password helper (i3, sway and other bare window managers) cannot show it.
   Run this once in a terminal, inside `AoC-Recomp`, and click **BUILD** again:
   ```sh
   bash tools/setup_wsl.sh --minimal
   ```
5. Let it work: **1 to 2 hours** the first time (the list on the right shows each step). It continues from where it
   stopped if you close it or something fails.
6. When it is done the window turns into the game's launcher, as on Windows: settings and **PLAY**. The game is in
   `AoC-Recomp/dist/aoc-deck`; `./aoc.sh` there starts it too, and `sh install-shortcut.sh` puts it in your
   application menu (and so in Steam's *Add a Non-Steam Game* list). The game data (`romfs.bin`) goes into that folder
   as a hard link, which takes no extra space. To play on a Steam Deck, see section 4.

**Without the window** (over SSH, or if the launcher does not open): the same build from a terminal, inside
`AoC-Recomp`:
```sh
python3 tools/make_build.py --deck --lang en --game-dir ~/path/to/your/game/files
```
Then `dist/aoc-deck/aoc.sh` starts the game.

---

## 4. Copying to the Steam Deck

The Deck does not compile anything: it gets the ready folder `AoC-Recomp/dist/aoc-deck`. (If you built on the Deck
itself, the folder is already there: skip to step 3.)

1. **The first time**, on Windows, tick **include romfs.bin** before building (the game data, 10.9 GiB, goes into the
   folder; on Linux it always goes in). For later updates you can leave it unticked: the data does not change. The
   DLCs found in your game files folder always go in (`romfs/dlc-*.bin`, 1.4 GiB for the four); copy them once along
   with `romfs.bin`.
2. Copy the whole `aoc-deck` folder to the Deck — USB stick, SD card, network share, or `scp` — for example to the
   SD card: `/run/media/mmcblk0p1/aoc-deck`. A USB stick must be formatted **exFAT** or NTFS: FAT32 cannot hold the
   10.9 GiB `romfs.bin`.
3. On the Deck, in **Desktop Mode**, open the folder, open a terminal there (*Konsole*) and run once:
   ```sh
   sh install-shortcut.sh
   ```
4. In Steam: *Games* → *Add a Non-Steam Game* → tick **Hyrule Warriors: Age of Calamity (AoC Recomp)** → *Add*.
   Back in **Game Mode** it is in your library.

The `README.txt` file in the folder (`LEIA-ME.txt` in Portuguese) has the controls (hold **L3+R3** for the quick menu)
and the log tools.

---

## 5. Updating to a new version

Extract the new zip **over the old `AoC-Recomp` folder** (replace the files) and build again. Your `build` and `dist`
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
| SteamOS, Bazzite and similar: the compiler's container | distrobox container `aoc-recomp` | ~1.5 GB |

To remove everything: delete the `AoC-Recomp` folder; on Windows run `wsl --unregister AoC-Recomp` in a terminal, and
delete `C:\msys64` if the launcher installed it; on Linux delete `~/aoc-build` and `~/.venvs/aoc`, and where there is a
container, `distrobox rm aoc-recomp`.

---

## 7. If something goes wrong

**Before building**

- **A red dot in "Your files"**: the file is not in the chosen folder. `prod.keys` must sit in the same folder as the
  NSPs. The NSPs can have any name: without the ID in the name the launcher shows "checked when building" and the
  build's first step identifies them by their contents.
- **"The update in your folder is another version"** or **"the extracted game code is not version 1.3.0"**: the port
  only works with update **1.3.0** (v327680). Update 1.4.1 (v458752) is not accepted yet. Replace the update NSP with
  the 1.3.0 one and click **BUILD** again; what the earlier attempt left behind is redone by itself.
- **"Not enough free space"**: the message says how much is needed; free some space and build again.
- **"This PC's processor lacks AVX2"**: the game cannot run on this PC (section 1). You can still build the Steam Deck
  version here and copy it to the Deck.
- **The zip will not open, or Explorer hangs on it**: extract it with 7-Zip or WinRAR (section 2).

**While building**

- **A step failed**: the reason is under the step, in red, and the full log is below. Click **BUILD** again:
  finished steps are skipped. **Only check** tests your dump without building. To ask for help, press **Report a
  problem…** and attach `aoc-report.zip` (it holds the logs and your PC's details, nothing of the game).
- **"Unable to create temp file: No such file or directory"** at **Compile for Windows** (version 0.1.5): MSYS2's
  temporary folder is missing. Create the folder `C:\msys64\tmp` and build again. From version 0.1.6 the builder makes
  it by itself.
- **SteamOS or Bazzite: "unable to lock database", "rpm-ostree", or "does not let the build tools be installed"**:
  versions up to 0.1.5 cannot install the compiler on these systems. From version 0.1.6 the builder uses a distrobox
  container (section 3); until then, build on a Windows or Linux PC and copy the folder (section 4).
- **The build is very slow**: an antivirus scanning every file slows the compiler a lot (see "Before you start");
  a hard disk (HDD) instead of an SSD too. With 8 GB of RAM the largest files take long: close the browser and games
  while it works.

**When playing**

- **PLAY turns into PLAYING and back, and the game never shows up**: the game stopped as it started. From version
  0.1.6 the launcher says so under the buttons, with the reason when the log has one. The usual causes: a processor
  without AVX2, a graphics card or driver without Vulkan 1.3 (update the driver from NVIDIA's, AMD's or Intel's
  site), or, on Linux with version 0.1.5, `romfs.bin` missing from the game folder (build again with **include
  romfs.bin** ticked). Press **Report a problem…** and send the zip: the log says which.
- **The game shows stutters the first time**: shaders are translated while you play the first time; they are cached
  for the next sessions.
- **The game froze, the screen went black or dark, or an effect is missing**: the game writes a report to its log by
  itself when it shows no picture for 10 s or stays black/dark for 15 s; press **F8** when you see any other glitch to
  mark it. To look into hits and effects, start the game with `monitor.bat` in the game folder (Windows) instead of
  **PLAY**: it saves pictures of every hit and a full frame capture at a mark or a dark scene (a bit slower, and it
  takes space in `logs\diag`). Then press **Report a problem…** and send the zip.
- **Frame drops or stutters**: every session writes one performance row a second to `logs/desempenho/`. When it
  stutters, hold **L3+R3** and choose **Mark this moment** (F8 works too on PC). On the Steam Deck,
  `./aoc-logs.sh performance` sums the session up and `./aoc-logs.sh package` bundles everything to send; on PC, **Report a problem…**.

---

## 8. Reporting a problem

The more people test and say what they saw, the faster the port gets better. To report:

1. In the launcher, press **Report a problem…**. It makes `aoc-report.zip` (logs and your PC's details; nothing of
   the game, and your user name is replaced by `user` in the texts), opens the folder the zip is in and opens the
   project's problem form in your browser: <https://github.com/Azzulin/EXCUUUUSE-ME-PRINCESS-/issues>.
2. Fill in the form (it needs a GitHub account) and drag `aoc-report.zip` into the report field. A screenshot alone
   rarely says why something failed; the zip does.
3. On a Steam Deck without the launcher: in the game folder, `./aoc-logs.sh package` makes
   `logs/pacote-<date>.tar.gz`; attach that file to the same form.

Before opening a new problem, check the list for one like yours. **Never attach game files, `prod.keys` or saves.**

---

## 9. Common questions

- **Can I delete the NSPs after building?** Keep them for now: building again (after an update of AoC Recomp) still
  checks them. What was already extracted from them is not extracted again, so it is quick.
- **Does it work with update 1.4.1?** Not yet. It is the most requested change and is tracked on the issues page.
- **Can I build on one PC and play on another?** Yes: the Deck folder (`dist/aoc-deck`) works on any Linux PC and
  on the Steam Deck. The Windows folder (`dist/aoc-windows`) can be copied to another Windows PC with an AVX2
  processor and a Vulkan 1.3 graphics card.
- **Can I share the built folder?** No. It holds the game, made from your copy: it is for your own use.

## Legal

Use only a copy you own, dumped from your own console. This project contains no game code, data or keys, and it is
not affiliated with Nintendo or Koei Tecmo. The project's own code is under the [MIT licence](LICENSE); the components
it uses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
