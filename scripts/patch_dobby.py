#!/usr/bin/env python3
# Patch Dobby .asm files so they compile with NDK clang (LLVM integrated assembler)
# 1. Strip cdecl() macro (identity on Linux; .asm files skip the C preprocessor)
# 2. Replace adrp/add @PAGE/@PAGEOFF pair with a PC-relative literal load (avoids
#    LLVM's relocation specifier issues with @PAGE / :pg_hi21:)
import re
import glob
import sys

patched = []
for f in glob.glob('Dobby/**/*.asm', recursive=True):
    s = open(f, 'r', encoding='utf-8', errors='replace').read()
    orig = s
    # Replace the adrp/add pair with a single literal load from the .data pointer
    s = re.sub(
        r'adrp\s+TMP_REG_0,\s*cdecl\(common_closure_bridge_handler\)@PAGE\s*\n',
        'ldr TMP_REG_0, common_closure_bridge_handler_addr\n', s)
    s = re.sub(
        r'add\s+TMP_REG_0,\s*TMP_REG_0,\s*cdecl\(common_closure_bridge_handler\)@PAGEOFF\s*\n',
        '', s)
    # Strip cdecl() macro
    s = re.sub(r'cdecl\(([^)]*)\)', r'\1', s)
    if s != orig:
        open(f, 'w', encoding='utf-8').write(s)
        patched.append(f)

print('patched %d files' % len(patched))
for p in patched:
    print('  ', p)
sys.exit(0)
