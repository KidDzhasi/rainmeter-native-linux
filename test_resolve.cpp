#include "src/parser/IniLexer.hpp"
#include <iostream>
#include <filesystem>
#include <fstream>
namespace fs = std::filesystem;

int main() {
    fs::create_directories("test_dir/AsSeTs");
    std::ofstream("test_dir/AsSeTs/pLaY.PnG") << "test";
    
    // If we pass base="test_dir/assets", it will fail because test_dir/assets doesn't exist
    std::string res1 = IniLexer::resolveCaseInsensitivePath("test_dir/assets", "play.png");
    std::cout << "Wrong Base: " << res1 << " (exists: " << fs::exists(res1) << ")" << std::endl;
    
    // If we pass base="test_dir", rel="assets/play.png", it should work
    std::string res2 = IniLexer::resolveCaseInsensitivePath("test_dir", "assets/play.png");
    std::cout << "Right Base: " << res2 << " (exists: " << fs::exists(res2) << ")" << std::endl;
    
    return 0;
}
