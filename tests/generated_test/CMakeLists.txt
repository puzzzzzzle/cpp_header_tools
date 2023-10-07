include_directories(.)
include_directories(./generated_code)

aux_source_directory(. srcs)
aux_source_directory(./generated_code generated_srcs )

add_executable(generated_code ${srcs} ${generated_srcs})
