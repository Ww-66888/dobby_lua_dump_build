cmake_minimum_required(VERSION 3.16)
project(lua_dump C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Dobby is cloned by workflow into ./Dobby
add_subdirectory(${CMAKE_SOURCE_DIR}/Dobby EXCLUDE_FROM_ALL)

# ---- Our library ----
add_library(dump_lua SHARED src/dump_lua.c)
target_include_directories(dump_lua PRIVATE
  ${CMAKE_SOURCE_DIR}/Dobby/include
  ${CMAKE_BINARY_DIR}/Dobby  # for config.h
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

install(TARGETS dump_lua
  LIBRARY DESTINATION lib/arm64-v8a
)