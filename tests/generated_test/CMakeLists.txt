include_directories(.)
include_directories(./generated_code)

aux_source_directory(. srcs)

add_executable(generated_code ${srcs})
