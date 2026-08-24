// ================================================================
// Dobby inline-hook Lua dump module for com.mhxcz.mhxc
// Hooks luaL_loadbuffer / luaL_loadbufferx / xluaL_loadbuffer
// in libxlua.so and dumps plaintext Lua chunks to /sdcard/luadump/
//
// Build: NDK + CMake, arm64-v8a only
//   cmake -DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake \
//         -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 -B build
//   cmake --build build --config Release
// ================================================================

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <pthread.h>
#include <unistd.h>
#include <dlfcn.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <errno.h>
#include <time.h>

#include "dobby.h"

// ---- Logging ----
#include <android/log.h>
#define LOG_TAG "LuaDump"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// ---- Output directory ----
// Primary: /sdcard/luadump/ (widely accessible)
// Fallback: game's external files dir (if sdcard fails)
#define OUT_DIR   "/sdcard/luadump/"
#define OUT_DIR2  "/storage/emulated/0/Android/data/com.mhxcz.mhxc/files/luadump/"

// ---- Dedup hash set ----
#define HASH_SET_SIZE 4096
static uint32_t g_hash_set[HASH_SET_SIZE] = {0};
static int g_file_counter = 0;
static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;

// ---- Original function pointers ----
static int (*orig_xluaL_loadbuffer)(void* L, const char* buff, int size, const char* name) = NULL;
static int (*orig_luaL_loadbuffer)(void* L, const char* buff, size_t size, const char* name) = NULL;
static int (*orig_luaL_loadbufferx)(void* L, const char* buff, size_t size, const char* name, const char* mode) = NULL;

// ================================================================
// Dedup: hash first 256 bytes, skip if seen before
// ================================================================
static bool is_dup(const char* data, size_t size) {
    uint32_t h = 0;
    for (size_t i = 0; i < size && i < 256; i++)
        h = h * 31 + (unsigned char)data[i];
    uint32_t idx = h % HASH_SET_SIZE;
    pthread_mutex_lock(&g_mutex);
    bool dup = (g_hash_set[idx] == h);
    if (!dup) g_hash_set[idx] = h;
    pthread_mutex_unlock(&g_mutex);
    return dup;
}

// ================================================================
// Write chunk to disk
// ================================================================
static void dump_lua_chunk(const char* name, const char* buff, size_t size) {
    if (!buff || size == 0 || size > 8 * 1024 * 1024) return;
    if (is_dup(buff, size)) return;

    // Try both directories
    mkdir(OUT_DIR, 0755);
    mkdir(OUT_DIR2, 0755);

    // Build filename
    char fname[256];
    if (name && name[0]) {
        // Sanitize: replace / \ : with _
        const char* src = name;
        char* dst = fname;
        int n = 0;
        while (*src && n < (int)sizeof(fname) - 20) {
            if (*src == '/' || *src == '\\' || *src == ':')
                *dst++ = '_';
            else
                *dst++ = *src;
            src++;
            n++;
        }
        *dst = '\0';
    } else {
        snprintf(fname, sizeof(fname), "chunk_%d", g_file_counter);
    }

    char path[512];
    int written = 0;

    // Try primary dir
    snprintf(path, sizeof(path), "%s%s_%d.lua", OUT_DIR, fname, g_file_counter);
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd >= 0) {
        write(fd, buff, size);
        close(fd);
        written = 1;
    }

    // Try fallback dir
    if (!written) {
        snprintf(path, sizeof(path), "%s%s_%d.lua", OUT_DIR2, fname, g_file_counter);
        fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd >= 0) {
            write(fd, buff, size);
            close(fd);
            written = 1;
        }
    }

    pthread_mutex_lock(&g_mutex);
    int idx = g_file_counter++;
    pthread_mutex_unlock(&g_mutex);

    if (written) {
        LOGI("[DUMP] SAVED %s (%zu bytes) name=%s", path, size, name ? name : "(null)");
    } else {
        LOGE("[DUMP] FAIL open for %s (errno=%d)", fname, errno);
    }
}

// ================================================================
// Hook replacements
// ================================================================
static int my_xluaL_loadbuffer(void* L, const char* buff, int size, const char* name) {
    if (size > 0) {
        dump_lua_chunk(name, buff, (size_t)size);
    }
    return orig_xluaL_loadbuffer(L, buff, size, name);
}

static int my_luaL_loadbuffer(void* L, const char* buff, size_t size, const char* name) {
    dump_lua_chunk(name, buff, size);
    return orig_luaL_loadbuffer(L, buff, size, name);
}

static int my_luaL_loadbufferx(void* L, const char* buff, size_t size,
                               const char* name, const char* mode) {
    dump_lua_chunk(name, buff, size);
    return orig_luaL_loadbufferx(L, buff, size, name, mode);
}

// ================================================================
// Worker thread: wait for libxlua.so, then hook all three exports
// ================================================================
static void* worker_thread(void* arg) {
    (void)arg;

    // Create output dirs
    mkdir(OUT_DIR, 0755);
    mkdir(OUT_DIR2, 0755);
    LOGI("[LUADUMP] worker started, waiting for libxlua.so ...");

    void* handle = NULL;
    for (int i = 0; i < 180; i++) {  // up to 90 seconds
        handle = dlopen("libxlua.so", RTLD_NOLOAD);
        if (handle) {
            LOGI("[LUADUMP] libxlua.so loaded (try %d)", i);
            break;
        }
        usleep(500000);  // 500ms
    }

    if (!handle) {
        LOGE("[LUADUMP] libxlua.so NOT FOUND after 90s, giving up");
        return NULL;
    }

    // Hook xluaL_loadbuffer (exported by libxlua)
    void* addr = dlsym(handle, "xluaL_loadbuffer");
    if (addr) {
        LOGI("[LUADUMP] xluaL_loadbuffer @ %p", addr);
        DobbyHook(addr, (void*)my_xluaL_loadbuffer, (void**)&orig_xluaL_loadbuffer);
        LOGI("[LUADUMP] -> hooked xluaL_loadbuffer");
    } else {
        LOGE("[LUADUMP] xluaL_loadbuffer not found");
    }

    // Hook luaL_loadbuffer
    addr = dlsym(handle, "luaL_loadbuffer");
    if (addr) {
        LOGI("[LUADUMP] luaL_loadbuffer @ %p", addr);
        DobbyHook(addr, (void*)my_luaL_loadbuffer, (void**)&orig_luaL_loadbuffer);
        LOGI("[LUADUMP] -> hooked luaL_loadbuffer");
    } else {
        LOGI("[LUADUMP] luaL_loadbuffer not found (trying luaL_loadbufferx)");
    }

    // Hook luaL_loadbufferx
    addr = dlsym(handle, "luaL_loadbufferx");
    if (addr) {
        LOGI("[LUADUMP] luaL_loadbufferx @ %p", addr);
        DobbyHook(addr, (void*)my_luaL_loadbufferx, (void**)&orig_luaL_loadbufferx);
        LOGI("[LUADUMP] -> hooked luaL_loadbufferx");
    } else {
        LOGI("[LUADUMP] luaL_loadbufferx not found");
    }

    // Also hook lua_load (lower-level, called by luaL_loadbuffer)
    addr = dlsym(handle, "lua_load");
    if (addr) {
        LOGI("[LUADUMP] lua_load @ %p (will hook via luaL_loadbufferx instead)", addr);
        // lua_load is called internally by luaL_loadbuffer, skip to avoid double-dump
    }

    LOGI("[LUADUMP] all hooks installed");
    return NULL;
}

// ================================================================
// Constructor: auto-started when library is loaded
// ================================================================
__attribute__((constructor)) static void init() {
    LOGI("[LUADUMP] library loaded, spawning worker thread");
    pthread_t tid;
    pthread_create(&tid, NULL, worker_thread, NULL);
    pthread_detach(tid);
}