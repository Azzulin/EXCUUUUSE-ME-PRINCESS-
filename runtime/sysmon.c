// Machine telemetry in the log (Linux handhelds, made for the Steam Deck): every 10 s of play one "sys:" line with the
// frame rate of those 10 s, the APU's power, the battery's power and charge, the temperatures, the fan, how busy the
// GPU is, the CPU load of the machine and of the game, and the CPU and GPU clocks. It is always on, so a session the
// owner played from Gaming Mode can be read afterwards in logs/aoc.log next to the frame-time summary: what the game
// cost in watts and degrees at each point, without a second tool running on the device.
//
// Sources (sysfs and procfs, read once a second by a thread of its own; a missing file leaves its number out):
//   /sys/class/hwmon/hwmon*/name = amdgpu: power1_average (the APU's package power, microwatts; power1_input on
//       kernels that name it so), temp1_input (millidegrees), freq1_input (GPU clock, Hz)
//   .../name = k10temp: temp1_input (CPU, millidegrees)       .../name = steamdeck_hwmon: fan1_input (rpm)
//   /sys/class/power_supply/*/type = Battery: status, capacity, voltage_now (uV) x current_now (uA)
//   /sys/class/drm/card*/device/gpu_busy_percent
//   /proc/stat (machine CPU time), CLOCK_PROCESS_CPUTIME_ID (the game's), cpu*/cpufreq/scaling_cur_freq (kHz)
// On other systems sysmon_start does nothing.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "gfx.h"
#include "host.h"
#include "platform/platform.h"

#ifdef __linux__
#include <dirent.h>
#include <time.h>
#include <unistd.h>

#define PERIOD_S 10

extern GfxStats gfx_counters;   // nvn_api.h: frames presented

static struct {
    char apu_power[160], gpu_temp[160], gpu_freq[160], cpu_temp[160], fan[160], gpu_busy[160];
    char bat_status[160], bat_capacity[160], bat_voltage[160], bat_current[160];
    int ncpu;
} P;

static int read_text(const char *path, char *out, size_t n) {
    if (!path[0]) return 0;
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    size_t got = fread(out, 1, n - 1, f);
    fclose(f);
    out[got] = 0;
    while (got && (out[got - 1] == '\n' || out[got - 1] == ' ')) out[--got] = 0;
    return got > 0;
}

static int read_num(const char *path, double *v) {
    char b[64];
    if (!read_text(path, b, sizeof b)) return 0;
    char *end;
    *v = strtod(b, &end);
    return end != b;
}

static int exists(const char *path) { return access(path, R_OK) == 0; }

// dir/<entry>/<leaf> for every entry of dir whose <key> file holds want; fills out[i] with the entry's leaves[i].
static void find(const char *dir, const char *key, const char *want, const char *const *leaves, char (*out[])[160], int n) {
    DIR *d = opendir(dir);
    if (!d) return;
    struct dirent *e;
    while ((e = readdir(d))) {
        if (e->d_name[0] == '.') continue;
        char path[160], text[64];
        snprintf(path, sizeof path, "%s/%s/%s", dir, e->d_name, key);
        if (!read_text(path, text, sizeof text) || strcmp(text, want)) continue;
        for (int i = 0; i < n; i++) {
            if ((*out[i])[0]) continue;
            snprintf(path, sizeof path, "%s/%s/%s", dir, e->d_name, leaves[i]);
            if (exists(path)) snprintf(*out[i], sizeof *out[i], "%s", path);
        }
    }
    closedir(d);
}

static void discover(void) {
    static const char *const amd[] = {"power1_average", "power1_input", "temp1_input", "freq1_input"};
    char (*amd_out[])[160] = {&P.apu_power, &P.apu_power, &P.gpu_temp, &P.gpu_freq};
    find("/sys/class/hwmon", "name", "amdgpu", amd, amd_out, 4);
    static const char *const k10[] = {"temp1_input"};
    char (*k10_out[])[160] = {&P.cpu_temp};
    find("/sys/class/hwmon", "name", "k10temp", k10, k10_out, 1);
    static const char *const fan[] = {"fan1_input"};
    char (*fan_out[])[160] = {&P.fan};
    find("/sys/class/hwmon", "name", "steamdeck_hwmon", fan, fan_out, 1);
    static const char *const bat[] = {"status", "capacity", "voltage_now", "current_now"};
    char (*bat_out[])[160] = {&P.bat_status, &P.bat_capacity, &P.bat_voltage, &P.bat_current};
    find("/sys/class/power_supply", "type", "Battery", bat, bat_out, 4);
    for (int i = 0; i < 4 && !P.gpu_busy[0]; i++) {
        char path[160];
        snprintf(path, sizeof path, "/sys/class/drm/card%d/device/gpu_busy_percent", i);
        if (exists(path)) snprintf(P.gpu_busy, sizeof P.gpu_busy, "%s", path);
    }
    long n = sysconf(_SC_NPROCESSORS_ONLN);
    P.ncpu = n > 0 ? (int)n : 1;
}

// Machine CPU time from the first line of /proc/stat: busy and total jiffies.
static int cpu_times(double *busy, double *total) {
    char b[256];
    if (!read_text("/proc/stat", b, sizeof b)) return 0;
    unsigned long long v[8] = {0};
    if (sscanf(b, "cpu %llu %llu %llu %llu %llu %llu %llu %llu", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7]) < 4)
        return 0;
    *total = 0;
    for (int i = 0; i < 8; i++) *total += (double)v[i];
    *busy = *total - (double)v[3] - (double)v[4];   // less idle and iowait
    return 1;
}

static double cpu_mhz(void) {
    double sum = 0;
    int n = 0;
    for (int i = 0; i < P.ncpu && i < 64; i++) {
        char path[96];
        double v;
        snprintf(path, sizeof path, "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq", i);
        if (read_num(path, &v)) sum += v / 1000.0, n++;
    }
    return n ? sum / n : 0;
}

typedef struct { double sum, max; int n; } Acc;
static void acc(Acc *a, double v) {
    a->sum += v, a->n++;
    if (a->n == 1 || v > a->max) a->max = v;
}
static double avg(const Acc *a) { return a->n ? a->sum / a->n : 0; }

static void sampler(void *arg) {
    (void)arg;
    discover();
    rt_log("sys: sensors: APU power %s, battery %s, CPU temperature %s, GPU temperature %s, fan %s, GPU load %s; %d CPU threads",
           P.apu_power[0] ? "yes" : "no", P.bat_voltage[0] && P.bat_current[0] ? "yes" : "no", P.cpu_temp[0] ? "yes" : "no",
           P.gpu_temp[0] ? "yes" : "no", P.fan[0] ? "yes" : "no", P.gpu_busy[0] ? "yes" : "no", P.ncpu);
    Acc apu = {0}, batw = {0}, ct = {0}, gt = {0}, fan = {0}, busy = {0}, mhz = {0}, gmhz = {0};
    double busy0 = 0, total0 = 0;
    int have_cpu = cpu_times(&busy0, &total0);
    struct timespec ts;
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
    double proc0 = (double)ts.tv_sec + ts.tv_nsec / 1e9;
    uint64_t t0 = plat_now_ns(), frames0 = __atomic_load_n(&gfx_counters.frames, __ATOMIC_RELAXED);
    for (int tick = 1;; tick++) {
        plat_sleep_ms(1000);
        double v, u, i;
        if (read_num(P.apu_power, &v)) acc(&apu, v / 1e6);
        if (read_num(P.bat_voltage, &u) && read_num(P.bat_current, &i)) acc(&batw, u * i / 1e12);
        if (read_num(P.cpu_temp, &v)) acc(&ct, v / 1000.0);
        if (read_num(P.gpu_temp, &v)) acc(&gt, v / 1000.0);
        if (read_num(P.fan, &v)) acc(&fan, v);
        if (read_num(P.gpu_busy, &v)) acc(&busy, v);
        if (read_num(P.gpu_freq, &v)) acc(&gmhz, v / 1e6);
        if ((v = cpu_mhz()) > 0) acc(&mhz, v);
        if (tick % PERIOD_S) continue;
        uint64_t t1 = plat_now_ns(), frames1 = __atomic_load_n(&gfx_counters.frames, __ATOMIC_RELAXED);
        double secs = (double)(t1 - t0) / 1e9, busy1 = 0, total1 = 0;
        clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
        double proc1 = (double)ts.tv_sec + ts.tv_nsec / 1e9;
        char line[640], status[32] = "", cap[16] = "";
        size_t n = (size_t)snprintf(line, sizeof line, "sys: %.0f s to frame %llu: %.1f fps", secs, (unsigned long long)frames1,
                                    secs > 0 ? (double)(frames1 - frames0) / secs : 0.0);
#define ADD(...) (n += n < sizeof line ? (size_t)snprintf(line + n, sizeof line - n, __VA_ARGS__) : 0)
        if (apu.n) ADD("; APU %.1f W (peak %.1f)", avg(&apu), apu.max);
        if (batw.n) {
            read_text(P.bat_status, status, sizeof status);
            read_text(P.bat_capacity, cap, sizeof cap);
            ADD("; battery %.1f W %s, %s%%", avg(&batw), status[0] ? status : "?", cap[0] ? cap : "?");
        }
        if (ct.n) ADD("; cpu %.0f C (peak %.0f)", avg(&ct), ct.max);
        if (gt.n) ADD(", gpu %.0f C", avg(&gt));
        if (fan.n) ADD(", fan %.0f rpm", avg(&fan));
        if (busy.n) ADD("; gpu busy %.0f%%", avg(&busy));
        if (have_cpu && cpu_times(&busy1, &total1) && total1 > total0)
            ADD("; cpu load %.0f%% of %d threads", 100.0 * (busy1 - busy0) / (total1 - total0), P.ncpu);
        if (secs > 0) ADD(", the game %.2f cores", (proc1 - proc0) / secs);
        if (mhz.n) ADD("; cpu %.0f MHz", avg(&mhz));
        if (gmhz.n) ADD(", gpu %.0f MHz", avg(&gmhz));
#undef ADD
        rt_log("%s", line);
        apu = batw = ct = gt = fan = busy = mhz = gmhz = (Acc){0};
        busy0 = busy1, total0 = total1, proc0 = proc1, t0 = t1, frames0 = frames1;
    }
}

void sysmon_start(void) {
    static int started;
    if (__atomic_exchange_n(&started, 1, __ATOMIC_ACQ_REL)) return;
    if (!plat_thread_spawn(sampler, NULL, "sysmon", 256u << 10)) rt_log("sys: the telemetry thread did not start");
}

#else
void sysmon_start(void) {}
#endif
