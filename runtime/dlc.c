// Add-on content (DLC): the RomFS of each DLC the player extracted, listed through nn::aoc and mounted through
// nn::fs::MountAddOnContent.
//
// Input: <romfs>/dlc-<title id>.bin next to romfs.bin (rt_config()->romfs), one plain RomFS image per DLC, written by
// tools/extract_dlc.py from the player's NSPs with the whole IVFC hash tree checked. The DLC of index n has the title
// id DLC_BASE_ID + n; the images found at the first use are the add-on content the game sees, in index order. No
// image: the game runs without add-on content, as on a console without it.
//
// Each image's directory and file tables are parsed once into a list of paths sorted the way strcmp orders them; a
// malformed image stops the game (extract it again). Files are read with positional reads (platform.h
// plat_file_pread), so threads read in parallel. A DLC is read-only and can be mounted under several names at once;
// file handles stay valid after the mount's name is unmounted, as they keep the image, not the name.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "fs.h"
#include "host.h"
#include "romfs_path.h"
#include "platform/platform.h"

#define DLC_BASE_ID 0x01002B00111A3000ull   // Age of Calamity's application id + 0x1000
#define NDLC 64                             // indices 1..NDLC-1 are looked for
#define NMOUNT 16
#define NH 4096                             // file handle slots
#define NO_ENTRY 0xffffffffu
#define READ_CHUNK (64u << 20)

typedef struct { uint64_t offset, size; char *name; } DlcFile;
typedef struct {
    int index;
    PlatFile *image;
    uint64_t image_size;
    char path[2100];
    uint8_t header[0x50];
    uint8_t *tables[4];        // directory hash, directory meta, file hash, file meta, as the image has them
    uint64_t table_size[4];
    DlcFile *files;            // sorted by name
    size_t nfiles, cap;
} Dlc;

static Dlc *dlcs[NDLC];        // by index; NULL when the player has no image of it
static int present[NDLC], npresent;   // the indices that have an image, ascending
static struct { char name[32]; Dlc *d; } mounts[NMOUNT];
static struct { Dlc *d; uint32_t file; } handles[NH];   // d NULL: free
static PlatMutex lock = PLAT_MUTEX_INIT;

// ---- image parsing
static void bad(const Dlc *d, const char *what) {
    rt_fatal("DLC %d: image %s is malformed (%s); extract it again (tools/extract_dlc.py --force)", d->index, d->path,
             what);
}

static int64_t read_at(PlatFile *f, void *buf, uint32_t n, uint64_t off) {
    mem_thaw((uintptr_t)buf, n);   // the kernel's write would fail on a frozen page instead of faulting
    int64_t got = plat_file_pread(f, buf, n, off);
    return got < 0 ? -1 : got;
}

static void file_add(Dlc *d, const char *prefix, const uint8_t *name, uint32_t nlen, uint64_t off, uint64_t size) {
    uint64_t data = *(const uint64_t *)(d->header + 0x48);
    if (data > d->image_size || off > d->image_size - data || size > d->image_size - data - off) bad(d, "file bounds");
    if (!nlen || memchr(name, 0, nlen) || memchr(name, '/', nlen) || memchr(name, '\\', nlen)) bad(d, "file name");
    if (d->nfiles == d->cap) {
        d->cap = d->cap ? d->cap * 2 : 64;
        d->files = realloc(d->files, d->cap * sizeof *d->files);
        if (!d->files) bad(d, "out of memory");
    }
    size_t pn = strlen(prefix);
    char *path = malloc(pn + nlen + 1);
    if (!path) bad(d, "out of memory");
    memcpy(path, prefix, pn);
    memcpy(path + pn, name, nlen);
    path[pn + nlen] = 0;
    d->files[d->nfiles++] = (DlcFile){data + off, size, path};
}

// The files of the directory entry at `at` of the directory meta table and of its subdirectories (depth bounds a
// table that loops).
static void walk(Dlc *d, uint32_t at, const char *prefix, int depth) {
    const uint8_t *dm = d->tables[1], *fm = d->tables[3];
    uint64_t dn = d->table_size[1], fn = d->table_size[3];
    if (depth > 64 || at > dn || dn - at < 0x18) bad(d, "directory table");
    uint32_t child, file;
    memcpy(&child, dm + at + 8, 4);
    memcpy(&file, dm + at + 12, 4);
    for (uint32_t cur = file, steps = 0; cur != NO_ENTRY; steps++) {
        if (steps > 1000000 || cur > fn || fn - cur < 0x20) bad(d, "file table");
        uint32_t sibling, nlen;
        uint64_t off, size;
        memcpy(&sibling, fm + cur + 4, 4);
        memcpy(&off, fm + cur + 8, 8);
        memcpy(&size, fm + cur + 16, 8);
        memcpy(&nlen, fm + cur + 28, 4);
        if (nlen > fn - cur - 0x20) bad(d, "file name bounds");
        file_add(d, prefix, fm + cur + 0x20, nlen, off, size);
        cur = sibling;
    }
    for (uint32_t cur = child, steps = 0; cur != NO_ENTRY; steps++) {
        if (steps > 1000000 || cur > dn || dn - cur < 0x18) bad(d, "directory table");
        uint32_t sibling, nlen;
        memcpy(&sibling, dm + cur + 4, 4);
        memcpy(&nlen, dm + cur + 20, 4);
        size_t pn = strlen(prefix);
        if (!nlen || nlen > dn - cur - 0x18 || pn + nlen + 2 > 4096 || memchr(dm + cur + 0x18, 0, nlen) ||
            memchr(dm + cur + 0x18, '/', nlen))
            bad(d, "directory name");
        char sub[4096];
        memcpy(sub, prefix, pn);
        memcpy(sub + pn, dm + cur + 0x18, nlen);
        sub[pn + nlen] = '/';
        sub[pn + nlen + 1] = 0;
        walk(d, cur, sub, depth + 1);
        cur = sibling;
    }
}

static int name_order(const void *a, const void *b) {
    return strcmp(((const DlcFile *)a)->name, ((const DlcFile *)b)->name);
}

static Dlc *load(int index, const char *path, PlatFile *image) {
    Dlc *d = calloc(1, sizeof *d);
    if (!d) rt_fatal("DLC %d: out of memory", index);
    d->index = index;
    d->image = image;
    snprintf(d->path, sizeof d->path, "%s", path);
    PlatFileId id;
    if (!plat_file_id(image, &id)) bad(d, "file information");
    d->image_size = id.size;
    if (read_at(image, d->header, sizeof d->header, 0) != (int64_t)sizeof d->header) bad(d, "header");
    const uint64_t *h = (const uint64_t *)d->header;
    if (h[0] != 0x50) bad(d, "header size");
    for (int t = 0; t < 4; t++) {
        uint64_t off = h[1 + 2 * t], size = h[2 + 2 * t];
        if (off > d->image_size || size > d->image_size - off || size > (256u << 20)) bad(d, "table bounds");
        d->table_size[t] = size;
        d->tables[t] = malloc(size ? (size_t)size : 1);
        if (!d->tables[t]) bad(d, "out of memory");
        if (read_at(image, d->tables[t], (uint32_t)size, off) != (int64_t)size) bad(d, "table read");
    }
    walk(d, 0, "", 0);
    qsort(d->files, d->nfiles, sizeof *d->files, name_order);
    for (size_t i = 1; i < d->nfiles; i++)
        if (!strcmp(d->files[i - 1].name, d->files[i].name)) bad(d, "repeated path");
    return d;
}

static void init_once(void *param) {
    (void)param;
    const char *dir = rt_config()->romfs;
    uint64_t bytes = 0;
    for (int i = 1; i < NDLC; i++) {
        char path[2100];
        if (snprintf(path, sizeof path, "%s/dlc-%016llX.bin", dir, (unsigned long long)(DLC_BASE_ID + (uint64_t)i)) >=
            (int)sizeof path)
            rt_fatal("DLC: path too long under %s", dir);
        PlatFile *f = plat_file_open(path);
        if (!f) continue;
        dlcs[i] = load(i, path, f);
        present[npresent++] = i;
        bytes += dlcs[i]->image_size;
        rt_log("DLC %d: %s, %zu files, %.1f MiB", i, path, dlcs[i]->nfiles, dlcs[i]->image_size / 1048576.0);
    }
    if (npresent) rt_log("DLC: %d add-on contents, %.2f GiB", npresent, bytes / 1073741824.0);
    else rt_log("DLC: none (no dlc-*.bin in %s; tools/extract_dlc.py writes them)", dir);
}

static void init(void) {
    static PlatOnce once = PLAT_ONCE_INIT;
    plat_once(&once, init_once, NULL);
}

// ---- nn::aoc
int dlc_count(void) {
    init();
    return npresent;
}

int dlc_list(int32_t *out, int offset, int count) {
    init();
    int n = 0;
    for (int k = offset; k < npresent && n < count; k++) out[n++] = present[k];
    return n;
}

// ---- mounts
static Dlc *mounted(const char *path, const char **rel, int *root) {
    if (!path) return NULL;
    Dlc *d = NULL;
    size_t n = 0;
    plat_mutex_lock_shared(&lock);
    for (int i = 0; i < NMOUNT && !d; i++) {
        n = strlen(mounts[i].name);
        if (n && !strncmp(path, mounts[i].name, n) && path[n] == ':') d = mounts[i].d;
    }
    plat_mutex_unlock_shared(&lock);
    if (!d) return NULL;
    const char *p = path + n + 1;
    int slash = *p == '/';
    while (*p == '/') p++;
    if (root) *root = slash && !*p;                       // "<mount>:/": the mount's root directory
    if (rel) *rel = slash && romfs_path_valid_relative(p) ? p : NULL;
    return d;
}

int dlc_owns(const char *path) { return mounted(path, NULL, NULL) != NULL; }

uint32_t dlc_cache_size(uint64_t *out, int index) {
    init();
    if (!out) return FS_R_INVALID;
    if (index < 1 || index >= NDLC || !dlcs[index]) return FS_R_TARGET_NOT_FOUND;
    const Dlc *d = dlcs[index];
    uint64_t n = sizeof d->header;
    for (int t = 0; t < 4; t++) n += d->table_size[t];
    *out = (n + 0xfff) & ~0xfffull;
    return 0;
}

// nn::fs::MountAddOnContent: `cache` receives what the fs service writes there on a console, the RomFS header and its
// four metadata tables with the header's offsets rebased onto the buffer (as romfs.c ov_mount_rom does for MountRom).
uint32_t dlc_mount(const char *name, int index, void *cache, uint64_t cache_size) {
    init();
    if (!name || !*name || strlen(name) >= sizeof mounts[0].name || strchr(name, ':') || strchr(name, '/'))
        return FS_R_INVALID_ARGUMENT;
    if (index < 1 || index >= NDLC || !dlcs[index]) {
        rt_log("fs mount %s: add-on content %d is not installed", name, index);
        return FS_R_TARGET_NOT_FOUND;
    }
    Dlc *d = dlcs[index];
    char as_path[40];
    snprintf(as_path, sizeof as_path, "%s:", name);
    if (romfs_owns(as_path) || dlc_owns(as_path)) return FS_R_ALREADY_EXISTS;
    uint64_t need = 0;
    dlc_cache_size(&need, index);
    if (cache && cache_size >= need) {
        mem_thaw((uintptr_t)cache, need);
        uint8_t *c = cache;
        memcpy(c, d->header, sizeof d->header);
        uint64_t at = sizeof d->header;
        for (int t = 0; t < 4; t++) {
            memcpy(c + 8 + 16 * t, &at, 8);   // the table's offset in the cache; its size stays
            memcpy(c + at, d->tables[t], (size_t)d->table_size[t]);
            at += d->table_size[t];
        }
    } else if (cache) {
        rt_log("fs mount %s: cache of %#llx bytes is smaller than the %#llx the metadata needs; none copied", name,
               (unsigned long long)cache_size, (unsigned long long)need);
    }
    plat_mutex_lock(&lock);
    for (int i = 0; i < NMOUNT; i++)
        if (!mounts[i].name[0]) {
            mounts[i].d = d;
            strcpy(mounts[i].name, name);
            plat_mutex_unlock(&lock);
            rt_log("fs mount %s: -> add-on content %d (%zu files)", name, index, d->nfiles);
            return 0;
        }
    plat_mutex_unlock(&lock);
    rt_fatal("DLC: mount table full (%d)", NMOUNT);
}

int dlc_unmount(const char *name) {
    if (!name || !*name) return 0;
    plat_mutex_lock(&lock);
    for (int i = 0; i < NMOUNT; i++)
        if (!strcmp(mounts[i].name, name)) {
            mounts[i].name[0] = 0;
            mounts[i].d = NULL;
            plat_mutex_unlock(&lock);
            rt_log("fs unmount %s (add-on content)", name);
            return 1;
        }
    plat_mutex_unlock(&lock);
    return 0;
}

// ---- files
static size_t lower(const Dlc *d, const char *name) {
    size_t lo = 0, hi = d->nfiles;
    while (lo < hi) {
        size_t m = lo + (hi - lo) / 2;
        if (strcmp(d->files[m].name, name) < 0) lo = m + 1;
        else hi = m;
    }
    return lo;
}

int dlc_handle(uint64_t h) { return h > DLC_HANDLE_BASE && h < DLC_HANDLE_BASE + NH; }

uint32_t dlc_open(uint64_t *out, const char *path, int mode) {
    fs_trace("dlc", path);
    if (!out || mode != FS_OPEN_READ) return FS_R_UNSUPPORTED_OPEN;
    const char *p;
    Dlc *d = mounted(path, &p, NULL);
    if (!d || !p) return FS_R_PATH_NOT_FOUND;
    size_t i = lower(d, p);
    if (i >= d->nfiles || strcmp(d->files[i].name, p)) return FS_R_PATH_NOT_FOUND;
    plat_mutex_lock(&lock);
    for (unsigned j = 1; j < NH; j++)
        if (!handles[j].d) {
            handles[j].d = d;
            handles[j].file = (uint32_t)i;
            *out = DLC_HANDLE_BASE + j;
            plat_mutex_unlock(&lock);
            return 0;
        }
    plat_mutex_unlock(&lock);
    rt_fatal("DLC: file handle table full (%d)", NH);
}

static const DlcFile *handle_file(uint64_t h, Dlc **d) {
    if (!dlc_handle(h)) return NULL;
    plat_mutex_lock_shared(&lock);
    *d = handles[h - DLC_HANDLE_BASE].d;
    uint32_t i = handles[h - DLC_HANDLE_BASE].file;
    plat_mutex_unlock_shared(&lock);
    return *d ? &(*d)->files[i] : NULL;
}

uint32_t dlc_read(uint64_t *out, uint64_t h, int64_t offset, void *buffer, uint64_t size) {
    Dlc *d;
    const DlcFile *f = out && offset >= 0 ? handle_file(h, &d) : NULL;
    if (!f || (uint64_t)offset > f->size || (!buffer && size)) return FS_R_INVALID;
    uint64_t n = size < f->size - (uint64_t)offset ? size : f->size - (uint64_t)offset, done = 0;
    while (done < n) {
        uint32_t chunk = n - done > READ_CHUNK ? READ_CHUNK : (uint32_t)(n - done);
        int64_t r = read_at(d->image, (uint8_t *)buffer + done, chunk, f->offset + (uint64_t)offset + done);
        if (r <= 0) rt_fatal("DLC %d: read failure at %#llx of %s", d->index,
                             (unsigned long long)(f->offset + (uint64_t)offset + done), d->path);
        done += (uint64_t)r;
    }
    diag_read(done);
    *out = done;
    return 0;
}

uint32_t dlc_size(int64_t *out, uint64_t h) {
    Dlc *d;
    const DlcFile *f = out ? handle_file(h, &d) : NULL;
    if (!f) return FS_R_INVALID;
    *out = (int64_t)f->size;
    return 0;
}

void dlc_close(uint64_t h) {
    Dlc *d;
    if (!handle_file(h, &d)) rt_fatal("DLC: close of invalid file handle %#llx", (unsigned long long)h);
    plat_mutex_lock(&lock);
    handles[h - DLC_HANDLE_BASE].d = NULL;
    plat_mutex_unlock(&lock);
}

// 1 when a file lies under folder (a path ending in '/').
static int folder_exists(const Dlc *d, const char *folder) {
    size_t i = lower(d, folder);
    return i < d->nfiles && !strncmp(d->files[i].name, folder, strlen(folder));
}

uint32_t dlc_entry_type(int *out, const char *path) {
    if (!out) return FS_R_INVALID;
    const char *p;
    int root = 0;
    Dlc *d = mounted(path, &p, &root);
    if (!d) return FS_R_PATH_NOT_FOUND;
    if (root) {
        *out = FS_ENTRY_DIRECTORY;
        return 0;
    }
    if (!p) return FS_R_PATH_NOT_FOUND;
    size_t i = lower(d, p);
    if (i < d->nfiles && !strcmp(d->files[i].name, p)) {
        *out = FS_ENTRY_FILE;
        return 0;
    }
    char dir[4096];
    if (snprintf(dir, sizeof dir, "%s/", p) >= (int)sizeof dir) return FS_R_INVALID;
    if (!folder_exists(d, dir)) return FS_R_PATH_NOT_FOUND;
    *out = FS_ENTRY_DIRECTORY;
    return 0;
}

// Direct children of the directory `path` names: add(name, kind, size) for each, in path order. 0 when the path is no
// directory of a mounted DLC.
int dlc_dir_list(const char *path, int (*add)(const char *name, int kind, uint64_t size, void *ctx), void *ctx) {
    const char *p;
    int root = 0;
    Dlc *d = mounted(path, &p, &root);
    if (!d || (!root && !p)) return 0;
    if (root) p = "";
    size_t dn = strlen(p);
    while (dn && p[dn - 1] == '/') dn--;   // "name:/asset/" and "name:/asset" are the same directory
    char last[769];                        // one child name: nn::fs caps names at 768 bytes
    int have = 0, found = !dn;
    for (size_t i = 0; i < d->nfiles; i++) {
        const char *name = d->files[i].name;
        if (dn && (strncmp(name, p, dn) || name[dn] != '/')) continue;   // not under the directory
        found = 1;
        const char *child = name + (dn ? dn + 1 : 0);
        const char *slash = strchr(child, '/');
        size_t cn = slash ? (size_t)(slash - child) : strlen(child);
        if (cn >= sizeof last) continue;
        if (have && !strncmp(last, child, cn) && !last[cn]) continue;    // same child, already listed
        memcpy(last, child, cn);
        last[cn] = 0;
        have = 1;
        if (add && !add(last, slash ? PLAT_FS_DIR : PLAT_FS_FILE, slash ? 0 : d->files[i].size, ctx)) break;
    }
    return found;
}

// ---- overrides
// int nn::aoc::CountAddOnContent()
static void ov_aoc_count(Cpu *c) { ret_x(c, (uint64_t)dlc_count()); }

// int nn::aoc::ListAddOnContent(AddOnContentIndex *out, int offset, int count): the indices written
static void ov_aoc_list(Cpu *c) {
    int32_t *out = arg_p(c, 0);
    int offset = (int)arg_x(c, 1), count = (int)arg_x(c, 2);
    if (offset < 0 || count < 0 || (!out && count)) rt_fatal("aoc: ListAddOnContent range %d+%d", offset, count);
    ret_x(c, (uint64_t)dlc_list(out, offset, count));
}

// nn::Result nn::fs::QueryMountAddOnContentCacheSize(size_t *out, AddOnContentIndex index)
static void ov_query_cache(Cpu *c) { ret_x(c, dlc_cache_size(arg_p(c, 0), (int)arg_x(c, 1))); }

// nn::Result nn::fs::MountAddOnContent(const char *name, AddOnContentIndex index, void *cache, size_t cache_size)
static void ov_mount(Cpu *c) { ret_x(c, dlc_mount(arg_p(c, 0), (int)arg_x(c, 1), arg_p(c, 2), arg_x(c, 3))); }

HOST_OVERRIDE("_ZN2nn3aoc17CountAddOnContentEv", ov_aoc_count);
HOST_OVERRIDE("_ZN2nn3aoc16ListAddOnContentEPiii", ov_aoc_list);
HOST_OVERRIDE("_ZN2nn2fs31QueryMountAddOnContentCacheSizeEPmi", ov_query_cache);
HOST_OVERRIDE("_ZN2nn2fs17MountAddOnContentEPKciPvm", ov_mount);
