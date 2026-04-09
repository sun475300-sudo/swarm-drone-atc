"""
Phase 332: WebAssembly Runtime Engine
드론 펌웨어용 WASM 바이트코드 해석기.
스택 기반 가상머신 + 메모리 샌드박스.
"""

import struct
import numpy as np
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Dict, Optional, Callable, Any


class WasmOpcode(IntEnum):
    NOP = 0x00
    CONST_I32 = 0x41
    CONST_F64 = 0x44
    ADD_I32 = 0x6A
    SUB_I32 = 0x6B
    MUL_I32 = 0x6C
    DIV_I32 = 0x6D
    ADD_F64 = 0xA0
    SUB_F64 = 0xA1
    MUL_F64 = 0xA2
    DIV_F64 = 0xA3
    LOCAL_GET = 0x20
    LOCAL_SET = 0x21
    LOAD_I32 = 0x28
    STORE_I32 = 0x36
    CALL = 0x10
    IF = 0x04
    ELSE = 0x05
    END = 0x0B
    RETURN = 0x0F
    LT_I32 = 0x48
    GT_I32 = 0x4A
    EQ_I32 = 0x46
    BR = 0x0C
    DROP = 0x1A


@dataclass
class WasmFunction:
    name: str
    param_count: int
    local_count: int
    bytecode: List[int]
    is_export: bool = True


@dataclass
class WasmModule:
    name: str
    functions: Dict[str, WasmFunction] = field(default_factory=dict)
    memory_pages: int = 1  # 64KB per page
    globals: Dict[str, Any] = field(default_factory=dict)


class WasmMemory:
    """Linear memory with bounds checking."""
    PAGE_SIZE = 65536  # 64KB

    def __init__(self, initial_pages: int = 1, max_pages: int = 16):
        self.data = bytearray(initial_pages * self.PAGE_SIZE)
        self.max_pages = max_pages

    def load_i32(self, offset: int) -> int:
        if offset + 4 > len(self.data):
            raise RuntimeError(f"Memory access out of bounds: {offset}")
        return struct.unpack_from('<i', self.data, offset)[0]

    def store_i32(self, offset: int, value: int) -> None:
        if offset + 4 > len(self.data):
            raise RuntimeError(f"Memory access out of bounds: {offset}")
        struct.pack_into('<i', self.data, offset, value)

    def load_f64(self, offset: int) -> float:
        if offset + 8 > len(self.data):
            raise RuntimeError(f"Memory access out of bounds: {offset}")
        return struct.unpack_from('<d', self.data, offset)[0]

    def store_f64(self, offset: int, value: float) -> None:
        if offset + 8 > len(self.data):
            raise RuntimeError(f"Memory access out of bounds: {offset}")
        struct.pack_into('<d', self.data, offset, value)

    def grow(self, pages: int) -> int:
        old_pages = len(self.data) // self.PAGE_SIZE
        new_pages = old_pages + pages
        if new_pages > self.max_pages:
            return -1
        self.data.extend(bytearray(pages * self.PAGE_SIZE))
        return old_pages


class WasmVM:
    """Stack-based WebAssembly virtual machine."""

    MAX_STACK = 1024
    MAX_CALL_DEPTH = 64

    def __init__(self):
        self.stack: List[Any] = []
        self.call_stack: List[Dict] = []
        self.memory = WasmMemory()
        self.modules: Dict[str, WasmModule] = {}
        self.host_functions: Dict[str, Callable] = {}
        self.step_count = 0

    def load_module(self, module: WasmModule) -> None:
        self.modules[module.name] = module
        self.memory = WasmMemory(module.memory_pages)

    def register_host_function(self, name: str, func: Callable) -> None:
        self.host_functions[name] = func

    def _push(self, value: Any) -> None:
        if len(self.stack) >= self.MAX_STACK:
            raise RuntimeError("Stack overflow")
        self.stack.append(value)

    def _pop(self) -> Any:
        if not self.stack:
            raise RuntimeError("Stack underflow")
        return self.stack.pop()

    def execute(self, module_name: str, func_name: str,
                args: Optional[List[Any]] = None) -> Any:
        module = self.modules.get(module_name)
        if not module:
            raise RuntimeError(f"Module not found: {module_name}")

        func = module.functions.get(func_name)
        if not func:
            raise RuntimeError(f"Function not found: {func_name}")

        locals_arr = list(args or [])
        locals_arr.extend([0] * func.local_count)

        self.call_stack.append({
            "module": module_name, "function": func_name,
            "locals": locals_arr, "pc": 0,
            "stack_base": len(self.stack)
        })

        result = self._run(func.bytecode, locals_arr)
        if self.call_stack:
            self.call_stack.pop()
        return result

    def _run(self, bytecode: List[int], locals_arr: List[Any]) -> Any:
        pc = 0
        while pc < len(bytecode):
            op = bytecode[pc]
            pc += 1
            self.step_count += 1

            if op == WasmOpcode.NOP:
                pass

            elif op == WasmOpcode.CONST_I32:
                val = bytecode[pc] if pc < len(bytecode) else 0
                pc += 1
                self._push(val)

            elif op == WasmOpcode.CONST_F64:
                val = float(bytecode[pc]) if pc < len(bytecode) else 0.0
                pc += 1
                self._push(val)

            elif op == WasmOpcode.ADD_I32:
                b, a = self._pop(), self._pop()
                self._push(int(a) + int(b))

            elif op == WasmOpcode.SUB_I32:
                b, a = self._pop(), self._pop()
                self._push(int(a) - int(b))

            elif op == WasmOpcode.MUL_I32:
                b, a = self._pop(), self._pop()
                self._push(int(a) * int(b))

            elif op == WasmOpcode.DIV_I32:
                b, a = self._pop(), self._pop()
                self._push(int(a) // int(b) if b != 0 else 0)

            elif op == WasmOpcode.ADD_F64:
                b, a = self._pop(), self._pop()
                self._push(float(a) + float(b))

            elif op == WasmOpcode.SUB_F64:
                b, a = self._pop(), self._pop()
                self._push(float(a) - float(b))

            elif op == WasmOpcode.MUL_F64:
                b, a = self._pop(), self._pop()
                self._push(float(a) * float(b))

            elif op == WasmOpcode.DIV_F64:
                b, a = self._pop(), self._pop()
                self._push(float(a) / float(b) if b != 0 else 0.0)

            elif op == WasmOpcode.LOCAL_GET:
                idx = bytecode[pc]; pc += 1
                self._push(locals_arr[idx] if idx < len(locals_arr) else 0)

            elif op == WasmOpcode.LOCAL_SET:
                idx = bytecode[pc]; pc += 1
                val = self._pop()
                if idx < len(locals_arr):
                    locals_arr[idx] = val

            elif op == WasmOpcode.LOAD_I32:
                offset = self._pop()
                self._push(self.memory.load_i32(int(offset)))

            elif op == WasmOpcode.STORE_I32:
                val = self._pop()
                offset = self._pop()
                self.memory.store_i32(int(offset), int(val))

            elif op == WasmOpcode.LT_I32:
                b, a = self._pop(), self._pop()
                self._push(1 if int(a) < int(b) else 0)

            elif op == WasmOpcode.GT_I32:
                b, a = self._pop(), self._pop()
                self._push(1 if int(a) > int(b) else 0)

            elif op == WasmOpcode.EQ_I32:
                b, a = self._pop(), self._pop()
                self._push(1 if a == b else 0)

            elif op == WasmOpcode.DROP:
                self._pop()

            elif op == WasmOpcode.CALL:
                func_idx = bytecode[pc]; pc += 1
                # Simplified: call host function by index
                host_names = list(self.host_functions.keys())
                if func_idx < len(host_names):
                    fname = host_names[func_idx]
                    result = self.host_functions[fname]()
                    if result is not None:
                        self._push(result)

            elif op == WasmOpcode.RETURN:
                return self._pop() if self.stack else None

            elif op == WasmOpcode.END:
                break

        return self._pop() if self.stack else None

    def summary(self) -> Dict:
        return {
            "modules": len(self.modules),
            "host_functions": len(self.host_functions),
            "memory_bytes": len(self.memory.data),
            "step_count": self.step_count,
            "stack_depth": len(self.stack),
        }


class DroneFirmwareCompiler:
    """Compiles simple drone commands to WASM bytecode."""

    def compile_altitude_hold(self, target_alt: int, kp: int = 1) -> WasmFunction:
        bytecode = [
            WasmOpcode.LOCAL_GET, 0,          # current_alt
            WasmOpcode.CONST_I32, target_alt,  # target
            WasmOpcode.SUB_I32,                # error = current - target
            WasmOpcode.CONST_I32, kp,          # Kp
            WasmOpcode.MUL_I32,                # correction = error * Kp
            WasmOpcode.RETURN,
        ]
        return WasmFunction("altitude_hold", param_count=1, local_count=0,
                            bytecode=bytecode)

    def compile_waypoint_distance(self) -> WasmFunction:
        bytecode = [
            WasmOpcode.LOCAL_GET, 0,  # dx
            WasmOpcode.LOCAL_GET, 0,  # dx again
            WasmOpcode.MUL_I32,       # dx*dx
            WasmOpcode.LOCAL_GET, 1,  # dy
            WasmOpcode.LOCAL_GET, 1,  # dy again
            WasmOpcode.MUL_I32,       # dy*dy
            WasmOpcode.ADD_I32,       # dx*dx + dy*dy
            WasmOpcode.RETURN,
        ]
        return WasmFunction("waypoint_distance_sq", param_count=2, local_count=0,
                            bytecode=bytecode)

    def compile_geofence_check(self, max_range: int) -> WasmFunction:
        bytecode = [
            WasmOpcode.LOCAL_GET, 0,        # distance
            WasmOpcode.CONST_I32, max_range, # max
            WasmOpcode.LT_I32,              # distance < max?
            WasmOpcode.RETURN,
        ]
        return WasmFunction("geofence_check", param_count=1, local_count=0,
                            bytecode=bytecode)


if __name__ == "__main__":
    vm = WasmVM()
    compiler = DroneFirmwareCompiler()

    module = WasmModule("drone_fw")
    module.functions["altitude_hold"] = compiler.compile_altitude_hold(50)
    module.functions["waypoint_dist"] = compiler.compile_waypoint_distance()
    module.functions["geofence"] = compiler.compile_geofence_check(1000)
    vm.load_module(module)

    correction = vm.execute("drone_fw", "altitude_hold", [45])
    print(f"Altitude correction: {correction}")

    dist_sq = vm.execute("drone_fw", "waypoint_dist", [30, 40])
    print(f"Waypoint distance²: {dist_sq}")

    in_fence = vm.execute("drone_fw", "geofence", [500])
    print(f"In geofence: {in_fence}")

    print(f"VM Summary: {vm.summary()}")
