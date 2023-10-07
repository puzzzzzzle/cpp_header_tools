cmake_minimum_required(VERSION 3.0)
project(untitled1)

set(CMAKE_CXX_STANDARD 11)
# 生成 command json
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include_directories(test_utils)
add_subdirectory(generated_test)

