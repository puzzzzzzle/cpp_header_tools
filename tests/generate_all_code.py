import os
from pathlib import Path
from cpp_header_tools.utils.logger_init import init_logger
from cpp_header_tools.generator_builder import CompileDBBuilder


def main():
    proj_path = str(Path(".").absolute().resolve())
    cmake_path = Path(f"{proj_path}/cmake-build-debug/")
    builder = CompileDBBuilder(str(cmake_path))
    builder.build_one_target(f"{proj_path}/generated_test/book_actor.h",
                             f"{proj_path}/generated_test/book_actor.cpp",
                             f"{proj_path}/generated_test/generated_code/")
    builder.write_all()

    pass


if __name__ == '__main__':
    init_logger("./log/")
    # win_main()
    main()
