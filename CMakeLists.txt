cmake_minimum_required(VERSION 3.16)
project(lua_dump C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# ---- Fetch Dobby source ----
include(FetchContent)
FetchContent_Declare(
  dobby
  GIT_REPOSITORY  https://github.com/jmpews/Dobby.git
  GIT_TAG         master
  GIT_SHALLOW     TRUE
)
set(DOBBY_BUILD_SHARED OFF CACHE BOOL "")  # build static lib
FetchContent_MakeAvailable(dobby)

# ---- Our library ----
add_library(dump_lua SHARED src/dump_lua.c)
target_include_directories(dump_lua PRIVATE
  ${dobby_SOURCE_DIR}/include
  ${dobby_BINARY_DIR}
)
target_link_libraries(dump_lua PRIVATE
  dobby
  log
  dl
)
set_target_properties(dump_lua PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
  PREFIX ""
  OUTPUT_NAME "dump"
)

# ---- Install rules ----
install(TARGETS dump_lua
  LIBRARY DESTINATION lib/arm64-v8a
)