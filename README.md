## 🧠 P2V-MEM IP – Basic Tier

<<<<<<< HEAD
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
=======
This is the Basic Tier of the P2V-MEM IP. 
 
Features:<br>
	* simply specify dimentions of virtual memory (total memory) <br>
	* automatic calculation of row and bank numbers <br>
	* ff or library sram implemetation <br>
	* single or dual ports, each can be read, write or read and write <br>
	* same or different clocks for each port <br>
	* bit select and byte select <br>
	* attribute extraction from library sram <br>
	* optional sampling of output <br>
	* testbench tasks: read, write and load file <br>
 <br>
Unsupported features (contact Eyal Hochberg: eyalhoc@gmail.com for inquires) <br>
	* support tiling different srams for exact size matching <br>
	* hamming code error correction (ECC), two bit detection one bit correction <br>
	* supports optional sampling both input and output of ecc decoder <br>
	* ECC byte access by performing read-modify-write <br>
	* AXI bus interface <br>
	* multiple interfaces with simulatanious access to different parts of memory (different sram rows) <br>
 <br>
	
>>>>>>> f7bc5b50d7b5a348b4a9893317205af22467cac2
