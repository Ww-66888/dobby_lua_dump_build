cmake_minimum_required(VERSION 3.16)
project(lua_dump C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Dobby is expected to be prebuilt at DOBBY_PREFIX/include and DOBBY_PREFIX/lib
set(DOBBY_PREFIX "${CMAKE_CURRENT_SOURCE_DIR}/Dobby" CACHE PATH "Path to Dobby build")

# Our library
add_library(dump_lua SHARED src/dump_lua.c)
target_include_directories(dump_lua PRIVATE
  ${DOBBY_PREFIX}/include
)
target_link_directories(dump_lua PRIVATE
  ${DOBBY_PREFIX}/lib
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