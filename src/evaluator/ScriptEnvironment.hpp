#pragma once

#include <string>
#include <functional>

struct lua_State;
class IniLexer;
class MeasureEvaluator;

class ScriptEnvironment {
public:
    ScriptEnvironment(IniLexer* skin, MeasureEvaluator* measures, const std::string& sectionName = "");
    ~ScriptEnvironment();

    bool loadScript(const std::string& path);
    
    void callInitialize();
    std::string callUpdate();
    void executeCommand(const std::string& command);

private:
    lua_State* L_;
    IniLexer* skin_;
    MeasureEvaluator* measures_;
    std::string sectionName_;

    // Setup global SKIN object and SELF object
    void bindSkinApi();

    // C functions mapped to Lua SKIN object
    static int l_GetVariable(lua_State* L);
    static int l_SetVariable(lua_State* L);
    static int l_GetMeasure(lua_State* L);
    static int l_GetMeter(lua_State* L);
    static int l_Bang(lua_State* L);
    static int l_ParseFormula(lua_State* L);

    // C functions mapped to Lua SELF object
    static int l_Self_GetOption(lua_State* L);
    static int l_Self_GetNumberOption(lua_State* L);
    static int l_Self_GetName(lua_State* L);

    // Measure object methods
    static int l_Measure_GetValue(lua_State* L);
    static int l_Measure_GetStringValue(lua_State* L);
    static int l_Measure_gc(lua_State* L);
};
