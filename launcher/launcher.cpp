// AoC Recomp launcher: builds the game from the player's own dump (tools/make_build.py) for the Steam Deck and for
// Windows, and starts the Windows build. Dear ImGui on SDL3's renderer (runtime/third_party/imgui, MIT). The look is
// drawn here (colours, geometric lines, rings): no game or Nintendo artwork is in the repository.
//
// The launcher runs tools/make_build.py and reads its protocol: "@@PLAN <id> <title>", "@@STEP <id> <state> <text>",
// "@@DONE ok|fail"; every other line goes to the log. Settings live in launcher.ini beside the executable.
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
#include <windows.h>

#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <deque>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "imgui.h"
#include "imgui_impl_sdl3.h"
#include "imgui_impl_sdlrenderer3.h"

namespace fs = std::filesystem;

// ---- palette (Sheikah blue, Guardian orange, Calamity red on a night background)
static const ImVec4 C_BG0(0.020f, 0.039f, 0.070f, 1.0f);
static const ImVec4 C_BG1(0.043f, 0.090f, 0.150f, 1.0f);
static const ImVec4 C_PANEL(0.035f, 0.070f, 0.120f, 0.86f);
static const ImVec4 C_CYAN(0.282f, 0.820f, 1.000f, 1.0f);
static const ImVec4 C_CYAN_DIM(0.160f, 0.470f, 0.620f, 1.0f);
static const ImVec4 C_ORANGE(1.000f, 0.604f, 0.235f, 1.0f);
static const ImVec4 C_RED(0.831f, 0.227f, 0.353f, 1.0f);
static const ImVec4 C_TEXT(0.902f, 0.945f, 1.000f, 1.0f);
static const ImVec4 C_MUTED(0.560f, 0.660f, 0.760f, 1.0f);
static const ImVec4 C_OK(0.380f, 0.900f, 0.660f, 1.0f);

static ImU32 col(const ImVec4 &c, float a = -1) { return ImGui::GetColorU32(ImVec4(c.x, c.y, c.z, a < 0 ? c.w : a)); }

// ---- paths and settings
static fs::path g_exe_dir, g_root;
struct Settings {
    std::string game_dir, deck_host = "deck@192.168.100.130", win_work, wsl_distro;
    bool deck = true, windows = false, send = false, with_romfs = false;
};
static Settings S;

static std::wstring widen(const std::string &s) {
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), nullptr, 0);
    std::wstring w(n, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), w.data(), n);
    return w;
}
static std::string narrow(const std::wstring &w) {
    int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), nullptr, 0, nullptr, nullptr);
    std::string s(n, '\0');
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), s.data(), n, nullptr, nullptr);
    return s;
}
static std::string u8(const fs::path &p) { return narrow(p.wstring()); }
static fs::path upath(const std::string &s) { return fs::path(widen(s)); }

static void settings_load() {
    std::ifstream f(g_exe_dir / "launcher.ini");
    std::string line;
    while (std::getline(f, line)) {
        size_t eq = line.find('=');
        if (eq == std::string::npos) continue;
        std::string k = line.substr(0, eq), v = line.substr(eq + 1);
        if (k == "game_dir") S.game_dir = v;
        else if (k == "deck_host") S.deck_host = v;
        else if (k == "win_work") S.win_work = v;
        else if (k == "wsl_distro") S.wsl_distro = v;
        else if (k == "deck") S.deck = v == "1";
        else if (k == "windows") S.windows = v == "1";
        else if (k == "send") S.send = v == "1";
        else if (k == "with_romfs") S.with_romfs = v == "1";
    }
}
static void settings_save() {
    std::ofstream f(g_exe_dir / "launcher.ini");
    f << "game_dir=" << S.game_dir << "\ndeck_host=" << S.deck_host << "\nwin_work=" << S.win_work
      << "\nwsl_distro=" << S.wsl_distro << "\ndeck=" << S.deck << "\nwindows=" << S.windows << "\nsend=" << S.send
      << "\nwith_romfs=" << S.with_romfs << "\n";
}

// ---- the dump folder at a glance (names only; the build checks the contents)
struct DumpScan {
    int nsp = 0, dlc = 0;
    bool base = false, update = false, keys = false, exists = false;
};
static DumpScan scan_dump(const std::string &dir) {
    DumpScan d;
    std::error_code ec;
    fs::path p = upath(dir);
    if (dir.empty() || !fs::is_directory(p, ec)) return d;
    d.exists = true;
    d.keys = fs::is_regular_file(p / "prod.keys", ec);
    for (auto it = fs::recursive_directory_iterator(p, fs::directory_options::skip_permission_denied, ec);
         it != fs::recursive_directory_iterator(); it.increment(ec)) {
        if (ec) break;
        if (!it->is_regular_file(ec)) continue;
        std::string name = u8(it->path().filename());
        for (auto &ch : name) ch = (char)toupper((unsigned char)ch);
        if (name.size() < 4 || name.substr(name.size() - 4) != ".NSP") continue;
        d.nsp++;
        if (name.find("01002B00111A2000") != std::string::npos) d.base = true;
        else if (name.find("01002B00111A2800") != std::string::npos) d.update = true;
        else if (name.find("01002B00111A3") != std::string::npos) d.dlc++;
    }
    return d;
}

// ---- the build process
struct Step {
    std::string id, title, state = "pending", note;
    double t0 = 0, t1 = 0;
};
static std::mutex g_lock;
static std::vector<Step> g_steps;
static std::deque<std::string> g_log;
static std::atomic<int> g_running{0};   // 1 while make_build.py runs
static std::string g_done;              // "", "ok", "fail", "cancel"
static bool g_check_only;              // the running or last run was "only check the files"
static HANDLE g_job, g_proc;
static double now_s() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

static void log_line(const std::string &l) {
    g_log.push_back(l);
    while (g_log.size() > 4000) g_log.pop_front();
}

static void handle_line(const std::string &l) {   // g_lock held
    if (l.rfind("@@PLAN ", 0) == 0) {
        size_t sp = l.find(' ', 7);
        Step s;
        s.id = l.substr(7, sp - 7);
        s.title = sp == std::string::npos ? s.id : l.substr(sp + 1);
        g_steps.push_back(s);
    } else if (l.rfind("@@STEP ", 0) == 0) {
        size_t a = l.find(' ', 7), b = a == std::string::npos ? a : l.find(' ', a + 1);
        std::string id = l.substr(7, a - 7), st = a == std::string::npos ? "" : l.substr(a + 1, b - a - 1);
        std::string note = b == std::string::npos ? "" : l.substr(b + 1);
        for (auto &s : g_steps)
            if (s.id == id) {
                if (st == "run") s.t0 = now_s();
                else s.t1 = now_s();
                s.state = st;
                if (st == "fail") s.note = note;
            }
    } else if (l.rfind("@@DONE ", 0) == 0) {
        if (g_done.empty()) g_done = l.substr(7);
    } else {
        log_line(l);
    }
}

static fs::path python_exe() {
    fs::path msys = "C:/msys64/ucrt64/bin/python3.exe";   // has the packages tools/extract.py needs
    std::error_code ec;
    return fs::is_regular_file(msys, ec) ? msys : fs::path(L"python");
}

static std::wstring quote(const std::wstring &s) { return L"\"" + s + L"\""; }

static void start_build(bool check_only) {
    g_check_only = check_only;
    {
        std::lock_guard<std::mutex> g(g_lock);
        g_steps.clear();
        g_log.clear();
        g_done.clear();
    }
    std::wstring cmd = quote(python_exe().wstring()) + L" -u " + quote((g_root / "tools" / "make_build.py").wstring());
    cmd += L" --game-dir " + quote(widen(S.game_dir));
    if (S.deck) cmd += L" --deck";
    if (S.windows) cmd += L" --windows";
    if (S.deck && S.with_romfs) cmd += L" --with-romfs";
    if (S.deck && S.send) cmd += L" --send --deck-host " + quote(widen(S.deck_host));
    if (!S.win_work.empty()) cmd += L" --win-work " + quote(widen(S.win_work));
    if (!S.wsl_distro.empty()) cmd += L" --wsl-distro " + quote(widen(S.wsl_distro));
    if (check_only) cmd += L" --check-only";

    SECURITY_ATTRIBUTES sa{sizeof sa, nullptr, TRUE};
    HANDLE rd, wr;
    if (!CreatePipe(&rd, &wr, &sa, 0)) return;
    SetHandleInformation(rd, HANDLE_FLAG_INHERIT, 0);
    STARTUPINFOW si{};
    si.cb = sizeof si;
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = si.hStdError = wr;
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    PROCESS_INFORMATION pi{};
    std::wstring cl = cmd;
    std::wstring cwd = g_root.wstring();
    if (!CreateProcessW(nullptr, cl.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW | CREATE_SUSPENDED, nullptr,
                        cwd.c_str(), &si, &pi)) {
        CloseHandle(rd), CloseHandle(wr);
        std::lock_guard<std::mutex> g(g_lock);
        log_line("não consegui iniciar o Python: " + narrow(python_exe().wstring()));
        g_done = "fail";
        return;
    }
    // A job: Cancel (or closing the launcher) ends the whole tree
    g_job = CreateJobObjectW(nullptr, nullptr);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION li{};
    li.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    SetInformationJobObject(g_job, JobObjectExtendedLimitInformation, &li, sizeof li);
    AssignProcessToJobObject(g_job, pi.hProcess);
    ResumeThread(pi.hThread);
    CloseHandle(pi.hThread);
    CloseHandle(wr);
    g_proc = pi.hProcess;
    g_running = 1;
    std::thread([rd]() {
        std::string buf;
        char chunk[4096];
        DWORD n;
        while (ReadFile(rd, chunk, sizeof chunk, &n, nullptr) && n) {
            buf.append(chunk, n);
            size_t pos;
            while ((pos = buf.find('\n')) != std::string::npos) {
                std::string line = buf.substr(0, pos);
                if (!line.empty() && line.back() == '\r') line.pop_back();
                std::lock_guard<std::mutex> g(g_lock);
                handle_line(line);
                buf.erase(0, pos + 1);
            }
        }
        CloseHandle(rd);
        WaitForSingleObject(g_proc, INFINITE);
        std::lock_guard<std::mutex> g(g_lock);
        if (g_done.empty()) g_done = "fail";
        for (auto &s : g_steps)
            if (s.state == "run") s.state = g_done == "cancel" ? "cancel" : "fail", s.t1 = now_s();
        g_running = 0;
    }).detach();
}

static void cancel_build() {
    {
        std::lock_guard<std::mutex> g(g_lock);
        g_done = "cancel";
        log_line("cancelado pelo usuário");
    }
    if (g_job) TerminateJobObject(g_job, 1);
    // the Linux side of a WSL step keeps running without its wsl.exe: stop the build there too
    std::wstring cl = L"wsl " + (S.wsl_distro.empty() ? L"" : L"-d " + widen(S.wsl_distro) + L" ") +
                      L"-e pkill -f tools/build.py";
    STARTUPINFOW si{sizeof si};
    PROCESS_INFORMATION pi{};
    if (CreateProcessW(nullptr, cl.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi))
        CloseHandle(pi.hThread), CloseHandle(pi.hProcess);
}

static void open_folder(const fs::path &p) { ShellExecuteW(nullptr, L"open", p.wstring().c_str(), nullptr, nullptr, SW_SHOW); }

// ---- folder dialog (SDL3 calls back, possibly on another thread)
static std::mutex g_pick_lock;
static std::string g_picked;
static void SDLCALL on_folder(void *, const char *const *list, int) {
    if (!list || !list[0]) return;
    std::lock_guard<std::mutex> g(g_pick_lock);
    g_picked = list[0];
}

// ---- drawing helpers
static ImFont *F_BODY, *F_HEAD, *F_TITLE, *F_SMALL;

static void draw_background(float t) {
    ImDrawList *dl = ImGui::GetBackgroundDrawList();
    ImVec2 sz = ImGui::GetIO().DisplaySize;
    dl->AddRectFilledMultiColor(ImVec2(0, 0), sz, col(C_BG1), col(C_BG1), col(C_BG0), col(C_BG0));
    // the Calamity's glow along the bottom
    dl->AddRectFilledMultiColor(ImVec2(0, sz.y * 0.70f), sz, col(C_RED, 0.0f), col(C_RED, 0.0f), col(C_RED, 0.16f),
                                col(C_RED, 0.16f));
    // a faint technical grid
    for (float x = 0; x < sz.x; x += 48) dl->AddLine(ImVec2(x, 0), ImVec2(x, sz.y), col(C_CYAN, 0.035f));
    for (float y = 0; y < sz.y; y += 48) dl->AddLine(ImVec2(0, y), ImVec2(sz.x, y), col(C_CYAN, 0.035f));
    // slow concentric rings, upper right
    ImVec2 c(sz.x * 0.86f, sz.y * 0.20f);
    for (int i = 0; i < 6; i++) {
        float r = 60.0f + i * 34.0f, a0 = t * (0.15f + 0.05f * i) * (i % 2 ? -1 : 1) + i;
        dl->PathArcTo(c, r, a0, a0 + 3.14159f * (0.6f + 0.15f * i), 48);
        dl->PathStroke(col(i % 3 == 2 ? C_ORANGE : C_CYAN, 0.10f + 0.02f * (5 - i)), 0, 2.0f);
        dl->AddCircle(c, r, col(C_CYAN, 0.035f), 96, 1.0f);
    }
    for (int k = 0; k < 12; k++) {   // tick marks on the outer ring
        float a = k * 3.14159f / 6 + t * 0.05f, r0 = 60 + 5 * 34 + 6, r1 = r0 + 12;
        dl->AddLine(ImVec2(c.x + cosf(a) * r0, c.y + sinf(a) * r0), ImVec2(c.x + cosf(a) * r1, c.y + sinf(a) * r1),
                    col(C_CYAN, 0.18f), 2.0f);
    }
}

// Panel with a Sheikah-style frame: thin border, bright corner brackets.
static void panel_begin(const char *id, const char *title, ImVec2 size) {
    ImGui::PushStyleColor(ImGuiCol_ChildBg, C_PANEL);
    ImGui::PushStyleVar(ImGuiStyleVar_ChildRounding, 4.0f);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(18, 14));
    ImGui::BeginChild(id, size, ImGuiChildFlags_Borders | ImGuiChildFlags_AlwaysUseWindowPadding);
    ImDrawList *dl = ImGui::GetWindowDrawList();
    ImVec2 p0 = ImGui::GetWindowPos(), p1(p0.x + ImGui::GetWindowWidth(), p0.y + ImGui::GetWindowHeight());
    float L = 16;
    ImU32 cc = col(C_CYAN, 0.9f);
    dl->AddLine(p0, ImVec2(p0.x + L, p0.y), cc, 2), dl->AddLine(p0, ImVec2(p0.x, p0.y + L), cc, 2);
    dl->AddLine(ImVec2(p1.x - L, p0.y), ImVec2(p1.x, p0.y), cc, 2), dl->AddLine(ImVec2(p1.x, p0.y), ImVec2(p1.x, p0.y + L), cc, 2);
    dl->AddLine(ImVec2(p0.x, p1.y), ImVec2(p0.x + L, p1.y), cc, 2), dl->AddLine(ImVec2(p0.x, p1.y - L), ImVec2(p0.x, p1.y), cc, 2);
    dl->AddLine(ImVec2(p1.x - L, p1.y), p1, cc, 2), dl->AddLine(ImVec2(p1.x, p1.y - L), p1, cc, 2);
    if (title) {
        ImGui::PushFont(F_HEAD);
        ImGui::TextColored(C_CYAN, "%s", title);
        ImGui::PopFont();
        ImVec2 q = ImGui::GetCursorScreenPos();
        dl->AddRectFilledMultiColor(ImVec2(q.x, q.y), ImVec2(q.x + ImGui::GetContentRegionAvail().x, q.y + 1),
                                    col(C_CYAN, 0.6f), col(C_CYAN, 0.0f), col(C_CYAN, 0.0f), col(C_CYAN, 0.6f));
        ImGui::Dummy(ImVec2(0, 8));
    }
}
static void panel_end() {
    ImGui::EndChild();
    ImGui::PopStyleVar(2);
    ImGui::PopStyleColor();
}

static void status_dot(bool ok, const char *label, const char *detail = nullptr) {
    ImDrawList *dl = ImGui::GetWindowDrawList();
    ImVec2 p = ImGui::GetCursorScreenPos();
    float h = ImGui::GetTextLineHeight();
    ImVec2 c(p.x + 7, p.y + h * 0.5f);
    dl->AddCircleFilled(c, 5.0f, col(ok ? C_OK : C_RED));
    dl->AddCircle(c, 8.0f, col(ok ? C_OK : C_RED, 0.35f), 0, 1.5f);
    ImGui::Dummy(ImVec2(20, h));
    ImGui::SameLine();
    ImGui::TextColored(ok ? C_TEXT : C_MUTED, "%s", label);
    if (detail) {
        ImGui::SameLine();
        ImGui::TextColored(C_MUTED, "%s", detail);
    }
}

// State marker of a build step: ring (pending), turning arc (running), check (ok), cross (fail), dash (skipped).
static void step_marker(const std::string &st, float t) {
    ImDrawList *dl = ImGui::GetWindowDrawList();
    ImVec2 p = ImGui::GetCursorScreenPos();
    float h = ImGui::GetTextLineHeight();
    ImVec2 c(p.x + 9, p.y + h * 0.5f);
    if (st == "run") {
        dl->PathArcTo(c, 7, t * 6, t * 6 + 4.2f, 24);
        dl->PathStroke(col(C_ORANGE), 0, 2.5f);
    } else if (st == "ok") {
        dl->AddCircleFilled(c, 8, col(C_CYAN, 0.18f));
        dl->AddLine(ImVec2(c.x - 4, c.y), ImVec2(c.x - 1, c.y + 3.5f), col(C_CYAN), 2.2f);
        dl->AddLine(ImVec2(c.x - 1, c.y + 3.5f), ImVec2(c.x + 4.5f, c.y - 3.5f), col(C_CYAN), 2.2f);
    } else if (st == "skip") {
        dl->AddCircle(c, 7, col(C_CYAN_DIM), 0, 1.5f);
        dl->AddLine(ImVec2(c.x - 3, c.y), ImVec2(c.x + 3, c.y), col(C_CYAN_DIM), 2.0f);
    } else if (st == "fail" || st == "cancel") {
        dl->AddCircleFilled(c, 8, col(C_RED, 0.25f));
        dl->AddLine(ImVec2(c.x - 3.5f, c.y - 3.5f), ImVec2(c.x + 3.5f, c.y + 3.5f), col(C_RED), 2.2f);
        dl->AddLine(ImVec2(c.x - 3.5f, c.y + 3.5f), ImVec2(c.x + 3.5f, c.y - 3.5f), col(C_RED), 2.2f);
    } else {
        dl->AddCircle(c, 7, col(C_MUTED, 0.6f), 0, 1.5f);
    }
    ImGui::Dummy(ImVec2(24, h));
}

// The big "forge" button: gradient body, glow when hovered.
static bool forge_button(const char *label, ImVec2 size, bool enabled, float t) {
    ImGui::PushID(label);
    ImVec2 p = ImGui::GetCursorScreenPos();
    bool pressed = ImGui::InvisibleButton("b", size) && enabled;
    bool hov = ImGui::IsItemHovered() && enabled;
    ImDrawList *dl = ImGui::GetWindowDrawList();
    ImVec2 q(p.x + size.x, p.y + size.y);
    float glow = hov ? 0.55f + 0.25f * sinf(t * 4) : 0.25f;
    if (enabled) {
        for (int i = 4; i >= 1; i--)
            dl->AddRect(ImVec2(p.x - i * 2, p.y - i * 2), ImVec2(q.x + i * 2, q.y + i * 2), col(C_ORANGE, glow * 0.12f * i), 6, 0, 2);
        dl->AddRectFilledMultiColor(p, q, col(C_ORANGE, 0.95f), col(C_RED, 0.95f), col(C_RED, 0.85f), col(C_ORANGE, 0.85f));
    } else {
        dl->AddRectFilled(p, q, col(C_MUTED, 0.25f), 4);
    }
    dl->AddRect(p, q, col(enabled ? C_TEXT : C_MUTED, 0.6f), 4, 0, 1.5f);
    ImGui::PushFont(F_HEAD);
    ImVec2 ts = ImGui::CalcTextSize(label);
    dl->AddText(ImVec2(p.x + (size.x - ts.x) * 0.5f, p.y + (size.y - ts.y) * 0.5f), col(enabled ? C_TEXT : C_MUTED), label);
    ImGui::PopFont();
    ImGui::PopID();
    return pressed;
}

static void apply_theme() {
    ImGuiStyle &s = ImGui::GetStyle();
    s.WindowRounding = 0, s.FrameRounding = 3, s.GrabRounding = 3, s.ChildRounding = 4, s.ScrollbarRounding = 3;
    s.FramePadding = ImVec2(10, 6), s.ItemSpacing = ImVec2(10, 8), s.WindowBorderSize = 0, s.ChildBorderSize = 1;
    ImVec4 *c = s.Colors;
    c[ImGuiCol_Text] = C_TEXT;
    c[ImGuiCol_TextDisabled] = C_MUTED;
    c[ImGuiCol_WindowBg] = ImVec4(0, 0, 0, 0);
    c[ImGuiCol_ChildBg] = C_PANEL;
    c[ImGuiCol_PopupBg] = ImVec4(0.04f, 0.08f, 0.13f, 0.98f);
    c[ImGuiCol_Border] = ImVec4(C_CYAN.x, C_CYAN.y, C_CYAN.z, 0.22f);
    c[ImGuiCol_FrameBg] = ImVec4(0.06f, 0.12f, 0.20f, 1);
    c[ImGuiCol_FrameBgHovered] = ImVec4(0.09f, 0.18f, 0.28f, 1);
    c[ImGuiCol_FrameBgActive] = ImVec4(0.11f, 0.22f, 0.34f, 1);
    c[ImGuiCol_CheckMark] = C_CYAN;
    c[ImGuiCol_Button] = ImVec4(0.08f, 0.20f, 0.30f, 1);
    c[ImGuiCol_ButtonHovered] = ImVec4(0.12f, 0.30f, 0.44f, 1);
    c[ImGuiCol_ButtonActive] = ImVec4(0.16f, 0.40f, 0.56f, 1);
    c[ImGuiCol_ScrollbarBg] = ImVec4(0, 0, 0, 0.2f);
    c[ImGuiCol_ScrollbarGrab] = ImVec4(C_CYAN_DIM.x, C_CYAN_DIM.y, C_CYAN_DIM.z, 0.6f);
    c[ImGuiCol_Separator] = ImVec4(C_CYAN.x, C_CYAN.y, C_CYAN.z, 0.25f);
    c[ImGuiCol_TextSelectedBg] = ImVec4(C_CYAN.x, C_CYAN.y, C_CYAN.z, 0.30f);
}

static fs::path find_root(fs::path from) {
    std::error_code ec;
    for (int i = 0; i < 6 && !from.empty(); i++, from = from.parent_path())
        if (fs::is_regular_file(from / "tools" / "make_build.py", ec)) return from;
    return {};
}

int main(int argc, char **argv) {
    wchar_t buf[MAX_PATH];
    GetModuleFileNameW(nullptr, buf, MAX_PATH);
    g_exe_dir = fs::path(buf).parent_path();
    g_root = find_root(g_exe_dir);
    settings_load();
    if (S.game_dir.empty() && !g_root.empty()) S.game_dir = u8(g_root / "Game Files");
    if (S.wsl_distro.empty()) S.wsl_distro = "archlinux";

    if (!SDL_Init(SDL_INIT_VIDEO)) return 1;
    float scale = SDL_GetDisplayContentScale(SDL_GetPrimaryDisplay());
    if (scale <= 0) scale = 1;
    SDL_Window *win = SDL_CreateWindow("Age of Calamity Recomp", (int)(1180 * scale), (int)(820 * scale),
                                       SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY);
    SDL_Renderer *ren = SDL_CreateRenderer(win, nullptr);
    SDL_SetRenderVSync(ren, 1);
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO &io = ImGui::GetIO();
    io.IniFilename = nullptr;
    fs::path font = g_root / "runtime" / "ui" / "fonts" / "Roboto-Medium.ttf";
    std::string fp = u8(font);
    std::error_code ec;
    if (fs::is_regular_file(font, ec)) {
        F_BODY = io.Fonts->AddFontFromFileTTF(fp.c_str(), 17 * scale);
        F_SMALL = io.Fonts->AddFontFromFileTTF(fp.c_str(), 14 * scale);
        F_HEAD = io.Fonts->AddFontFromFileTTF(fp.c_str(), 21 * scale);
        F_TITLE = io.Fonts->AddFontFromFileTTF(fp.c_str(), 46 * scale);
    }
    if (!F_BODY) F_BODY = F_SMALL = F_HEAD = F_TITLE = io.Fonts->AddFontDefault();
    apply_theme();
    ImGui::GetStyle().ScaleAllSizes(scale);
    ImGui_ImplSDL3_InitForSDLRenderer(win, ren);
    ImGui_ImplSDLRenderer3_Init(ren);

    DumpScan scan = scan_dump(S.game_dir);
    std::string scanned_dir = S.game_dir;
    char path_buf[1024], host_buf[256], work_buf[512], distro_buf[64];
    snprintf(path_buf, sizeof path_buf, "%s", S.game_dir.c_str());
    snprintf(host_buf, sizeof host_buf, "%s", S.deck_host.c_str());
    snprintf(work_buf, sizeof work_buf, "%s", S.win_work.c_str());
    snprintf(distro_buf, sizeof distro_buf, "%s", S.wsl_distro.c_str());
    bool autoscroll = true, quit = false;
    for (int i = 1; i < argc; i++)
        if (!strcmp(argv[i], "--check-now")) start_build(true);
    double t_start = now_s();

    while (!quit) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            ImGui_ImplSDL3_ProcessEvent(&e);
            if (e.type == SDL_EVENT_QUIT || e.type == SDL_EVENT_WINDOW_CLOSE_REQUESTED) quit = true;
        }
        {
            std::lock_guard<std::mutex> g(g_pick_lock);
            if (!g_picked.empty()) {
                snprintf(path_buf, sizeof path_buf, "%s", g_picked.c_str());
                g_picked.clear();
            }
        }
        S.game_dir = path_buf, S.deck_host = host_buf, S.win_work = work_buf, S.wsl_distro = distro_buf;
        if (S.game_dir != scanned_dir) scan = scan_dump(S.game_dir), scanned_dir = S.game_dir;

        ImGui_ImplSDLRenderer3_NewFrame();
        ImGui_ImplSDL3_NewFrame();
        ImGui::NewFrame();
        float t = (float)(now_s() - t_start);
        draw_background(t);

        ImGui::SetNextWindowPos(ImVec2(0, 0));
        ImGui::SetNextWindowSize(io.DisplaySize);
        ImGui::Begin("root", nullptr, ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove |
                                          ImGuiWindowFlags_NoBringToFrontOnFocus | ImGuiWindowFlags_NoSavedSettings);
        ImGui::PushFont(F_BODY);
        float pad = 28 * scale;
        ImGui::SetCursorPos(ImVec2(pad, pad * 0.8f));

        // ---- header
        ImGui::PushFont(F_TITLE);
        {
            ImVec2 tp = ImGui::GetCursorScreenPos();
            ImDrawList *dl = ImGui::GetWindowDrawList();
            for (int i = 1; i <= 3; i++)   // a soft glow under the title
                for (int k = 0; k < 4; k++)
                    dl->AddText(ImVec2(tp.x + (k & 1 ? i : -i) * 1.2f, tp.y + (k & 2 ? i : -i) * 1.2f), col(C_CYAN, 0.06f),
                                "AGE OF CALAMITY");
        }
        ImGui::TextColored(C_TEXT, "AGE OF CALAMITY");
        ImGui::PopFont();
        ImGui::SetCursorPosX(pad);
        ImGui::PushFont(F_HEAD);
        ImGui::TextColored(C_CYAN, "RECOMP");
        ImGui::SameLine();
        ImGui::TextColored(C_MUTED, "·  forja do seu port, a partir da sua cópia");
        ImGui::PopFont();
        {
            ImDrawList *dl = ImGui::GetWindowDrawList();
            ImVec2 q = ImGui::GetCursorScreenPos();
            float w = io.DisplaySize.x - 2 * pad;
            q.x = pad, q.y += 6;
            dl->AddRectFilledMultiColor(q, ImVec2(q.x + w, q.y + 2), col(C_CYAN, 0.9f), col(C_ORANGE, 0.0f),
                                        col(C_ORANGE, 0.0f), col(C_CYAN, 0.9f));
            for (int i = 0; i < 3; i++) {   // small diamonds on the line
                ImVec2 d(q.x + 60 + i * 18, q.y + 1);
                dl->AddQuadFilled(ImVec2(d.x, d.y - 5), ImVec2(d.x + 5, d.y), ImVec2(d.x, d.y + 5), ImVec2(d.x - 5, d.y),
                                  col(i == 1 ? C_ORANGE : C_CYAN));
            }
        }
        ImGui::Dummy(ImVec2(0, 20 * scale));

        float total_w = io.DisplaySize.x - 2 * pad;
        float left_w = total_w * 0.40f, right_w = total_w - left_w - 18 * scale;
        float body_h = io.DisplaySize.y - ImGui::GetCursorPosY() - 46 * scale;
        bool running = g_running.load() != 0;

        float gap = 10 * scale, files_h = 252 * scale, buttons_h = 54 * scale + ImGui::GetFrameHeight() + 3 * gap;
        float targets_h = fmaxf(body_h - files_h - buttons_h - gap, 200 * scale);
        ImGui::SetCursorPosX(pad);
        ImGui::BeginGroup();
        // ---- 1: files
        panel_begin("files", "1 · SEUS ARQUIVOS", ImVec2(left_w, files_h));
        ImGui::TextColored(C_MUTED, "Pasta com os NSPs (base, update 1.3.0, DLCs) e o prod.keys");
        ImGui::SetNextItemWidth(ImGui::GetContentRegionAvail().x - 110 * scale);
        ImGui::BeginDisabled(running);
        ImGui::InputText("##dir", path_buf, sizeof path_buf);
        ImGui::SameLine();
        if (ImGui::Button("Procurar...", ImVec2(100 * scale, 0)))
            SDL_ShowOpenFolderDialog(on_folder, nullptr, win, S.game_dir.empty() ? nullptr : S.game_dir.c_str(), false);
        ImGui::EndDisabled();
        ImGui::Dummy(ImVec2(0, 4));
        if (!scan.exists) {
            status_dot(false, "pasta não encontrada");
        } else {
            status_dot(scan.base, "Jogo base", scan.base ? "01002B00111A2000" : "(faltando)");
            status_dot(scan.update, "Update 1.3.0", scan.update ? "01002B00111A2800" : "(faltando)");
            char d[48];
            snprintf(d, sizeof d, "%d encontrado(s)", scan.dlc);
            status_dot(scan.dlc > 0, "DLCs", d);
            status_dot(scan.keys, "prod.keys", scan.keys ? "(conteúdo nunca exibido)" : "(faltando)");
        }
        panel_end();
        ImGui::Dummy(ImVec2(0, gap - ImGui::GetStyle().ItemSpacing.y));

        // ---- 2: targets
        panel_begin("targets", "2 · DESTINO", ImVec2(left_w, targets_h));
        ImGui::BeginDisabled(running);
        ImGui::Checkbox("Steam Deck", &S.deck);
        if (S.deck) {
            ImGui::Indent(26 * scale);
            ImGui::Checkbox("incluir o romfs.bin (primeira instalação, 10,9 GiB)", &S.with_romfs);
            ImGui::Checkbox("enviar ao Deck por SSH no fim", &S.send);
            if (S.send) {
                ImGui::SetNextItemWidth(260 * scale);
                ImGui::InputText("usuário@endereço", host_buf, sizeof host_buf);
            }
            ImGui::Unindent(26 * scale);
        }
        ImGui::Checkbox("Windows (este PC)", &S.windows);
        ImGui::Dummy(ImVec2(0, 2 * scale));
        ImGui::PushStyleColor(ImGuiCol_Header, ImVec4(0, 0, 0, 0));
        if (ImGui::CollapsingHeader("Avançado")) {
            ImGui::SetNextItemWidth(200 * scale);
            ImGui::InputText("distro do WSL", distro_buf, sizeof distro_buf);
            ImGui::SetNextItemWidth(200 * scale);
            ImGui::InputTextWithHint("pasta de trabalho (Windows)", "padrão", work_buf, sizeof work_buf);
        }
        ImGui::PopStyleColor();
        ImGui::EndDisabled();
        panel_end();
        ImGui::Dummy(ImVec2(0, gap - ImGui::GetStyle().ItemSpacing.y));

        // ---- 3: forge
        bool ready = scan.base && scan.update && scan.keys && (S.deck || S.windows);
        float bw = left_w;
        if (!running) {
            if (forge_button("FORJAR O PORT", ImVec2(bw, 54 * scale), ready, t)) {
                settings_save();
                start_build(false);
            }
            ImGui::BeginDisabled(!scan.exists);
            if (ImGui::Button("Só conferir os arquivos", ImVec2(bw, 0))) start_build(true);
            ImGui::EndDisabled();
        } else {
            forge_button("FORJANDO...", ImVec2(bw, 54 * scale), false, t);
            if (ImGui::Button("Cancelar", ImVec2(bw, 0))) cancel_build();
        }
        ImGui::EndGroup();

        // ---- progress and log
        ImGui::SameLine(0, 18 * scale);
        ImGui::BeginGroup();
        panel_begin("progress", "PROGRESSO", ImVec2(right_w, body_h));
        {
            std::lock_guard<std::mutex> g(g_lock);
            int done = 0;
            for (auto &s : g_steps) done += s.state == "ok" || s.state == "skip";
            float frac = g_steps.empty() ? 0.0f : (float)done / g_steps.size();
            // progress bar: Sheikah blue fill with a moving highlight
            ImDrawList *dl = ImGui::GetWindowDrawList();
            ImVec2 p = ImGui::GetCursorScreenPos();
            float w = ImGui::GetContentRegionAvail().x, h = 8 * scale;
            dl->AddRectFilled(p, ImVec2(p.x + w, p.y + h), col(C_CYAN, 0.10f), 3);
            if (frac > 0) dl->AddRectFilledMultiColor(p, ImVec2(p.x + w * frac, p.y + h), col(C_CYAN_DIM), col(C_CYAN),
                                                      col(C_CYAN), col(C_CYAN_DIM));
            if (g_running) {
                float x = p.x + fmodf(t * 160 * scale, w);
                dl->AddRectFilled(ImVec2(x, p.y), ImVec2(fminf(x + 40 * scale, p.x + w), p.y + h), col(C_ORANGE, 0.5f), 3);
            }
            ImGui::Dummy(ImVec2(w, h + 6));
            if (g_steps.empty()) {
                ImGui::TextColored(C_MUTED, "Escolha a pasta do seu dump e o destino, e forje.");
                ImGui::TextColored(C_MUTED, "Tudo é compilado neste PC a partir dos seus arquivos.");
            }
            for (auto &s : g_steps) {
                step_marker(s.state, t);
                ImGui::SameLine();
                ImGui::TextColored(s.state == "pending" ? C_MUTED : C_TEXT, "%s", s.title.c_str());
                if (s.t0 > 0) {
                    double el = (s.t1 > 0 ? s.t1 : now_s()) - s.t0;
                    ImGui::SameLine();
                    ImGui::TextColored(C_MUTED, s.state == "skip" ? "(já feito)" : "%dm%02ds", (int)el / 60, (int)el % 60);
                }
                if (!s.note.empty()) {
                    ImGui::PushFont(F_SMALL);
                    ImGui::SetCursorPosX(ImGui::GetCursorPosX() + 34 * scale);
                    ImGui::TextColored(C_RED, "%s", s.note.c_str());
                    ImGui::PopFont();
                }
            }
            if (g_done == "ok") ImGui::TextColored(C_OK, g_check_only ? "Arquivos conferidos: tudo certo." : "Pronto. O port foi forjado.");
            else if (g_done == "fail") ImGui::TextColored(C_RED, "Falhou. Veja o registro abaixo.");
            else if (g_done == "cancel") ImGui::TextColored(C_ORANGE, "Cancelado.");
            ImGui::Separator();
            ImGui::PushFont(F_SMALL);
            ImGui::TextColored(C_MUTED, "Registro");
            ImGui::SameLine();
            ImGui::Checkbox("acompanhar", &autoscroll);
            float log_h = ImGui::GetContentRegionAvail().y - 40 * scale;
            ImGui::BeginChild("log", ImVec2(0, log_h), ImGuiChildFlags_Borders, ImGuiWindowFlags_HorizontalScrollbar);
            ImGuiListClipper clip;
            clip.Begin((int)g_log.size());
            while (clip.Step())
                for (int i = clip.DisplayStart; i < clip.DisplayEnd; i++) {
                    const std::string &l = g_log[i];
                    bool err = l.rfind("ERRO", 0) == 0 || l.find("FAILED") != std::string::npos || l.find("error:") != std::string::npos;
                    ImGui::TextColored(err ? C_RED : C_MUTED, "%s", l.c_str());
                }
            if (autoscroll && g_running) ImGui::SetScrollHereY(1.0f);
            ImGui::EndChild();
            ImGui::PopFont();
        }
        // the finished folders
        std::error_code ec2;
        fs::path deck_dir = g_root / "dist" / "aoc-deck", win_dir = g_root / "dist" / "aoc-windows";
        bool has_deck = fs::exists(deck_dir / "aoc", ec2), has_win = fs::exists(win_dir / "aoc.exe", ec2);
        ImGui::BeginDisabled(!has_deck);
        if (ImGui::Button("Abrir pasta do Deck")) open_folder(deck_dir);
        ImGui::EndDisabled();
        ImGui::SameLine();
        ImGui::BeginDisabled(!has_win);
        if (ImGui::Button("Abrir pasta do Windows")) open_folder(win_dir);
        ImGui::SameLine();
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(C_ORANGE.x * 0.55f, C_ORANGE.y * 0.40f, 0.10f, 1));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(C_ORANGE.x * 0.75f, C_ORANGE.y * 0.55f, 0.15f, 1));
        if (ImGui::Button("Jogar no Windows")) ShellExecuteW(nullptr, L"open", (win_dir / "aoc.exe").wstring().c_str(),
                                                             nullptr, win_dir.wstring().c_str(), SW_SHOW);
        ImGui::PopStyleColor(2);
        ImGui::EndDisabled();
        panel_end();
        ImGui::EndGroup();

        // ---- footer
        ImGui::SetCursorPos(ImVec2(pad, io.DisplaySize.y - 30 * scale));
        ImGui::PushFont(F_SMALL);
        ImGui::TextColored(C_MUTED, "Use somente a sua cópia, extraída do seu console. Nada do jogo é distribuído: tudo "
                                    "é gerado e fica neste PC.");
        ImGui::PopFont();
        ImGui::PopFont();
        ImGui::End();

        ImGui::Render();
        SDL_SetRenderScale(ren, io.DisplayFramebufferScale.x, io.DisplayFramebufferScale.y);
        SDL_SetRenderDrawColorFloat(ren, C_BG0.x, C_BG0.y, C_BG0.z, 1);
        SDL_RenderClear(ren);
        ImGui_ImplSDLRenderer3_RenderDrawData(ImGui::GetDrawData(), ren);
        SDL_RenderPresent(ren);
    }
    settings_save();
    if (g_running) cancel_build();
    ImGui_ImplSDLRenderer3_Shutdown();
    ImGui_ImplSDL3_Shutdown();
    ImGui::DestroyContext();
    SDL_DestroyRenderer(ren);
    SDL_DestroyWindow(win);
    SDL_Quit();
    return 0;
}
