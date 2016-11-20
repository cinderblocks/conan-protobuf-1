from conans import ConanFile, CMake, tools, ConfigureEnvironment
import os
import shutil


class ProtobufConan(ConanFile):
    name = "Protobuf"
    version = "3.1.0"
    url = "https://github.com/inexor-game/conan-protobuf.git"
    license = "https://github.com/google/protobuf/blob/v{}/LICENSE".format(version)
    requires = "zlib/1.2.8@lasote/stable"
    settings = "os", "compiler", "build_type", "arch"
    exports = "cmake*.cmake"
   # exports = "CMakeLists.txt", "lib*.cmake", "extract_includes.bat.in", "protoc.cmake", "tests.cmake", "change_dylib_names.sh"
    options = {"shared": [True, False]}
    default_options = "shared=False"
    generators = "cmake"
    folder = "protobuf-{}".format(version)

    def config(self):
        self.options["zlib"].shared = self.options.shared

    def source(self):
        tools.download("https://github.com/google/protobuf/"
                       "releases/download/v{0}/protobuf-cpp-{0}.zip".format(self.version),
                       "protobuf.zip")
        tools.unzip("protobuf.zip")
        os.unlink("protobuf.zip")
        cmake_file = "{}/cmake/CMakeLists.txt".format(self.folder)
        tools.replace_in_file(cmake_file, "project(protobuf C CXX)", '''project(protobuf C CXX)
include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup()''')
        tools.replace_in_file(cmake_file, "include(install.cmake)", "# include(install.cmake) # commented by conan: we install manually")

    def build(self):
        args = ["-Dprotobuf_BUILD_TESTS=OFF", "-Dprotobuf_BUILD_EXAMPLES=OFF"]
        args += ["-DBUILD_SHARED_LIBS={}".format('ON' if self.options.shared else 'OFF')]
        args += ["-Dprotobuf_WITH_ZLIB=ON"]
        if self.settings.compiler == "Visual Studio":
            if self.settings.compiler.runtime == "MT" or self.settings.compiler.runtime == "MTd":
                args += ["-Dprotobuf_MSVC_STATIC_RUNTIME=ON"]
            else:
                args += ["-Dprotobuf_MSVC_STATIC_RUNTIME=OFF"]
        cmake = CMake(self.settings)
        self.run('cmake {}/cmake {} {}'.format(self.folder, cmake.command_line, ' '.join(args)))
        self.output.warn("CMAKE OUTPUT: {}".format(cmake.command_line))
        self.run("cmake --build . {}".format(cmake.build_config))

    def package(self):
        # Copy FindProtobuf.cmakes to package
        cmake_files = ["protobuf-config.cmake", "protobuf-config-version.cmake", "protobuf-options.cmake", "protobuf-module.cmake", "protobuf-targets.cmake"]
        for file in cmake_files:
            self.copy(file, dst=".", src="cmake/")
          # Copy the build_type specific file only for the right one:
        self.copy("protobuf-targets-{}.cmake".format("debug" if self.settings.build_type == "Debug" else "release"), dst=".", src="cmake/")

        # Copy Headers to package include folder
        self.copy_headers("*.h", "{}/src".format(self.folder))

        # Copy all proto files:
        self.copy("*.proto", dst="bin", src="{}/src".format(self.folder))

        if self.settings.os == "Windows":
            self.copy("*.lib", dst="lib", src="lib", keep_path=False)
            self.copy("protoc.exe", dst="bin", src="bin", keep_path=False)

            if self.options.shared:
                self.copy("*.dll", dst="bin", src="", keep_path=False)
        else:
            # Copy the libs to lib
            if not self.options.shared:
                self.copy("*.a", "lib", "", keep_path=False)
            else:
                self.copy("*.so*", "lib", "", keep_path=False)
                self.copy("*.9.dylib", "lib", "", keep_path=False)

            # Copy the exe to bin
            # we need some sort of dynlib converter for macosx here, see memshardeds protobuf
            self.copy("protoc", "bin", "bin", keep_path=False)

    def package_info(self):
        basename = "libprotobuf"
        if self.settings.build_type == "Debug":
            basename = "libprotobufd"

        if self.settings.os == "Windows":
            self.cpp_info.libs = [basename]
            if self.options.shared:
                self.cpp_info.defines = ["PROTOBUF_USE_DLLS"]
        elif self.settings.os == "Macos":
            self.cpp_info.libs = [basename + ".a"] if not self.options.shared else [basename + ".9.dylib"]
        else:
            self.cpp_info.libs = [basename + ".a"] if not self.options.shared else [basename + ".so.9"]
