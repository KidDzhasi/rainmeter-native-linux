#include "ScriptEnvironment.hpp"
#include "parser/IniLexer.hpp"
#include "MeasureEvaluator.hpp"
#include <iostream>
#include <cstring>

#include <lua.hpp>

ScriptEnvironment::ScriptEnvironment(IniLexer* skin, MeasureEvaluator* measures)
    : skin_(skin), measures_(measures) {
    L_ = luaL_newstate();
    luaL_openlibs(L_);
    bindSkinApi();
    
    std::string resourcesPath = skin_->getCaseInsensitive("Variables", "@").value_or("");
    if (!resourcesPath.empty()) {
        lua_getglobal(L_, "package");
        lua_getfield(L_, -1, "path");
        std::string curPath = lua_tostring(L_, -1);
        lua_pop(L_, 1);
        
        curPath += ";" + resourcesPath + "?.lua";
        curPath += ";" + resourcesPath + "Lua/?.lua";
        
        lua_pushstring(L_, curPath.c_str());
        lua_setfield(L_, -2, "path");
        lua_pop(L_, 1); // pop package table
    }
}

ScriptEnvironment::~ScriptEnvironment() {
    if (L_) lua_close(L_);
}

bool ScriptEnvironment::loadScript(const std::string& path) {
    if (luaL_dofile(L_, path.c_str()) != LUA_OK) {
        std::cerr << "Lua Error loading script " << path << ": " << lua_tostring(L_, -1) << "\n";
        lua_pop(L_, 1);
        return false;
    }
    return true;
}

void ScriptEnvironment::callInitialize() {
    lua_getglobal(L_, "Initialize");
    if (lua_isfunction(L_, -1)) {
        if (lua_pcall(L_, 0, 0, 0) != LUA_OK) {
            std::cerr << "Lua Error in Initialize(): " << lua_tostring(L_, -1) << "\n";
            lua_pop(L_, 1);
        }
    } else {
        lua_pop(L_, 1);
    }
}

std::string ScriptEnvironment::callUpdate() {
    lua_getglobal(L_, "Update");
    if (lua_isfunction(L_, -1)) {
        if (lua_pcall(L_, 0, 1, 0) != LUA_OK) {
            std::cerr << "Lua Error in Update(): " << lua_tostring(L_, -1) << "\n";
            lua_pop(L_, 1);
            return "";
        }
        std::string result;
        if (lua_isstring(L_, -1)) {
            result = lua_tostring(L_, -1);
        } else if (lua_isnumber(L_, -1)) {
            result = std::to_string(lua_tonumber(L_, -1));
        }
        lua_pop(L_, 1);
        return result;
    } else {
        lua_pop(L_, 1);
    }
    return "";
}

void ScriptEnvironment::executeCommand(const std::string& command) {
    if (luaL_dostring(L_, command.c_str()) != LUA_OK) {
        std::cerr << "Lua Error executing command '" << command << "': " << lua_tostring(L_, -1) << "\n";
        lua_pop(L_, 1);
    }
}

// --- Bindings ---

void ScriptEnvironment::bindSkinApi() {
    // We pass `this` pointer as a light userdata to the SKIN methods
    lua_newtable(L_); // SKIN table
    
    lua_pushlightuserdata(L_, this);
    lua_pushcclosure(L_, l_GetVariable, 1);
    lua_setfield(L_, -2, "GetVariable");
    
    lua_pushlightuserdata(L_, this);
    lua_pushcclosure(L_, l_GetMeasure, 1);
    lua_setfield(L_, -2, "GetMeasure");
    
    lua_pushlightuserdata(L_, this);
    lua_pushcclosure(L_, l_GetMeter, 1);
    lua_setfield(L_, -2, "GetMeter");
    
    lua_pushlightuserdata(L_, this);
    lua_pushcclosure(L_, l_Bang, 1);
    lua_setfield(L_, -2, "Bang");
    
    lua_setglobal(L_, "SKIN");
    
    // Create metatable for Measure object
    luaL_newmetatable(L_, "MeasureMeta");
    lua_pushvalue(L_, -1);
    lua_setfield(L_, -2, "__index"); // Meta.__index = Meta
    
    lua_pushlightuserdata(L_, this);
    lua_pushcclosure(L_, l_Measure_GetValue, 1);
    lua_setfield(L_, -2, "GetValue");
    
    lua_pushlightuserdata(L_, this);
    lua_pushcclosure(L_, l_Measure_GetStringValue, 1);
    lua_setfield(L_, -2, "GetStringValue");
    
    lua_pushcfunction(L_, l_Measure_gc);
    lua_setfield(L_, -2, "__gc");
    
    lua_pop(L_, 1); // pop metatable
}

int ScriptEnvironment::l_GetVariable(lua_State* L) {
    ScriptEnvironment* self = (ScriptEnvironment*)lua_touserdata(L, lua_upvalueindex(1));
    const char* varName = luaL_checkstring(L, 2); // param 1 is SKIN table, param 2 is varName
    std::string val = self->skin_->getCaseInsensitive("Variables", varName).value_or("");
    lua_pushstring(L, val.c_str());
    return 1;
}

int ScriptEnvironment::l_GetMeasure(lua_State* L) {
    // Returns a userdata wrapping the measure name
    const char* measureName = luaL_checkstring(L, 2);
    
    // Allocate userdata
    char** udata = (char**)lua_newuserdata(L, sizeof(char*));
    // Allocate string copy
    *udata = strdup(measureName);
    
    // Set metatable
    luaL_getmetatable(L, "MeasureMeta");
    lua_setmetatable(L, -2);
    
    return 1;
}

int ScriptEnvironment::l_GetMeter(lua_State* L) {
    // Stub
    lua_pushnil(L);
    return 1;
}

int ScriptEnvironment::l_Bang(lua_State* L) {
    ScriptEnvironment* self = (ScriptEnvironment*)lua_touserdata(L, lua_upvalueindex(1));
    const char* bangStr = luaL_checkstring(L, 2);
    self->measures_->fireBang(bangStr);
    return 0;
}

// Measure methods
int ScriptEnvironment::l_Measure_GetValue(lua_State* L) {
    ScriptEnvironment* self = (ScriptEnvironment*)lua_touserdata(L, lua_upvalueindex(1));
    char** udata = (char**)luaL_checkudata(L, 1, "MeasureMeta");
    if (udata && *udata) {
        double val = self->measures_->numericValue(*udata);
        lua_pushnumber(L, val);
        return 1;
    }
    lua_pushnumber(L, 0);
    return 1;
}

int ScriptEnvironment::l_Measure_GetStringValue(lua_State* L) {
    ScriptEnvironment* self = (ScriptEnvironment*)lua_touserdata(L, lua_upvalueindex(1));
    char** udata = (char**)luaL_checkudata(L, 1, "MeasureMeta");
    if (udata && *udata) {
        std::string val = self->measures_->value(*udata);
        lua_pushstring(L, val.c_str());
        return 1;
    }
    lua_pushstring(L, "");
    return 1;
}

int ScriptEnvironment::l_Measure_gc(lua_State* L) {
    char** udata = (char**)luaL_checkudata(L, 1, "MeasureMeta");
    if (udata && *udata) {
        free(*udata);
        *udata = nullptr;
    }
    return 0;
}
