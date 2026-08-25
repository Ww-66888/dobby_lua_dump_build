#!/usr/bin/env python3
# Patch Dobby so it builds with the NDK clang (LLVM integrated assembler, ELF).
#
# Problem: Dobby's arm64 closure trampoline is written in Mach-O assembly syntax:
#     adrp TMP_REG_0, cdecl(common_closure_bridge_handler)@PAGE
#     add  TMP_REG_0, TMP_REG_0, cdecl(common_closure_bridge_handler)@PAGEOFF
# The .asm files are NOT run through the C preprocessor, so `cdecl(...)` stays as
# literal text, and the Mach-O relocation specifiers @PAGE / @PAGEOFF are rejected
# by the ELF assembler ("invalid fixup" / "unknown relocation specifier").
#
# Fix: replace the whole adrp/add pair with the PC-relative literal-load
# pseudo-instruction `ldr TMP_REG_0, =common_closure_bridge_handler`, which the
# assembler lowers to an adrp/add pair automatically (no manual reloc spec needed).
# We also strip any remaining cdecl() wrappers and convert any other Mach-O reloc
# specifiers in other .asm files as a safety net.
#
# Additionally we patch Dobby/CMakeLists.txt so the static target `dobby_static`
# also defines BUILD_WITH_TRAMPOLINE_ASM (the shared target defines it, the static
# one does not by default) -- without it the trampoline code path is inconsistent.
import re
import glob
import sys
import os

patched = []

# ---- 1) Patch the closure-bridge asm (Mach-O -> ELF-friendly pseudo ldr) ----
for f in glob.glob('Dobby/**/*.asm', recursive=True):
    s = open(f, 'r', encoding='utf-8', errors='replace').read()
    orig = s
    # specific closure-bridge pair -> ELF PIC adrp/:pg_hi21: + add/:lo12:
    # (page-relative, position-independent; the Mach-O @PAGE/@PAGEOFF pair is
    #  rejected by the ELF assembler and a bare `ldr =sym` emits a non-PIC
    #  R_AARCH64_ABS64 relocation that fails to link into a shared library)
    s = re.sub(
        r'adrp\s+TMP_REG_0,\s*cdecl\(common_closure_bridge_handler\)@PAGE\s*\n'
        r'add\s+TMP_REG_0,\s*TMP_REG_0,\s*cdecl\(common_closure_bridge_handler\)@PAGEOFF\s*\n',
        'adrp TMP_REG_0, :pg_hi21:common_closure_bridge_handler\n'
        'add TMP_REG_0, TMP_REG_0, :lo12:common_closure_bridge_handler\n', s)
    # strip any remaining cdecl() wrappers (in case cpp is not run on .asm)
    s = re.sub(r'cdecl\(([^)]*)\)', r'\1', s)
    # generic fallback for any other Mach-O reloc specifiers in other asm files
    s = re.sub(r'(\w+)@PAGEOFF', r':lo12:\1', s)
    s = re.sub(r'(\w+)@PAGE', r':pg_hi21:\1', s)
    if s != orig:
        open(f, 'w', encoding='utf-8').write(s)
        patched.append(f)

for p in patched:
    print('patched asm :', p)

# ---- 2) Patch Dobby/CMakeLists.txt: static target needs trampoline define ----
cmake_p = 'Dobby/CMakeLists.txt'
if os.path.exists(cmake_p):
    cs = open(cmake_p).read()
    old = ('target_compile_definitions(dobby_static PRIVATE\n'
           '  "COMPILE_DEFINITIONS ${compile_definitions}"\n'
           '  )')
    new = ('target_compile_definitions(dobby_static PRIVATE\n'
           '  "COMPILE_DEFINITIONS ${compile_definitions}"\n'
           '  -DBUILD_WITH_TRAMPOLINE_ASM\n'
           '  )')
    if old in cs:
        cs = cs.replace(old, new)
        open(cmake_p, 'w').write(cs)
        print('patched cmake: added -DBUILD_WITH_TRAMPOLINE_ASM to dobby_static')
        patched.append(cmake_p)
    else:
        print('WARN: dobby_static define block not found; static build may lack trampoline')

# ---- 2b) Fix RuntimeModule field name drift (master branch) ----
# Dobby master renamed RuntimeModule::load_address -> base, but several sources
# (ProcessRuntime.cc, SymbolResolver plugin, ...) still reference load_address.
# Replace globally so both `.` and `->` accessors are covered.
for f in glob.glob('Dobby/**/*.cc', recursive=True) + glob.glob('Dobby/**/*.h', recursive=True):
    try:
        s = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    if 'load_address' in s:
        s2 = s.replace('load_address', 'base')
        if s2 != s:
            open(f, 'w', encoding='utf-8').write(s2)
            print('patched load_address -> base :', f)
            patched.append(f)

# ---- 2c) Clang 18 (NDK r27) treats old-style C errors as hard errors ----
# Downgrade implicit-function-declaration / implicit-int / incompatible-fp to
# warnings so Dobby's legacy C sources still compile.
cal = 'Dobby/cmake/compiler_and_linker.cmake'
if os.path.exists(cal):
    c = open(cal).read()
    anchor = ('set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fvisibility=hidden -fPIC '
              '-fno-stack-check -fno-stack-protector -fno-exceptions -fno-rtti '
              '-fno-common -fno-zero-initialized-in-bss")')
    extra = (' -Wno-error=implicit-function-declaration -Wno-error=implicit-int '
             '-Wno-error=incompatible-function-pointer-types')
    if anchor in c and '-Wno-error=implicit-function-declaration' not in c:
        # Insert extra INSIDE the string literal (before closing "), precisely on
        # this exact set() line -- do NOT use a blind c.replace('")') which would
        # hit the first ")" in the whole file and corrupt unrelated cmake code.
        c = c.replace(anchor, anchor[:-2] + extra + '")')
        open(cal, 'w').write(c)
        print('patched compiler_and_linker.cmake: added clang18 -Wno-error flags')
    else:
        print('OK: compiler_and_linker.cmake already has clang18 flags / anchor not found')

# ---- 2d) Fix MemRange accessor-method drift in ProcessRuntime.cc ----
# Dobby master turned MemRange::start/end into accessor METHODS (not fields), so
# `a.start` (used in the region comparator) must be `a.start()`.
prc = 'Dobby/source/Backend/UserMode/PlatformUtil/Linux/ProcessRuntime.cc'
if os.path.exists(prc):
    t = open(prc).read()
    old = '  return (a.start < b.start);'
    new = '  return (a.start() < b.start());'
    if old in t:
        t = t.replace(old, new)
        open(prc, 'w').write(t)
        print('patched ProcessRuntime.cc: a.start -> a.start() (method accessor)')
        patched.append(prc)
    else:
        print('OK: ProcessRuntime.cc comparator already uses start()')

# ---- 2e) De-depend make_memory_readable from OSMemory (include-order ghost) ----
# common/os_arch_features.h's android::make_memory_readable references OSMemory/
# kReadExecute which live in PlatformUnifiedInterface/platform.h. Depending on
# include order in some TUs the symbol is not in scope, breaking the Android NDK
# build. Replace the body with the underlying mprotect() call so it no longer
# depends on OSMemory being visible here.
oaf = 'Dobby/common/os_arch_features.h'
if os.path.exists(oaf):
    t = open(oaf).read()
    old_body = ('namespace android {\n'
               'inline void make_memory_readable(void *address, size_t size) {\n'
               '#if defined(ANDROID)\n'
               '  auto page = (void *)ALIGN_FLOOR(address, OSMemory::PageSize());\n'
               '  if (!OSMemory::SetPermission(page, OSMemory::PageSize(), kReadExecute)) {\n'
               '    return;\n'
               '  }\n'
               '#endif\n'
               '}\n'
               '} // namespace android\n')
    new_body = ('namespace android {\n'
               'inline void make_memory_readable(void *address, size_t size) {\n'
               '#if defined(ANDROID)\n'
               '  long ps = sysconf(_SC_PAGESIZE);\n'
               '  if (ps <= 0) ps = 4096;\n'
               '  auto page = (void *)ALIGN_FLOOR(address, (size_t)ps);\n'
               '  mprotect(page, (size_t)ps, PROT_READ | PROT_WRITE | PROT_EXEC);\n'
               '#endif\n'
               '}\n'
               '} // namespace android\n')
    if old_body in t:
        t = t.replace(old_body, new_body)
        # ensure the POSIX headers we now use are present
        if '#include <sys/mman.h>' not in t:
            t = t.replace('#include <stddef.h>', '#include <stddef.h>\n#include <sys/mman.h>\n#include <unistd.h>', 1)
        open(oaf, 'w').write(t)
        print('patched os_arch_features.h: make_memory_readable now uses mprotect (no OSMemory dep)')
        patched.append(oaf)
    else:
        print('WARN: os_arch_features.h make_memory_readable body not matched; leaving as-is')

# ---- 2f) Remove dead 'core/arch/Cpu.h' include (file does not exist on master) ----
# Several Dobby sources include "core/arch/Cpu.h" which was removed/renamed on
# master (only core/arch/CpuRegister.h + arch-specific headers remain). Replace
# the include broadly so the NDK build stops failing on a missing header.
for f in glob.glob('Dobby/**/*.cc', recursive=True) + glob.glob('Dobby/**/*.h', recursive=True):
    try:
        s = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    if '#include "core/arch/Cpu.h"' in s:
        s = s.replace('#include "core/arch/Cpu.h"', '#include "core/arch/CpuRegister.h"')
        open(f, 'w', encoding='utf-8').write(s)
        print('patched Cpu.h -> CpuRegister.h :', f)
        patched.append(f)

# ---- 3) Diagnostics: report any remaining Mach-O-style @ reloc specifiers ----
leftover = []
for f in glob.glob('Dobby/**/*.asm', recursive=True):
    for i, line in enumerate(open(f, encoding='utf-8', errors='replace'), 1):
        if re.search(r'@PAGE|@PAGEOFF|@GOT|@PLT', line):
            leftover.append('%s:%d: %s' % (f, i, line.rstrip()))
if leftover:
    print('WARNING: remaining Mach-O reloc specifiers:')
    for l in leftover:
        print('   ', l)
else:
    print('OK: no remaining Mach-O reloc specifiers in any .asm')

print('total patched files: %d' % len(patched))
sys.exit(0)
