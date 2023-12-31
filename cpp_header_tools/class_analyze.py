from pathlib import Path
import logging
from pprint import pprint, pformat
import cpp_header_tools.utils.show_info_tools as show
import clang.cindex as cl

from cpp_header_tools.templates_mng import TemplatesMng
from cpp_header_tools.utils.exceptions import GeneratedException
from cpp_header_tools.utils.tools import time_me

logger = logging.getLogger(__name__)


class BuildArgsGetter:
    def get_compile_cmd(self, path, is_header: bool):
        raise NotImplementedError("BuildArgsGetter")


def node_kind(node):
    try:
        kind = node.kind
    except ValueError as e:
        kind = f"unknown kind {node._kind_id}"
    return kind


class CppClassAnalyze:
    """
    generator for one header define
    one header must have only one class with generated macros
    """

    def __init__(self, header_path: str, cpp_path: str, build_args: BuildArgsGetter, templates: TemplatesMng,
                 out_header_dir: str):
        self.header_path = header_path
        self.cpp_path = cpp_path
        self.build_args = build_args
        self.templates = templates
        self.out_dir = out_header_dir
        self.file_name = Path(header_path).stem
        self.index = cl.Index.create()

        self.out_header = None
        self.header_tu = None
        self.header_inc = None

        self.header_uid = str(Path(self.header_path).resolve().as_posix()) \
            .replace("/", "_") \
            .replace(".", "_") \
            .replace(":", "_")
        self.header_mark = f"__CPP_HEADER_TOOLS_"

        self.relations = []

    @time_me()
    def analyze(self):
        """
        build generated code for header define
        :return:
        """
        # init out header
        self.out_header = Path(self.out_dir) / (self.file_name + ".generated.h")
        with open(self.out_header, "w+t") as f:
            f.write(self._pre_gen_macro())

        # load source
        self._load_source()

        # check include
        self._pre_check_includes()

        # check only one GENERATED()
        # TODO

        # load macro infos
        self._analyze_macro_relations()

        # check all macro only be used in target class/struct
        # TODO

        # check all decorated is macro instantiation
        # TODO

        # check decorated target correct
        # TODO

    def _pre_gen_macro(self):
        """
        pre gen all macros for clang to analyze
        :return:
        """
        macros: dict = self.templates.templates
        result = """// pre generated header, just for clang to analyze
#undef CONCAT_IMPL
#undef MACRO_CONCAT
#define CONCAT_IMPL( x, y )  x##y
#define MACRO_CONCAT( x, y ) CONCAT_IMPL( x, y )
"""
        result += f"#undef CH_GENERATED\n"
        for name, info in macros.items():
            result += f"#undef {name}\n"

        result += f"#define CH_GENERATED(id) struct MACRO_CONCAT({self.header_mark}_GENERATED_MARK_,id) {{}};\n"
        for name, info in macros.items():
            pre_defined = f"#define {name}(...) struct MACRO_CONCAT({self.header_mark}_{name}_MARK_,__COUNTER__) {{}};\n"
            result += pre_defined

        return result

    @time_me()
    def _load_source(self):
        """
        load cpp and header translation unit info
        :return:
        """
        # load header
        header_tu = self.index.parse(None, self.build_args.get_compile_cmd(self.header_path, True),
                                     options=cl.TranslationUnit.PARSE_INCOMPLETE | cl.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        self.header_tu = header_tu
        diagnostics = show.get_diagnostics(header_tu)
        if len(diagnostics) != 0:
            logger.warning(f"{pformat(diagnostics)}")
        # load cpp
        cpp_tu = self.index.parse(None, self.build_args.get_compile_cmd(self.cpp_path, False),
                                  options=cl.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        self.cpp_tu = cpp_tu
        diagnostics = show.get_diagnostics(cpp_tu)
        if len(diagnostics) != 0:
            logger.warning(f"{pformat(diagnostics)}")

    @time_me()
    def _pre_check_includes(self):
        """
        xxx.generated.h mast be included at last of the xxx.h
        """
        header_tu = self.header_tu
        includes = [x for x in header_tu.get_includes()]
        if len(includes) <= 0:
            raise GeneratedException(f"{self.file_name}.generated.h must be included by {self.header_path}")
        last = includes[-1]
        if not last.include.name.endswith(f"{self.file_name}.generated.h"):
            raise GeneratedException(f"{self.file_name}.generated.h must be included at last")
        logger.debug(f"pass include check")
        cpp_tu = self.cpp_tu
        # for x in cpp_tu.get_includes():
        #     if Path(x.include.name).resolve() == Path(self.header_path).resolve():
        #         self.header_inc = cl.Cursor.from_location(cpp_tu, x.location)
        #         sp = self.header_inc.spelling
        #         break
        for x in cpp_tu.cursor.get_children():
            if node_kind(x) == cl.CursorKind.INCLUSION_DIRECTIVE:
                self.header_inc = x
                break
        if self.header_inc is None:
            raise GeneratedException(f"{self.file_name} cannot find header include")

    @time_me()
    def _analyze_macro_relations(self):
        # show.traverse(self.cpp_tu.cursor, 0, self.header_path)

        generated_class_cursor: cl.Cursor = None
        custom_id = None
        brothers = []
        decorate_info = []
        decorate_info_display = []

        def pre_check(node):
            src_file: cl.File = node.location.file
            if src_file is None and node.kind == cl.CursorKind.TRANSLATION_UNIT:
                return True
            if src_file is not None and Path(src_file.name).resolve() == Path(self.header_path).resolve():
                return True
            else:
                return False

        valid_type = [cl.CursorKind.STRUCT_DECL, cl.CursorKind.CLASS_DECL, cl.CursorKind.UNION_DECL]
        def get_basic_infos(node: cl.Cursor):
            nonlocal generated_class_cursor
            nonlocal custom_id
            if generated_class_cursor is not None:
                return
            if not pre_check(node):
                return
                # process
            kind = node_kind(node)
            if kind in valid_type and node.spelling.startswith(f"{self.header_mark}_GENERATED_MARK"):
                generated_class_cursor = node.semantic_parent
                custom_id = node.spelling[len(f"{self.header_mark}_GENERATED_MARK_"):]
            # recursive children
            for n in node.get_children():
                child_kind = node_kind(n)
                if child_kind != cl.CursorKind.NAMESPACE and child_kind not in valid_type:
                    continue
                get_basic_infos(n)

        def trans_to_cursor(node: cl.Cursor):
            return cl.Cursor.from_location(self.cpp_tu, node.location)

        get_basic_infos(self.cpp_tu.cursor)
        if generated_class_cursor is None:
            raise GeneratedException("cannot find CH_GENERATED() in one class or struct")

        for node in generated_class_cursor.semantic_parent.get_children():
            if not pre_check(node):
                continue
            kind = node_kind(node)
            if kind == cl.CursorKind.STRUCT_DECL and node.spelling.startswith(self.header_mark):
                brothers.append(node)
            if node == generated_class_cursor:
                brothers.append(node)
        if len(brothers) < 2:
            raise GeneratedException("at least needs CH_CLASS() ")
        if brothers[-1] != generated_class_cursor:
            raise GeneratedException("should not use any CH_ macros after class defined")
        brothers.pop()
        brothers = [trans_to_cursor(x) for x in brothers]

        curr_decorated = []
        # 0 : None, 1 : find next decorated target
        status = 0
        for node in generated_class_cursor.get_children():
            if not pre_check(node):
                continue
            if node.spelling.startswith(f"{self.header_mark}_GENERATED_MARK"):
                continue
            kind = node_kind(node)
            # got one decorated info, save and marked
            if kind == cl.CursorKind.STRUCT_DECL and node.spelling.startswith(self.header_mark):
                curr_decorated.append(node)
                if status == 0:
                    status = 1
                continue
            # decorated info is empty, ignore
            if status == 0:
                continue

            # get decorated target, recorde and clean
            curr_decorated = [trans_to_cursor(x) for x in curr_decorated]
            decorate_info.append({"target": node, "decorated": curr_decorated})
            decorate_info_display.append(
                [(node.kind, node.spelling), [(x.kind, x.spelling) for x in curr_decorated]])
            curr_decorated = []
            status = 0
        if status != 0:
            raise GeneratedException(
                f"some decorated not found target {[pformat(show.get_node_info(x)) for x in curr_decorated]}")
        logger.debug(
            f"\nclass:{pformat((generated_class_cursor.kind, generated_class_cursor.spelling))}\n"
            f"class decorated:\n{pformat([(x.kind, x.spelling) for x in brothers])}\n")
        logger.debug(f"inner decorated:\n{pformat(decorate_info_display)}")
        self.relations.append({"class": generated_class_cursor, "decorated": brothers,
                               "inner_decorated": decorate_info, "custom_id": custom_id})
        pass
