# CI diag run 29 sha efa457f0

## dobby static lib present?
```
dobby-build/libdobby.a
```

## output/log/error.txt
```
NO libdump.so produced

```

## our build log
```
[ 50%] Building C object CMakeFiles/dump_lua.dir/src/dump_lua.c.o
[100%] Linking CXX shared library lib/dump.so
[100%] Built target dump_lua

```

## dobby build error lines
```

```

## our config log (tail)
```


CMake Deprecation Warning at /usr/local/lib/android/sdk/ndk/27.0.12077973/build/cmake/android-legacy.toolchain.cmake:35 (cmake_minimum_required):
  Compatibility with CMake < 3.10 will be removed from a future version of
  CMake.

  Update the VERSION argument <min> value.  Or, use the <min>...<max> syntax
  to tell CMake that the project requires at least <min> but has been updated
  to work with policies introduced by <max> or earlier.
Call Stack (most recent call first):
  /usr/local/lib/android/sdk/ndk/27.0.12077973/build/cmake/android.toolchain.cmake:55 (include)
  /home/runner/work/dobby_lua_dump_build/dobby_lua_dump_build/build/CMakeFiles/3.31.6/CMakeSystem.cmake:6 (include)
  /home/runner/work/dobby_lua_dump_build/dobby_lua_dump_build/build/CMakeFiles/CMakeScratch/TryCompile-kkH9sQ/CMakeLists.txt:4 (project)


-- Detecting C compiler ABI info - done
-- Check for working C compiler: /usr/local/lib/android/sdk/ndk/27.0.12077973/toolchains/llvm/prebuilt/linux-x86_64/bin/clang - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Configuring done (0.1s)
CMake Error: Error required internal CMake variable not set, cmake may not be built correctly.
Missing variable is:
CMAKE_CXX_CREATE_SHARED_LIBRARY
-- Generating done (0.0s)
CMake Generate step failed.  Build files cannot be regenerated correctly.
```

## dobby config log (tail)
```
-- 	Compiler: 	 Clang
-- 	Processor:	 aarch64
-- 	System:   	 Android
-- ***************************************
-- 
-- CMAKE_C_COMPILER: /usr/local/lib/android/sdk/ndk/27.0.12077973/toolchains/llvm/prebuilt/linux-x86_64/bin/clang
-- CMAKE_CXX_COMPILER: /usr/local/lib/android/sdk/ndk/27.0.12077973/toolchains/llvm/prebuilt/linux-x86_64/bin/clang++
-- CMAKE_C_FLAGS: -g -DANDROID -fdata-sections -ffunction-sections -funwind-tables -fstack-protector-strong -no-canonical-prefixes -D_FORTIFY_SOURCE=2 -Wformat -Werror=format-security -fPIC -fvisibility=hidden -fPIC -fno-stack-check -fno-stack-protector -fno-exceptions -fno-rtti -fno-common -fno-zero-initialized-in-bss -Wno-error=implicit-function-declaration -Wno-error=implicit-int -Wno-error=incompatible-function-pointer-types -fomit-frame-pointer -ffunction-sections -fdata-sections -O3 -fno-rtti -fvisibility=hidden -fvisibility-inlines-hidden
-- CMAKE_CXX_FLAGS: -g -DANDROID -fdata-sections -ffunction-sections -funwind-tables -fstack-protector-strong -no-canonical-prefixes -D_FORTIFY_SOURCE=2 -Wformat -Werror=format-security -fPIC -fvisibility=hidden -fPIC -fno-stack-check -fno-stack-protector -fno-exceptions -fno-rtti -fno-common -fno-zero-initialized-in-bss -Wno-error=implicit-function-declaration -Wno-error=implicit-int -Wno-error=incompatible-function-pointer-types -fomit-frame-pointer -ffunction-sections -fdata-sections -O3 -fno-rtti -fvisibility=hidden -fvisibility-inlines-hidden -g -DANDROID -fdata-sections -ffunction-sections -funwind-tables -fstack-protector-strong -no-canonical-prefixes -D_FORTIFY_SOURCE=2 -Wformat -Werror=format-security  -fPIC
-- CMAKE_SHARED_LINKER_FLAGS: -static-libstdc++ -Wl,--build-id=sha1 -Wl,--no-rosegment -Wl,--no-undefined-version -Wl,--fatal-warnings -Wl,--no-undefined -Qunused-arguments 
-- [Dobby] CMAKE_BUILD_TYPE: Release
-- [Dobby] DOBBY_DEBUG: OFF
-- [Dobby] NearBranch: ON
-- [Dobby] FullFloatingPointRegisterPack: OFF
-- [Dobby] Plugin.SymbolResolver: ON
-- [Dobby] Plugin.ImportTableReplace: OFF
-- [Dobby] Plugin.Android.BionicLinkerUtil: OFF
-- [Dobby] DOBBY_BUILD_EXAMPLE: OFF
-- [Dobby] DOBBY_BUILD_TEST: OFF
-- [Dobby] DOBBY_BUILD_KERNEL_MODE: OFF
-- [Dobby] Private.Obfuscation: OFF
-- [Dobby] Dobby-20260825-5dfc854
-- Configuring done (1.3s)
-- Generating done (0.0s)
-- Build files have been written to: /home/runner/work/dobby_lua_dump_build/dobby_lua_dump_build/dobby-build
```