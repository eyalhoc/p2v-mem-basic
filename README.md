## 🧠 P2V-MEM IP – Basic Tier  
_Reduced feature set for open source version_

### ✅ Supported Features
- Intuitive specification of total virtual memory dimensions  
- Automatic calculation of memory rows and banks  
- Supports both flip-flop (FF) and library SRAM implementations  
- Flexible memory port configuration:  
  - Single or dual ports  
  - Each port independently configurable as:  
    - Read-only  
    - Write-only  
    - Read/Write  
- Clocking options: independent or shared per port  
- Bit-select and byte-select support  
- Attribute extraction from target library SRAM  
- Optional output sampling for post-processing  
- Built-in testbench tasks for quick verification:  
  - `read`  
  - `write`  
  - `load file`

---

### ❌ Unsupported Features  
_For enhanced capabilities, contact [Eyal Hochberg](mailto:eyalhoc@gmail.com)_  
- Tiling of heterogeneous SRAM blocks to match capacity constraints  
- Error-correcting code (ECC): 2-bit detection, 1-bit correction  
- ECC decoder path input/output sampling  
- Read-modify-write ECC byte access  
- AXI protocol interface  
- Concurrent multi-interface access for separate memory regions  

---

### ▶️ Quick Start
To build and test:  
```bash
bash build_basic.sh
