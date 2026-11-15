// Adapted from MacNativeGames games/aoc/runtime/host/hle_movie.c @ 3ac015c3 (MIT, Copyright (c) 2026 MacNativeGames
// contributors): ogg_crc, ogg_page, md_vorbis_open, md_vorbis.
// Vorbis for ov_movie.c (the sound track of a WebM movie) with stb_vorbis (runtime/third_party/stb_vorbis, MIT or public
// domain), built into this file with its push-data API only.
// The game's demuxer (movie::Extractor) hands over raw Vorbis packets, the content of WebM blocks. stb_vorbis reads Ogg
// pages, so every packet goes in as one page of its own: at open the identification header, a comment header made up
// here (stb_vorbis only checks its type) and the setup header; then one page per audio packet. The page checksum is
// filled in because stb_vorbis verifies it when it resynchronises after an error.
// One decoder is used by one thread at a time (ov_movie.c: the decoder's worker, or a guest thread with the worker
// quiesced).
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "movie.h"

#define STB_VORBIS_NO_STDIO
#define STB_VORBIS_NO_PULLDATA_API
#define STB_VORBIS_NO_INTEGER_CONVERSION
#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Weverything"
#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wall"
#pragma GCC diagnostic ignored "-Wextra"
#endif
#include "third_party/stb_vorbis/stb_vorbis.c"
#if defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
#undef L
#undef C
#undef R

enum { PACKET_MAX = 255 * 255 - 1, PAGE_MAX = 27 + 255 + PACKET_MAX };   // one page: 255 segments of up to 255 bytes

struct MovieVorbis {
    stb_vorbis *vb;
    int channels, rate, max_frames;
    uint32_t seq;                 // Ogg page sequence number
    int64_t granule;              // samples decoded so far
    uint8_t page[PAGE_MAX];
};

static uint32_t ogg_crc(const uint8_t *p, size_t n) {
    static uint32_t t[256];
    static int ready;
    if (!ready) {   // idempotent: two threads building it write the same values
        for (uint32_t i = 0; i < 256; i++) {
            uint32_t r = i << 24;
            for (int k = 0; k < 8; k++) r = r & 0x80000000u ? r << 1 ^ 0x04c11db7u : r << 1;
            t[i] = r;
        }
        ready = 1;
    }
    uint32_t c = 0;
    for (size_t i = 0; i < n; i++) c = c << 8 ^ t[(c >> 24 ^ p[i]) & 0xff];
    return c;
}

// One packet as an Ogg page at out (PAGE_MAX bytes): returns its length. n <= PACKET_MAX.
static size_t ogg_page(MovieVorbis *v, uint8_t *out, const uint8_t *pkt, int n, int first) {
    int seg = n / 255 + 1;
    memcpy(out, "OggS", 4);
    out[4] = 0;
    out[5] = first ? 2 : 0;
    memcpy(out + 6, &v->granule, 8);
    uint32_t serial = 0x41564f4du;
    memcpy(out + 14, &serial, 4);
    uint32_t seq = v->seq++;
    memcpy(out + 18, &seq, 4);
    memset(out + 22, 0, 4);
    out[26] = (uint8_t)seg;
    for (int i = 0; i < seg - 1; i++) out[27 + i] = 255;
    out[27 + seg - 1] = (uint8_t)(n % 255);
    memcpy(out + 27 + seg, pkt, (size_t)n);
    size_t len = 27 + (size_t)seg + (size_t)n;
    uint32_t crc = ogg_crc(out, len);
    memcpy(out + 22, &crc, 4);
    return len;
}

MovieVorbis *movie_vorbis_open(const uint8_t *id, int id_n, const uint8_t *setup, int setup_n, int *error) {
    static const uint8_t comment[] = {3, 'v', 'o', 'r', 'b', 'i', 's', 0, 0, 0, 0, 0, 0, 0, 0, 1};
    *error = 0;
    if (!id || !setup || id_n <= 0 || setup_n <= 0 || id_n > PACKET_MAX || setup_n > PACKET_MAX) {
        *error = -1;
        return NULL;
    }
    MovieVorbis *v = calloc(1, sizeof *v);
    uint8_t *buf = malloc(3 * (size_t)PAGE_MAX);
    if (!v || !buf) {
        free(v);
        free(buf);
        *error = -2;
        return NULL;
    }
    size_t n = ogg_page(v, buf, id, id_n, 1);
    n += ogg_page(v, buf + n, comment, (int)sizeof comment, 0);
    n += ogg_page(v, buf + n, setup, setup_n, 0);
    int used = 0;
    v->vb = stb_vorbis_open_pushdata(buf, (int)n, &used, error, NULL);
    free(buf);
    if (!v->vb) {
        free(v);
        return NULL;
    }
    stb_vorbis_info in = stb_vorbis_get_info(v->vb);
    v->channels = in.channels;
    v->rate = (int)in.sample_rate;
    v->max_frames = in.max_frame_size;
    return v;
}

void movie_vorbis_close(MovieVorbis *v) {
    if (!v) return;
    stb_vorbis_close(v->vb);
    free(v);
}

int movie_vorbis_channels(const MovieVorbis *v) { return v->channels; }
int movie_vorbis_rate(const MovieVorbis *v) { return v->rate; }
int movie_vorbis_max_frames(const MovieVorbis *v) { return v->max_frames; }

// After a seek: the next packet starts a new run (it only primes the overlap, as the first packet of a stream does).
void movie_vorbis_flush(MovieVorbis *v) { stb_vorbis_flush_pushdata(v->vb); }

// One packet to interleaved PCM16 at dst (room for cap sample frames). Returns the sample frames written: 0 for the
// packet that primes the overlap, -1 for a packet stb_vorbis rejects or one that does not fit.
int movie_vorbis_decode(MovieVorbis *v, const uint8_t *pkt, int n, int16_t *dst, int cap) {
    if (n <= 0 || n > PACKET_MAX) return -1;
    size_t len = ogg_page(v, v->page, pkt, n, 0);
    int ch = 0, frames = 0;
    float **pcm = NULL;
    int used = stb_vorbis_decode_frame_pushdata(v->vb, v->page, (int)len, &ch, &pcm, &frames);
    if (!used || stb_vorbis_get_error(v->vb)) return -1;
    if (frames <= 0 || ch <= 0 || !pcm) return 0;
    if (frames > cap || ch != v->channels) return -1;
    v->granule += frames;
    for (int i = 0; i < frames; i++)
        for (int c = 0; c < ch; c++) {
            float s = pcm[c][i] * 32767.0f;
            dst[i * ch + c] = (int16_t)(s > 32767.0f ? 32767 : s < -32768.0f ? -32768 : (int)s);
        }
    return frames;
}
