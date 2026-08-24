# Dobby Lua Dump — 免 root 真机注入 Lua 明文抽取

## 原理

用 **Dobby inline hook 框架** 在 ARM64 真机上 hook `libxlua.so` 的：
- `luaL_loadbuffer`
- `luaL_loadbufferx`
- `xluaL_loadbuffer`

C# 解密后的明文 Lua 源码在调用这些函数时经过参数，**直接落盘到 `/sdcard/luadump/`**。

## 与 frida-gadget 的区别

- ✅ **无 frida 字符串** — ACE 检测不到 frida 特征
- ✅ **Dobby 是纯 C inline hook** — 轻量、快速、无侵入
- ✅ **不依赖 dex 修改** — 只改 ELF DT_NEEDED，ACE 触发阈值低
- ⚠️ 仍需改包重签（ACE 可能依然检测签名变化）

## 构建

### 方式 A：GitHub Actions（推荐）

1. 创建 GitHub 仓库（如 `dobby_lua_dump_build`）
2. 推送本仓库源码到 GitHub
3. Actions 自动构建 arm64-v8a 的 `libdump.so`
4. 从 Actions 产物下载

### 方式 B：本地 NDK 构建

```bash
cmake -B build \
  -DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-24 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

产物：`build/lib/libdump.so`

## APK 注入

1. 用 `injector.exe` 给原版 APK 的 `lib/arm64-v8a/libmain.so` 添加 `DT_NEEDED libdump.so`
2. 把 `libdump.so` 放入 `lib/arm64-v8a/`
3. 重签 APK
4. 安装到真机
5. 游戏启动后自动 dump Lua → `/sdcard/luadump/`