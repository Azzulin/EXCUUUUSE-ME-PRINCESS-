// State recorder for stalls and black screens, always on: what the game was doing in the seconds before the picture
// stopped or went black, written to the log when it happens. tools/diag_view.py reads the reports.
//
// One host thread (started at the first present, kern_watch_present) takes a sample a second into a ring of
// DG_SAMPLES: presents, the picture's brightness (a 320x180 copy of the presented frame, gfx_present.c thumbnails, one a
// second), draws per frame, the audio output's peak, bytes read from the RomFS, draws skipped and zero-view bindings
// (the two ways a draw can lose content here), live movie decoders, the main thread's state and the virtual cores
// held. A report holds the last DG_ROWS samples, the movie decoders, every guest thread with its wait and guest call
// chain (kernel.c kern_threads_report) and the last DG_THUMBS picture copies as PNG files under <log dir>/diag/.
// Reports come from:
//   - no present for AOC_HANG_SECS (10; 0 off), once per stall, and once more at three times that if it goes on
//     (two thread tables tell a thread that is stuck from one that is working);
//   - a black picture (under 2 in 1000 pixels above luma 16) for AOC_BLACK_SECS (15; 0 off) while the game presents,
//     once per black stretch (a load shows 5-6 s of black, hence 15);
//   - a dark picture (mean luma under 25, not black) with the scene being drawn (over 150 draws a frame) for
//     AOC_DARK_SECS (15; 0 off), once per dark stretch;
//   - F8 with the game window in front: a mark. Also saves that present full size under <log dir>/diag/marks/.
// Hit watch: the start of a controller vibration is the game's own sign of a hit given or taken (ov_input.c). Each
// one is counted in the timeline; with AOC_HIT_SHOTS=<n> the next 8 presents after a hit are saved full size under
// <log dir>/diag/hits/ for the first n hits at least 3 s apart, to see whether the hit effect is drawn.
// Attack watch: AOC_ATTACK_SHOTS=<n> saves presents 3 to 14 after a press of the regular attack button (Y) under
// <log dir>/diag/hits/a<nn>-*.png, for the first n presses at least 20 s apart: the frames where the blow lands,
// whatever the vibration does. AOC_ATTACK_DUMP=<k> dumps the frame 6 presents after the k-th of them.
// Frame dumps (vk_dump.c, AOC_DUMP=arm): AOC_HIT_DUMP=<k> dumps the frame after the k-th watched hit; AOC_MARK_DUMP=1
// dumps on F8; a dark or black report dumps too.
// Input: a game run that writes a log also records the input to <log dir>/sessions/input-<time>.txt (an
// AOC_INPUT_SCRIPT), unless AOC_INPUT_RECORD or AOC_INPUT_SCRIPT is set.
// Cost while nothing happens: per present one time read; per second one 320x180 blit and its read-back, and this
// thread's sample. Every 60 s a "diag: image:" line when draws were skipped or bindings read the zero view.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "cfg.h"
#include "flight.h"
#include "host.h"
#include "input.h"
#include "movie.h"
#include "vk_exec.h"
#include "platform/platform.h"

#define DG_SAMPLES 120
#define DG_ROWS 45
#define DG_THUMBS 10
#define TH_PIXELS (FLIGHT_THUMB_W * FLIGHT_THUMB_H)

typedef struct {
    float t;                       // seconds since the guest started
    uint64_t frame;
    uint32_t presents, draws, read_kib, skip_pipe, skip_shader, zero_views;
    int luma, lit;                 // mean luma 0..255 and pixels above 16 per thousand; -1 no picture copy this second
    float audio;                   // peak of the output, 0..1
    int movies, cores, rumbles;
    char main_st[8];
} Sample;

static Sample ring[DG_SAMPLES];
static uint64_t n_samples;

static volatile uint64_t g_frame;            // latest present (diag_frame)
static volatile int64_t g_audio_peak_u;      // peak * 1e6 since the last sample
static volatile int64_t g_read_bytes;

// Picture copies. The present thread asks once a second (diag_thumb_wanted) and queues the frame; this thread reads it
// back when its fence has signalled.
static volatile uint64_t g_thumb_last_ns;
static volatile uint64_t g_want[8];
static volatile uint32_t g_want_w;
static uint32_t g_want_r;
static int g_thumbs_on;
static struct { uint64_t frame; float t; uint8_t *px; } thumbs[DG_THUMBS];
static uint64_t n_thumbs;
static uint8_t *thumb_tmp;

void diag_setup(void) {
    const char *e = cfg_get("AOC_DIAG");
    if (e && !strcmp(e, "0")) return;
    g_thumbs_on = 1;
    vk_thumbs_enable(64);   // a no-op when the flight recorder already asked for its own ring
}

// <log dir>, or <exe dir>/logs when this run writes no log file.
static void log_dir(char *dir, size_t cap) {
    const char *lp = rt_log_path();
    if (lp) {
        snprintf(dir, cap, "%s", lp);
        char *s = plat_last_sep(dir);
        if (s) *s = 0;
    } else {
        char *s = plat_exe_path(dir, PLAT_PATH_MAX) ? plat_last_sep(dir) : NULL;
        if (s) snprintf(s, 16, "/logs");
        else snprintf(dir, cap, "logs");
    }
}

// input.c: where this run records its input when nothing else says, NULL for no recording.
const char *diag_record_path(void) {
    static char path[PLAT_PATH_MAX * 3 + 96];
    const char *e = cfg_get("AOC_DIAG"), *sc = cfg_get("AOC_INPUT_SCRIPT");
    if ((e && !strcmp(e, "0")) || (sc && *sc) || !rt_log_path()) return NULL;
    log_dir(path, PLAT_PATH_MAX * 3);
    size_t n = strlen(path);
    snprintf(path + n, sizeof path - n, "/sessions");
    plat_file_mkdir_p(path);
    struct tm st;
    plat_local_time(&st);
    n = strlen(path);
    snprintf(path + n, sizeof path - n, "/input-%04d%02d%02d-%02d%02d%02d.txt", st.tm_year + 1900, st.tm_mon + 1,
             st.tm_mday, st.tm_hour, st.tm_min, st.tm_sec);
    return path;
}

// ---- hit watch and marks
static volatile int32_t g_rumbles;           // vibration starts since the last sample
static volatile int32_t g_burst, g_burst_id, g_burst_skip, g_burst_kind, g_burst_dump, g_mark_shot, g_mark_id;
static volatile uint64_t g_hit_ns;
static int hit_shots = -1, hit_dump, n_hits;
static int atk_shots = -1, atk_dump, n_atks, atk_was;
static uint64_t atk_ns;

// input.c, every poll of the merged controller state: y is the regular attack button.
void diag_attack_button(int y) {
    int edge = y && !atk_was;
    atk_was = y;
    if (!edge) return;
    if (atk_shots < 0) {
        const char *e = cfg_get("AOC_ATTACK_SHOTS"), *d = cfg_get("AOC_ATTACK_DUMP");
        atk_dump = d && *d ? atoi(d) : 0;
        atk_shots = e && *e ? atoi(e) : 0;
    }
    uint64_t now = kern_now_ns();
    if (n_atks >= atk_shots || frame_step_world_us() < 0 || (atk_ns && now - atk_ns < 20000000000ull) ||
        __atomic_load_n(&g_burst, __ATOMIC_RELAXED) > 0)
        return;
    atk_ns = now;
    int id = ++n_atks;
    __atomic_store_n(&g_burst_id, id, __ATOMIC_RELAXED);
    __atomic_store_n(&g_burst_kind, 'a', __ATOMIC_RELAXED);
    __atomic_store_n(&g_burst_skip, 3, __ATOMIC_RELAXED);
    __atomic_store_n(&g_burst_dump, id == atk_dump ? 4 : 0, __ATOMIC_RELAXED);   // asked 4 presents in: dumps the 6th
    __atomic_store_n(&g_burst, 12, __ATOMIC_RELEASE);
    rt_log("diag: attack %d: Y pressed at frame %llu, %.1f s of game time; presents 3 to 14 after it go to "
           "logs/diag/hits/a%02d-*.png%s", id, (unsigned long long)__atomic_load_n(&g_frame, __ATOMIC_RELAXED),
           (double)frame_step_world_us() / 1e6, id, id == atk_dump ? "; frame dump asked" : "");
}

void diag_rumble(float amp) {
    __atomic_add_fetch(&g_rumbles, 1, __ATOMIC_RELAXED);
    if (hit_shots < 0) {
        const char *e = cfg_get("AOC_HIT_SHOTS"), *d = cfg_get("AOC_HIT_DUMP");
        hit_dump = d && *d ? atoi(d) : 0;
        hit_shots = e && *e ? atoi(e) : 0;
    }
    uint64_t now = kern_now_ns(), last = __atomic_load_n(&g_hit_ns, __ATOMIC_RELAXED);
    if (n_hits >= hit_shots || frame_step_world_us() < 0 || (last && now - last < 3000000000ull)) return;
    __atomic_store_n(&g_hit_ns, now, __ATOMIC_RELAXED);
    int id = ++n_hits;
    __atomic_store_n(&g_burst_id, id, __ATOMIC_RELAXED);
    __atomic_store_n(&g_burst_kind, 'h', __ATOMIC_RELAXED);
    __atomic_store_n(&g_burst_skip, 0, __ATOMIC_RELAXED);
    __atomic_store_n(&g_burst_dump, 0, __ATOMIC_RELAXED);
    __atomic_store_n(&g_burst, 8, __ATOMIC_RELEASE);
    if (id == hit_dump) vk_dump_trigger("hit");
    rt_log("diag: hit %d: vibration %.2f starts at frame %llu, %.1f s of game time; the next 8 presents go to "
           "logs/diag/hits/h%02d-*.png%s", id, (double)amp, (unsigned long long)__atomic_load_n(&g_frame, __ATOMIC_RELAXED),
           (double)frame_step_world_us() / 1e6, id, id == hit_dump ? "; frame dump asked" : "");
}

int diag_shot_wanted(uint64_t present, char *path, size_t cap) {
    int burst = __atomic_load_n(&g_burst, __ATOMIC_ACQUIRE), mark = __atomic_exchange_n(&g_mark_shot, 0, __ATOMIC_ACQUIRE);
    if (burst <= 0 && !mark) return 0;
    if (!mark) {
        int skip = __atomic_load_n(&g_burst_skip, __ATOMIC_RELAXED), dump = __atomic_load_n(&g_burst_dump, __ATOMIC_RELAXED);
        if (dump && !--dump) vk_dump_trigger("attack");
        __atomic_store_n(&g_burst_dump, dump, __ATOMIC_RELAXED);
        if (skip > 0) {
            __atomic_store_n(&g_burst_skip, skip - 1, __ATOMIC_RELAXED);
            return 0;
        }
    }
    log_dir(path, PLAT_PATH_MAX * 3);
    size_t n = strlen(path);
    snprintf(path + n, cap - n, mark ? "/diag/marks" : "/diag/hits");
    plat_file_mkdir_p(path);
    n = strlen(path);
    if (mark) {
        snprintf(path + n, cap - n, "/m%02d-p%07llu.png", (int)__atomic_load_n(&g_mark_id, __ATOMIC_RELAXED),
                 (unsigned long long)present);
    } else {
        __atomic_store_n(&g_burst, burst - 1, __ATOMIC_RELEASE);
        snprintf(path + n, cap - n, "/%c%02d-p%07llu.png", (char)__atomic_load_n(&g_burst_kind, __ATOMIC_RELAXED),
                 (int)__atomic_load_n(&g_burst_id, __ATOMIC_RELAXED), (unsigned long long)present);
    }
    return 1;
}

// A full-size picture of the next present under diag/marks/, and a frame dump when asked (AOC_DUMP=arm).
static void mark(const char *why, int dump) {
    int id = __atomic_add_fetch(&g_mark_id, 1, __ATOMIC_RELAXED);
    __atomic_store_n(&g_mark_shot, 1, __ATOMIC_RELEASE);
    if (dump) vk_dump_trigger(why);
    rt_log("diag: mark %d (%s) at frame %llu, %.1f s of game time: picture logs/diag/marks/m%02d-*.png%s", id, why,
           (unsigned long long)__atomic_load_n(&g_frame, __ATOMIC_RELAXED), (double)frame_step_world_us() / 1e6, id,
           dump ? ", frame dump asked" : "");
}

void diag_frame(uint64_t frame) { __atomic_store_n(&g_frame, frame, __ATOMIC_RELAXED); }

void diag_audio(const float *lr, int frames) {
    float p = 0;
    for (int k = 0; k < 2 * frames; k++) {
        float x = lr[k] < 0 ? -lr[k] : lr[k];
        if (x > p) p = x;
    }
    int64_t u = (int64_t)(p * 1e6f), cur = __atomic_load_n(&g_audio_peak_u, __ATOMIC_RELAXED);
    while (u > cur && !__atomic_compare_exchange_n(&g_audio_peak_u, &cur, u, 1, __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {}
}

void diag_read(uint64_t bytes) { plat_add64(&g_read_bytes, (int64_t)bytes); }

int diag_thumb_wanted(uint64_t frame) {
    if (!g_thumbs_on) return 0;
    uint64_t now = kern_now_ns(), last = __atomic_load_n(&g_thumb_last_ns, __ATOMIC_RELAXED);
    if (last && now - last < 1000000000ull) return 0;
    __atomic_store_n(&g_thumb_last_ns, now, __ATOMIC_RELAXED);
    uint32_t w = __atomic_load_n(&g_want_w, __ATOMIC_RELAXED);
    __atomic_store_n(&g_want[w % 8], frame, __ATOMIC_RELAXED);
    __atomic_store_n(&g_want_w, w + 1, __ATOMIC_RELEASE);
    return 1;
}

// Reads the queued picture copies that are complete; the newest one's brightness goes to *luma and *lit.
static void take_thumbs(float t, int *luma, int *lit) {
    if (!thumb_tmp && !(thumb_tmp = malloc((size_t)TH_PIXELS * 4))) return;
    uint32_t w = __atomic_load_n(&g_want_w, __ATOMIC_ACQUIRE);
    if (w - g_want_r > 8) g_want_r = w - 8;
    while (g_want_r != w) {
        uint64_t f = __atomic_load_n(&g_want[g_want_r % 8], __ATOMIC_RELAXED);
        if (!vk_thumbs_read(f, thumb_tmp)) {
            if (w - g_want_r > 3) { g_want_r++; continue; }   // never completed (swapchain rebuilt, minimised): dropped
            break;
        }
        g_want_r++;
        uint64_t sum = 0;
        uint32_t above = 0;
        for (int i = 0; i < TH_PIXELS; i++) {
            const uint8_t *p = thumb_tmp + 4 * i;
            uint32_t y = (2u * p[0] + 5u * p[1] + p[2]) >> 3;
            sum += y;
            above += y > 16;
        }
        *luma = (int)(sum / TH_PIXELS);
        *lit = (int)((uint64_t)above * 1000 / TH_PIXELS);
        unsigned k = (unsigned)(n_thumbs % DG_THUMBS);
        if (!thumbs[k].px) thumbs[k].px = malloc((size_t)TH_PIXELS * 4);
        if (thumbs[k].px) {
            memcpy(thumbs[k].px, thumb_tmp, (size_t)TH_PIXELS * 4);
            thumbs[k].frame = f, thumbs[k].t = t;
            n_thumbs++;
        }
    }
}

static void write_thumbs(const char *why) {
    if (!n_thumbs) {
        rt_log("diag: no picture copies to write (none completed yet, or no GPU)");
        return;
    }
    char dir[PLAT_PATH_MAX * 3 + 64], path[PLAT_PATH_MAX * 3 + 128];
    log_dir(dir, PLAT_PATH_MAX * 3);
    struct tm st;
    plat_local_time(&st);
    size_t n = strlen(dir);
    snprintf(dir + n, sizeof dir - n, "/diag/%04d%02d%02d-%02d%02d%02d-%s", st.tm_year + 1900, st.tm_mon + 1, st.tm_mday,
             st.tm_hour, st.tm_min, st.tm_sec, why);
    plat_file_mkdir_p(dir);
    int wrote = 0;
    uint64_t have = n_thumbs < DG_THUMBS ? n_thumbs : DG_THUMBS;
    for (uint64_t i = n_thumbs - have; i < n_thumbs; i++) {
        unsigned k = (unsigned)(i % DG_THUMBS);
        snprintf(path, sizeof path, "%s/t%05d-f%06llu.png", dir, (int)thumbs[k].t, (unsigned long long)thumbs[k].frame);
        wrote += flight_write_png(path, thumbs[k].px);
    }
    rt_log("diag: %d picture copies (320x180, one a second, the last at %.0f s) written to %s", wrote,
           (double)thumbs[(n_thumbs - 1) % DG_THUMBS].t, dir);
}

static int n_reports;

static void report(const char *why, const char *slug, const char *thread_tag) {
    int id = ++n_reports;
    uint64_t now = kern_now_ns();
    rt_log("diag: report %d: %s; %.1f s after the game started, frame %llu, port %s", id, why,
           rt_guest_start_ns ? (double)(now - rt_guest_start_ns) / 1e9 : 0.0,
           (unsigned long long)__atomic_load_n(&g_frame, __ATOMIC_RELAXED), rt_port_version);
    rt_log("diag: timeline, one row a second, newest last (luma: mean 0-255 of the presented picture, lit: pixels "
           "above 16 per thousand, -1 no copy that second; skipped: draws dropped while their pipeline / shader was "
           "built; zero: buffer-texture bindings that read zeros; main: the main thread's state at the sample)");
    uint64_t rows = n_samples < DG_ROWS ? n_samples : DG_ROWS;
    for (uint64_t i = n_samples - rows; i < n_samples; i++) {
        const Sample *s = &ring[i % DG_SAMPLES];
        rt_log("diag:  t %7.1f frame %7llu presents %2u luma %3d lit %4d draws %5u audio %.3f read %6u KiB skipped %u/%u "
               "zero %u movies %d main %-7s cores %d hits %d", (double)s->t, (unsigned long long)s->frame, s->presents, s->luma,
               s->lit, s->presents ? s->draws / s->presents : 0, (double)s->audio, s->read_kib, s->skip_pipe,
               s->skip_shader, s->zero_views, s->movies, s->main_st, s->cores, s->rumbles);
    }
    char mv[768];
    if (movie_diag(mv, sizeof mv)) rt_log("diag: movie decoders: %s", mv);
    else rt_log("diag: movie decoders: none live (a cutscene now is drawn by the game, not a video)");
    rt_log("diag: image totals since the start: %llu draws skipped while their pipeline was built, %llu while their "
           "shader was translated, %llu waited instead; %llu buffer-texture bindings read zeros",
           (unsigned long long)perf_total(PERF_CNT_PIPE_SKIP), (unsigned long long)perf_total(PERF_CNT_SHADER_SKIP),
           (unsigned long long)(perf_total(PERF_CNT_PIPE_WAIT) + perf_total(PERF_CNT_ONESHOT_WAIT)),
           (unsigned long long)vk_exec_zero_views());
    kern_threads_report(thread_tag);
    write_thumbs(slug);
    rt_log("diag: end of report %d", id);
}

static void diag_main(void *arg) {
    (void)arg;
    const char *v = cfg_get("AOC_HANG_SECS");
    double hang_s = v && *v ? atof(v) : 10.0;
    v = cfg_get("AOC_BLACK_SECS");
    double black_s = v && *v ? atof(v) : 15.0;
    v = cfg_get("AOC_DARK_SECS");
    double dark_s = v && *v ? atof(v) : 15.0;
    uint64_t hang_ns = hang_s > 0 ? (uint64_t)(hang_s * 1e9) : 0, black_ns = black_s > 0 ? (uint64_t)(black_s * 1e9) : 0;
    uint64_t dark_ns = dark_s > 0 ? (uint64_t)(dark_s * 1e9) : 0, dark_since = 0;
    const char *md = cfg_get("AOC_MARK_DUMP");
    int dark_reported = 0, mark_dump = md && *md && strcmp(md, "0");
    rt_log("diag: state recorder on: report after %.0f s without a present (AOC_HANG_SECS), %.0f s of black picture "
           "(AOC_BLACK_SECS) or F8; picture copies %s", hang_s, black_s, g_thumbs_on ? "one a second" : "off (AOC_DIAG=0)");
    uint64_t next = kern_now_ns() + 1000000000ull, hang_reported = 0, hang_again = 0, black_since = 0, minute = 0;
    uint64_t p_frame = __atomic_load_n(&g_frame, __ATOMIC_RELAXED), p_draws = vk_exec_frame.draws;
    uint64_t p_pipe = 0, p_shader = 0, p_zero = 0, m_pipe = 0, m_shader = 0, m_zero = 0;
    int black_reported = 0, key_was = 0;
    for (;;) {
        plat_sleep_ms(100);
        uint64_t now = kern_now_ns();
        int key = input_flight_key();
        if (key && !key_was) {
            mark("f8", mark_dump);
            report("F8 pressed", "f8", "diag");
        }
        key_was = key;
        if (now < next) continue;
        next += 1000000000ull;
        if (next < now) next = now + 1000000000ull;

        Sample *s = &ring[n_samples % DG_SAMPLES];
        memset(s, 0, sizeof *s);
        s->t = rt_guest_start_ns ? (float)((double)(now - rt_guest_start_ns) / 1e9) : 0;
        s->frame = __atomic_load_n(&g_frame, __ATOMIC_RELAXED);
        s->presents = (uint32_t)(s->frame - p_frame);
        p_frame = s->frame;
        uint64_t d = vk_exec_frame.draws;   // the replay thread's counter, read without a lock: a diagnosis figure
        s->draws = (uint32_t)(d >= p_draws ? d - p_draws : d);   // AOC_TRACE=gfx resets it every frame
        p_draws = d;
        s->audio = (float)__atomic_exchange_n(&g_audio_peak_u, 0, __ATOMIC_RELAXED) / 1e6f;
        s->read_kib = (uint32_t)((uint64_t)__atomic_exchange_n(&g_read_bytes, 0, __ATOMIC_RELAXED) >> 10);
        uint64_t pipe = perf_total(PERF_CNT_PIPE_SKIP), shader = perf_total(PERF_CNT_SHADER_SKIP), zero = vk_exec_zero_views();
        s->skip_pipe = (uint32_t)(pipe - p_pipe), s->skip_shader = (uint32_t)(shader - p_shader);
        s->zero_views = (uint32_t)(zero - p_zero);
        p_pipe = pipe, p_shader = shader, p_zero = zero;
        s->movies = movie_diag(NULL, 0);
        s->cores = kern_diag_brief(s->main_st, sizeof s->main_st);
        s->rumbles = __atomic_exchange_n(&g_rumbles, 0, __ATOMIC_RELAXED);
        s->luma = s->lit = -1;
        take_thumbs(s->t, &s->luma, &s->lit);
        n_samples++;

        if (++minute >= 60) {
            minute = 0;
            if (pipe != m_pipe || shader != m_shader || zero != m_zero)
                rt_log("diag: image: in the last 60 s %llu draws were skipped while their pipeline was built and %llu "
                       "while their shader was translated; %llu buffer-texture bindings read zeros",
                       (unsigned long long)(pipe - m_pipe), (unsigned long long)(shader - m_shader),
                       (unsigned long long)(zero - m_zero));
            m_pipe = pipe, m_shader = shader, m_zero = zero;
        }

        uint64_t last = kern_last_present_ns();
        char why[160];
        if (hang_ns && last && now > last + hang_ns) {
            if (hang_reported != last) {
                hang_reported = last;
                hang_again = now + 2 * hang_ns;
                snprintf(why, sizeof why, "no present for %.1f s", (double)(now - last) / 1e9);
                rt_log("hang: %s (the state recorder's report follows)", why);
                report(why, "hang", "hang");
            } else if (hang_again && now > hang_again) {
                hang_again = 0;
                rt_log("diag: still no present after %.1f s; the threads again, to compare with the report above",
                       (double)(now - last) / 1e9);
                kern_threads_report("hang");
            }
            continue;
        }
        if (s->luma >= 0) {
            if (s->lit < 2) {
                if (!black_since) black_since = now;
                if (black_ns && !black_reported && now - black_since >= black_ns) {
                    black_reported = 1;
                    snprintf(why, sizeof why, "black picture for %.1f s while the game presents (%u presents in the last second)",
                             (double)(now - black_since) / 1e9, s->presents);
                    mark("black", 1);
                    report(why, "black", "diag");
                }
            } else {
                if (black_reported)
                    rt_log("diag: the picture is back after %.1f s of black", (double)(now - black_since) / 1e9);
                black_since = 0, black_reported = 0;
            }
            // dark, not black, with the scene drawn: the game renders and something darkens it
            if (s->lit >= 2 && s->luma < 25 && s->presents && s->draws / s->presents > 150) {
                if (!dark_since) dark_since = now;
                if (dark_ns && !dark_reported && now - dark_since >= dark_ns) {
                    dark_reported = 1;
                    snprintf(why, sizeof why, "dark picture (mean luma %d) for %.1f s with %u draws a frame", s->luma,
                             (double)(now - dark_since) / 1e9, s->draws / s->presents);
                    mark("dark", 1);
                    report(why, "dark", "diag");
                }
            } else {
                if (dark_reported)
                    rt_log("diag: the picture is bright again after %.1f s of dark", (double)(now - dark_since) / 1e9);
                dark_since = 0, dark_reported = 0;
            }
        }
    }
}

// prof_write, when the game exits (window closed, --seconds): the last seconds stay in the log even when nothing
// tripped a report, so a session closed by hand at a bad scene can still be read.
void diag_exit(void) {
    static int32_t done;
    if (!n_samples || plat_xchg32(&done, 1)) return;
    report("the game is exiting", "exit", "diag");
}

void diag_start(void) {
    static int32_t started;
    if (plat_xchg32(&started, 1)) return;
    const char *e = cfg_get("AOC_DIAG");
    if (e && !strcmp(e, "0")) {
        const char *h = cfg_get("AOC_HANG_SECS");
        if (h && *h && atof(h) <= 0) return;
    }
    plat_thread_spawn(diag_main, NULL, "aoc diag", 0);
}
