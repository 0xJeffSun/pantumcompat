/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Local interoperability filter: CUPS PS -> outlined PDF -> PCL XL -> XOR A5.
 * macOS' upstream PostScript RIP handles copies, page selection, n-up and layout.
 * No printer connection is made by this program. Rendering must finish before
 * any encoded bytes are released to the CUPS backend.
 */
#include <cups/cups.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef PANTUM_RUNTIME_ROOT
#define PANTUM_RUNTIME_ROOT "/Library/Printers/PantumCompat/Runtime"
#endif
#define GS_PATH PANTUM_RUNTIME_ROOT "/bin/gs"
#define GS_SHARE PANTUM_RUNTIME_ROOT "/share/ghostscript"

static volatile sig_atomic_t cancelled;
static volatile sig_atomic_t renderer_pid = -1;
static void cancel_job(int sig) {
    (void)sig;
    cancelled = 1;
    if (renderer_pid > 0) kill((pid_t)renderer_pid, SIGTERM);
}
static int write_all(int fd, const unsigned char *p, size_t n) {
    while (n) {
        if (cancelled) return -1;
        ssize_t k = write(fd, p, n);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) return -1;
        p += k; n -= (size_t)k;
    }
    return 0;
}
static const char *paper_name(const char *s) {
    if (!s || !*s || !strcasecmp(s, "A4") || strstr(s, "iso_a4")) return "a4";
    if (!strcasecmp(s, "A5") || strstr(s, "iso_a5")) return "a5";
    if (!strcasecmp(s, "Letter") || strstr(s, "na_letter")) return "letter";
    if (!strcasecmp(s, "Legal") || strstr(s, "na_legal")) return "legal";
    return NULL;
}
static int run_renderer(char *const args[], int input) {
    pid_t pid = fork();
    if (pid < 0) return -1;
    if (!pid) {
        signal(SIGTERM, SIG_DFL); signal(SIGINT, SIG_DFL);
        if (input != STDIN_FILENO && dup2(input, STDIN_FILENO) < 0) _exit(126);
        if (dup2(STDERR_FILENO, STDOUT_FILENO) < 0) _exit(126);
        setenv("GS_LIB", GS_SHARE "/Resource/Init:" GS_SHARE "/lib:"
               GS_SHARE "/Resource/Font:" GS_SHARE "/fonts:" GS_SHARE "/iccprofiles", 1);
        setenv("GS_FONTPATH", GS_SHARE "/Resource/Font:" GS_SHARE "/fonts", 1);
        setenv("FONTCONFIG_FILE", PANTUM_RUNTIME_ROOT "/fonts.conf", 1);
        setenv("FONTCONFIG_PATH", PANTUM_RUNTIME_ROOT, 1);
        unsetenv("GS_OPTIONS");
        execv(GS_PATH, args);
        perror("ERROR: Cannot execute Ghostscript"); _exit(126);
    }
    renderer_pid = pid;
    if (cancelled) kill(pid, SIGTERM);
    int status = 0;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno == EINTR) continue;
        renderer_pid = -1; return -1;
    }
    renderer_pid = -1;
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}
int main(int argc, char **argv) {
    int rc = 1, input = STDIN_FILENO, temporary = -1, outlined = -1;
    char path[1024] = "", outline_path[1024] = "";
    char output_arg[1100], outline_arg[1100], paper_arg[64];
    cups_option_t *options = NULL;
    int count = 0;
    unsigned char buf[65536], head[160] = {0}, tail[9];
    struct stat st;
    struct sigaction sa = {0};
    sa.sa_handler = cancel_job;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);
    signal(SIGPIPE, SIG_IGN);
    if (argc != 6 && argc != 7) {
        fprintf(stderr, "ERROR: Usage: filter job-id user title copies options [file]\n");
        return 1;
    }
    fprintf(stderr, "DEBUG: PantumCompat 0.2.2 uid=%u euid=%u renderer=%s\n",
            (unsigned)getuid(), (unsigned)geteuid(), GS_PATH);
    if (access(GS_PATH, X_OK)) {
        int why = errno;
        fprintf(stderr, "ERROR: Cannot access bundled renderer %s: %s (errno=%d uid=%u euid=%u).\n",
                GS_PATH, strerror(why), why, (unsigned)getuid(), (unsigned)geteuid());
        return 1;
    }
    count = cupsParseOptions(argv[5], 0, &options);
    const char *media = cupsGetOption("PageSize", count, options);
    if (!media) media = cupsGetOption("media", count, options);
    const char *paper = paper_name(media);
    if (!paper) {
        fprintf(stderr, "ERROR: Unsupported paper size. Choose A4, A5, Letter or Legal.\n");
        goto done;
    }
    bool duplex = false, tumble = false;
    const char *side = cupsGetOption("sides", count, options);
    const char *dup = cupsGetOption("Duplex", count, options);
    if (side) {
        if (!strcmp(side, "two-sided-long-edge")) duplex = true;
        else if (!strcmp(side, "two-sided-short-edge")) duplex = tumble = true;
        else if (strcmp(side, "one-sided")) {
            fprintf(stderr, "ERROR: Unsupported sides option.\n"); goto done;
        }
    } else if (dup) {
        if (!strcmp(dup, "DuplexNoTumble")) duplex = true;
        else if (!strcmp(dup, "DuplexTumble")) duplex = tumble = true;
        else if (strcmp(dup, "None")) {
            fprintf(stderr, "ERROR: Unsupported Duplex option.\n"); goto done;
        }
    }
    if (argc == 7) {
        input = open(argv[6], O_RDONLY);
        if (input < 0) { perror("ERROR: Cannot open print input"); goto done; }
    }
    temporary = cupsTempFd(path, sizeof(path));
    if (temporary < 0) { perror("ERROR: Cannot create conversion temporary file"); goto done; }
    outlined = cupsTempFd(outline_path, sizeof(outline_path));
    if (outlined < 0) { perror("ERROR: Cannot create outline temporary file"); goto done; }
    fcntl(temporary, F_SETFD, FD_CLOEXEC);
    fcntl(outlined, F_SETFD, FD_CLOEXEC);
    snprintf(output_arg, sizeof(output_arg), "-sOutputFile=%s", path);
    snprintf(outline_arg, sizeof(outline_arg), "-sOutputFile=%s", outline_path);
    snprintf(paper_arg, sizeof(paper_arg), "-sPAPERSIZE=%s", paper);
    /* Convert available glyphs to outlines before PCL generation. Missing or
       substituted input fonts cannot be reconstructed by this step. */
    char *outline_args[] = {"gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
        "-sDEVICE=pdfwrite", "-dNoOutputFonts", "-dNumCopies=1", paper_arg,
        outline_arg, "-", NULL};
    if (run_renderer(outline_args, input) != 0 || cancelled) {
        fprintf(stderr, "ERROR: Font outline conversion failed; no print data released.\n"); goto done;
    }
    if (fstat(outlined, &st) || st.st_size < 8 ||
        pread(outlined, head, 5, 0) != 5 || memcmp(head, "%PDF-", 5)) {
        fprintf(stderr, "ERROR: Invalid intermediate PDF; no print data released.\n"); goto done;
    }
    memset(head, 0, sizeof(head));
    if (lseek(outlined, 0, SEEK_SET) < 0) goto done;
    char *pcl_args[] = {"gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
        "-sDEVICE=pxlmono", "-r600", "-dNumCopies=1", paper_arg,
        duplex ? "-dDuplex=true" : "-dDuplex=false",
        tumble ? "-dTumble=true" : "-dTumble=false", output_arg, "-", NULL};
    if (run_renderer(pcl_args, outlined) != 0 || cancelled) {
        fprintf(stderr, "ERROR: Page conversion failed; no print data released.\n"); goto done;
    }
    if (fstat(temporary, &st) || st.st_size < 32 ||
        pread(temporary, head, sizeof(head)-1, 0) < 1 ||
        pread(temporary, tail, sizeof(tail), st.st_size-9) != 9) {
        fprintf(stderr, "ERROR: Incomplete renderer output; no print data released.\n"); goto done;
    }
    head[sizeof(head)-1] = 0;
    if (memcmp(head, "\033%-12345X", 9) || !strstr((char *)head, "PCLXL") ||
        memcmp(tail, "\033%-12345X", 9)) {
        fprintf(stderr, "ERROR: Unexpected renderer output; no print data released.\n"); goto done;
    }
    if (lseek(temporary, 0, SEEK_SET) < 0) goto done;
    fprintf(stderr, "INFO: P3305DN conversion complete: %lld bytes, 600 dpi.\n", (long long)st.st_size);
    for (;;) {
        ssize_t n = read(temporary, buf, sizeof(buf));
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { perror("ERROR: Cannot read renderer output"); goto done; }
        if (!n) break;
        for (ssize_t k = 0; k < n; ++k) buf[k] ^= 0xA5;
        if (write_all(STDOUT_FILENO, buf, (size_t)n)) {
            if (!cancelled) perror("ERROR: Cannot write to print backend");
            goto done;
        }
    }
    rc = 0;
done:
    if (input != STDIN_FILENO && input >= 0) close(input);
    if (temporary >= 0) close(temporary);
    if (outlined >= 0) close(outlined);
    /* Each temporary file is removed individually by its exact generated path. */
    if (*path) unlink(path);
    if (*outline_path) unlink(outline_path);
    cupsFreeOptions(count, options);
    return cancelled ? 0 : rc;
}
