## 🧠 P2V-MEM IP – Basic Tier

### ✅ Features
- Simplified specification of total virtual memory dimensions
- Automatic calculation of row and bank counts
- Supports flip-flop (FF) or library SRAM implementations
- Single or dual memory ports, each configurable as:
  - Read-only
  - Write-only
  - Read/Write
- Independent or shared clocking per port
- Bit-select and byte-select capabilities
- Attribute extraction from library SRAM
- Optional output sampling
- Built-in testbench tasks:
  - `read`
  - `write`
  - `load file`

### ❌ Unsupported Features  
_Contact [Eyal Hochberg](mailto:eyalhoc@gmail.com) for inquiries_
- Tiling heterogeneous SRAM blocks for exact capacity alignment
- Hamming code (ECC): 2-bit error detection, 1-bit correction
- Input/output sampling on ECC decoder path
- ECC byte access via read-modify-write cycles
- AXI bus interface support
- Multiple concurrent interfaces for independent memory regions (multi-row access)