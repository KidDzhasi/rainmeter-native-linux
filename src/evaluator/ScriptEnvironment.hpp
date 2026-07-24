#pragma once

#include <string>
#include <functional>

struct lua_State;
class IniLexer;
class MeasureEvaluator;

class ScriptEnvironment {
public:
    ScriptEnvironment(IniLexer* skin, MeasureEvaluator* measures);
    ~ScriptEnvironment();

    bool loadScript(const std::string& path);
    
    void callInitialize();
    std::string callUpdate();
    void executeCommand(const std::string& command);

private:
    lua_State* L_;
    IniLexer* skin_;
    MeasureEvaluator* measures_;

    // Setup global SKIN object
    void bindSkinApi();

    // C functions mapped to Lua SKIN object
    static int l_GetVariable(lua_State* L);
    static int l_GetMeasure(lua_State* L);
    static int l_GetMeter(lua_State* L);
    static int l_Bang(lua_State* L);

    // Measure object methods
    static int l_Measure_GetValue(lua_State* L);
    static int l_Measure_GetStringValue(lua_State* L);
    static int l_Measure_gc(lua_State* L);
};
