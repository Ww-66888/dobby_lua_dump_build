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
    # specific closure-bridge pair -> pseudo ldr =sym (robust, no reloc specifiers)
    s = re.sub(
        r'adrp\s+TMP_REG_0,\s*cdecl\(common_closure_bridge_handler\)@PAGE\s*\n'
        r'add\s+TMP_REG_0,\s*TMP_REG_0,\s*cdecl\(common_closure_bridge_handler\)@PAGEOFF\s*\n',
        'ldr TMP_REG_0, =common_closure_bridge_handler\n', s)
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

# ---- 2b) Fix RuntimeModule field name mismatch (master branch inconsistency) ----
# Dobby's Linux/ProcessRuntime.cc references module.load_address, but the
# RuntimeModule struct (source/PlatformUtil/ProcessRuntime.h) defines `void *base`.
pr = 'Dobby/source/Backend/UserMode/PlatformUtil/Linux/ProcessRuntime.cc'
if os.path.exists(pr):
    t = open(pr).read()
    if 'module.load_address' in t:
        t = t.replace('module.load_address', 'module.base')
        open(pr, 'w').write(t)
        print('patched ProcessRuntime.cc: load_address -> base')
    else:
        print('OK: ProcessRuntime.cc already uses base (no load_address)')

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
        # Insert extra INSIDE the string (before closing ")"), not after it
        c = c.replace('")', extra + '")', 1)
        open(cal, 'w').write(c)
        print('patched compiler_and_linker.cmake: added clang18 -Wno-error flags')
    else:
        print('OK: compiler_and_linker.cmake already has clang18 flags / anchor not found')

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
