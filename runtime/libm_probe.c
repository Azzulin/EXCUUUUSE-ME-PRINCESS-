// --probe-libm: the game's own math functions (the SDK's libc, lifted like the rest of the code) against the host's
// libm. Each guest function is called on the guest main thread with arguments in v0/v1 (x0 for the ldexp exponent),
// and its result is compared with the host's within a few ulps. A wrong result here means a lifter bug in a
// floating-point instruction, which reaches every constant the game computes on the CPU (Age of Calamity's exposure
// meter limits looked like exponents where 2^x belonged).
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "cfg.h"
#include "host.h"

typedef enum { F1, F2, D1, D2, FI } Kind;   // float(float), float(float, float), double(double), ..., float(float, int)
typedef struct { const char *name; Kind kind; double a, b; } Case;

static const Case cases[] = {
    {"exp2f", F1, 16, 0}, {"exp2f", F1, 9.84916, 0}, {"exp2f", F1, -2.6, 0}, {"exp2f", F1, 0.5, 0},
    {"exp2f", F1, -6.625, 0}, {"powf", F2, 2, 16}, {"powf", F2, 2, 9.84916}, {"powf", F2, 10, 2.5},
    {"powf", F2, 0.5, 2.2}, {"powf", F2, 3.7, -1.3}, {"expf", F1, 1, 0}, {"expf", F1, -3.25, 0},
    {"logf", F1, 10, 0}, {"logf", F1, 0.125, 0}, {"log10f", F1, 1000, 0}, {"log10f", F1, 0.37, 0},
    {"sqrtf", F1, 2, 0}, {"exp2", D1, 16, 0}, {"exp2", D1, -7.3, 0}, {"pow", D2, 2, 16}, {"pow", D2, 1.7, 3.3},
    {"log", D1, 7.5, 0}, {"sqrt", D1, 3, 0}, {"ldexpf", FI, 1.5, 10}, {"ldexpf", FI, 3, -4},
};

static int failures;

static double host_of(const Case *k) {
    float a = (float)k->a, b = (float)k->b;
    if (!strcmp(k->name, "exp2f")) return exp2f(a);
    if (!strcmp(k->name, "powf")) return powf(a, b);
    if (!strcmp(k->name, "expf")) return expf(a);
    if (!strcmp(k->name, "logf")) return logf(a);
    if (!strcmp(k->name, "log10f")) return log10f(a);
    if (!strcmp(k->name, "sqrtf")) return sqrtf(a);
    if (!strcmp(k->name, "ldexpf")) return ldexpf(a, (int)k->b);
    if (!strcmp(k->name, "exp2")) return exp2(k->a);
    if (!strcmp(k->name, "pow")) return pow(k->a, k->b);
    if (!strcmp(k->name, "log")) return log(k->a);
    if (!strcmp(k->name, "sqrt")) return sqrt(k->a);
    return NAN;
}

static void probe_main(Cpu *c) {
    for (size_t i = 0; i < sizeof cases / sizeof *cases; i++) {
        const Case *k = &cases[i];
        uint64_t fn = ldr_symbol(k->name);
        if (!fn) {
            printf("%-7s not exported by the loaded modules\n", k->name);
            failures++;
            continue;
        }
        memset(c->v, 0, sizeof c->v[0] * 2);
        double got;
        if (k->kind == D1 || k->kind == D2) {
            double a = k->a, b = k->b;
            memcpy(&c->v[0], &a, 8);
            memcpy(&c->v[1], &b, 8);
            rt_call(c, fn, 0);
            memcpy(&got, &c->v[0], 8);
        } else {
            float a = (float)k->a, b = (float)k->b, r;
            memcpy(&c->v[0], &a, 4);
            memcpy(&c->v[1], &b, 4);
            if (k->kind == FI) rt_call(c, fn, 1, (uint64_t)(int64_t)(int)k->b);
            else rt_call(c, fn, 0);
            memcpy(&r, &c->v[0], 4);
            got = r;
        }
        double want = host_of(k);
        double tol = (k->kind == D1 || k->kind == D2) ? 1e-12 : 4e-7;
        int ok = fabs(got - want) <= tol * fmax(1, fabs(want));
        if (!ok) failures++;
        char args[64];
        if (k->kind == F2 || k->kind == D2 || k->kind == FI) snprintf(args, sizeof args, "%g, %g", k->a, k->b);
        else snprintf(args, sizeof args, "%g", k->a);
        printf("%-7s(%s) guest %.9g host %.9g %s\n", k->name, args, got, want, ok ? "ok" : "WRONG");
    }
}

int probe_libm(void) {
    ldr_load(rt_config()->exefs);
    kern_run_on_guest_main(probe_main);
    printf("probe-libm: %s (%d wrong)\n", failures ? "FAILED" : "passed", failures);
    return failures ? 1 : 0;
}
