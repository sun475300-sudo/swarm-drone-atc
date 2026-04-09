/// Phase 342: Rust WASM Executor
/// Stack-based WebAssembly bytecode interpreter.
/// Memory-safe with zero-cost abstractions.

use std::collections::HashMap;

// ── Opcodes ──────────────────────────────────────────────────────
#[derive(Debug, Clone, Copy, PartialEq)]
#[repr(u8)]
enum WasmOp {
    Nop = 0x00,
    ConstI32 = 0x41,
    ConstF64 = 0x44,
    AddI32 = 0x6A,
    SubI32 = 0x6B,
    MulI32 = 0x6C,
    DivI32 = 0x6D,
    AddF64 = 0xA0,
    SubF64 = 0xA1,
    MulF64 = 0xA2,
    LocalGet = 0x20,
    LocalSet = 0x21,
    LtI32 = 0x48,
    GtI32 = 0x4A,
    EqI32 = 0x46,
    Return = 0x0F,
    End = 0x0B,
    Drop = 0x1A,
}

// ── Value ────────────────────────────────────────────────────────
#[derive(Debug, Clone, Copy)]
enum WasmValue {
    I32(i32),
    F64(f64),
}

impl WasmValue {
    fn as_i32(&self) -> i32 {
        match self {
            WasmValue::I32(v) => *v,
            WasmValue::F64(v) => *v as i32,
        }
    }
    fn as_f64(&self) -> f64 {
        match self {
            WasmValue::F64(v) => *v,
            WasmValue::I32(v) => *v as f64,
        }
    }
}

// ── Function ─────────────────────────────────────────────────────
#[derive(Debug, Clone)]
struct WasmFunction {
    name: String,
    param_count: usize,
    local_count: usize,
    bytecode: Vec<u8>,
}

// ── Linear Memory ────────────────────────────────────────────────
struct LinearMemory {
    data: Vec<u8>,
    max_pages: usize,
}

impl LinearMemory {
    const PAGE_SIZE: usize = 65536;

    fn new(initial_pages: usize, max_pages: usize) -> Self {
        Self {
            data: vec![0u8; initial_pages * Self::PAGE_SIZE],
            max_pages,
        }
    }

    fn load_i32(&self, offset: usize) -> Result<i32, String> {
        if offset + 4 > self.data.len() {
            return Err(format!("OOB read at {}", offset));
        }
        Ok(i32::from_le_bytes([
            self.data[offset], self.data[offset + 1],
            self.data[offset + 2], self.data[offset + 3],
        ]))
    }

    fn store_i32(&mut self, offset: usize, value: i32) -> Result<(), String> {
        if offset + 4 > self.data.len() {
            return Err(format!("OOB write at {}", offset));
        }
        let bytes = value.to_le_bytes();
        self.data[offset..offset + 4].copy_from_slice(&bytes);
        Ok(())
    }

    fn grow(&mut self, pages: usize) -> i32 {
        let old = self.data.len() / Self::PAGE_SIZE;
        if old + pages > self.max_pages {
            return -1;
        }
        self.data.resize((old + pages) * Self::PAGE_SIZE, 0);
        old as i32
    }
}

// ── Module ───────────────────────────────────────────────────────
struct WasmModule {
    name: String,
    functions: HashMap<String, WasmFunction>,
}

// ── VM ───────────────────────────────────────────────────────────
struct WasmVM {
    stack: Vec<WasmValue>,
    memory: LinearMemory,
    modules: HashMap<String, WasmModule>,
    step_count: u64,
}

impl WasmVM {
    const MAX_STACK: usize = 1024;

    fn new() -> Self {
        Self {
            stack: Vec::with_capacity(64),
            memory: LinearMemory::new(1, 16),
            modules: HashMap::new(),
            step_count: 0,
        }
    }

    fn load_module(&mut self, module: WasmModule) {
        self.modules.insert(module.name.clone(), module);
    }

    fn execute(&mut self, module: &str, func: &str, args: &[WasmValue]) -> Result<Option<WasmValue>, String> {
        let bytecode = {
            let m = self.modules.get(module).ok_or("Module not found")?;
            let f = m.functions.get(func).ok_or("Function not found")?;
            f.bytecode.clone()
        };

        let mut locals: Vec<WasmValue> = args.to_vec();
        self.run(&bytecode, &mut locals)
    }

    fn run(&mut self, bytecode: &[u8], locals: &mut Vec<WasmValue>) -> Result<Option<WasmValue>, String> {
        let mut pc = 0usize;
        while pc < bytecode.len() {
            let op = bytecode[pc];
            pc += 1;
            self.step_count += 1;

            match op {
                0x00 => {} // Nop
                0x41 => { // ConstI32
                    let val = bytecode.get(pc).copied().unwrap_or(0) as i32;
                    pc += 1;
                    self.push(WasmValue::I32(val))?;
                }
                0x44 => { // ConstF64
                    let val = bytecode.get(pc).copied().unwrap_or(0) as f64;
                    pc += 1;
                    self.push(WasmValue::F64(val))?;
                }
                0x6A => { // AddI32
                    let b = self.pop()?.as_i32();
                    let a = self.pop()?.as_i32();
                    self.push(WasmValue::I32(a.wrapping_add(b)))?;
                }
                0x6B => { // SubI32
                    let b = self.pop()?.as_i32();
                    let a = self.pop()?.as_i32();
                    self.push(WasmValue::I32(a.wrapping_sub(b)))?;
                }
                0x6C => { // MulI32
                    let b = self.pop()?.as_i32();
                    let a = self.pop()?.as_i32();
                    self.push(WasmValue::I32(a.wrapping_mul(b)))?;
                }
                0x6D => { // DivI32
                    let b = self.pop()?.as_i32();
                    let a = self.pop()?.as_i32();
                    self.push(WasmValue::I32(if b != 0 { a / b } else { 0 }))?;
                }
                0xA0 => { // AddF64
                    let b = self.pop()?.as_f64();
                    let a = self.pop()?.as_f64();
                    self.push(WasmValue::F64(a + b))?;
                }
                0xA1 => { // SubF64
                    let b = self.pop()?.as_f64();
                    let a = self.pop()?.as_f64();
                    self.push(WasmValue::F64(a - b))?;
                }
                0xA2 => { // MulF64
                    let b = self.pop()?.as_f64();
                    let a = self.pop()?.as_f64();
                    self.push(WasmValue::F64(a * b))?;
                }
                0x20 => { // LocalGet
                    let idx = bytecode.get(pc).copied().unwrap_or(0) as usize;
                    pc += 1;
                    let val = locals.get(idx).copied().unwrap_or(WasmValue::I32(0));
                    self.push(val)?;
                }
                0x21 => { // LocalSet
                    let idx = bytecode.get(pc).copied().unwrap_or(0) as usize;
                    pc += 1;
                    let val = self.pop()?;
                    if idx < locals.len() { locals[idx] = val; }
                }
                0x48 => { // LtI32
                    let b = self.pop()?.as_i32();
                    let a = self.pop()?.as_i32();
                    self.push(WasmValue::I32(if a < b { 1 } else { 0 }))?;
                }
                0x4A => { // GtI32
                    let b = self.pop()?.as_i32();
                    let a = self.pop()?.as_i32();
                    self.push(WasmValue::I32(if a > b { 1 } else { 0 }))?;
                }
                0x46 => { // EqI32
                    let b = self.pop()?.as_i32();
                    let a = self.pop()?.as_i32();
                    self.push(WasmValue::I32(if a == b { 1 } else { 0 }))?;
                }
                0x1A => { self.pop()?; } // Drop
                0x0F => return Ok(self.stack.pop()), // Return
                0x0B => break, // End
                _ => return Err(format!("Unknown opcode: 0x{:02X}", op)),
            }
        }
        Ok(self.stack.pop())
    }

    fn push(&mut self, val: WasmValue) -> Result<(), String> {
        if self.stack.len() >= Self::MAX_STACK {
            return Err("Stack overflow".into());
        }
        self.stack.push(val);
        Ok(())
    }

    fn pop(&mut self) -> Result<WasmValue, String> {
        self.stack.pop().ok_or_else(|| "Stack underflow".into())
    }
}

fn main() {
    let mut vm = WasmVM::new();

    let mut functions = HashMap::new();
    // altitude_hold: param[0] - 50
    functions.insert("altitude_hold".to_string(), WasmFunction {
        name: "altitude_hold".into(),
        param_count: 1, local_count: 0,
        bytecode: vec![0x20, 0, 0x41, 50, 0x6B, 0x0F],
    });
    // add_test: 10 + 20
    functions.insert("add_test".into(), WasmFunction {
        name: "add_test".into(),
        param_count: 0, local_count: 0,
        bytecode: vec![0x41, 10, 0x41, 20, 0x6A, 0x0F],
    });

    let module = WasmModule { name: "drone_fw".into(), functions };
    vm.load_module(module);

    match vm.execute("drone_fw", "add_test", &[]) {
        Ok(Some(WasmValue::I32(v))) => println!("add_test = {}", v),
        Ok(v) => println!("add_test = {:?}", v),
        Err(e) => eprintln!("Error: {}", e),
    }

    match vm.execute("drone_fw", "altitude_hold", &[WasmValue::I32(45)]) {
        Ok(Some(WasmValue::I32(v))) => println!("altitude_hold(45) = {}", v),
        Ok(v) => println!("altitude_hold = {:?}", v),
        Err(e) => eprintln!("Error: {}", e),
    }

    println!("Steps: {}", vm.step_count);
}
